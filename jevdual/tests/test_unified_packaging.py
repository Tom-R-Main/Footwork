"""Installed tool resources survive checkout isolation and remain source-identical."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path

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
