#!/usr/bin/env python3
"""Turn a restored production backup into a four-app refresh snapshot (P39).

The nightly Restic backup holds production's raw layout: all-database dumps,
the briefly stopped Drive and Mail stores and the live-copied paths. The test
loader (`restore_test_data.py`) accepts only the checksummed snapshot archive
written by `export_snapshot.py`. This tool builds that same archive from a
restored backup directory, so a disaster-recovery rehearsal (or a real
recovery onto a test-tier stack) reuses the tested loading path.

It runs on the recovery host, never contacts production, and imports the
dumps only into throwaway, network-less, digest-pinned database containers
that it removes afterwards. Like the exporter it leaves out the sign-in
database, ERP site configuration and application code.

  backup_to_snapshot.py --config C.private.json
"""
import argparse
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_snapshot import safe_copy, tree_manifest  # noqa: E402

DIGEST = re.compile(r'[a-z0-9./_-]+@sha256:[0-9a-f]{64}')
LAYOUT_KEYS = ('erp_sites', 'dms_root', 'drive_data', 'drive_config', 'mail_data',
               'mail_config', 'worker_state', 'worker_config')
ERP_DUMP = ('export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mariadb-dump -uroot --single-transaction '
            '--routines --triggers --hex-blob --ignore-table-data="$1.__Auth" '
            '--ignore-table-data="$1.tabSessions" --ignore-table-data="$1.tabOAuth Bearer Token" '
            '--ignore-table-data="$1.tabOAuth Authorization Code" "$1"')
DMS_DUMP = ('export PGPASSWORD="$POSTGRES_PASSWORD"; exec pg_dump -U "$POSTGRES_USER" --no-owner --no-acl '
            '--exclude-table-data=public.django_session --exclude-table-data=public.authtoken_token '
            '--exclude-table-data=public.socialaccount_socialtoken "$POSTGRES_DB"')


def validate(config):
    root = Path(config['restore_root'])
    if not root.is_absolute() or len(root.parts) < 3:
        raise ValueError('restore_root must be an absolute private directory')
    for kind in ('mariadb', 'postgres'):
        if not DIGEST.fullmatch(config['images'][kind]):
            raise ValueError('Database images must be pinned by digest')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', config['erp_site']):
        raise ValueError('Invalid ERP site name')
    layout = config['layout']
    for key in LAYOUT_KEYS:
        relative = Path(layout[key])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Layout paths are relative to restore_root: ' + key)
    if not re.fullmatch(r'[A-Za-z0-9_-]+', config['source_instance']):
        raise ValueError('Invalid source instance')
    return root


def throwaway(kind, image, name, password, database=None):
    if kind == 'mariadb':
        env = ['-e', 'MARIADB_ROOT_PASSWORD=' + password, '-e', 'MYSQL_ROOT_PASSWORD=' + password]
    else:
        env = ['-e', 'POSTGRES_PASSWORD=' + password, '-e', 'POSTGRES_USER=postgres']
        if database:
            env += ['-e', 'POSTGRES_DB=' + database]
    return ['docker', 'run', '-d', '--rm', '--network', 'none', '--name', name, *env, image]


