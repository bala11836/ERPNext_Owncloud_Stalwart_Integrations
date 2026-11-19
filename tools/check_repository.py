#!/usr/bin/env python3
"""Offline syntax, schema and publication checks. Never reads a live site."""
import argparse
import ast
import json
import pathlib
import re
import sys

def check(root, deny=()):
    root=pathlib.Path(root);errors=[];count=0
    for p in root.rglob('*'):
        if not p.is_file() or any(x in p.parts for x in ['.git','node_modules','__pycache__','.runtime','.build']):
            continue
        if p.suffix not in {'.py','.js','.json','.ts','.tsx','.html','.md','.yml','.yaml','.toml','.svg','.txt','.sh'} and p.name not in {'Dockerfile','.env.example','.gitignore'}:
            continue
        text=p.read_text();count+=1
        for term in deny:
            if term and term.lower() in text.lower():errors.append(f'{p.relative_to(root)}: disallowed publication text')
        if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',text):errors.append(f'{p.relative_to(root)}: private key')
        if re.search(r'(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}',text):errors.append(f'{p.relative_to(root)}: credential token')
        try:
            if p.suffix=='.py':ast.parse(text,filename=str(p))
            if p.suffix=='.json':json.loads(text)
        except (SyntaxError,ValueError) as exc:errors.append(f'{p.relative_to(root)}: {exc}')
    if errors:raise ValueError('\n'.join(errors))
    return count

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',default=str(pathlib.Path(__file__).resolve().parents[1]));parser.add_argument('--deny-file');args=parser.parse_args()
    deny=json.loads(pathlib.Path(args.deny_file).read_text()) if args.deny_file else []
    print(f'Checked {check(args.root,deny)} source/doc files: passed')
