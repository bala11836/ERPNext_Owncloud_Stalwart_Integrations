#!/usr/bin/env python3
"""Switch HTTP/3 off on a Coolify proxy (relay host for test hostnames).

The relay passes test hostnames through by TCP SNI only. With HTTP/3 on,
browsers that remembered an HTTP/3 alternative send QUIC (UDP 443) to the
relay host, which then answers test hostnames itself (503). Turning HTTP/3
off makes that attempt fail fast, so browsers fall back to TCP, which the
relay passes through. Writes Coolify's saved proxy configuration and the
compose file; `--restart` recreates the proxy and reattaches its networks. Only the HTTP/3 flag and UDP 443
change (see coolify_proxy_hosts.apply).
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from coolify_proxy_hosts import COMPOSE, apply, psql  # noqa: E402


def disable(server_id=0):
    text = apply(COMPOSE.read_text(), {}, http3=False)
    proxy = json.loads(psql(f'select proxy from servers where id={server_id};'))
    if proxy.get('last_saved_proxy_configuration'):
        proxy['last_saved_proxy_configuration'] = apply(proxy['last_saved_proxy_configuration'], {}, http3=False)
        proxy['last_saved_settings'] = hashlib.md5(proxy['last_saved_proxy_configuration'].encode()).hexdigest()
        tag = 'p' + hashlib.sha256(json.dumps(proxy).encode()).hexdigest()[:16]
        psql(f"update servers set proxy=${tag}${json.dumps(proxy)}${tag}$::json where id={server_id};")
    COMPOSE.write_text(text)
    return 'HTTP/3 disabled in the saved proxy configuration and compose file; restart the proxy to apply'


def restart_keeping_networks(run=None):
    """Recreate the proxy and reattach every network it had before.

    Coolify attaches its proxy to each service network at deploy time; a plain
    recreate keeps only the networks in the compose file (found on production
    18 November 2026: four service networks were dropped).
    """
    import subprocess
    run = run or subprocess.run
    inspect = lambda: set(json.loads(run(['docker', 'inspect', 'coolify-proxy', '--format', '{{json .NetworkSettings.Networks}}'],
                                         capture_output=True, text=True, check=True).stdout))
    before = inspect()
    run(['docker', 'compose', 'up', '-d', '--force-recreate'], cwd=str(COMPOSE.parent), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    missing = sorted(before - inspect())
    for network in missing:
        run(['docker', 'network', 'connect', network, 'coolify-proxy'], check=True)
    return missing


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--server-id', type=int, default=0)
    p.add_argument('--restart', action='store_true', help='recreate the proxy, keeping its networks')
    a = p.parse_args()
    print(disable(a.server_id))
    if a.restart:
        print('Proxy recreated; reattached networks:', restart_keeping_networks() or 'none needed')