def wait_ready(kind, name):
    probe = (['docker', 'exec', name, 'sh', '-c', 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mariadb -uroot -e "select 1"']
             if kind == 'mariadb' else ['docker', 'exec', name, 'pg_isready', '-U', 'postgres'])
    for _ in range(90):
        if subprocess.run(probe, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            return
        time.sleep(2)
    raise RuntimeError('Throwaway database did not start')


def load(name, importer, dump):
    with dump.open('rb') as data:
        subprocess.run(['docker', 'exec', '-i', name, *importer], stdin=data, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def dump_gz(name, command, output, *args):
    with tempfile.TemporaryFile() as raw:
        subprocess.run(['docker', 'exec', name, 'sh', '-c', command, 'sh', *args], stdout=raw, check=True,
                       stderr=subprocess.DEVNULL)
        raw.seek(0)
        with gzip.open(output, 'wb', compresslevel=6) as target:
            shutil.copyfileobj(raw, target)


def dms_database(name):
    names = subprocess.check_output(['docker', 'exec', name, 'psql', '-U', 'postgres', '-At', '-c',
        "select datname from pg_database where not datistemplate"], text=True).split()
    for database in names:
        found = subprocess.run(['docker', 'exec', name, 'psql', '-U', 'postgres', '-d', database, '-At', '-c',
            "select to_regclass('public.documents_document') is not null"], capture_output=True, text=True)
        if found.stdout.strip() == 't':
            return database
    raise RuntimeError('No DMS database in the restored dump')


def convert(config):
    root = validate(config)
    layout = {key: root / value for key, value in config['layout'].items()}
    site = layout['erp_sites'] / config['erp_site']
    database = json.loads((site / 'site_config.json').read_text())['db_name']
    if not re.fullmatch(r'[A-Za-z0-9_]+', database):
        raise ValueError('Invalid ERP database name')
    output = Path(config['output'])
    work = Path(config['work_root'])
    work.mkdir(parents=True, exist_ok=True, mode=0o700)
    token = secrets.token_hex(3)
    erp, dms = 'p39-snapshot-erp-' + token, 'p39-snapshot-dms-' + token
    with tempfile.TemporaryDirectory(prefix='snapshot-', dir=work) as temporary:
        data = Path(temporary)
        try:
            password = secrets.token_urlsafe(18)
            subprocess.run(throwaway('mariadb', config['images']['mariadb'], erp, password), check=True,
                           stdout=subprocess.DEVNULL)
            subprocess.run(throwaway('postgres', config['images']['postgres'], dms, password), check=True,
                           stdout=subprocess.DEVNULL)
            wait_ready('mariadb', erp)
            wait_ready('postgres', dms)
            dumps = root / 'staging' / 'databases'
            load(erp, ['sh', '-c', 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mariadb -uroot'], dumps / 'erp.sql')
            load(dms, ['psql', '-U', 'postgres', '-q', '-v', 'ON_ERROR_STOP=0'], dumps / 'dms.sql')
            dms_db = dms_database(dms)
            # The exporter's dump commands read POSTGRES_DB from the container.
            dump_gz(erp, ERP_DUMP, data / 'erp.sql.gz', database)
            dump_gz(dms, 'export POSTGRES_DB=' + dms_db + '; ' + DMS_DUMP, data / 'dms.sql.gz')
            counts = _counts(erp, dms, database, dms_db)
        finally:
            subprocess.run(['docker', 'rm', '-f', erp, dms], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for kind in ('public', 'private'):
            directory = site / kind / 'files'
            if directory.exists():
                safe_copy(directory, data / 'erp-files' / kind)
        for name in ('media', 'data', 'consume'):
            safe_copy(layout['dms_root'] / name, data / ('dms-' + name))
        safe_copy(layout['drive_data'], data / 'drive-data', exclude=['web/assets'], allow_internal_links=True)
        safe_copy(layout['mail_data'], data / 'mail-data')
        safe_copy(layout['mail_config'], data / 'mail-config')
        shutil.copy2(layout['drive_config'] / 'ocis.yaml', data / 'drive-runtime.private.yaml')
        jobs = layout['worker_state'] / 'jobs.sqlite3'
        if jobs.exists():
            shutil.copy2(jobs, data / 'document-jobs.sqlite3')
        enrollment = json.loads(layout['worker_config'].read_text())
        public = {key: enrollment[key] for key in ('office_space_id', 'office_processor')}
        public['users'] = [{'email': user['email']} for user in enrollment['users']]
        (data / 'document-enrollment.json').write_text(json.dumps(public) + '\n')
        manifest = {'format': 1, 'source_instance': config['source_instance'],
                    'snapshot_id': 'backup-' + config['backup_snapshot'],
                    'exported_at': config['backup_time'], 'maintenance_seconds': 0,
                    'source': 'restic-backup', 'converted_at': datetime.now(timezone.utc).isoformat(),
                    **tree_manifest(data), 'counts': counts,
                    'code_included': False, 'identity_database_included': False}
        (data / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        partial = output.with_name(output.name + '.partial')
        with tarfile.open(partial, 'w:gz') as archive:
            for file in sorted(data.rglob('*')):
                if file.is_file() and not file.is_symlink():
                    archive.add(file, arcname=str(file.relative_to(data)), recursive=False)
        partial.chmod(0o600)
        os.replace(partial, output)
    return {key: value for key, value in manifest.items() if key not in ('files', 'links', 'directories')}


def _counts(erp, dms, database, dms_db):
    """The exporter's business counts (same tables and queries as
    export_snapshot.business_counts), read from the throwaway databases."""
    tables = ['tabUser', 'tabCompany', 'tabFile', 'tabSupplier', 'tabEmployee', 'tabPurchase Order', 'tabSales Invoice']
    def mysql(sql):
        return int(subprocess.check_output(['docker', 'exec', erp, 'sh', '-c',
            'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mariadb -N -B -uroot "$1" -e "$2"', 'sh', database, sql],
            text=True, stderr=subprocess.DEVNULL).strip())
    counts = {table: mysql('SELECT COUNT(*) FROM `' + table + '`') for table in tables}
    uploaded = mysql('SELECT COUNT(*) FROM `tabFile` WHERE is_folder=0')
    documents = int(subprocess.check_output(['docker', 'exec', dms, 'psql', '-U', 'postgres', '-d', dms_db, '-At',
        '-c', 'SELECT COUNT(*) FROM documents_document'], text=True).strip())
    return {'erp': counts, 'erp_uploaded_files': uploaded, 'dms_documents': documents}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    path = Path(parser.parse_args().config)
    os.umask(0o077)
    if path.stat().st_uid != 0 or path.stat().st_mode & 0o077:
        raise SystemExit('Config must be root-owned and private')
    print(json.dumps(convert(json.loads(path.read_text())), indent=2))
