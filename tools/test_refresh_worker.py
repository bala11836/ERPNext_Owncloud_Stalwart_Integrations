#!/usr/bin/env python3
"""Consume fixed test refresh requests; all privileged configuration is host-only.

The web app supplies only a UUID, actor and time. Source, destination, SSH key,
native services and restore policy come from a root-owned private profile.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime,timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import stat
import subprocess
import sys
import tempfile
import time
import traceback
import uuid

from restore_test_data import restore


def now():return datetime.now(timezone.utc).isoformat()


def publish_status(directory,status):
    name='.status-'+uuid.uuid4().hex
    descriptor=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
    try:
        with os.fdopen(descriptor,'w') as stream:
            json.dump(status,stream);stream.write('\n');stream.flush()
            os.fchmod(stream.fileno(),0o644);os.fchown(stream.fileno(),0,0);os.fsync(stream.fileno())
        os.replace(name,'status.json',src_dir_fd=directory,dst_dir_fd=directory)
    finally:
        try:os.unlink(name,dir_fd=directory)
        except FileNotFoundError:pass


def private_profile(path):
    path=Path(path)
    info=path.stat()
    if info.st_uid!=0 or info.st_mode&0o077:raise ValueError('Worker configuration must be root-owned and private')
    value=json.loads(path.read_text())
    if value.get('tier')!='test':raise ValueError('Worker is test-only')
    runtime=Path(value['runtime'])
    if json.loads((runtime/'.cloud-runtime.json').read_text())!={'instance':value['instance'],'tier':'test'}:
        raise ValueError('Runtime marker does not match this worker')
    return value


def execute(config,retry_staged=False):
    state=Path(config['state_root']);state.mkdir(parents=True,exist_ok=True,mode=0o700)
    public=Path(config['request_directory']);request=public/'request.json'
    if not request.exists():return
    with (state/'worker.lock').open('w') as lock, ExitStack() as cleanup:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        directory=os.open(public,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        cleanup.callback(os.close,directory)
        descriptor=os.open('request.json',os.O_RDONLY|os.O_NOFOLLOW,dir_fd=directory)
        cleanup.callback(os.close,descriptor)
        info=os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size>4096 or info.st_uid!=1000:
            raise ValueError('Invalid test refresh request file')
        incoming=json.loads(os.read(descriptor,4097).decode())
        request_id=str(uuid.UUID(incoming['request_id']))
        kind=incoming.get('kind','data')
        if request_id!=incoming['request_id'] or incoming['actor'].casefold() not in {u.casefold() for u in config['allowed_users']}:
            raise ValueError('Unapproved refresh actor or request identifier')
        if kind=='code':
            # Consume queued requests from browsers that had the old button open.
            os.unlink('request.json',dir_fd=directory)
            return
        if kind!='data':raise ValueError('Unknown refresh kind')
        receipt=state/'last-result.private.json'
        prior=json.loads(receipt.read_text()) if receipt.exists() else {}
        status={'request_id':request_id,'requested_at':incoming['requested_at'],'started_at':now(),
                'last_successful_at':prior.get('last_successful_at'),'kind':'data'}
        def publish(phase):
            status['phase']=phase
            # Official ERP images use uid 1000 with primary gid 0. This file
            # contains public progress/times only; keep it root-owned and
            # readable independently of the image's primary group.
            publish_status(directory,status)
        attempt=state/'last-attempt.private.json'
        try:
            if not retry_staged and attempt.exists() and time.time()-attempt.stat().st_mtime<config.get('minimum_interval_seconds',300):
                raise RuntimeError('Test refresh cooldown is active')
            attempt.write_text(json.dumps({'at':now()})+'\n')
            publish('restoring' if retry_staged else 'snapshotting')
            with tempfile.TemporaryDirectory(prefix='refresh-',dir=state) as temporary:
                archive=Path(temporary)/'production-data.tgz'
                staged=state/'latest-staged.private.tgz';metadata=state/'latest-staged.private.json'
                if retry_staged:
                    record=json.loads(metadata.read_text())
                    with staged.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
                    if record['source_instance']!=config['source_instance'] or record['sha256']!=digest:
                        raise ValueError('Staged snapshot identity/integrity mismatch')
                else:
                    ssh=config['export_ssh']
                    args=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
                        '-o','UserKnownHostsFile='+ssh['known_hosts'],'-o','ServerAliveInterval=15',
                        '-o','ServerAliveCountMax=3','-i',ssh['key'],ssh['destination'],'export-test']
                    maximum=config.get('max_snapshot_bytes',20*1024**3)
                    def limit_output():resource.setrlimit(resource.RLIMIT_FSIZE,(maximum,maximum))
                    with archive.open('wb') as output,(state/'last-export-error.private.log').open('wb') as errors:
                        subprocess.run(args,stdout=output,stderr=errors,timeout=config.get('export_timeout_seconds',1800),check=True,preexec_fn=limit_output)
                    archive.chmod(0o600)
                    with archive.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
                    os.replace(archive,staged)
                    metadata.write_text(json.dumps({'source_instance':config['source_instance'],'sha256':digest,'fetched_at':now()})+'\n')
                publish('restoring')
                report=restore(config,staged)
                publish('validating')
                # Native restore checks business counts, app health and fresh
                # owner credentials. Save success only after all of them pass.
                status.update(finished_at=now(),last_successful_at=now())
                report.update(status);report['phase']='succeeded'
                receipt.write_text(json.dumps(report,indent=2)+'\n');receipt.chmod(0o600)
                publish('succeeded')
        except Exception as error:
            status['finished_at']=now();publish('failed')
            (state/'last-failure.private.json').write_text(json.dumps({'at':now(),'error_type':type(error).__name__})+'\n')
            (state/'last-failure.private.log').write_text(traceback.format_exc())
            print('Test refresh failed: '+type(error).__name__,file=sys.stderr)
        finally:
            # Leave the request in place throughout the job, so another click
            # cannot queue a second destructive refresh while one is running.
            try:os.unlink('request.json',dir_fd=directory)
            except FileNotFoundError:pass


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--retry-staged',action='store_true')
    args=parser.parse_args();os.umask(0o077);execute(private_profile(args.config),args.retry_staged)
