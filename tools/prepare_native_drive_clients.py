#!/usr/bin/env python3
"""Populate private fresh-identity inputs from pinned official native defaults.

Stock desktop/iOS clients use published compiled registration constants. Random
secrets would break them. No production credential is read or printed here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import yaml


def prepare(source,output):
    source,output=Path(source).resolve(),Path(output).resolve()
    if source in output.parents or source==output:raise ValueError('Keep identity values outside Git')
    lock=json.loads((source/'deployment/native-clients-lock.json').read_text())
    if lock['repository']!='https://github.com/owncloud/ocis-konnectd':raise ValueError('Unexpected native source')
    url='https://raw.githubusercontent.com/owncloud/ocis-konnectd/'+lock['commit']+'/'+lock['path']
    with urllib.request.urlopen(url,timeout=30) as response:data=response.read(1024*1024)
    if hashlib.sha256(data).hexdigest()!=lock['sha256']:raise ValueError('Native registration input checksum mismatch')
    native={row['id']:row for row in yaml.safe_load(data)['clients']}
    entries=json.loads((source/'integrations/authentik/configuration.json').read_text())['entries']
    expected=json.loads((source/'deployment/drive-clients.example.json').read_text())
    values=json.loads(output.read_text()) if output.exists() else {}
    configured=0
    for client in expected:
        if client['client_type']!='confidential':continue
        ident=client['client_id'];value=native[ident]['secret']
        provider=next(row for row in entries if row['attrs'].get('client_id')==ident)
        key=provider['attrs']['client_secret']['$secret']
        values[key]=value;configured+=1
    output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    output.write_text(json.dumps(values,indent=2)+'\n');output.chmod(0o600)
    return {'native_clients_prepared':configured,'live_credentials_read':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--output',required=True);args=parser.parse_args()
    print(prepare(args.source,args.output))
