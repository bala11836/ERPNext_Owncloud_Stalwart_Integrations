"""P39: a restored backup becomes the same snapshot archive the exporter writes."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import backup_to_snapshot as b  # noqa: E402
import snapshot_archive  # noqa: E402

SOURCE = (ROOT / 'tools/backup_to_snapshot.py').read_text()
EXPORTER = (ROOT / 'tools/export_snapshot.py').read_text()
PINNED = {'mariadb': 'mariadb@sha256:' + 'a' * 64, 'postgres': 'postgres@sha256:' + 'b' * 64}


def config(**changes):
    value = {'restore_root': '/data/p39/restore/backup', 'images': dict(PINNED), 'erp_site': 'erp.internal',
             'source_instance': 'production', 'layout': {key: 'x/' + key for key in b.LAYOUT_KEYS}}
    value.update(changes)
    return value


class BackupToSnapshotTests(unittest.TestCase):
    def test_validation(self):
        b.validate(config())
        with self.assertRaises(ValueError):
            b.validate(config(images={'mariadb': 'mariadb:latest', 'postgres': PINNED['postgres']}))
        with self.assertRaises(ValueError):
            b.validate(config(layout={**{k: 'x' for k in b.LAYOUT_KEYS}, 'drive_data': '/etc'}))
        with self.assertRaises(ValueError):
            b.validate(config(layout={**{k: 'x' for k in b.LAYOUT_KEYS}, 'mail_data': '../x'}))
        with self.assertRaises(ValueError):
            b.validate(config(erp_site='../site'))

    def test_dumps_match_the_exporter(self):
        # Same data exclusions as the live exporter: no sessions or tokens.
        self.assertIn(b.ERP_DUMP, EXPORTER)
        self.assertIn(b.DMS_DUMP, EXPORTER)

    def test_counts_match_the_exporter(self):
        exporter = re.search(r"tables=\[([^\]]*)\]", EXPORTER).group(1)
        mine = re.search(r"tables = \[([^\]]*)\]", SOURCE).group(1)
        self.assertEqual([t.strip(" '") for t in exporter.split(',')], [t.strip(" '") for t in mine.split(',')])
        self.assertIn("'SELECT COUNT(*) FROM `tabFile` WHERE is_folder=0'", SOURCE)

    def test_archive_content_is_what_the_loader_accepts(self):
        for name in ['erp.sql.gz', 'dms.sql.gz', 'drive-runtime.private.yaml', 'document-jobs.sqlite3',
                     'document-enrollment.json']:
            self.assertIn(name, snapshot_archive.FILES)
            self.assertIn("'" + name + "'", SOURCE)
        for name in ['erp-files', 'dms-media', 'dms-data', 'dms-consume', 'drive-data', 'mail-data', 'mail-config']:
            self.assertIn(name, snapshot_archive.DIRECTORIES)
        self.assertIn("'code_included': False, 'identity_database_included': False", SOURCE)
        self.assertIn("exclude=['web/assets']", SOURCE)

    def test_throwaway_databases_have_no_network(self):
        self.assertIn("'--network', 'none'", SOURCE)
        self.assertIn("subprocess.run(['docker', 'rm', '-f', erp, dms]", SOURCE)


if __name__ == '__main__':
    unittest.main()
