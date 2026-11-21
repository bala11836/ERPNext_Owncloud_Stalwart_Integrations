#!/usr/bin/env python3
"""Trust forwarded headers on the SSO host's private entry point, for the test bridge only (P65).

The test site reaches the sign-in service through the SSO host's private (tailnet-only) entry point. Traefik drops
X-Forwarded-* headers from sources it does not trust, including X-Forwarded-Uri, so after the passkey the sign-in
gateway returned to "/" instead of the page that was asked for. This adds
`--entrypoints.<entry>.forwardedheaders.trustedips=<sources>` for that one entry point.

Rules: never for a public entry point (http, https, web, websecure); the entry point must already be defined; the
sources are exact addresses (/32 or /128), normally the test VM only (from
`prepare_auth_bridge.py --print-forwarded-trust`). The setting is written to the proxy compose file and to Coolify's
saved proxy configuration, so a restart from the dashboard or a reboot keeps it (20 November 2026 lesson). Nothing is
restarted here: restart the proxy afterwards at a quiet moment (it cuts web traffic for a few seconds).

Usage (on the SSO host, as root):
  python3 tools/sso_proxy_trust.py --entrypoint mailprivate --trust 100.64.0.20 [--dry-run]
  python3 tools/sso_proxy_trust.py --entrypoint mailprivate --trust ''        # remove the setting
"""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import subprocess
import yaml

COMPOSE = Path('/data/coolify/proxy/docker-compose.yml')
PUBLIC = {'http', 'https', 'web', 'websecure'}


def ranges(values):
    out = []
    for value in values:
        if not value:
            continue
        network = ipaddress.ip_network(value if '/' in value else value + ('/128' if ':' in value else '/32'))
        if network.num_addresses != 1:
            raise ValueError('Trust exact addresses only: ' + value)
        out.append(str(network))
    return out


def apply(text, entrypoint, trusted):
    """Return compose text with exactly this trusted-IPs flag on this private entry point."""
    if not re.fullmatch(r'[A-Za-z0-9-]+', entrypoint) or entrypoint.lower() in PUBLIC:
        raise ValueError('Only a private entry point may trust forwarded headers')
    data = yaml.safe_load(text)
    service = data['services']['traefik']
    command = [str(c) for c in service.get('command', [])]
    if not any(c.lower().startswith('--entrypoints.%s.address=' % entrypoint.lower()) for c in command):
        raise ValueError('Entry point %s is not defined on this proxy' % entrypoint)
    prefix = '--entrypoints.%s.forwardedheaders.trustedips=' % entrypoint
    command = [c for c in command if not c.lower().startswith(prefix.lower())]
    nets = ranges(trusted)
    if nets:
        command.append(prefix + ','.join(nets))
    service['command'] = command
    return yaml.safe_dump(data, sort_keys=False)


def psql(sql):
    return subprocess.run(['docker', 'exec', '-i', 'coolify-db', 'psql', '-U', 'coolify', '-d', 'coolify', '-At', '-v', 'ON_ERROR_STOP=1'],
                          input=sql, capture_output=True, text=True, check=True).stdout


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--entrypoint', required=True)
    parser.add_argument('--trust', required=True, help='comma-separated exact addresses; empty removes the setting')
    parser.add_argument('--server-id', type=int, default=0)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    trusted = [t.strip() for t in args.trust.split(',') if t.strip()]
    new_compose = apply(COMPOSE.read_text(), args.entrypoint, trusted)
    proxy = json.loads(psql(f'select proxy from servers where id={args.server_id};'))
    saved = proxy.get('last_saved_proxy_configuration')
    if not saved:
        raise SystemExit('Coolify has no saved proxy configuration for this server: save it in Coolify first')
    proxy['last_saved_proxy_configuration'] = apply(saved, args.entrypoint, trusted)
    proxy['last_saved_settings'] = hashlib.md5(proxy['last_saved_proxy_configuration'].encode()).hexdigest()
    flag = [c for c in yaml.safe_load(new_compose)['services']['traefik']['command'] if 'forwardedheaders.trustedips' in c.lower()]
    if args.dry_run:
        print('dry run: would set', flag or 'no trusted-IPs flag')
        raise SystemExit(0)
    tag = 'p' + hashlib.sha256(json.dumps(proxy).encode()).hexdigest()[:16]
    psql(f"update servers set proxy=${tag}${json.dumps(proxy)}${tag}$::json where id={args.server_id};")
    COMPOSE.write_text(new_compose)
    print('Proxy configuration written', flag or '(trusted-IPs flag removed)', '; restart the proxy at a quiet moment to apply')
