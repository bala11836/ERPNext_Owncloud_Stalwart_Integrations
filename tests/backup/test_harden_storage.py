"""P40: production may add and prune backups but never destroy old versions."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'integrations/backup'))
import harden_storage as h  # noqa: E402


class HardenStorageTests(unittest.TestCase):
    def test_policy_denies_destroying_history(self):
        document = h.policy('company-backups')
        deny = [s for s in document['Statement'] if s['Effect'] == 'Deny'][0]
        for action in ['s3:DeleteObjectVersion', 's3:PutBucketVersioning', 's3:PutBucketPolicy', 's3:DeleteBucket']:
            self.assertIn(action, deny['Action'])
        allowed = [a for s in document['Statement'] if s['Effect'] == 'Allow' for a in s['Action']]
        # restic still needs to remove its locks and prune (delete markers only).
        self.assertIn('s3:DeleteObject', allowed)
        self.assertNotIn('s3:DeleteObjectVersion', allowed)
        with self.assertRaises(ValueError):
            h.policy('Bad_Bucket!')

    def test_lifecycle_keeps_history_for_the_chosen_days(self):
        rule = h.lifecycle(30)['Rules'][0]
        self.assertEqual(rule['NoncurrentVersionExpiration'], {'NoncurrentDays': 30})
        for days in (0, 400):
            with self.assertRaises(ValueError):
                h.lifecycle(days)

    def test_policy_uses_only_actions_rustfs_accepts(self):
        # RustFS rejected the whole policy over this unknown action name.
        self.assertNotIn('s3:PutLifecycleConfiguration', h.DENY)
        allowed = [a for s in h.policy('b-ucket')['Statement'] if s['Effect'] == 'Allow' for a in s['Action']]
        self.assertNotIn('s3:PutLifecycleConfiguration', allowed)

    def test_verify_never_pipes_stdin(self):
        source = (ROOT / 'integrations/backup/harden_storage.py').read_text()
        self.assertIn('stdin=subprocess.DEVNULL', source)
        self.assertNotIn("'/dev/stdin'", source)
        self.assertIn("'list-object-versions'", source)

    def test_cli_is_pinned_and_credentials_come_from_a_file(self):
        self.assertRegex(h.CLI, r'@sha256:[0-9a-f]{64}$')
        source = (ROOT / 'integrations/backup/harden_storage.py').read_text()
        self.assertIn("'--env-file', env_file", source)
        self.assertNotIn('AWS_SECRET_ACCESS_KEY=', source)


if __name__ == '__main__':
    unittest.main()
