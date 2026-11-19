#!/usr/bin/env python3
"""Rehearse four-app restore ONLY on a fresh test without business documents.

No production SSH is used. A private snapshot of the empty test stores exercises
SQL import, target backup, quarantine, native bootstrap and fresh credentials.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import uuid

from export_snapshot import inspect,mount,safe_copy,sql_dump,business_counts,tree_manifest
from restore_test_data import restore
from test_refresh_worker import private_profile


def rehearse(config):
    c=config['containers']
    sites=mount(c['erp_backend'],'/home/frappe/frappe-bench/sites');site=sites/config['site']
    settings=json.loads((site/'site_config.json').read_text())
    if config['tier']!='test' or settings.get('cloud_test_copy') is not True:
        raise ValueError('Rehearsal is restricted to fresh test data')
    counts=business_counts(c,settings['db_name'])
    if (counts['dms_documents'] or counts['erp_uploaded_files']
            or any(n for table,n in counts['erp'].items() if table not in {'tabUser','tabFile'})
            or counts['erp']['tabUser']>3):
        raise ValueError('Test contains business data; empty-test rehearsal refused')
    state=Path(config['state_root']);state.mkdir(parents=True,exist_ok=True,mode=0o700)
    with tempfile.TemporaryDirectory(prefix='rehearsal-',dir=state) as temporary:
        root=Path(temporary);data=root/'data';data.mkdir()
        selected=[name for name in config['application_containers'] if inspect(name)['State']['Running']]
        try:
            subprocess.run(['docker','stop','--time','25',*selected],check=True,stdout=subprocess.DEVNULL)
            mysql='export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mariadb-dump -uroot --single-transaction --routines --triggers --hex-blob --ignore-table-data="$1.__Auth" --ignore-table-data="$1.tabSessions" --ignore-table-data="$1.tabOAuth Bearer Token" --ignore-table-data="$1.tabOAuth Authorization Code" "$1"'
            sql_dump(['docker','exec',c['erp_database'],'sh','-c',mysql,'sh',settings['db_name']],data/'erp.sql.gz')
            postgres='export PGPASSWORD="$POSTGRES_PASSWORD"; exec pg_dump -U "$POSTGRES_USER" --no-owner --no-acl --exclude-table-data=public.django_session --exclude-table-data=public.authtoken_token --exclude-table-data=public.socialaccount_socialtoken "$POSTGRES_DB"'
            sql_dump(['docker','exec',c['dms_database'],'sh','-c',postgres],data/'dms.sql.gz')
            for name,target in [('dms-media','/usr/src/paperless/media'),('dms-data','/usr/src/paperless/data'),('dms-consume','/usr/src/paperless/consume')]:
                safe_copy(mount(c['dms'],target),data/name)
            for kind in ['public','private']:
                source=site/kind/'files'
                if source.exists():safe_copy(source,data/'erp-files'/kind)
            safe_copy(mount(c['drive'],'/var/lib/ocis'),data/'drive-data',exclude=['web/assets'],allow_internal_links=True)
            shutil.copy2(mount(c['drive'],'/etc/ocis')/'ocis.yaml',data/'drive-runtime.private.yaml')
            safe_copy(mount(c['mail'],'/var/lib/stalwart'),data/'mail-data')
            safe_copy(mount(c['mail'],'/etc/stalwart'),data/'mail-config')
            (data/'document-enrollment.json').write_text(json.dumps({'office_space_id':'','office_processor':'','users':[]}))
        finally:
            subprocess.run(['docker','start',*selected],check=True,stdout=subprocess.DEVNULL)
        contents=tree_manifest(data)
        manifest={'format':1,'source_instance':'rehearsal','snapshot_id':str(uuid.uuid4()),
            'exported_at':datetime.now(timezone.utc).isoformat(),**contents,'counts':counts,
            'code_included':False,'identity_database_included':False}
        (data/'manifest.json').write_text(json.dumps(manifest))
        archive=root/'data.tgz'
        with tarfile.open(archive,'w:gz') as output:
            for file in data.rglob('*'):
                if file.is_file() and not file.is_symlink():output.add(file,arcname=str(file.relative_to(data)),recursive=False)
        result=restore(dict(config,source_instance='rehearsal'),archive)
        (state/'empty-test-rehearsal.private.json').write_text(json.dumps(result,indent=2)+'\n')
        return {'empty_test_rehearsal_passed':True,'production_contacted':False,'counts_verified':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True)
    print(rehearse(private_profile(parser.parse_args().config)))
