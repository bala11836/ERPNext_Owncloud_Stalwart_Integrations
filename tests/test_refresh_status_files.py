"""The privileged worker must never follow an app-writable status symlink."""
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from test_refresh_worker import publish_status


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


if __name__=='__main__':unittest.main()
