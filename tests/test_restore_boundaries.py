import gzip
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from restore_test_data import restore,replace_tree,import_sql


class RestoreBoundaries(unittest.TestCase):
    def test_production_marker_is_refused_before_docker_or_data_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'.cloud-runtime.json').write_text(json.dumps({'instance':'production','tier':'production'}))
            with self.assertRaises(ValueError):restore({'runtime':str(root),'instance':'production','tier':'production'},root/'missing.tgz')

    def test_unapproved_replacement_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'target';target.mkdir();(target/'keep').write_text('original')
            with self.assertRaises(ValueError):replace_tree(root/'missing',target,set())
            self.assertEqual((target/'keep').read_text(),'original')

    def test_sql_pipe_receives_decompressed_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);compressed=root/'dump.gz';output=root/'received.sql'
            payload=b'SELECT 1;\n'*1024
            with gzip.open(compressed,'wb') as stream:stream.write(payload)
            import_sql([sys.executable,'-c','import pathlib,sys;pathlib.Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read())',str(output)],compressed)
            self.assertEqual(output.read_bytes(),payload)


if __name__=='__main__':unittest.main()
