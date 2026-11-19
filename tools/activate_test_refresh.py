#!/usr/bin/env python3
"""Enable the test-only button/timer after a verified production snapshot restore.

Run as root on the test host. Never enables a production site. Secrets remain
in existing private profiles; systemd units contain paths only.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import yaml

from test_refresh_worker import private_profile


def activate(path):
    config = private_profile(path)
    receipt = json.loads((Path(config['state_root'])/'last-result.private.json').read_text())
    if not (receipt.get('phase') == 'succeeded' and receipt.get('counts_verified') is True
            and receipt.get('source_instance') == config['source_instance']
            and receipt.get('snapshot_id') and receipt.get('last_successful_at')):
        raise ValueError('A verified source snapshot restore must succeed before activation')
    status = Path(config['request_directory'])/'status.json'
    if status.is_symlink() or not status.is_file():
        raise ValueError('Expected a regular public refresh status file')
    status.chmod(0o644); os.chown(status, 0, 0)
    source = Path(config['source']).resolve()
    profile_path = Path(config['runtime_profile']).resolve()
    for value in [str(source), str(profile_path), str(Path(path).resolve())]:
        if any(char.isspace() for char in value) or '%' in value:
            raise ValueError('System service paths must not contain whitespace or specifiers')
    profile = json.loads(profile_path.read_text())
    if profile.get('tier') != 'test' or profile.get('instance') != config['instance']:
        raise ValueError('Runtime identity does not match test worker')
    profile['refresh_ready'] = True
    profile_path.write_text(json.dumps(profile, indent=2)+'\n'); profile_path.chmod(0o600)
    bootstrap = Path(config['erp_bootstrap_profile'])
    values = json.loads(bootstrap.read_text()); values['refresh_ready'] = True
    bootstrap.write_text(json.dumps(values, indent=2)+'\n'); bootstrap.chmod(0o600); os.chown(bootstrap, 1000, 1000)
    compose = Path('/data/coolify/services')/config['erp_project']/'docker-compose.yml'
    subprocess.run(['docker','compose','-p',config['erp_project'],'-f',str(compose),
        'run','--rm','-T','--no-deps','-v',str(bootstrap)+':/run/secrets/erp-bootstrap.json:ro',
        '--entrypoint','bench','backend','--site',config['site'],'execute',
        'erpnext_drive_integrations.operations.bootstrap.configure','--kwargs',
        json.dumps({'profile_path':'/run/secrets/erp-bootstrap.json'})],check=True,stdout=subprocess.DEVNULL)
    # User-triggered reports/background work need queues on a useful test site.
    # Start them only after a verified quarantined restore; leave the business
    # scheduler stopped and copied outbound definitions/credentials disabled.
    subprocess.run(['docker','compose','-p',config['erp_project'],'-f',str(compose),
        '--profile','manual-workers','up','-d','--no-deps','queue-short','queue-long'],check=True,stdout=subprocess.DEVNULL)
    native=yaml.safe_load(compose.read_text())
    for role in ['queue-short','queue-long']:
        name=native['services'][role]['container_name']
        if name not in config['application_containers']:config['application_containers'].append(name)
    Path(path).write_text(json.dumps(config,indent=2)+'\n');Path(path).chmod(0o600)
    units = Path('/etc/systemd/system')
    service = (source/'deployment/test-refresh-worker.service.example').read_text()
    service = service.replace('/opt/cloud-integrations/repository',str(source)).replace(
        '/etc/cloud-integrations/test-refresh.private.json',str(Path(path).resolve()))
    (units/'test-refresh-worker.service').write_text(service)
    (units/'test-refresh-worker.timer').write_text((source/'deployment/test-refresh-worker.timer.example').read_text())
    (units/'cloud-test-egress.service').write_text('[Unit]\nDescription=Isolated test application egress policy\n'
        'After=docker.service network-online.target\nRequires=docker.service\n\n[Service]\nType=oneshot\n'
        'RemainAfterExit=yes\nExecStart=/usr/bin/python3 '+str(source)+'/tools/test_egress.py --profile '+str(profile_path)+
        '\n\n[Install]\nWantedBy=multi-user.target\n')
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now','cloud-test-egress.service','test-refresh-worker.timer'],check=True)
    return {'button_enabled':True,'timer_enabled':True,'source_snapshot':receipt['snapshot_id'],
            'last_successful_at':receipt['last_successful_at']}


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True)
    args=parser.parse_args();os.umask(0o077);print(json.dumps(activate(args.config)))
