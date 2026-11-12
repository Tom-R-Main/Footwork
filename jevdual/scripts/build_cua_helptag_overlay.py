"""Reconstruct the additive HelpTag SDK candidate; build only from project-local offline caches."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
VENDOR = PROJECT / 'jevdual/vendor/cua-driver'
MANIFEST = VENDOR / 'patches/ordinary-helptag.json'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(output: Path) -> tuple[Path, dict]:
    if not output.resolve().is_relative_to(PROJECT):
        raise ValueError('output must remain inside the active project')
    record = json.loads(MANIFEST.read_text())
    original = (VENDOR / 'native-source.tar.gz').read_bytes()
    patch = VENDOR / 'patches/ordinary-helptag.patch'
    if sha(original) != record['base_archive_sha256'] or sha(patch.read_bytes()) != record['patch_sha256']:
        raise ValueError('base archive or additive patch checksum mismatch')
    spec = importlib.util.spec_from_file_location('cua_build_support', VENDOR / 'build_support.py')
    support = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(support)
    source = output / 'source-build'
    support.extract_source(VENDOR / 'native-source.tar.gz', source)
    subprocess.run(['patch', '--batch', '--forward', '-p1', '-i', str(patch.resolve())], cwd=source, check=True)
    memory = io.BytesIO()
    with (
        tarfile.open(fileobj=io.BytesIO(original), mode='r:gz') as base,
        gzip.GzipFile(filename='', fileobj=memory, mode='wb', mtime=0, compresslevel=9) as compressed,
        tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT) as bundle,
    ):
        for member in sorted(base.getmembers(), key=lambda item: item.name):
            info = tarfile.TarInfo(member.name)
            info.mode = member.mode
            if member.isdir():
                info.type = tarfile.DIRTYPE
                bundle.addfile(info)
            else:
                content = (source / member.name).read_bytes()
                info.size = len(content)
                bundle.addfile(info, io.BytesIO(content))
    archive = memory.getvalue()
    if sha(archive) != record['patched_archive_sha256']:
        raise ValueError('reconstructed candidate source checksum mismatch')
    package = output / 'package'
    package.mkdir(parents=True, exist_ok=True)
    for name in ('pyproject.toml', 'hatch_build.py', 'build_support.py', 'README.md', 'LICENSE'):
        shutil.copy2(VENDOR / name, package / name)
    shutil.copytree(VENDOR / 'src', package / 'src', dirs_exist_ok=True)
    (package / 'native-source.tar.gz').write_bytes(archive)
    for name in ('pyproject.toml', 'build_support.py'):
        path = package / name
        text = path.read_text().replace(record['base_version'], record['version'])
        text = text.replace(record['base_archive_sha256'], record['patched_archive_sha256'])
        path.write_text(text)
    return package, record


def build(output: Path) -> str:
    package, record = prepare(output)
    cache = PROJECT / 'output/cua-046-upgrade'
    if not (cache / 'cargo-home/registry').is_dir() or not (cache / 'target').is_dir():
        raise RuntimeError('existing project-local offline Cargo caches are required')
    os.environ.update(CARGO_HOME=str(cache / 'cargo-home'), CARGO_TARGET_DIR=str(cache / 'target'),
                      CARGO_NET_OFFLINE='true', RUSTUP_AUTO_INSTALL='0',
                      FOOTWORK_CUA_BUILD_CACHE=str(output / 'native-cache'))
    archives = cache / 'uv-cache/archive-v0'
    sys.path[:0] = [str(archives / item) for item in (
        'EriPAccuE05EIPx5WAx6y', 'THv7pqWbNiqi3j7G1z86P', '2LNpUb3Chd6AtNOjA8GWZ',
        '6sJEXuvhXmUW9X44kb9Dx', '5-i8i0vaYXHcus3jMsRoR', '3SmfQmliy_Okivr1yvToZ')]
    if importlib.metadata.version('hatchling') != '1.32.4':
        raise RuntimeError('cached Hatchling1.32.4 is required; no install/fetch is attempted')
    from hatchling.build import build_wheel

    wheelhouse = output / 'wheelhouse'
    wheelhouse.mkdir(exist_ok=True)
    os.chdir(package)
    wheel = build_wheel(str(wheelhouse.resolve()))
    (output / 'build-plan.json').write_text(json.dumps(record, indent=2) + '\n')
    return str(wheelhouse / wheel)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=PROJECT / 'jevdual/output/foreground-helptag')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    if args.prepare_only:
        package, _ = prepare(output)
        print(package)
    else:
        print(build(output))
