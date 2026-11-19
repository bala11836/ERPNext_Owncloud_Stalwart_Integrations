#!/usr/bin/env python3
"""Render the retained native authentik graph, without exporting any users/keys.

Run outside authentik to produce YAML; apply using its native import command.
Secrets JSON is a private runtime file. Existing instances must use the migration
procedure: this fresh-install graph is not an invitation to overwrite live flows.
"""
import argparse
import json
from pathlib import Path
import secrets
import yaml


class KeyOf(str):
    pass


class Find(list):
    pass


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(KeyOf, lambda d, v: d.represent_scalar('!KeyOf', str(v)))
Dumper.add_representer(Find, lambda d, v: d.represent_sequence('!Find', list(v)))


def retained(entries):
    """Keep roots and their forward dependencies plus attached native bindings."""
    by_id = {e['id']: e for e in entries}
    selected = {e['id'] for e in entries if e['model'] in {
        'authentik_core.application', 'authentik_core.group', 'authentik_brands.brand'}}

    def refs(value):
        if isinstance(value, dict):
            if '$ref' in value:
                yield value['$ref']
            else:
                for child in value.values():
                    yield from refs(child)
        elif isinstance(value, list):
            for child in value:
                yield from refs(child)

    while True:
        before = set(selected)
        for ident in list(selected):
            if ident not in by_id:
                raise ValueError('Missing configuration reference: ' + ident)
            selected.update(refs(by_id[ident]))
        for entry in entries:
            if entry['model'] not in {'authentik_flows.flowstagebinding', 'authentik_policies.policybinding'}:
                continue
            target = (entry['identifiers'] | entry['attrs']).get('target', {})
            if isinstance(target, dict) and target.get('$ref') in selected:
                selected.add(entry['id'])
        if selected == before:
            ordered, visiting, visited = [], set(), set()

            def visit(ident):
                if ident in visited:
                    return
                if ident in visiting:
                    raise ValueError('Cyclic configuration reference: ' + ident)
                visiting.add(ident)
                for dependency in refs(by_id[ident]):
                    visit(dependency)
                visiting.remove(ident)
                visited.add(ident)
                ordered.append(by_id[ident])

            for entry in entries:
                if entry['id'] in selected:
                    visit(entry['id'])
            return ordered


def render(source, domain, private_values):
    if not domain or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-.' for c in domain):
        raise ValueError('Use a lower-case DNS domain')

    def resolve(value):
        if isinstance(value, dict):
            if '$ref' in value:
                return KeyOf(value['$ref'])
            if '$certificate' in value:
                return Find(['authentik_crypto.certificatekeypair', ['name', 'authentik Self-signed Certificate']])
            if '$secret' in value:
                return private_values.setdefault(value['$secret'], secrets.token_urlsafe(48))
            return {k: resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [resolve(v) for v in value]
        if isinstance(value, str):
            return value.replace('example.com', domain)
        return value

    entries = retained(json.loads(Path(source).read_text())['entries'])
    return yaml.dump({'version': 1, 'metadata': {'name': 'Cloud workspace retained configuration'},
                      'entries': resolve(entries)}, Dumper=Dumper, sort_keys=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default=str(Path(__file__).resolve().parents[1] / 'integrations/authentik/configuration.json'))
    parser.add_argument('--domain', required=True)
    parser.add_argument('--secrets', required=True, help='Private JSON file, outside Git')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    secret_file = Path(args.secrets)
    values = json.loads(secret_file.read_text()) if secret_file.exists() else {}
    rendered = render(args.source, args.domain, values)
    secret_file.write_text(json.dumps(values, indent=2) + '\n')
    secret_file.chmod(0o600)
    Path(args.output).write_text(rendered)
    Path(args.output).chmod(0o600)
