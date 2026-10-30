"""Reproduce cleanup2 source bytes from the hash-pinned base and shipped diff."""
import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--upstream-archive', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
project = Path(__file__).resolve().parents[3]
vendor = project / 'vendor/cua-driver'
manifest = json.loads((vendor / 'patches/session-cleanup-join.json').read_text())
patch = vendor / 'patches/session-cleanup-join.patch'
assert hashlib.sha256(patch.read_bytes()).hexdigest() == manifest['patch_sha256']
assert hashlib.sha256(args.upstream_archive.read_bytes()).hexdigest() == manifest['upstream_archive_sha256']
spec = importlib.util.spec_from_file_location('native_build', vendor / 'build_support.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
with tempfile.TemporaryDirectory(prefix='footwork-native-rebuild-') as temporary:
    source = Path(temporary)
    build.extract_source(args.upstream_archive, source)
    subprocess.run(['git', 'apply', '--check', str(patch)], cwd=source, check=True)
    subprocess.run(['git', 'apply', str(patch)], cwd=source, check=True)
    for name, expected in manifest['files'].items():
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == expected['after'], name
    buffer = io.BytesIO()
    with tarfile.open(args.upstream_archive) as original, tarfile.open(fileobj=buffer, mode='w', format=tarfile.PAX_FORMAT) as result:
        for member in original:
            content = (source / member.name).read_bytes() if member.isfile() else None
            if content is not None:
                member.size = len(content)
            result.addfile(member, io.BytesIO(content) if content is not None else None)
    encoded = io.BytesIO()
    with gzip.GzipFile(fileobj=encoded, filename='', mode='wb', mtime=0, compresslevel=9) as result:
        result.write(buffer.getvalue())
    data = encoded.getvalue()
    digest = hashlib.sha256(data).hexdigest()
    assert digest == manifest['patched_archive_sha256']
    with args.output.open('xb') as result:
        result.write(data)
    print(json.dumps({'verified': True, 'sha256': digest, 'bytes': len(data), 'changed_files': len(manifest['files'])}))
