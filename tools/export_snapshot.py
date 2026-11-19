#!/usr/bin/env python3
"""Restricted production -> test data export. There is no restore/import path.

Install from a reviewed Git commit on the production host. A forced SSH key may
invoke only `export-test`. The root-owned configuration selects fixed containers
and paths. It cannot accept a caller-selected command, filename or destination.
Consistent four-app snapshots require explicitly approved brief maintenance.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def inspect(name):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',name):raise ValueError('Invalid fixed container name')
    return json.loads(subprocess.check_output(['docker','inspect',name]))[0]


def mount(container, target):
    rows=[m for m in inspect(container)['Mounts'] if m['Destination']==target]
    if len(rows)!=1:raise RuntimeError('Expected one native data mount')
    path=Path(rows[0]['Source']).resolve()
    if path==Path('/') or not path.is_dir():raise RuntimeError('Invalid native data directory')
    return path


def safe_copy(source, destination, exclude=(), allow_internal_links=False):
    """Make `destination` an exact data-only copy of `source`.

    Never follows uploaded symlinks outside the selected tree. Files whose size
    and modification time already match are kept, so a second pass (inside the
    maintenance pause) copies only what changed since the first pass (taken
    while production runs). Entries no longer in the source are removed.
    """
    source=Path(source);destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    seen=set()
    for path in source.rglob('*'):
        relative=path.relative_to(source)
        if any(relative==Path(p) or Path(p) in relative.parents for p in exclude):continue
        seen.add(relative)
        target=destination/relative
        if path.is_symlink():
            resolved=path.resolve()
            if (not allow_internal_links or Path(path.readlink()).is_absolute()
                    or (resolved!=source.resolve() and source.resolve() not in resolved.parents)):
                raise RuntimeError('External or unexpected symlink in snapshot data tree')
            if target.is_symlink() and target.readlink()==path.readlink():continue
            remove(target)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.symlink_to(path.readlink());continue
        if path.is_dir():
            if target.is_symlink() or (target.exists() and not target.is_dir()):remove(target)
            target.mkdir(exist_ok=True)
        elif path.is_file():
            info=path.stat()
            if target.is_file() and not target.is_symlink():
                current=target.stat()
                if current.st_size==info.st_size and current.st_mtime_ns==info.st_mtime_ns:continue
            remove(target)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,target)
    # Remove what was deleted from the source since the first pass.
    for path in sorted(destination.rglob('*'),key=lambda p:len(p.parts),reverse=True):
        if path.relative_to(destination) not in seen:remove(path)


def remove(path):
    path=Path(path)
    if path.is_symlink() or path.is_file():path.unlink()
    elif path.is_dir():shutil.rmtree(path)


def tree_manifest(data):
    files={};links={};directories=[]
    for file in data.rglob('*'):
        relative=str(file.relative_to(data))
        if file.is_symlink():links[relative]=str(file.readlink())
        elif file.is_dir():directories.append(relative)
        elif file.is_file():
            with file.open('rb') as contents:digest=hashlib.file_digest(contents,'sha256').hexdigest()
            files[relative]={'bytes':file.stat().st_size,'sha256':digest}
    return {'files':files,'links':links,'directories':sorted(directories)}


def sql_dump(args, output):
    """Write a native dump uncompressed: fast enough for the maintenance pause."""
    with output.open('wb') as file, tempfile.TemporaryFile() as errors:
        process=subprocess.Popen(args,stdout=file,stderr=errors)
        if process.wait():raise RuntimeError('Native database export failed; source data unchanged')


def compress(raw):
    """Gzip a dump after production has resumed; returns the .gz path."""
    raw=Path(raw);zipped=raw.with_name(raw.name+'.gz')
    with raw.open('rb') as source, gzip.open(zipped,'wb',compresslevel=6) as target:shutil.copyfileobj(source,target)
    raw.unlink()
    return zipped


def business_counts(containers,database):
    tables=['tabUser','tabCompany','tabFile','tabSupplier','tabEmployee','tabPurchase Order','tabSales Invoice']
    mysql='export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mariadb -N -B -uroot "$1" -e "$2"'
    counts={}
    for table in tables:
        output=subprocess.check_output(['docker','exec',containers['erp_database'],'sh','-c',mysql,
            'sh',database,'SELECT COUNT(*) FROM `'+table+'`'],stderr=subprocess.DEVNULL,text=True)
        counts[table]=int(output.strip())
    uploaded=int(subprocess.check_output(['docker','exec',containers['erp_database'],'sh','-c',mysql,
        'sh',database,'SELECT COUNT(*) FROM `tabFile` WHERE is_folder=0'],stderr=subprocess.DEVNULL,text=True).strip())
    postgres='export PGPASSWORD="$POSTGRES_PASSWORD"; exec psql -At -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) FROM documents_document"'
    documents=int(subprocess.check_output(['docker','exec',containers['dms_database'],'sh','-c',postgres],
        stderr=subprocess.DEVNULL,text=True).strip())
    return {'erp':counts,'erp_uploaded_files':uploaded,'dms_documents':documents}


def export(config):
    if config.get('source_tier')!='production' or config.get('allow_brief_maintenance') is not True:
        raise RuntimeError('Four-app snapshots require explicit maintenance authorization')
    root=Path(config['state_root']).resolve()
    if root==Path('/') or len(root.parts)<3:raise ValueError('Choose a private export state directory')
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    root.chmod(0o700)
    containers=config['containers']
    sites=mount(containers['erp_backend'],'/home/frappe/frappe-bench/sites')
    site=sites/config['site']
    if Path(config['site']).name!=config['site']:raise ValueError('Invalid site name')
    site_config=json.loads((site/'site_config.json').read_text())
    if site_config.get('cloud_test_copy') or site_config.get('host_name','').rstrip('/')!=config['production_erp_url'].rstrip('/'):
        raise RuntimeError('Source is not the configured production site')
    database=site_config['db_name']
    if not re.fullmatch(r'[A-Za-z0-9_]+',database):raise ValueError('Invalid native database name')
    selected=[]
    for name in config['pause_containers']:
        if inspect(name)['State']['Running']:selected.append(name)
    if not selected:raise RuntimeError('No running source applications to snapshot')
    # Identity, database engines, Coolify and the administrator network must never
    # be paused. Validate against the explicit configuration before any stop.
    protected=set(config['never_pause_containers'])|{containers['erp_database'],containers['dms_database']}
    if protected.intersection(selected):raise RuntimeError('A protected service appears in maintenance targets')
    with (root/'export.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        attempt=root/'last-attempt.json'
        if attempt.exists() and time.time()-attempt.stat().st_mtime<config.get('minimum_interval_seconds',300):
            raise RuntimeError('Production export is cooling down; retry later')
        attempt.write_text(json.dumps({'attempted_at':datetime.now(timezone.utc).isoformat()})+'\n')
        snapshot_id=str(uuid.uuid4())
        resume_file=root/'resume.json'
        resume_file.write_text(json.dumps(selected));resume_file.chmod(0o600)
        watchdog='cloud-snapshot-resume-'+snapshot_id
        script=str(Path(__file__).resolve())
        config_path=str(Path(config['_config_path']).resolve())
        # A separate system timer restarts only these pre-recorded containers if
        # the exporter is killed. Normal finally also restores their prior state.
        with tempfile.TemporaryDirectory(prefix='snapshot-',dir=root) as temporary:
            data=Path(temporary)
            def copy_files():
                for kind in ['public','private']:
                    directory=site/kind/'files'
                    if directory.exists():safe_copy(directory,data/'erp-files'/kind)
                safe_copy(mount(containers['dms'],'/usr/src/paperless/media'),data/'dms-media')
                safe_copy(mount(containers['dms'],'/usr/src/paperless/data'),data/'dms-data')
                safe_copy(mount(containers['dms'],'/usr/src/paperless/consume'),data/'dms-consume')
                safe_copy(mount(containers['drive'],'/var/lib/ocis'),data/'drive-data',exclude=['web/assets'],allow_internal_links=True)
                safe_copy(mount(containers['mail'],'/var/lib/stalwart'),data/'mail-data')
                safe_copy(mount(containers['mail'],'/etc/stalwart'),data/'mail-config')
            # First pass while production runs: the bulk of the file data.
            # Mounts are resolved now, while the containers are still running.
            copy_files()
            # Arm the watchdog only now, so the first pass cannot use up its time.
            run(['systemd-run','--quiet','--unit',watchdog,'--on-active=120s',
                 sys.executable,script,'--config',config_path,'--resume-only'],stdout=subprocess.DEVNULL)
            started=time.time()
            try:
                run(['docker','stop','--time','25',*selected],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                erp_command='export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mariadb-dump -uroot --single-transaction --routines --triggers --hex-blob --ignore-table-data="$1.__Auth" --ignore-table-data="$1.tabSessions" --ignore-table-data="$1.tabOAuth Bearer Token" --ignore-table-data="$1.tabOAuth Authorization Code" "$1"'
                sql_dump(['docker','exec',containers['erp_database'],'sh','-c',erp_command,'sh',database],data/'erp.sql')
                pg_command='export PGPASSWORD="$POSTGRES_PASSWORD"; exec pg_dump -U "$POSTGRES_USER" --no-owner --no-acl --exclude-table-data=public.django_session --exclude-table-data=public.authtoken_token --exclude-table-data=public.socialaccount_socialtoken "$POSTGRES_DB"'
                sql_dump(['docker','exec',containers['dms_database'],'sh','-c',pg_command],data/'dms.sql')
                # Second pass inside the pause: only what changed since the first.
                copy_files()
                # Native machine/service keys are needed for these data copies.
                # No SSO database, passkeys, OIDC signing keys or ERP site config.
                ocis=mount(containers['drive'],'/etc/ocis')/'ocis.yaml'
                shutil.copy2(ocis,data/'drive-runtime.private.yaml')
                worker=Path(config['document_worker_state'])/'jobs.sqlite3'
                if worker.exists():shutil.copy2(worker,data/'document-jobs.sqlite3')
                enrollment=json.loads(Path(config['document_worker_config']).read_text())
                public_enrollment={key:enrollment[key] for key in ['office_space_id','office_processor']}
                public_enrollment['users']=[{'email':user['email']} for user in enrollment['users']]
                (data/'document-enrollment.json').write_text(json.dumps(public_enrollment)+'\n')
                counts=business_counts(containers,database)
                if time.time()-started>=100:
                    raise RuntimeError('Snapshot exceeded its consistency window; no archive will be published')
            finally:
                run(['docker','start',*selected],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                run(['systemctl','stop',watchdog+'.timer'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            maintenance_seconds=round(time.time()-started,2)
            # Production is running again: compress the dumps now.
            for name in ['erp.sql','dms.sql']:compress(data/name)
            contents=tree_manifest(data)
            manifest={'format':1,'source_instance':config['source_instance'],'snapshot_id':snapshot_id,
                'exported_at':datetime.now(timezone.utc).isoformat(),'maintenance_seconds':maintenance_seconds,
                **contents,'counts':counts,'code_included':False,'identity_database_included':False}
            (data/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
            # Production is running again before compression/network transfer.
            with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as archive:
                for file in sorted(data.rglob('*')):
                    if file.is_file() and not file.is_symlink():archive.add(file,arcname=str(file.relative_to(data)),recursive=False)
            (root/'last-export.json').write_text(json.dumps({k:v for k,v in manifest.items() if k not in {'files','links','directories'}},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--resume-only',action='store_true')
    args=parser.parse_args()
    original=os.environ.get('SSH_ORIGINAL_COMMAND')
    if original is not None and (original!='export-test' or args.resume_only):
        raise SystemExit('Only export-test is permitted')
    os.umask(0o077)
    profile_path=Path(args.config).resolve()
    if profile_path.stat().st_uid!=0 or profile_path.stat().st_mode & 0o077:
        raise SystemExit('Configuration must be root-owned and private')
    config=json.loads(profile_path.read_text());config['_config_path']=str(profile_path)
    if args.resume_only:
        file=Path(config['state_root'])/'resume.json'
        names=json.loads(file.read_text())
        if not set(names)<=set(config['pause_containers']):raise SystemExit('Invalid resume record')
        run(['docker','start',*names],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else:export(config)
