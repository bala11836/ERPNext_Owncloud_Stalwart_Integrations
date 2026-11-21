#!/usr/bin/env python3
"""Render a source-IP-limited forward-auth bridge on an existing SSO host.

A second HTTPS proxy otherwise replaces X-Forwarded-Host with the SSO hostname.
Only the nominated test server(s) can use this fixed-host authentication context.
No credential, anonymous application access or wider origin permission is added.

`test_server_ip` is one public address or a list (e.g. old and new host during
a migration); it is not used for a relayed test host, which is reached only
over the private entry point. `auth_bridge_private` ({"entrypoint", "sources"}) adds a separate
router on the SSO proxy's private entry point for a test host that reaches it
over a private network such as a tailnet; the public router is not widened.
"""
import argparse
import ipaddress
import json
from pathlib import Path
import re
import yaml


def ranges_of(given):
    given=[given] if isinstance(given,str) else list(given)
    if not given:raise ValueError('At least one source address is required')
    return [a+('/128' if ':' in a else '/32') for a in (str(ipaddress.ip_address(x)) for x in given)]


def prepare(profile):
    hosts=profile['hosts'];prefix=profile.get('ingress_prefix','cloud-test')
    if profile.get('tier')!='test' or not hosts['erp'].startswith('test.'):
        raise ValueError('Only a test workspace may use this bridge')
    if not re.fullmatch('[a-z0-9-]+',prefix):raise ValueError('Invalid route prefix')
    source=prefix+'-auth-source';context=prefix+'-auth-context';path=prefix+'-auth-path'
    rule='Host(`'+hosts['sso']+'`) && Path(`/outpost.goauthentik.io/auth/'+prefix+'`)'
    service=profile['identity_service']
    # When the test hostnames are relayed by this host (prepare_test_relay.py),
    # its public HTTPS for them must be the pass-through: a public HTTPS route
    # for the test ERP host would capture that hostname. The callback route is
    # then served on the private entry point only, and no public source
    # address is trusted at all (a retired host's public address could later
    # belong to someone else).
    relayed=bool(profile.get('relay_target'))
    routers={};middlewares={}
    if not relayed:
        routers[prefix+'-auth-context']={'rule':rule,'entryPoints':['https'],'priority':51000,'service':service,
            'middlewares':[source,context,path],'tls':{}}
        middlewares[source]={'ipAllowList':{'sourceRange':ranges_of(profile['test_server_ip'])}}
    outpost=[] if relayed else ['https']
    private=profile.get('auth_bridge_private')
    if relayed and not private:raise ValueError('A relayed test host needs auth_bridge_private')
    if private:
        # A private entry point (e.g. bound only to the SSO host's tailnet
        # address). Its traffic may arrive address-translated, so it gets its
        # own router and allow list (e.g. the Docker gateway the private
        # traffic is seen from) instead of widening the public one.
        entry=private['entrypoint']
        if not re.fullmatch('[A-Za-z0-9-]+',entry) or entry in ('http','https'):raise ValueError('Invalid private entry point')
        private_source=prefix+'-auth-private-source'
        routers[prefix+'-auth-context-private']={'rule':rule,'entryPoints':[entry],'priority':51000,'service':service,
            'middlewares':[private_source,context,path],'tls':{}}
        middlewares[private_source]={'ipAllowList':{'sourceRange':ranges_of(private['sources'])}}
        outpost=outpost+[entry]
    routers[prefix+'-outpost']={'rule':'Host(`'+hosts['erp']+'`) && PathPrefix(`/outpost.goauthentik.io/`)',
        'entryPoints':outpost,'priority':51000,'service':service,'tls':{}}
    middlewares[context]={'headers':{'customRequestHeaders':{'X-Forwarded-Host':hosts['erp'],'X-Forwarded-Proto':'https'}}}
    middlewares[path]={'replacePath':{'path':'/outpost.goauthentik.io/auth/traefik'}}
    return {'http':{'routers':routers,'middlewares':middlewares}}



def forwarded_trust(profile):
    """Static setting for the SSO host's proxy (P65): trust forwarded headers on the bridge's private entry point
    from the bridge sources only. Without it the proxy drops X-Forwarded-Uri sent by the test proxy, so the sign-in
    gateway returns to "/" (the landing page) after the passkey instead of the requested page. The public entry
    points are never changed. Returns (entrypoint, ranges) or None when there is no private bridge."""
    private=profile.get('auth_bridge_private')
    if not private:return None
    entry=private['entrypoint']
    if not re.fullmatch('[A-Za-z0-9-]+',entry) or entry in ('http','https','web','websecure'):raise ValueError('Invalid private entry point')
    return entry,ranges_of(private['sources'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--profile',required=True);p.add_argument('--output')
    p.add_argument('--print-forwarded-trust',action='store_true',help='print the entry point and sources for tools/sso_proxy_trust.py')
    a=p.parse_args();profile=json.loads(Path(a.profile).read_text())
    if a.print_forwarded_trust:
        trust=forwarded_trust(profile);print(json.dumps({'entrypoint':trust[0],'trusted':trust[1]} if trust else {}))
    if a.output:Path(a.output).write_text(yaml.safe_dump(prepare(profile),sort_keys=False))
