#!/usr/bin/env python3
"""Restrict the isolated test workspace to local apps and its existing SSO.

Run as root before restoring business data. Does not alter host traffic or other
Docker networks. IPv6 must be disabled on this dedicated workspace network.
"""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import socket
import secrets
import subprocess


def allowed_sso_addresses(profile,resolve=None):
    """SSO's public IPv4 addresses plus any private (e.g. tailnet) addresses the
    proxy is pinned to for SSO through `proxy_hosts`; only the SSO host's."""
    resolve=resolve or (lambda host:{row[4][0] for row in socket.getaddrinfo(host,443,socket.AF_INET)})
    sso=profile['hosts']['sso']
    addresses=set(resolve(sso))
    pinned=(profile.get('proxy_hosts') or {}).get(sso)
    if pinned:addresses.add(str(ipaddress.IPv4Address(pinned)))
    return addresses


def apply(profile):
    if profile.get('tier')!='test':raise ValueError('Only test egress may be restricted')
    network=json.loads(subprocess.check_output(['docker','network','inspect',profile['network']]))[0]
    if network.get('EnableIPv6'):raise ValueError('Disable IPv6 on the isolated test network first')
    subnet=str(ipaddress.ip_network(profile['network_subnet']))
    if subnet not in {row.get('Subnet') for row in network['IPAM']['Config']}:
        raise ValueError('Runtime subnet does not match the selected Docker network')
    chain='CTEST-'+hashlib.sha256(profile['instance'].encode()).hexdigest()[:12]
    def call(*args,check=True):
        return subprocess.run(['iptables','-w','10',*args],check=check,capture_output=True)
    exists=call('-S',chain,check=False).returncode==0
    if not exists:call('-N',chain)
    # Populate a fresh chain while the fixed source rule remains fail-closed.
    staging=chain+'-'+secrets.token_hex(3)
    call('-N',staging)
    call('-A',staging,'-m','conntrack','--ctstate','ESTABLISHED,RELATED','-j','ACCEPT')
    call('-A',staging,'-d',subnet,'-j','ACCEPT')
    addresses=allowed_sso_addresses(profile)
    for address in sorted(addresses):
        call('-A',staging,'-d',str(ipaddress.ip_address(address)),'-p','tcp','--dport','443','-j','ACCEPT')
    smtp=profile.get('test_form_smtp')
    if smtp and smtp.get('address'):
        # P38: owner-approved form emails reach only this SMTP address/port.
        call('-A',staging,'-d',str(ipaddress.IPv4Address(smtp['address'])),'-p','tcp','--dport',str(int(smtp.get('port',465))),'-j','ACCEPT')
    call('-A',staging,'-j','REJECT')
    # Only this workspace source subnet jumps through this instance's chain.
    if call('-C','DOCKER-USER','-s',subnet,'-j',chain,check=False).returncode:
        call('-A',chain,'-j','REJECT')
        call('-I','DOCKER-USER','1','-s',subnet,'-j',chain)
    # Replace the sole jump atomically, without an empty accepting interval.
    call('-R',chain,'1','-j',staging)
    return {'restricted_network':profile['network'],'sso_ipv4_addresses':len(addresses)}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--profile',required=True)
    print(apply(json.loads(Path(parser.parse_args().profile).read_text())))
