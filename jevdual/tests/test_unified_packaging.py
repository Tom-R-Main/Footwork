"""Installed tool resources survive checkout isolation and remain source-identical."""
from __future__ import annotations

import importlib.util
import json
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tool_snapshot_is_current_and_excludes_private_artifacts():
    sync = script('sync_tool_resources')
    assert sync.synchronize(ROOT.parent, check=True) > 50
    names = sync.inventory(ROOT.parent)
    assert 'physical-workcell/scene.xml' in names
    assert 'desk-inbox-experiment/recognize.swift' in names
    assert not any('test_' in name or '.test.' in name or '/output/' in name for name in names)


def test_consumer_wheel_installs_all_runtime_assets_outside_checkout(tmp_path):
    builder = script('build_capability_wheel')
    wheel = builder.build(ROOT, tmp_path / 'wheels')
    installed = tmp_path / 'installed'
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(installed)
        names = archive.namelist()
        assert 'jevdual/_tool_resources/physical-workcell/scene.xml' in names
        assert 'jevdual/_tool_resources/browser-inspection/capture.mjs' in names
        metadata = archive.read('jevdual-0.0.1.dist-info/METADATA').decode()
        assert 'Provides-Extra: tools' in metadata
        assert 'mujoco==3.15.0; extra == "tools"' in metadata
    code = '''import sys,json;sys.path.insert(0,sys.argv[1]);from importlib.resources import files
p=files("jevdual").joinpath("_tool_resources")
print(json.dumps({"scene":p.joinpath("physical-workcell/scene.xml").is_file(),"manifest":json.loads(p.joinpath("MANIFEST.json").read_text())}))'''
    result = subprocess.run([sys.executable, '-I', '-S', '-c', code, str(installed)], cwd=tmp_path,
                            capture_output=True, text=True, check=True)
    got = json.loads(result.stdout)
    assert got['scene'] and 'browser-inspection/capture.mjs' in got['manifest']


