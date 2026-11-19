#!/usr/bin/env python3
"""Run mock-based rules/security suites in separate processes, without a live site."""
import os
import pathlib
import subprocess
import sys

root=pathlib.Path(__file__).resolve().parents[1]
env=dict(os.environ,PYTHONPATH=str(root)+os.pathsep+os.environ.get('PYTHONPATH',''))
files=sorted((root/'tests').rglob('test_*.py'))
for p in files:
    result=subprocess.run([sys.executable,str(p)],cwd=root,env=env)
    if result.returncode:raise SystemExit(result.returncode)
print(f'{len(files)} isolated test suites passed; no live database used')
