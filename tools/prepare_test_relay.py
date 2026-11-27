#!/usr/bin/env python3
"""Render a pass-through relay for the test hostnames on another Traefik host.

Used when the test host has no public address (e.g. a home server reached over
a tailnet): public DNS for the test hostnames points to the relay host, whose
proxy terminates TLS and forwards each request over HTTPS to the test host
(verifying its certificate per hostname); the test host trusts the relay's
X-Forwarded-For. Port 80 is forwarded for redirects; certificate challenges
for the relayed names are answered by the relay host itself (P11), so the
test host cannot obtain certificates for them through the relay.

Only the six test hostnames from a test profile are relayed; nothing else.
"""
import argparse
import ipaddress
import json
from pathlib import Path
import re
import yaml

NAMES = ['erp', 'drive', 'office', 'mail', 'dms', 'respond']


def prepare(profile):
    if profile.get('tier') != 'test':
        raise ValueError('Only a test workspace may be relayed')
    prefix = profile.get('ingress_prefix', 'cloud-test')
    if not re.fullmatch('[a-z0-9-]+', prefix): raise ValueError('Invalid route prefix')
    hosts = [profile['hosts'][name] for name in NAMES]
    for host in hosts:
        if not re.fullmatch(r'test[a-z0-9-]*\.[a-z0-9.-]+', host):
            raise ValueError('Only test hostnames may be relayed: ' + host)
    target = str(ipaddress.ip_address(profile['relay_target']))
    resolver = profile.get('cert_resolver', 'letsencrypt')
    # The relay host terminates TLS for the test hostnames with its own
    # certificate per name (P11: issued by its resolver through the HTTP
    # challenge, which the relay host answers itself; no copied wildcard) and
    # forwards HTTP over HTTPS to the test host, verifying the test host's
    # certificate for each hostname.
    # TCP pass-through by SNI is not used: browsers reuse ("coalesce") an
    # existing connection to the relay host for any hostname its certificate
    # covers, so requests for test hostnames arrive inside connections opened
    # for other names and would be answered by the relay host itself.
    routers, services, transports = {}, {}, {}
    for host in hosts:
        key = prefix + '-relay-' + host.split('.')[0]
        routers[key] = {'rule': 'Host(`' + host + '`)', 'entryPoints': ['https'], 'priority': 100000,
                        'service': key, 'tls': {'certResolver': resolver}}
        transports[key] = {'serverName': host}
        services[key] = {'loadBalancer': {'servers': [{'url': 'https://' + target}], 'passHostHeader': True,
                                          'serversTransport': key}}
    routers[prefix + '-relay-http'] = {'rule': ' || '.join('Host(`' + h + '`)' for h in hosts), 'entryPoints': ['http'],
                                       'priority': 52000, 'service': prefix + '-relay-http'}
    services[prefix + '-relay-http'] = {'loadBalancer': {'servers': [{'url': 'http://' + target}], 'passHostHeader': True}}
    # The relay host's own certificate challenges for these names are answered
    # here, above the port-80 relay, so its renewals never reach the test host.
    routers[prefix + '-relay-acme'] = {'rule': '(' + ' || '.join('Host(`' + h + '`)' for h in hosts) + ')'
                                               ' && PathPrefix(`/.well-known/acme-challenge/`)',
                                       'entryPoints': ['http'], 'priority': 100001, 'service': 'acme-http@internal'}
    return {'http': {'routers': routers, 'services': services, 'serversTransports': transports}}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--profile', required=True); p.add_argument('--output', required=True)
    a = p.parse_args()
    Path(a.output).write_text(yaml.safe_dump(prepare(json.loads(Path(a.profile).read_text())), sort_keys=False))
