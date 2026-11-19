#!/usr/bin/env python3
"""Make the backup bucket tamper-resistant (P40).

`apply` (run with the storage ADMIN key, never stored on a server):
  - enables bucket versioning, so a delete only adds a delete marker and the
    previous object version stays recoverable;
  - adds a lifecycle rule that removes non-current versions after N days
    (default 30) and cleans up expired delete markers, so pruning still frees
    space eventually.

`policy` prints the user policy to attach to the source host's key in the
storage console: it may read, write, list and delete current objects (restic
needs that for locks and pruning) but may NOT delete object versions or change
versioning, lifecycle, policies or the bucket.

`verify` (run on the source host with its own key) uploads a canary object,
deletes it, and confirms the old version survives and cannot be deleted.

Uses a digest-pinned AWS CLI container; credentials come from an env file
(AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY) and are never printed.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid

CLI = 'amazon/aws-cli@sha256:6977c83ae3dc99f28fcf8276b9ea5eec33833cd5be40574b34112e98113ec7a2'
# Belt and braces: the Allow statements already omit these. RustFS rejects
# 's3:PutLifecycleConfiguration' as an unknown action (seen 19 November 2026),
# so it is not listed; lifecycle changes are refused because they are not allowed.
DENY = ['s3:DeleteObjectVersion', 's3:PutBucketVersioning',
        's3:PutBucketPolicy', 's3:DeleteBucketPolicy', 's3:DeleteBucket', 's3:PutBucketObjectLockConfiguration']


def policy(bucket):
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', bucket):
        raise ValueError('Invalid bucket name')
    arn = 'arn:aws:s3:::' + bucket
    return {'Version': '2012-10-17', 'Statement': [
        {'Effect': 'Allow', 'Action': ['s3:GetBucketLocation', 's3:ListBucket', 's3:ListBucketVersions'],
         'Resource': [arn]},
        {'Effect': 'Allow', 'Action': ['s3:GetObject', 's3:PutObject', 's3:DeleteObject'],
         'Resource': [arn + '/*']},
        {'Effect': 'Deny', 'Action': DENY, 'Resource': [arn, arn + '/*']}]}


def lifecycle(days):
    if not 1 <= days <= 365:
        raise ValueError('Keep non-current versions between 1 and 365 days')
    return {'Rules': [{'ID': 'cloud-backup-noncurrent', 'Status': 'Enabled', 'Filter': {'Prefix': ''},
                       'NoncurrentVersionExpiration': {'NoncurrentDays': days},
                       'Expiration': {'ExpiredObjectDeleteMarker': True}}]}


def aws(endpoint, env_file, *args, mount=None):
    # stdin is never passed through: piped uploads fail in the CLI (it needs a
    # seekable file) and an inherited stdin could swallow a calling script.
    extra = ['-v', mount + ':/canary.txt:ro'] if mount else []
    command = ['docker', 'run', '--rm', '--network', 'host', '--env-file', env_file, *extra,
               '-e', 'AWS_DEFAULT_REGION=us-east-1', CLI, '--endpoint-url', endpoint, '--output', 'json', *args]
    return subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, text=True)


def apply(endpoint, env_file, bucket, days):
    steps = {}
    result = aws(endpoint, env_file, 's3api', 'put-bucket-versioning', '--bucket', bucket,
                 '--versioning-configuration', 'Status=Enabled')
    steps['versioning'] = 'enabled' if result.returncode == 0 else 'failed: ' + result.stderr.strip()[:200]
    status = aws(endpoint, env_file, 's3api', 'get-bucket-versioning', '--bucket', bucket)
    steps['versioning_status'] = (json.loads(status.stdout or '{}').get('Status') if status.returncode == 0
                                  else 'unreadable')
    result = aws(endpoint, env_file, 's3api', 'put-bucket-lifecycle-configuration', '--bucket', bucket,
                 '--lifecycle-configuration', json.dumps(lifecycle(days)))
    steps['lifecycle'] = 'set' if result.returncode == 0 else 'failed: ' + result.stderr.strip()[:200]
    return steps


def verify(endpoint, env_file, bucket):
    """Prove with the source host's key: writes work, a delete only hides the
    object, the hidden version survives and cannot be deleted, and versioning
    cannot be switched off. Survival is checked through the version list,
    which the key may read (it may not read old versions themselves)."""
    key = 'p40-canary/' + uuid.uuid4().hex
    report = {}
    with tempfile.NamedTemporaryFile('w', suffix='.txt') as canary:
        canary.write('canary\n')
        canary.flush()
        os.chmod(canary.name, 0o644)
        put = aws(endpoint, env_file, 's3api', 'put-object', '--bucket', bucket, '--key', key,
                  '--body', '/canary.txt', mount=canary.name)
    report['write'] = put.returncode == 0
    version = json.loads(put.stdout or '{}').get('VersionId')
    report['versioned'] = bool(version) and version != 'null'
    delete = aws(endpoint, env_file, 's3api', 'delete-object', '--bucket', bucket, '--key', key)
    report['delete_current_hides_it'] = delete.returncode == 0 and json.loads(delete.stdout or '{}').get('DeleteMarker') is True
    if report['versioned']:
        purge = aws(endpoint, env_file, 's3api', 'delete-object', '--bucket', bucket, '--key', key,
                    '--version-id', version)
        report['version_delete_denied'] = purge.returncode != 0
        listing = aws(endpoint, env_file, 's3api', 'list-object-versions', '--bucket', bucket, '--prefix', key)
        versions = json.loads(listing.stdout or '{}').get('Versions', []) if listing.returncode == 0 else []
        report['old_version_survives'] = any(v.get('VersionId') == version for v in versions)
    suspend = aws(endpoint, env_file, 's3api', 'put-bucket-versioning', '--bucket', bucket,
                  '--versioning-configuration', 'Status=Suspended')
    report['versioning_change_denied'] = suspend.returncode != 0
    report['protected'] = all(report.get(name) for name in
        ['write', 'versioned', 'delete_current_hides_it', 'version_delete_denied', 'old_version_survives',
         'versioning_change_denied'])
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['apply', 'policy', 'verify'])
    parser.add_argument('--bucket', required=True)
    parser.add_argument('--endpoint')
    parser.add_argument('--env-file')
    parser.add_argument('--noncurrent-days', type=int, default=30)
    args = parser.parse_args()
    if args.command == 'policy':
        print(json.dumps(policy(args.bucket), indent=2))
        sys.exit(0)
    if not args.endpoint or not args.env_file:
        raise SystemExit('--endpoint and --env-file are required')
    result = (apply(args.endpoint, args.env_file, args.bucket, args.noncurrent_days) if args.command == 'apply'
              else verify(args.endpoint, args.env_file, args.bucket))
    print(json.dumps(result, indent=2))
    if args.command == 'verify' and not result['protected']:
        sys.exit(1)
