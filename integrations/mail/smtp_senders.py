#!/usr/bin/env python3
"""Enroll SMTP-only service accounts through native Stalwart v1.1 JMAP.

Run deliberately on production, never during test refresh. Secrets are generated
by the server and written only to a root-private file outside the checkout.
Shared sender membership grants send-as; no mailbox-reading/admin rights exist.
"""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re

from stalwart_bootstrap import Client


def configure(profile,output):
    if profile.get('tier')!='production':raise ValueError('Test SMTP enrollment is disabled')
    output=Path(output).resolve();source=Path(__file__).resolve().parents[2]
    if output==source or source in output.parents:raise ValueError('Credentials must stay outside the repository')
    output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    state=json.loads(output.read_text()) if output.exists() else {}
    client=Client(profile['admin_url'],profile['recovery_credential'])
    domains=client.call('x:Domain/get',{})['list']
    domain=next(row['id'] for row in domains if row['name']==profile['mail_domain'])
    accounts=client.call('x:Account/get',{})['list']
    by_name={row['name']:row for row in accounts if row.get('domainId')==domain}
    for sender in profile['senders']:
        name=sender['name']
        if not re.fullmatch('[a-z0-9.-]+',name) or not (name.startswith('smtp-') or name.endswith('-noreply')):
            raise ValueError('Use a dedicated SMTP service account name')
        addresses={str(ipaddress.ip_network(value,strict=False)):True for value in sender['allowed_networks']}
        if not addresses:raise ValueError('SMTP credentials require an explicit source-network restriction')
        group=by_name[sender.get('shared_sender','noreply')]
        if group.get('@type')!='Group':raise ValueError('The integration sender must be a shared group mailbox')
        value={'@type':'User','name':name,'domainId':domain,'description':'SMTP-only service sender',
            'roles':{'@type':'Custom','roleIds':{}},
            'permissions':{'@type':'Replace','enabledPermissions':{'authenticate':True,'emailSend':True},'disabledPermissions':{}},
            'memberGroupIds':{group['id']:True}}
        if name in by_name:
            if by_name[name].get('@type')!='User':raise ValueError('Conflicting non-user service account')
            ident=by_name[name]['id'];client.call('x:Account/set',{'update':{ident:value}})
        else:ident=client.call('x:Account/set',{'create':{'sender':value}})['created']['sender']['id']
        old=state.get(name)
        if old and old['account_id']==ident:
            client.call('x:AppPassword/set',{'accountId':ident,'update':{old['credential_id']:{'allowedIps':addresses}}})
        else:
            credential=client.call('x:AppPassword/set',{'accountId':ident,'create':{'smtp':{
                'description':'SMTP-only integration sender','permissions':{'@type':'Replace',
                    'permissions':{'authenticate':True,'emailSend':True}},'allowedIps':addresses}}})['created']['smtp']
            state[name]={'account_id':ident,'credential_id':credential['id'],'password':credential['secret'],
                'username':name+'@'+profile['mail_domain'],'from_address':sender.get('shared_sender','noreply')+'@'+profile['mail_domain'],
                'host':profile['smtp_hostname'],'port':465,'ssl':True}
        temporary=output.with_suffix('.pending');temporary.write_text(json.dumps(state,indent=2)+'\n');temporary.chmod(0o600)
        os.replace(temporary,output)
    return {'smtp_only_services':len(profile['senders']),'credentials_displayed':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--profile',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();os.umask(0o077);print(configure(json.loads(Path(a.profile).read_text()),a.output))
