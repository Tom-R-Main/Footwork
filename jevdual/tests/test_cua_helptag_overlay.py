"""Optional project overlay provenance/compatibility; no native driver or activation is started."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('helptag_build', ROOT / 'scripts/build_cua_helptag_overlay.py')
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


def test_helptag_archive_reconstructs_without_changing_default_pin_or_binding_files(tmp_path, monkeypatch):
    monkeypatch.setattr(BUILD, 'PROJECT', tmp_path)
    paths = [ROOT / 'pyproject.toml', ROOT / 'uv.lock', BUILD.VENDOR / 'pyproject.toml', BUILD.VENDOR / 'native-source.tar.gz']
    before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    package, manifest = BUILD.prepare(tmp_path / 'candidate')
    assert hashlib.sha256((package / 'native-source.tar.gz').read_bytes()).hexdigest() == manifest['patched_archive_sha256']
    assert manifest['version'] in (package / 'pyproject.toml').read_text()
    for source in (BUILD.VENDOR / 'src/cua_driver').glob('*.py'):
        assert source.read_bytes() == (package / 'src/cua_driver' / source.name).read_bytes()
    assert before == {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def test_helptag_reconstruction_refuses_corrupt_base_before_creating_package(tmp_path, monkeypatch):
    manifest = json.loads(BUILD.MANIFEST.read_text())
    manifest['base_archive_sha256'] = '0' * 64
    path = tmp_path / 'bad.json'
    path.write_text(json.dumps(manifest))
    monkeypatch.setattr(BUILD, 'PROJECT', tmp_path)
    monkeypatch.setattr(BUILD, 'MANIFEST', path)
    with pytest.raises(ValueError, match='checksum mismatch'):
        BUILD.prepare(tmp_path / 'candidate')
    assert not (tmp_path / 'candidate').exists()


@pytest.mark.parametrize('version,accepted', [
    ('0.46.0+footwork.5486b624.cleanup2.focus1', True),
    ('0.46.0+footwork.5486b624.cleanup2.focus1.helptag1', True),
    ('0.46.0', False), ('0.46.0+unknown', False)])
def test_explicit_foreground_supports_only_two_exact_measured_versions(monkeypatch, version, accepted):
    from jevdual import native

    monkeypatch.setattr(native, 'sys', SimpleNamespace(platform='darwin'))
    monkeypatch.setattr(native, '_foreground_web_text_version', lambda: version)
    if accepted:
        native.require_foreground_web_text_runtime()
    else:
        with pytest.raises(native.NativeBridgeError, match='qualified cua-driver'):
            native.require_foreground_web_text_runtime()
