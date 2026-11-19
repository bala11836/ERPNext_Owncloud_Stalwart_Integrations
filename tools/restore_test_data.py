#!/usr/bin/env python3
"""Restore a verified four-app data snapshot into one explicit TEST runtime.

This host-only operation backs up stopped target stores first. Application code,
images, test site configuration and operator secrets always come from Git or the
test runtime. It never connects to or writes to production.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import uuid

from export_snapshot import inspect, mount, safe_copy, business_counts
from snapshot_archive import validate_extract


def run(args,**kwargs):return subprocess.run(args,check=True,**kwargs)


def import_sql(args,compressed):
    # Passing GzipFile as subprocess stdin would expose its compressed file
    # descriptor, not the decompressed stream. Explicitly pipe decoded bytes.
    process=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        with gzip.open(compressed,'rb') as sql:shutil.copyfileobj(sql,process.stdin)
        process.stdin.close()
    except BaseException:
        process.stdin.close();process.wait();raise
    if process.wait():raise RuntimeError('Native target SQL import failed')


def copy_owned(source,destination):
    safe_copy(source,destination,allow_internal_links=True)
    for item in [Path(source),*Path(source).rglob('*')]:
        if item.is_symlink():
            target=Path(destination)/item.relative_to(source);info=item.lstat();os.lchown(target,info.st_uid,info.st_gid);continue
        if not item.is_dir() and not item.is_file():continue
        target=Path(destination)/item.relative_to(source)
        stat=item.stat();os.chown(target,stat.st_uid,stat.st_gid)
        target.chmod(stat.st_mode & 0o777)


def replace_tree(source,target,allowed):
    target=Path(target).resolve()
    if target not in allowed or len(target.parts)<4 or target.is_symlink():
        raise ValueError('Unapproved test data replacement path')
    for item in target.iterdir():
        if item.is_symlink() or item.is_file():item.unlink()
        elif item.is_dir():shutil.rmtree(item)
        else:raise RuntimeError('Unexpected special file in test data')
    if Path(source).exists():copy_owned(source,target)


def require_crippled_snapshot(config,manifest):
    """Once enabled, only a scrambled N-day copy may reach this test site."""
    if config.get('require_crippled') is True and (manifest.get('crippled') or {}).get('policy')!='crippled-v1':
        raise ValueError('This test site accepts only crippled snapshots')


def restore(config,archive):
    runtime=Path(config['runtime']).resolve()
    marker=json.loads((runtime/'.cloud-runtime.json').read_text())
    if config.get('tier')!='test' or marker!={'instance':config['instance'],'tier':'test'}:
        raise ValueError('This operation requires the matching TEST runtime marker')
    containers=config['containers']
    projects=set(config['target_projects'])
    for name in set(containers.values())|set(config['application_containers']):
        native=inspect(name)
        if native['Config'].get('Labels',{}).get('com.docker.compose.project') not in projects:
            raise ValueError('Container does not belong to the selected test deployment')
    backend=inspect(containers['erp_backend'])
    if 'CLOUD_DEPLOYMENT_TIER=test' not in backend['Config']['Env']:
        raise ValueError('ERP backend is not a test build')
    sites=mount(containers['erp_backend'],'/home/frappe/frappe-bench/sites')
    if Path(config['site']).name!=config['site']:raise ValueError('Invalid test site name')
    site=sites/config['site'];site_config=json.loads((site/'site_config.json').read_text())
    if site_config.get('cloud_test_copy') is not True or site_config.get('host_name')!=config['test_erp_url']:
        raise ValueError('Target site host/flags do not match this test instance')
    database=site_config['db_name']
    if not re.fullmatch('[A-Za-z0-9_]+',database):raise ValueError('Invalid target database name')
    state=Path(config['state_root']).resolve();state.mkdir(parents=True,exist_ok=True,mode=0o700)
    backup=state/('rollback-'+str(uuid.uuid4()));backup.mkdir(mode=0o700)
    with tempfile.TemporaryDirectory(prefix='verified-',dir=state) as folder:
        data=Path(folder)/'data'
        manifest=validate_extract(archive,data,config['source_instance'],config.get('max_snapshot_bytes',100*1024**3))
        require_crippled_snapshot(config,manifest)
        paths={
            'erp-database':mount(containers['erp_database'],'/var/lib/mysql'),
            'dms-database':mount(containers['dms_database'],'/var/lib/postgresql/data'),
            'erp-public':site/'public/files','erp-private':site/'private/files',
            'dms-media':mount(containers['dms'],'/usr/src/paperless/media'),
            'dms-data':mount(containers['dms'],'/usr/src/paperless/data'),
            'dms-consume':mount(containers['dms'],'/usr/src/paperless/consume'),
            'drive-data':mount(containers['drive'],'/var/lib/ocis'),
            'drive-config':mount(containers['drive'],'/etc/ocis'),
            'mail-data':mount(containers['mail'],'/var/lib/stalwart'),
            'mail-config':mount(containers['mail'],'/etc/stalwart'),
            'worker-state':Path(config['document_worker_state'])}
        if runtime not in paths['worker-state'].resolve().parents:
            raise ValueError('Worker state must be inside this test runtime')
        if any(path.is_symlink() for path in paths.values()):
            raise ValueError('A target data root cannot be a symbolic link')
        allowed={path.resolve() for path in paths.values()}
        for path in paths.values():path.mkdir(parents=True,exist_ok=True)
        ownership={key:(path.stat().st_uid,path.stat().st_gid,path.stat().st_mode&0o777)
                   for key,path in paths.items()}
        applications=[name for name in config['application_containers'] if inspect(name)['State']['Running']]
        databases=[containers['erp_database'],containers['dms_database']]
        paused=list(dict.fromkeys(applications+databases))
        backup_complete=False
        try:
            run(['docker','stop','--time','25',*paused],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            for key,path in paths.items():copy_owned(path,backup/key)
            shutil.copy2(site/'site_config.json',backup/'erp-site-config.private.json')
            worker_profile=json.loads(Path(config['worker_enrollment_profile']).read_text())
            worker_secret=Path(worker_profile['worker_config'])
            if worker_secret.exists():
                shutil.copy2(worker_secret,backup/'worker-config.private.json')
            (backup/'receipt.json').write_text(json.dumps({'snapshot_id':manifest['snapshot_id'],'targets':{k:str(v) for k,v in paths.items()}}))
            backup_complete=True
            # Keep each target's database credentials/grants, replacing only its
            # named business schema through the native database tools.
            run(['docker','start',*databases],stdout=subprocess.DEVNULL)
            ready=False
            for _ in range(60):
                ready=all(inspect(name)['State'].get('Health',{}).get('Status')=='healthy' for name in databases)
                if ready:break
                time.sleep(1)
            if not ready:raise RuntimeError('Test databases did not become healthy')
            mysql='export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mariadb -uroot "$@"'
            run(['docker','exec','-i',containers['erp_database'],'sh','-c',mysql,'sh'],
                input=f'DROP DATABASE `{database}`; CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n'.encode(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            import_sql(['docker','exec','-i',containers['erp_database'],'sh','-c',mysql,'sh',database],data/'erp.sql.gz')
            postgres='export PGPASSWORD="$POSTGRES_PASSWORD"; exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
            run(['docker','exec','-i',containers['dms_database'],'sh','-c',postgres],
                input=b'DROP SCHEMA public CASCADE; CREATE SCHEMA public;\n',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            import_sql(['docker','exec','-i',containers['dms_database'],'sh','-c',postgres],data/'dms.sql.gz')
            if business_counts(containers,database)!=manifest.get('counts'):
                raise RuntimeError('Restored business counts do not match the source snapshot')
            for name in [containers['redis_cache'],containers['redis_queue'],containers['dms_broker']]:
                run(['docker','exec',name,'redis-cli','FLUSHALL'],stdout=subprocess.DEVNULL)
            sources={'erp-public':data/'erp-files/public','erp-private':data/'erp-files/private'}
            sources.update({name:data/name for name in ['dms-media','dms-data','dms-consume','drive-data','mail-data','mail-config']})
            worker_data=data/'worker-state';worker_data.mkdir()
            if (data/'document-jobs.sqlite3').exists():shutil.copy2(data/'document-jobs.sqlite3',worker_data/'jobs.sqlite3')
            sources['worker-state']=worker_data
            for name,source in sources.items():replace_tree(source,paths[name],allowed)
            shutil.copy2(data/'drive-runtime.private.yaml',paths['drive-config']/'ocis.yaml')
            for name in ['erp-public','erp-private','dms-media','dms-data','dms-consume',
                         'drive-data','drive-config','mail-data','mail-config','worker-state']:
                uid,gid,mode=ownership[name]
                for path in [paths[name],*paths[name].rglob('*')]:
                    if not path.is_symlink():os.chown(path,uid,gid)
                paths[name].chmod(mode)
            # Regenerate only repository-owned assets/configuration after native
            # data restoration. This must not copy production application code.
            from prepare_runtime import prepare
            prepare(config['source'],runtime,json.loads(Path(config['runtime_profile']).read_text()))
            uid=config['erp_project'];compose=Path('/data/coolify/services')/uid/'docker-compose.yml'
            bootstrap=Path(config['erp_bootstrap_profile'])
            def bench(method,kwargs=None):
                args=['docker','compose','-p',uid,'-f',str(compose),'run','--rm','-T','--no-deps',
                    '-v',str(bootstrap)+':/run/secrets/erp-bootstrap.json:ro','--entrypoint','bench','backend',
                    '--site',config['site'],'execute',method]
                if kwargs:args+=['--kwargs',json.dumps(kwargs)]
                run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            # Marked test configuration was preserved on disk; quarantine
            # copied authentication state BEFORE re-applying fresh test secrets.
            bench('erpnext_drive_integrations.operations.quarantine.apply')
            bench('erpnext_drive_integrations.operations.bootstrap.configure',{'profile_path':'/run/secrets/erp-bootstrap.json'})
            # Mail starts privately first. Its copied directory/audiences and
            # local credentials must be quarantined before its browser UI starts.
            run(['docker','start',containers['mail']],stdout=subprocess.DEVNULL)
            mail_profile=Path(config['mail_bootstrap_profile'])
            from importlib.util import spec_from_file_location,module_from_spec
            spec=spec_from_file_location('mail_bootstrap',Path(config['source'])/'integrations/mail/stalwart_bootstrap.py')
            module=module_from_spec(spec);spec.loader.exec_module(module)
            mail_ready=False
            last_mail_error=None
            for _ in range(30):
                try:module.configure(json.loads(mail_profile.read_text()));mail_ready=True;break
                except (OSError,ConnectionError) as error:last_mail_error=error;time.sleep(1)
            if not mail_ready:raise RuntimeError('Test Mail bootstrap did not complete') from last_mail_error
            document_worker=containers.get('document_worker')
            # This service bind-mounts its credential file. Atomic enrollment
            # replaces the inode, so it must remain stopped until enrollment
            # finishes and its next start remounts the new test credentials.
            ready_apps=[name for name in applications if name!=document_worker]
            run(['docker','start',*ready_apps],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            for name in [containers['drive'],containers['dms']]:
                ready=False
                for _ in range(90):
                    if inspect(name)['State'].get('Health',{}).get('Status')=='healthy':ready=True;break
                    time.sleep(1)
                if not ready:raise RuntimeError('A test application did not become healthy')
            from enroll_worker import enroll
            enrollment=json.loads(Path(config['worker_enrollment_profile']).read_text())
            enrollment.update(json.loads((data/'document-enrollment.json').read_text()))
            enroll(enrollment)
            from retarget_worker import retarget
            link_report=retarget(enrollment)
            from verify_test_collaboration import verify as verify_collaboration
            editor_report=verify_collaboration(config)
            worker_ready=None
            if document_worker and document_worker in applications:
                run(['docker','start',document_worker],stdout=subprocess.DEVNULL)
                worker_ready=False
                for _ in range(100):
                    if inspect(document_worker)['State'].get('Health',{}).get('Status')=='healthy':
                        worker_ready=True;break
                    time.sleep(1)
                if not worker_ready:raise RuntimeError('Freshly enrolled document worker did not become healthy')
            return {'restored':True,'snapshot_id':manifest['snapshot_id'],'rollback_directory':str(backup),
                    'source_instance':manifest['source_instance'],'snapshot_exported_at':manifest['exported_at'],
                    'counts_verified':True,'generated_links':link_report,'editor_registration':editor_report,
                    'document_worker_healthy':worker_ready}
        except BaseException:
            if backup_complete:
                run(['docker','stop','--time','25',*paused],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                for key,path in paths.items():replace_tree(backup/key,path,allowed)
                shutil.copy2(backup/'erp-site-config.private.json',site/'site_config.json')
                saved_worker=backup/'worker-config.private.json'
                if saved_worker.exists():
                    shutil.copy2(saved_worker,worker_secret);worker_secret.chmod(0o600);os.chown(worker_secret,10001,10001)
            run(['docker','start',*paused],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--archive',required=True)
    args=parser.parse_args();print(restore(json.loads(Path(args.config).read_text()),args.archive))
