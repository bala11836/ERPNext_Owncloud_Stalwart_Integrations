#!/usr/bin/env python3
"""Render the host check config and systemd files for one server (P57).

Reads the deployment's private profile (the same JSON the other renderers use,
with an optional "host_checks" section) and writes into an output directory:
  config.json                      the check configuration (hosts from the profile)
  cloud-boot-check.service         runs the boot check after Docker and Tailscale
  cloud-restart-watch.service/.timer   crash-loop watch every five minutes
  cloud-editor-check.service/.timer    (P80, hosts with Drive) editor registered, every five minutes
  docker.service.d/10-after-tailscale.conf   Docker starts after Tailscale
Nothing is installed; docs/production-moves.md lists the copy commands.
No host name, address or tenant detail lives in Git: they come from the profile.
"""
import argparse
import json
import re
from pathlib import Path

INSTALL_DIR = '/opt/cloud-host-check'
CONFIG_PATH = '/etc/cloud-host-check/config.json'

# Public host key -> path to request and statuses that count as up.
HOST_PATHS = {'erp': ('/', None), 'sso': ('/', None), 'drive': ('/', None), 'mail': ('/', None),
              'dms': ('/', None), 'office': ('/healthcheck', [200])}


def bridge_wanted(profile, options):
    """Check the editor bridge when the host runs Drive. A host whose checks are rendered from a profile
    without Drive (for example the ERP profile on a server that also runs Drive) says so explicitly
    with host_checks.check_bridge."""
    if 'check_bridge' in options:
        if not isinstance(options['check_bridge'], bool):
            raise ValueError('host_checks.check_bridge must be true or false')
        return options['check_bridge']
    return 'drive' in (profile.get('projects') or ['drive'])


EDITOR_KEYS = {'url', 'account', 'provider', 'extensions', 'ocis_prefix', 'repair', 'repair_interval_seconds',
               'registration_wait_seconds', 'drive_wait_seconds', 'min_drive_uptime_seconds', 'token_expiry',
               'admin_user'}


def editor_config(hosts, options, check_bridge):
    """P80: the signed-in editor registration check, on every host that checks the editor bridge.
    Off with host_checks.editor = false; settings in host_checks.editor override the defaults."""
    chosen = options.get('editor', {})
    if chosen is False or not check_bridge:
        return None
    if not isinstance(chosen, dict) or set(chosen) - EDITOR_KEYS:
        raise ValueError('host_checks.editor must be false or an object with the known keys')
    url = chosen.get('url') or ('https://' + hosts['drive'] if hosts.get('drive') else None)
    if not url:
        return None
    if not re.fullmatch(r'https://[A-Za-z0-9.-]+(:[0-9]+)?/?', url):
        raise ValueError('Invalid editor check URL')
    for key in ('account', 'ocis_prefix', 'admin_user', 'provider'):
        if key in chosen and not re.fullmatch(r'[A-Za-z0-9_.-]+', str(chosen[key])):
            raise ValueError('Invalid host_checks.editor.' + key)
    return dict(chosen, url=url.rstrip('/'))


def build_config(profile):
    hosts = profile.get('hosts') or {}
    options = profile.get('host_checks') or {}
    checks = []
    for key, (path, ok) in HOST_PATHS.items():
        host = hosts.get(key)
        if not host:
            continue
        if not re.fullmatch(r'[A-Za-z0-9.-]+', host):
            raise ValueError('Invalid host name for ' + key)
        item = {'name': key, 'url': 'https://' + host + path}
        if ok:
            item['ok'] = ok
        checks.append(item)
    config = {'http': checks, 'containers': list(options.get('containers', [])),
              'tcp': list(options.get('tcp', [])), 'check_bridge': bridge_wanted(profile, options),
              'bridge': {'container_prefix': options.get('bridge_prefix', 'collaboration-')}}
    if options.get('tailnet_ip'):
        if not re.fullmatch(r'[0-9.]+', options['tailnet_ip']):
            raise ValueError('Invalid tailnet address')
        config['tailnet_ip'] = options['tailnet_ip']
    if options.get('ignore_prefixes'):
        config['watch'] = {'ignore_prefixes': list(options['ignore_prefixes'])}
    editor = editor_config(hosts, options, config['check_bridge'])
    if editor:
        config['editor'] = editor
    for check in config['tcp']:
        if not re.fullmatch(r'[0-9.]+', str(check.get('host', ''))) or not str(check.get('port', '')).isdigit():
            raise ValueError('Invalid tcp check')
    return config


BOOT_SERVICE = """[Unit]
Description=Check that every stack came up after boot (P57)
After=docker.service tailscaled.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 {install}/host_check.py boot --config {config}
TimeoutStartSec=900
SuccessExitStatus=0

[Install]
WantedBy=multi-user.target
"""

WATCH_SERVICE = """[Unit]
Description=Flag containers that keep restarting (P57)
After=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 {install}/host_check.py watch --config {config}
"""

WATCH_TIMER = """[Unit]
Description=Crash-loop watch every five minutes (P57)

[Timer]
OnBootSec=10min
OnUnitActiveSec=5min
AccuracySec=30s

[Install]
WantedBy=timers.target
"""

EDITOR_SERVICE = """[Unit]
Description=Office editor registered with Drive; repair once if not (P80)
After=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 {install}/host_check.py editor --config {config}
TimeoutStartSec=600
"""

EDITOR_TIMER = """[Unit]
Description=Office editor registration check every five minutes (P80)

[Timer]
OnBootSec=12min
OnUnitActiveSec=5min
AccuracySec=30s

[Install]
WantedBy=timers.target
"""

DOCKER_DROPIN = """[Unit]
Wants=tailscaled.service
After=tailscaled.service network-online.target

[Service]
# Best effort (the leading minus ignores failure): wait up to a minute for the
# tailnet address so containers bound to it can start at once.
ExecStartPre=-/usr/bin/python3 {install}/host_check.py wait-tailnet --config {config} --timeout 60
"""


def render(profile, output):
    output = Path(output)
    (output / 'docker.service.d').mkdir(parents=True, exist_ok=True)
    fill = {'install': INSTALL_DIR, 'config': CONFIG_PATH}
    config = build_config(profile)
    files = {'config.json': json.dumps(config, indent=2) + '\n',
             'cloud-boot-check.service': BOOT_SERVICE.format(**fill),
             'cloud-restart-watch.service': WATCH_SERVICE.format(**fill),
             'cloud-restart-watch.timer': WATCH_TIMER,
             'docker.service.d/10-after-tailscale.conf': DOCKER_DROPIN.format(**fill)}
    if config.get('editor'):
        files['cloud-editor-check.service'] = EDITOR_SERVICE.format(**fill)
        files['cloud-editor-check.timer'] = EDITOR_TIMER
    for name, text in files.items():
        (output / name).write_text(text)
    return sorted(files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--profile', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    for written in render(json.loads(Path(args.profile).read_text()), args.output):
        print(written)
