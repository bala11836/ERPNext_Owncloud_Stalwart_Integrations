"""Validate data-only refresh archives before touching any test service.

Treat even a trusted server's archive as untrusted filesystem input. The source
identity, byte budget, paths, regular-file types and hashes must all match.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import shutil
import tarfile

DIRECTORIES={'erp-files','dms-media','dms-data','dms-consume','drive-data','mail-data','mail-config'}
FILES={'erp.sql.gz','dms.sql.gz','drive-runtime.private.yaml','document-jobs.sqlite3','document-enrollment.json'}


def validate_extract(archive, destination, source_instance, max_bytes=100*1024**3):
    destination=Path(destination)
    if destination.exists():raise ValueError('Extraction requires a new private directory')
    with tarfile.open(archive,'r:gz') as stream:
        members=stream.getmembers()
        names=set();total=0
        for member in members:
            path=PurePosixPath(member.name)
            if (not member.isfile() or path.is_absolute() or '..' in path.parts
                    or str(path)!=member.name or member.name in names):
                raise ValueError('Unsafe or duplicate snapshot entry')
            if member.name!='manifest.json' and path.parts[0] not in DIRECTORIES and member.name not in FILES:
                raise ValueError('Unexpected snapshot content')
            if path.parts[:3]==('drive-data','web','assets'):
                raise ValueError('Application code does not belong in a data refresh')
            names.add(member.name);total+=member.size
            if total>max_bytes:raise ValueError('Snapshot exceeds the configured byte budget')
        if 'manifest.json' not in names:raise ValueError('Missing snapshot manifest')
        manifest_member=stream.getmember('manifest.json')
        if manifest_member.size>16*1024**2:raise ValueError('Oversized snapshot manifest')
        manifest=json.load(stream.extractfile(manifest_member))
        if (manifest.get('format')!=1 or manifest.get('source_instance')!=source_instance
                or manifest.get('code_included') is not False
                or manifest.get('identity_database_included') is not False):
            raise ValueError('Snapshot identity or format does not match')
        if set(manifest['files'])!=names-{'manifest.json'}:raise ValueError('Manifest file set mismatch')
        if not {'erp.sql.gz','dms.sql.gz','drive-runtime.private.yaml'}<=names:
            raise ValueError('Incomplete four-app snapshot')
        links=manifest.get('links',{});directories=manifest.get('directories',[])
        if not isinstance(links,dict) or not isinstance(directories,list):raise ValueError('Invalid native tree metadata')
        def valid_path(name):
            path=PurePosixPath(name)
            return (not path.is_absolute() and '..' not in path.parts and str(path)==name
                    and path.parts and path.parts[0] in DIRECTORIES
                    and path.parts[:3]!=('drive-data','web','assets'))
        for name in directories:
            if not valid_path(name) or name in names or name in links:raise ValueError('Invalid native directory entry')
        for name,target in links.items():
            if (not valid_path(name) or not name.startswith('drive-data/') or name in names
                    or not isinstance(target,str) or PurePosixPath(target).is_absolute()):
                raise ValueError('Invalid native Drive link')
            resolved=posixpath.normpath(str(PurePosixPath(name).parent/PurePosixPath(target)))
            if resolved!='drive-data' and not resolved.startswith('drive-data/'):
                raise ValueError('Native Drive link escapes its data root')
        for name in (names-{'manifest.json'})|set(links)|set(directories):
            if any(str(parent) in links for parent in PurePosixPath(name).parents):
                raise ValueError('Snapshot entry traverses a symbolic-link parent')
        # Check every stream before creating any files. A second local read is
        # cheap compared with discovering corruption after stopping the target.
        for member in members:
            if member.name=='manifest.json':continue
            row=manifest['files'][member.name]
            with stream.extractfile(member) as contents:
                digest=hashlib.file_digest(contents,'sha256').hexdigest()
            if row.get('bytes')!=member.size or row.get('sha256')!=digest:
                raise ValueError('Snapshot checksum mismatch')
        destination.mkdir(parents=True,mode=0o700)
        try:
            for name in directories:(destination/name).mkdir(parents=True,exist_ok=True,mode=0o700)
            for member in members:
                target=destination/member.name
                target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                with stream.extractfile(member) as contents,target.open('xb') as output:
                    while chunk:=contents.read(1024*1024):output.write(chunk)
                target.chmod(0o600)
            for name,target in links.items():
                link=destination/name;link.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                link.symlink_to(target)
            # Check actual chained-link/.. semantics after creating links, with
            # no subsequent writes through them. Lexical normalization alone
            # misses a/../ escape when a itself points to the data root.
            drive=(destination/'drive-data').resolve()
            for name in links:
                try:resolved=(destination/name).resolve(strict=True)
                except FileNotFoundError:resolved=(destination/name).resolve()
                if resolved!=drive and drive not in resolved.parents:
                    raise ValueError('Chained native Drive link escapes its data root')
        except (OSError,RuntimeError,ValueError) as error:
            shutil.rmtree(destination)
            raise ValueError('Native snapshot tree validation failed') from error
    return manifest
