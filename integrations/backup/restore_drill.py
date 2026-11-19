#!/usr/bin/env python3
"""Restore drill: prove the latest backup can be restored (P02).

Runs as root on the TEST host with a READ-ONLY storage key and `--no-lock`; it
never contacts the backed-up host. Restores the latest snapshot into a scratch
directory, imports every database dump into a throwaway, network-less
database container, counts tables and files, then removes everything it made.

  restore_drill.py --profile P
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backup import DIGEST, restic, validate  # noqa: E402


def throwaway(kind, image, name, password):
    env = ['-e', 'MARIADB_ROOT_PASSWORD=' + password] if kind == 'mariadb' else ['-e', 'POSTGRES_PASSWORD=' + password]
    return ['docker', 'run', '-d', '--rm', '--network', 'none', '--name', name, *env, image]


def wait_ready(kind, name, password, run=subprocess.run):
    probe = (['docker', 'exec', '-e', 'MYSQL_PWD=' + password, name, 'mariadb', '-uroot', '-e', 'select 1']
             if kind == 'mariadb' else ['docker', 'exec', name, 'pg_isready', '-U', 'postgres'])
    for _ in range(90):
        if run(probe, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0: return
        time.sleep(2)
    raise RuntimeError('Throwaway database did not start')


def count_tables(kind, name, password):
    if kind == 'mariadb':
        sql = ("select count(*) from information_schema.tables where table_schema not in "
               "('mysql','information_schema','performance_schema','sys')")
        out = subprocess.check_output(['docker', 'exec', '-e', 'MYSQL_PWD=' + password, name, 'mariadb', '-uroot', '-N', '-e', sql])
    else:
        sql = "select count(*) from information_schema.tables where table_schema='public'"
        out = subprocess.check_output(['docker', 'exec', name, 'sh', '-c',
            'for d in $(psql -U postgres -At -c "select datname from pg_database where not datistemplate"); do '
            'psql -U postgres -d "$d" -At -c "' + sql + '"; done'])
    return sum(int(x) for x in out.decode().split())


def drill(profile):
    scratch = Path(profile['scratch'])
    validate(dict(profile, tier='test', staging=profile.get('staging', str(scratch))))
    if scratch.exists(): shutil.rmtree(scratch)
    scratch.mkdir(parents=True, mode=0o700)
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'databases': {}}
    try:
        subprocess.run(_restore_argv(profile, scratch), check=True, stdout=subprocess.DEVNULL)
        root = scratch / 'backup'
        report['files_restored'] = sum(1 for p in root.rglob('*') if p.is_file())
        for dump in sorted((root / 'staging' / 'databases').glob('*.sql')):
            kind = profile['database_kinds'][dump.stem]
            image = profile['images'][kind]
            if not DIGEST.fullmatch(image): raise ValueError('Drill database images must be pinned')
            name = 'restore-drill-' + dump.stem + '-' + secrets.token_hex(3)
            password = secrets.token_urlsafe(18)
            subprocess.run(throwaway(kind, image, name, password), check=True, stdout=subprocess.DEVNULL)
            try:
                wait_ready(kind, name, password)
                importer = (['docker', 'exec', '-i', '-e', 'MYSQL_PWD=' + password, name, 'mariadb', '-uroot']
                            if kind == 'mariadb' else ['docker', 'exec', '-i', name, 'psql', '-U', 'postgres', '-q', '-v', 'ON_ERROR_STOP=0'])
                with dump.open('rb') as data:
                    subprocess.run(importer, stdin=data, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                report['databases'][dump.stem] = {'kind': kind, 'bytes': dump.stat().st_size,
                                                  'tables': count_tables(kind, name, password)}
            finally:
                subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        minimum = profile.get('minimum_tables', {})
        short = {k: v['tables'] for k, v in report['databases'].items() if v['tables'] < minimum.get(k, 1)}
        report['result'] = 'passed' if report['databases'] and not short else 'failed'
        if short: report['too_few_tables'] = short
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
    return report


def _restore_argv(profile, scratch):
    argv = restic(profile, ['restore', 'latest', '--no-lock', '--target', '/restore'])
    image = argv.index(profile['restic_image'])
    return argv[:image] + ['-v', str(scratch) + ':/restore'] + argv[image:]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--profile', required=True)
    path = Path(parser.parse_args().profile); os.umask(0o077)
    if path.stat().st_uid != 0 or path.stat().st_mode & 0o077: raise SystemExit('Profile must be root-owned and private')
    result = drill(json.loads(path.read_text()))
    state = Path(json.loads(path.read_text())['state']); state.mkdir(parents=True, exist_ok=True, mode=0o700)
    (state / 'last-drill.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    if result['result'] != 'passed': raise SystemExit(1)