def test_installer_refuses_modified_bundle_before_creating_environment(tmp_path):
    sys.path.insert(0, str(ROOT / 'scripts'))
    try:
        bundle = script('build_agent_bundle')
    finally:
        sys.path.remove(str(ROOT / 'scripts'))
    installer = tmp_path / 'install.py'
    installer.write_text(bundle.INSTALLER)
    (tmp_path / 'product.whl').write_bytes(b'changed')
    (tmp_path / 'MANIFEST.json').write_text(json.dumps({'files': {'product.whl': '0' * 64}}))
    target = tmp_path / 'must-not-exist'
    result = subprocess.run([sys.executable, str(installer), '--venv', str(target)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 2 and 'checksum mismatch' in result.stderr
    assert not target.exists()


def test_installer_refuses_unverified_role_pointer(tmp_path):
    import hashlib
    sys.path.insert(0, str(ROOT / 'scripts'))
    try:
        bundle = script('build_agent_bundle')
    finally:
        sys.path.remove(str(ROOT / 'scripts'))
    installer = tmp_path / 'install.py'
    installer.write_text(bundle.INSTALLER)
    wheel = tmp_path / 'verified.whl'
    wheel.write_bytes(b'verified bytes')
    manifest = {'files': {'verified.whl': hashlib.sha256(wheel.read_bytes()).hexdigest()},
                'product': str(tmp_path.parent / 'unverified.whl'), 'cua': 'verified.whl'}
    (tmp_path / 'MANIFEST.json').write_text(json.dumps(manifest))
    target = tmp_path / 'must-not-exist'
    result = subprocess.run([sys.executable, str(installer), '--venv', str(target)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 2 and 'invalid bundle wheel role' in result.stderr
    assert not target.exists()


def installer_module():
    sys.path.insert(0, str(ROOT / 'scripts'))
    try:
        bundle = script('build_agent_bundle')
    finally:
        sys.path.remove(str(ROOT / 'scripts'))
    return bundle


def local_cua_tag():
    machine = platform.machine().lower()
    machine = {'amd64': 'x86_64', 'aarch64': 'arm64'}.get(machine, machine)
    if sys.platform == 'darwin':
        return 'macosx_13_0_' + machine
    if sys.platform == 'linux':
        return 'linux_' + {'arm64': 'aarch64'}.get(machine, machine)
    return 'win_' + {'x86_64': 'amd64'}.get(machine, machine)


def fixture_bundle(root, *, tag=None, requires=None):
    """Tiny real wheels exercise the installer without claiming Footwork runtime qualification."""
    import hashlib

    root.mkdir()
    installer = root / 'install.py'
    installer.write_text(installer_module().INSTALLER)
    product = 'jevdual-0.0.1-py3-none-any.whl'
    cua = 'cua_driver-0.38.0-py3-none-' + (tag or local_cua_tag()) + '.whl'
    for name, distribution in ((product, 'jevdual'), (cua, 'cua_driver')):
        version = '0.0.1' if distribution == 'jevdual' else '0.38.0'
        info = f'{distribution}-{version}.dist-info/'
        metadata = f'Metadata-Version: 2.1\nName: {distribution}\nVersion: {version}\n'
        if requires and distribution == 'jevdual':
            metadata += f'Requires-Dist: {requires}\n'
        entries = {
            info + 'METADATA': metadata,
            info + 'WHEEL': 'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: ' + name.rsplit('-', 3)[1]
            + '-none-' + name.rsplit('-', 1)[1][:-4] + '\n',
        }
        if distribution == 'jevdual':
            entries['fixture_cli.py'] = 'def main():\n    print("fixture tools available")\n'
            entries[info + 'entry_points.txt'] = '[console_scripts]\nfootwork = fixture_cli:main\n'
        entries[info + 'RECORD'] = ''.join(f'{path},,\n' for path in [*entries, info + 'RECORD'])
        with zipfile.ZipFile(root / name, 'w') as archive:
            for path, content in entries.items():
                archive.writestr(path, content)
    manifest = {'schema_version': 1, 'product': product, 'cua': cua,
                'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()}}
    (root / 'MANIFEST.json').write_text(json.dumps(manifest))
    return installer


def run_installer(installer, target, monkeypatch):
    # An existing interpreter plus pip must suffice even when PATH has no uv or compiler.
    monkeypatch.setenv('PATH', str(installer.parent / 'empty-path'))
    return subprocess.run(
        [sys._base_executable, str(installer), '--venv', str(target), '--offline', '--core-only'],
        capture_output=True, text=True, check=False,
    )


def test_installer_uses_existing_python_and_pip_without_uv(tmp_path, monkeypatch):
    installer = fixture_bundle(tmp_path / 'bundle')
    target = tmp_path / 'installed'
    result = run_installer(installer, target, monkeypatch)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout.splitlines()[-1])
    assert receipt['installed'] is True
    assert Path(receipt['environment']) == target
    observed = subprocess.run([receipt['executable'], 'tools'], capture_output=True, text=True, check=True)
    assert observed.stdout.strip() == 'fixture tools available'
    # Reusing an environment is refused without changing its entrypoint.
    before = Path(receipt['executable']).read_bytes()
    retry = run_installer(installer, target, monkeypatch)
    assert retry.returncode == 2 and 'never overwritten' in retry.stderr
    assert Path(receipt['executable']).read_bytes() == before


def test_installer_uses_bundled_ensurepip_without_uv_or_base_pip(tmp_path, monkeypatch):
    installer = fixture_bundle(tmp_path / 'bundle')
    base = tmp_path / 'python-without-pip'
    subprocess.run([sys._base_executable, '-I', '-m', 'venv', '--without-pip', str(base)], check=True)
    selected = base / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    probe = subprocess.run(
        [str(selected), '-I', '-c', 'import importlib.util;print(importlib.util.find_spec("pip"))'],
        check=True, capture_output=True, text=True,
    )
    assert probe.stdout.strip() == 'None'
    monkeypatch.setenv('PATH', str(tmp_path / 'empty-path'))
    target = tmp_path / 'installed'
    result = subprocess.run(
        [str(selected), str(installer), '--venv', str(target), '--offline', '--core-only'],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout.splitlines()[-1])
    assert receipt['installed'] is True
    observed = subprocess.run([receipt['executable'], 'tools'], check=True, capture_output=True, text=True)
    assert observed.stdout.strip() == 'fixture tools available'
    # Bootstrapping is confined to the destination; the selected interpreter stays pip-free.
    after = subprocess.run(
        [str(selected), '-I', '-c', 'import importlib.util;print(importlib.util.find_spec("pip"))'],
        check=True, capture_output=True, text=True,
    )
    assert after.stdout.strip() == 'None'


def test_installer_missing_pip_ensurepip_and_uv_refuses_before_creating_environment(tmp_path, monkeypatch):
    installer = fixture_bundle(tmp_path / 'bundle')
    spec = importlib.util.spec_from_file_location('generated_bundle_installer_missing_tools', installer)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    actual_run = subprocess.run

    def run(command, **kwargs):
        assert command[1:3] == ['-I', '-c'], 'no environment creation or installer should be invoked'
        result = actual_run(command, **kwargs)
        host = json.loads(result.stdout)
        host.update(pip=None, ensurepip=False)
        result.stdout = json.dumps(host)
        return result

    target = tmp_path / 'must-not-exist'
    monkeypatch.setenv('PATH', str(tmp_path / 'empty-path'))
    monkeypatch.setattr(module.subprocess, 'run', run)
    monkeypatch.setattr(sys, 'argv', [str(installer), '--venv', str(target), '--offline'])
    with pytest.raises(SystemExit) as failure:
        module.main()
    assert failure.value.code == 2
    assert not target.exists()


@pytest.mark.skipif(shutil.which('uv') is None, reason='existing uv executable is required for this route')
def test_installer_keeps_uv_route_offline(tmp_path):
    installer = fixture_bundle(tmp_path / 'bundle')
    result = subprocess.run(
        [sys.executable, str(installer), '--venv', str(tmp_path / 'installed'), '--offline', '--core-only'],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.splitlines()[-1])['installed'] is True
    assert 'fixture tools available' in result.stdout


@pytest.mark.parametrize('mismatch', ['platform', 'architecture'])
def test_installer_refuses_wrong_cua_target_before_creating_environment(tmp_path, monkeypatch, mismatch):
    tag = local_cua_tag()
    if mismatch == 'platform':
        tag = 'linux_x86_64' if sys.platform != 'linux' else 'macosx_13_0_x86_64'
    else:
        tag = tag.replace('x86_64', 'arm64') if tag.endswith('x86_64') else tag.rsplit('_', 1)[0] + '_x86_64'
        if sys.platform == 'linux':
            tag = tag.replace('arm64', 'aarch64')
    installer = fixture_bundle(tmp_path / 'bundle', tag=tag)
    target = tmp_path / 'must-not-exist'
    result = run_installer(installer, target, monkeypatch)
    assert result.returncode == 2 and 'CUA wheel is incompatible' in result.stderr
    assert not target.exists()


def test_installer_refuses_source_only_dependency_without_building_it(tmp_path, monkeypatch):
    import io
    import tarfile

    installer = fixture_bundle(tmp_path / 'bundle', requires='compile-trap==1.0')
    marker = tmp_path / 'source-build-was-invoked'
    setup = f'from pathlib import Path\nPath({str(marker)!r}).touch()\n'.encode()
    with tarfile.open(installer.parent / 'compile_trap-1.0.tar.gz', 'w:gz') as archive:
        entry = tarfile.TarInfo('compile_trap-1.0/setup.py')
        entry.size = len(setup)
        archive.addfile(entry, io.BytesIO(setup))
    result = run_installer(installer, tmp_path / 'installed', monkeypatch)
    assert result.returncode != 0
    assert 'No matching distribution found for compile-trap==1.0' in result.stderr
    assert not marker.exists()


def test_uv_route_never_downloads_python_or_builds_dependencies(tmp_path, monkeypatch):
    installer = fixture_bundle(tmp_path / 'bundle')
    spec = importlib.util.spec_from_file_location('generated_bundle_installer', installer)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    actual_run = subprocess.run

    def run(command, **kwargs):
        if command[1:3] == ['-I', '-c']:
            return actual_run(command, **kwargs)
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    actual_which = module.shutil.which
    monkeypatch.setattr(module.shutil, 'which', lambda name: '/existing/uv' if name == 'uv' else actual_which(name))
    monkeypatch.setattr(module.subprocess, 'run', run)
    monkeypatch.setattr(sys, 'argv', [str(installer), '--venv', str(tmp_path / 'installed'), '--offline'])
    module.main()
    assert calls[0][:3] == ['/existing/uv', 'venv', '--no-python-downloads']
    assert calls[1][:3] == ['/existing/uv', 'pip', 'install']
    assert calls[1][calls[1].index('--only-binary') + 1] == ':all:'
    assert '--offline' in calls[1]
    assert any(value.endswith('.whl[tools]') for value in calls[1])
