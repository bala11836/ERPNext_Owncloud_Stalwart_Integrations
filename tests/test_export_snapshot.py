"""Production export keeps the maintenance pause short (P33, 18 November 2026).

The first VM refresh was refused: all copying and gzip happened inside the
pause and it exceeded the 100-second consistency window. Files are now copied
first while production runs, then only the changes during the pause; dumps
are written raw in the pause and compressed after production resumes; the
restart watchdog is armed only just before the pause.
"""
import gzip
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import export_snapshot as ex  # noqa: E402


class SafeCopyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.src, self.dst = base / 'src', base / 'dst'
        (self.src / 'a').mkdir(parents=True)
        (self.src / 'a' / 'one.txt').write_text('one')
        (self.src / 'two.txt').write_text('two')

    def tearDown(self):
        self.tmp.cleanup()

    def test_second_pass_copies_only_changes_and_mirrors_deletions(self):
        ex.safe_copy(self.src, self.dst)
        kept = self.dst / 'a' / 'one.txt'
        marker = os.stat(kept).st_ino
        (self.src / 'two.txt').write_text('changed!')
        (self.src / 'three.txt').write_text('new')
        (self.src / 'a' / 'one.txt').touch()  # same size, new mtime -> recopied
        os.utime(self.src / 'a' / 'one.txt', ns=(os.stat(kept).st_atime_ns, os.stat(kept).st_mtime_ns))
        (self.src / 'gone').mkdir(); (self.src / 'gone' / 'x').write_text('x')
        ex.safe_copy(self.src, self.dst)
        (self.src / 'gone' / 'x').unlink(); (self.src / 'gone').rmdir()
        ex.safe_copy(self.src, self.dst)
        self.assertEqual(os.stat(kept).st_ino, marker, 'unchanged file not recopied')
        self.assertEqual((self.dst / 'two.txt').read_text(), 'changed!')
        self.assertEqual((self.dst / 'three.txt').read_text(), 'new')
        self.assertFalse((self.dst / 'gone').exists(), 'deleted source entries removed')
        self.assertEqual(ex.tree_manifest(self.src)['files'], ex.tree_manifest(self.dst)['files'])

    def test_external_symlinks_still_refused(self):
        (self.src / 'evil').symlink_to('/etc/passwd')
        with self.assertRaises(RuntimeError):
            ex.safe_copy(self.src, self.dst, allow_internal_links=True)

    def test_compress_after_resume_keeps_archive_name(self):
        raw = Path(self.tmp.name) / 'erp.sql'
        raw.write_bytes(b'SELECT 1;\n' * 100)
        zipped = ex.compress(raw)
        self.assertEqual(zipped.name, 'erp.sql.gz')
        self.assertFalse(raw.exists())
        self.assertEqual(gzip.decompress(zipped.read_bytes()), b'SELECT 1;\n' * 100)


class OrderTests(unittest.TestCase):
    def test_bulk_copy_before_pause_watchdog_just_before_stop_compress_after_start(self):
        source = (ROOT / 'tools/export_snapshot.py').read_text()
        body = source[source.index('def export(config):'):]
        first_copy = body.index('copy_files()\n            # Arm')
        watchdog = body.index("'systemd-run'")
        stop = body.index("'docker','stop'")
        second_copy = body.index('copy_files()', stop)
        start = body.index("'docker','start'")
        compress = body.index("compress(data/name)")
        self.assertLess(first_copy, watchdog)
        self.assertLess(watchdog, stop)
        self.assertLess(stop, second_copy)
        self.assertLess(second_copy, start)
        self.assertLess(start, compress)
        self.assertNotIn('GzipFile', source[source.index('def sql_dump'):source.index('def compress')])


if __name__ == '__main__':
    unittest.main(verbosity=2)
