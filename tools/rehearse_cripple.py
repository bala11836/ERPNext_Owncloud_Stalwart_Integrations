#!/usr/bin/env python3
"""Rehearse the crippled export on a TEST host, against copies of its own data.

Reads the test site's databases and files into a private scratch folder, runs
the same `cripple()` used by the production exporter, then audits the result:
identifiers seen in the originals (e-mail addresses, Indian mobile numbers, PAN,
GSTIN) that survive are counted per table, and Drive is checked for surviving
file names. Prints counts only, never values. Live test data is not changed;
the scratch folder is removed at the end.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from cripple_snapshot import cripple, unpack
from export_snapshot import inspect, mount, safe_copy, business_counts, sql_dump

TOKENS = re.compile(rb'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9.-]+|(?<![0-9])[6-9][0-9]{9}(?![0-9])|'
                    rb'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]|(?<![A-Z])[A-Z]{5}[0-9]{4}[A-Z](?![A-Z])')
TABLE = re.compile(rb'^INSERT INTO [`"]?([^`" ]+)[`"]?|^COPY (?:public\.)?([a-z_]+)')


def tokens_by_table(path):
    found = {}
    current = b'?'
    with open(path, 'rb') as stream:
        for line in stream:
            match = TABLE.match(line)
            if match:
                current = match.group(1) or match.group(2)
            for token in TOKENS.findall(line):
                found.setdefault(token.lower(), set()).add(current.decode(errors='replace'))
    return found


def drive_names(root):
    names = set()
    for file in Path(root).rglob('*.mpk'):
        if file.is_symlink():
            continue
        try:
            value = unpack(file.read_bytes()).get('user.ocis.name')
        except ValueError:
            continue
        if value and len(value) > 3:
            names.add(value)
    return names


def rehearse(config, keep_accounts, days):
    containers = config['containers']
    backend = inspect(containers['erp_backend'])
    if 'CLOUD_DEPLOYMENT_TIER=test' not in backend['Config']['Env']:
        raise SystemExit('Rehearsal runs only on a test site')
    sites = mount(containers['erp_backend'], '/home/frappe/frappe-bench/sites')
    site = sites / config['site']
    site_config = json.loads((site / 'site_config.json').read_text())
    if site_config.get('cloud_test_copy') is not True:
        raise SystemExit('Not a test copy')
    database = site_config['db_name']
    state = Path(config['state_root'])
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix='rehearse-cripple-', dir=state) as folder:
        data = Path(folder)
        mysql = ('export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mariadb-dump -uroot --single-transaction --routines '
                 '--triggers --hex-blob "$1"')
        sql_dump(['docker', 'exec', containers['erp_database'], 'sh', '-c', mysql, 'sh', database], data / 'erp.sql')
        postgres = ('export PGPASSWORD="$POSTGRES_PASSWORD"; exec pg_dump -U "$POSTGRES_USER" --no-owner --no-acl '
                    '"$POSTGRES_DB"')
        sql_dump(['docker', 'exec', containers['dms_database'], 'sh', '-c', postgres], data / 'dms.sql')
        for kind in ['public', 'private']:
            if (site / kind / 'files').exists():
                safe_copy(site / kind / 'files', data / 'erp-files' / kind)
        safe_copy(mount(containers['dms'], '/usr/src/paperless/media'), data / 'dms-media')
        safe_copy(mount(containers['dms'], '/usr/src/paperless/data'), data / 'dms-data')
        safe_copy(mount(containers['drive'], '/var/lib/ocis'), data / 'drive-data', exclude=['web/assets'],
                  allow_internal_links=True)
        (data / 'dms-consume').mkdir()
        (data / 'mail-data').mkdir()
        (data / 'document-enrollment.json').write_text(json.dumps({'users': []}) + '\n')
        before = {'erp': tokens_by_table(data / 'erp.sql'), 'dms': tokens_by_table(data / 'dms.sql')}
        names_before = drive_names(data / 'drive-data')
        blob_layout = None
        sample = next((m for m in (data / 'drive-data/storage/users/spaces').rglob('*.mpk')
                       if not m.is_symlink() and '.REV.' not in m.name
                       and unpack(m.read_bytes()).get('user.ocis.type') == b'1'), None)
        if sample is not None:
            from cripple_snapshot import split_id
            blobid = unpack(sample.read_bytes())['user.ocis.blobid'].decode()
            space = next(p for p in sample.parents if p.name == 'nodes').parent
            blob_layout = (space / 'blobs' / split_id(blobid)).is_file()
        counts_before = business_counts(containers, database)
        settings = {'cripple': {'enabled': True, 'days': days, 'keep_accounts': keep_accounts}}
        result = cripple(data, settings, containers, database, business_counts)
        keep = {account.casefold().encode() for account in keep_accounts}
        report = {'business_counts_before': counts_before, 'business_counts_after': result.pop('counts'),
                  'cripple': result, 'drive_blob_layout_confirmed': blob_layout}
        for name, path in [('erp', data / 'erp.sql'), ('dms', data / 'dms.sql')]:
            after = tokens_by_table(path)
            surviving = Counter()
            for token, tables in after.items():
                if token in before[name] and token not in keep:
                    for table in tables:
                        surviving[table] += 1
            report[f'{name}_identifiers_before'] = len(before[name])
            report[f'{name}_identifiers_surviving_by_table'] = dict(surviving.most_common(40))
        names_after = drive_names(data / 'drive-data')
        report['drive_names_before'] = len(names_before)
        report['drive_original_names_surviving'] = len(names_before & names_after)
        files = [p for p in (data / 'erp-files').rglob('*') if p.is_file()]
        report['erp_files_not_placeholders'] = sum(1 for p in files if not re.fullmatch(r'file-[0-9a-f]{16}(\.[a-z0-9]+)?', p.name))
        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, help='root-owned test refresh worker profile')
    parser.add_argument('--keep', action='append', default=[], help='account kept real (repeatable)')
    parser.add_argument('--days', type=int, default=60)
    args = parser.parse_args()
    os.umask(0o077)
    profile = Path(args.config)
    if profile.stat().st_uid != 0 or profile.stat().st_mode & 0o077:
        raise SystemExit('Configuration must be root-owned and private')
    config = json.loads(profile.read_text())
    if config.get('tier') != 'test':
        raise SystemExit('Test-only')
    print(json.dumps(rehearse(config, args.keep, args.days), indent=2, default=str))
