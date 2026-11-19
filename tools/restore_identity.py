#!/usr/bin/env python3
"""Restore the sign-in service (authentik) from a restored backup (P44).

Two steps, run as root on the recovery host:

  restore_identity.py secrets --backup-compose C --output S.private.json
      Read production's authentik secret key and passwords from the Coolify
      compose file inside the restored backup and write them as renderer
      settings (`CI_IDENTITY_*`). The secret key MUST be production's: authentik
      derives users' sign-in identifiers from it, so a new key would make Drive,
      ERP and the other apps see every user as new.

  restore_identity.py load --config C.private.json
      Into the repository identity stack (rendered with those settings and
      registered): stop server and worker, replace the authentik database with
      the backup's dump, copy the media folder, start again, wait until ready
      and report user/application/provider counts.

Nothing here contacts production. Values are never printed.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time

SECRET_KEYS = {
    'AUTHENTIK_SECRET_KEY': 'CI_IDENTITY_SERVER_AUTHENTIK_SECRET_KEY',
    'AUTHENTIK_POSTGRESQL__PASSWORD': 'CI_IDENTITY_POSTGRESQL_POSTGRES_PASSWORD',
    'AUTHENTIK_EMAIL__PASSWORD': 'CI_IDENTITY_SERVER_AUTHENTIK_EMAIL__PASSWORD',
}
COUNTS = ("from authentik.core.models import User, Application;"
          "from authentik.providers.oauth2.models import OAuth2Provider;"
          "import json;print('IDENTITY_COUNTS='+json.dumps({'users':User.objects.exclude_anonymous().count(),"
          "'applications':Application.objects.count(),'oauth2_providers':OAuth2Provider.objects.count()}))")


def secrets_from_compose(text):
    """First value of each secret in the legacy Coolify compose (server section)."""
    found = {}
    for key, setting in SECRET_KEYS.items():
        match = re.search(r'^\s*' + re.escape(key) + r"""\s*:\s*['"]?([^'"\n]+?)['"]?\s*$""", text, re.M)
        if not match:
            raise ValueError('Backup compose lacks ' + key)
        found[setting] = match.group(1)
    if len(found['CI_IDENTITY_SERVER_AUTHENTIK_SECRET_KEY']) < 32:
        raise ValueError('Implausible authentik secret key')
    return found


def write_private(path, data):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    with open(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as stream:
        stream.write(json.dumps(data, indent=2) + '\n')
    os.replace(temporary, path)


def compose(config, *args, **kwargs):
    project = config['project']
    if not re.fullmatch(r'[a-z0-9]+', project):
        raise ValueError('Invalid Coolify project id')
    directory = Path('/data/coolify/services') / project
    return subprocess.run(['docker', 'compose', '-p', project, '-f', str(directory / 'docker-compose.yml'),
                           '--env-file', str(directory / '.env'), *args], check=True, **kwargs)


def container(config, service):
    return service + '-' + config['project']


def wait(check, seconds, message):
    for _ in range(seconds // 2):
        if check():
            return
        time.sleep(2)
    raise RuntimeError(message)


def load(config):
    dump = Path(config['dump'])
    media = Path(config['media']) if config.get('media') else None
    if not dump.is_file():
        raise ValueError('Identity dump not found')
    database = container(config, 'postgresql')
    compose(config, 'stop', 'server', 'worker', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    compose(config, 'up', '-d', '--pull', 'missing', 'postgresql', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait(lambda: subprocess.run(['docker', 'exec', database, 'sh', '-c', 'pg_isready -U "$POSTGRES_USER"'],
                                stdout=subprocess.DEVNULL).returncode == 0, 120, 'Identity database did not start')
    psql = 'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres'
    subprocess.run(['docker', 'exec', '-i', database, 'sh', '-c', psql],
                   input=b'DROP DATABASE IF EXISTS authentik WITH (FORCE); CREATE DATABASE authentik OWNER authentik;\n',
                   check=True, stdout=subprocess.DEVNULL)
    # pg_dumpall output: role and CREATE DATABASE statements fail harmlessly on
    # the existing role/database; the authentik data then loads into it.
    with dump.open('rb') as data:
        subprocess.run(['docker', 'exec', '-i', database, 'sh', '-c',
                        'exec psql -q -v ON_ERROR_STOP=0 -U "$POSTGRES_USER" -d postgres'],
                       stdin=data, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if media and media.is_dir():
        server = container(config, 'server')
        compose(config, 'create', 'server', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['docker', 'cp', str(media) + '/.', server + ':/data/media'], check=True,
                       stdout=subprocess.DEVNULL)
    compose(config, 'up', '-d', '--pull', 'missing', 'server', 'worker', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    server = container(config, 'server')
    wait(lambda: subprocess.run(['docker', 'exec', server, 'ak', 'healthcheck'], stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL).returncode == 0, 300, 'authentik did not become ready')
    output = subprocess.check_output(['docker', 'exec', server, 'ak', 'shell', '-c', COUNTS], text=True,
                                     stderr=subprocess.DEVNULL)
    return json.loads(output.split('IDENTITY_COUNTS=', 1)[1].splitlines()[0])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    first = sub.add_parser('secrets')
    first.add_argument('--backup-compose', required=True)
    first.add_argument('--output', required=True)
    second = sub.add_parser('load')
    second.add_argument('--config', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    if args.command == 'secrets':
        write_private(args.output, secrets_from_compose(Path(args.backup_compose).read_text()))
        print('Identity settings written (values not shown)')
    else:
        path = Path(args.config)
        if path.stat().st_uid != 0 or path.stat().st_mode & 0o077:
            raise SystemExit('Config must be root-owned and private')
        print(json.dumps(load(json.loads(path.read_text()))))
