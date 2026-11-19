import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.error

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from retarget_worker import retarget


class GeneratedLinks(unittest.TestCase):
    def test_deleted_shortcut_is_not_recreated_and_sharing_is_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);config=root/'worker.json';state=root/'state';state.mkdir()
            config.write_text(json.dumps({'files_url':'https://test-drive.example.net',
                'paperless_public_url':'https://test-dms.example.net','users':[{'email':'alex@example.net','files_token':'test-only'}]}))
            payload={'status':'done','document_id':7,'shared':False,
                'paperless_link':'https://dms.example.net/documents/7/details',
                'file':{'fid':'file-one','name':'sample.pdf','url':'https://drive.example.net/remote.php/dav/spaces/space/sample.pdf'}}
            with sqlite3.connect(state/'jobs.sqlite3') as db:
                db.execute('CREATE TABLE jobs (key TEXT PRIMARY KEY,payload TEXT NOT NULL)')
                db.execute('INSERT INTO jobs VALUES (?,?)',('alex@example.net|space|file-one',json.dumps(payload)))
            profile={'tier':'test','worker_config':str(config),'worker_state':str(state),
                'source_files_origins':['https://drive.example.net'],'source_dms_origins':['https://dms.example.net'],
                'dms_container':'test-dms'}
            calls=[]
            def missing(request,timeout):
                calls.append(request.get_method())
                raise urllib.error.HTTPError(request.full_url,404,'Missing',{},None)
            with patch('urllib.request.urlopen',side_effect=missing),patch('subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='0\n')):
                result=retarget(profile)
            self.assertEqual(calls,['GET'])
            self.assertEqual(result['absent_generated_links_preserved'],1)
            with sqlite3.connect(state/'jobs.sqlite3') as db:updated=json.loads(db.execute('SELECT payload FROM jobs').fetchone()[0])
            self.assertFalse(updated['shared']);self.assertEqual(updated['document_id'],7)
            self.assertEqual(updated['paperless_link'],'https://test-dms.example.net/documents/7/details')


if __name__=='__main__':unittest.main()
