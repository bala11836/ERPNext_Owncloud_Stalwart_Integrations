"""P36: the repository is a set of self-contained, reusable modules.

modules.json assigns every tracked file to exactly one module (repository-level
files and docs/ excepted). Each module has a README with the sections needed
to reuse it on its own, its own tests, declared dependencies and the upstream
projects it adapts, with their licenses (owner principles 2, 4 and 6).
"""
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / 'modules.json').read_text())
SECTIONS = ['## Purpose', '## Contents', '## Requirements', '## Reuse', '## Configuration', '## Tests', '## Licenses']


def pattern(glob):
    out = ''
    i = 0
    while i < len(glob):
        if glob.startswith('**', i):
            out += '.*'
            i += 2
        elif glob[i] == '*':
            out += '[^/]*'
            i += 1
        else:
            out += re.escape(glob[i])
            i += 1
    return re.compile(out + r'\Z')


def matches(path, globs):
    return any(pattern(g).match(path) for g in globs)


def tracked_files():
    try:
        out = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        files = [line for line in out.splitlines() if line]
        if files:
            return files
    except (OSError, subprocess.CalledProcessError):
        pass
    skip = {'.git', '__pycache__', 'node_modules'}
    return [str(p.relative_to(ROOT)) for p in ROOT.rglob('*')
            if p.is_file() and not skip & set(p.relative_to(ROOT).parts)]


def owners(path):
    return [m['id'] for m in MANIFEST['modules']
            if matches(path, m['paths']) and not matches(path, m.get('exclude', []))]


class ModuleManifestTests(unittest.TestCase):
    def test_every_file_belongs_to_exactly_one_module(self):
        unowned, shared = [], []
        for path in tracked_files():
            if matches(path, MANIFEST['repository_files']):
                continue
            found = owners(path)
            if not found:
                unowned.append(path)
            elif len(found) > 1:
                shared.append((path, found))
        self.assertEqual(unowned, [], 'files without a module')
        self.assertEqual(shared, [], 'files owned by more than one module')

    def test_module_readmes_have_reuse_sections(self):
        for module in MANIFEST['modules']:
            readme = ROOT / module['readme']
            self.assertTrue(readme.is_file(), module['readme'])
            text = readme.read_text()
            for section in SECTIONS:
                self.assertIn(section, text, f"{module['readme']} lacks {section}")
            self.assertIn('AI', text, f"{module['readme']} lacks the AI-assistance note")

    def test_tests_dependencies_and_upstream_are_declared(self):
        ids = [m['id'] for m in MANIFEST['modules']]
        self.assertEqual(len(ids), len(set(ids)))
        for module in MANIFEST['modules']:
            self.assertTrue(module['tests'], module['id'])
            for test in module['tests']:
                self.assertTrue((ROOT / test).is_file(), test)
            for dep in module['depends_on']:
                self.assertIn(dep, ids, f"{module['id']} depends on unknown {dep}")
            for upstream in module['upstream']:
                self.assertTrue(upstream.get('name') and upstream.get('license') and upstream.get('url'), upstream)

    def test_dependencies_have_no_cycles(self):
        graph = {m['id']: m['depends_on'] for m in MANIFEST['modules']}
        state = {}

        def visit(node, trail):
            if state.get(node) == 'done':
                return
            self.assertNotEqual(state.get(node), 'active', 'cycle: ' + ' -> '.join(trail + [node]))
            state[node] = 'active'
            for dep in graph[node]:
                visit(dep, trail + [node])
            state[node] = 'done'

        for node in graph:
            visit(node, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
