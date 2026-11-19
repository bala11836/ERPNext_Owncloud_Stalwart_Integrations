#!/usr/bin/env python3
"""Prepare pinned upstream Mail plus the selected overlay and corresponding source.

Use a rendered release as --source for production URLs. Build context is new and
outside the repository; no deployment environment or secret files are copied.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import zipfile


def prepare(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or source in output.parents or output.exists():
        raise ValueError("Output must be a new directory outside the source tree")
    lock = json.loads((source / "integrations/mail/upstream.json").read_text())
    if lock["repository"] != "https://github.com/bulwarkmail/webmail":
        raise ValueError("Unexpected upstream repository")
    subprocess.run(["git", "clone", "--no-checkout", lock["repository"], str(output)], check=True)
    subprocess.run(["git", "-C", str(output), "checkout", "--detach", lock["commit"]], check=True)
    shutil.copytree(source / "integrations/mail/overlay", output, dirs_exist_ok=True)
    archive = output / "public/cloud-customization-source.zip"
    archive.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in output.rglob("*"):
            if not path.is_file() or path == archive:
                continue
            relative = path.relative_to(output)
            if any(p in {".git", "node_modules", ".next"} for p in relative.parts):
                continue
            if path.name.startswith(".env") or path.suffix in {".pem", ".key", ".zip"}:
                continue
            zipped.write(path, relative)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(prepare(args.source, args.output))
