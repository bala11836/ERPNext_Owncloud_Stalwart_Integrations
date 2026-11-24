"""The privileged worker must never follow an app-writable status symlink."""
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from test_refresh_worker import execute, publish_status


class StatusFiles(unittest.TestCase):
    def test_precreated_symlink_does_not_overwrite_its_target(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'private-target';target.write_text('unchanged')
            (root/'.status-forced').symlink_to(target)
            directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:
                with patch('test_refresh_worker.uuid.uuid4',return_value=SimpleNamespace(hex='forced')):
                    with self.assertRaises(FileExistsError):publish_status(directory,{'phase':'succeeded'})
            finally:os.close(directory)
            self.assertEqual(target.read_text(),'unchanged')
            self.assertFalse((root/'status.json').exists())


class RetiredCodeRequests(unittest.TestCase):
    def test_legacy_code_request_is_consumed_without_servicing_it(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            request = root / 'request.json'
            request.write_text(json.dumps({
                'request_id': 'fc87c16a-2e8f-4df7-8a84-920305a4bda0',
                'actor': 'admin@example.com',
                'kind': 'code',
            }))
            info = request.stat()
            app_stat = SimpleNamespace(st_mode=info.st_mode, st_size=info.st_size, st_uid=1000)
            with patch('test_refresh_worker.os.fstat', return_value=app_stat), \
                    patch('test_refresh_worker.restore') as restore:
                execute({'state_root': folder, 'request_directory': folder,
                         'allowed_users': ['admin@example.com']})
            self.assertFalse(request.exists())
            restore.assert_not_called()


if __name__=='__main__':unittest.main()
