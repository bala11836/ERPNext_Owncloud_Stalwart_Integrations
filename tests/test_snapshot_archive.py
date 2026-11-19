import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from snapshot_archive import validate_extract


class SnapshotBoundary(unittest.TestCase):
    def archive(self,root,extra=None,corrupt=False,source='production',links=None,directories=None):
        files={'erp.sql.gz':b'erp','dms.sql.gz':b'dms','drive-runtime.private.yaml':b'private'}
        if extra:files.update(extra)
        manifest={'format':1,'source_instance':source,'code_included':False,'identity_database_included':False,
                  'files':{name:{'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()} for name,value in files.items()}}
        manifest.update(links=links or {},directories=directories or [])
        if corrupt:manifest['files']['erp.sql.gz']['sha256']='0'*64
        files['manifest.json']=json.dumps(manifest).encode()
        archive=root/'snapshot.tgz'
        with tarfile.open(archive,'w:gz') as stream:
            for name,value in files.items():
                member=tarfile.TarInfo(name);member.size=len(value);stream.addfile(member,io.BytesIO(value))
        return archive

    def test_valid_data_only_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);manifest=validate_extract(self.archive(root),root/'out','production')
            self.assertEqual(manifest['source_instance'],'production')
            self.assertEqual((root/'out/erp.sql.gz').read_bytes(),b'erp')

    def test_native_internal_links_and_empty_directories_survive(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            archive=self.archive(root,extra={'drive-data/storage/nodes/a/metadata':b'node'},
                links={'drive-data/storage/refs/current':'../nodes/a'},
                directories=['drive-data/storage/nodes/a/children'])
            validate_extract(archive,root/'out','production')
            self.assertTrue((root/'out/drive-data/storage/nodes/a/children').is_dir())
            link=root/'out/drive-data/storage/refs/current'
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(),root/'out/drive-data/storage/nodes/a')

    def test_rejects_external_chained_and_parent_link_escapes(self):
        cases=[({'drive-data/bad':'/etc/passwd'},{}),
               ({'drive-data/bad':'../../outside'},{}),
               ({'drive-data/a':'.','drive-data/bad':'a/../outside'},{}),
               ({'drive-data/a':'.'},{'drive-data/a/file':b'not allowed'}),
               ({'drive-data/loop':'loop'}, {})]
        for links,extra in cases:
            with self.subTest(links=links),tempfile.TemporaryDirectory() as folder:
                root=Path(folder)
                with self.assertRaises(ValueError):validate_extract(self.archive(root,extra=extra,links=links),root/'out','production')
                self.assertFalse((root/'out').exists())

    def test_rejects_paths_code_checksum_wrong_source_and_budget_before_extracting(self):
        cases=[{'extra':{'../escape':b'x'}},{'extra':{'drive-data/web/assets/app.js':b'x'}},
               {'extra':{'application.py':b'x'}},{'corrupt':True},{'source':'other'}]
        for case in cases:
            with self.subTest(case=case),tempfile.TemporaryDirectory() as folder:
                root=Path(folder)
                with self.assertRaises(ValueError):validate_extract(self.archive(root,**case),root/'out','production')
                self.assertFalse((root/'out').exists())
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with self.assertRaises(ValueError):validate_extract(self.archive(root),root/'out','production',max_bytes=1)


if __name__=='__main__':unittest.main()
