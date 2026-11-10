"""Profile selection is verified at wheel and installer boundaries, not import mocks."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import zipfile
from email.parser import BytesParser
from pathlib import Path

import pytest
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def wheel_requirements(wheel):
    with zipfile.ZipFile(wheel) as archive:
        metadata = BytesParser().parsebytes(archive.read("jevdual-0.0.1.dist-info/METADATA"))
    return metadata, [Requirement(value) for value in metadata.get_all("Requires-Dist", [])]


def selected(requirements, *, extra="", platform="linux"):
    return {
        req.name for req in requirements
        if req.marker is None or req.marker.evaluate({"extra": extra, "sys_platform": platform})
    }


def test_built_wheel_has_light_base_and_platform_scoped_full_extras(tmp_path):
    wheel = script("build_capability_wheel").build(ROOT, tmp_path / "wheel")
    metadata, requirements = wheel_requirements(wheel)
    base = selected(requirements)
    assert {"mcp", "typesafe-sdk", "orjson", "psutil", "websockets", "packaging"} <= base
    assert not {"cua-driver", "browser-use", "jeepney", "pyobjc-framework-cocoa"} & base
    assert {"desktop", "agent", "tools"} <= set(metadata.get_all("Provides-Extra", []))
    desktop_linux = selected(requirements, extra="desktop")
    desktop_mac = selected(requirements, extra="desktop", platform="darwin")
    assert "cua-driver" in desktop_linux and "jeepney" in desktop_linux
    assert "jeepney" not in desktop_mac and "pyobjc-framework-cocoa" in desktop_mac
    assert "browser-use" in selected(requirements, extra="agent")
    assert "cua-driver" not in selected(requirements, extra="agent")


def test_light_bundle_never_builds_or_carries_cua(tmp_path, monkeypatch):
    bundle = script("build_agent_bundle")
    monkeypatch.setattr(bundle.subprocess, "run", lambda *a, **kw: pytest.fail("light built native code"))
    output = tmp_path / "bundle"
    manifest = bundle.build_bundle(output, profile="light")
    assert manifest["profile"] == "light" and "cua" not in manifest
    assert not list(output.glob("cua_driver-*.whl"))
    assert (output / manifest["product"]).is_file()
    assert (output / "install.py").is_file()


def test_light_bundle_rejects_full_install_before_environment_creation(tmp_path):
    output = tmp_path / "bundle"
    script("build_agent_bundle").build_bundle(output, profile="light")
    target = tmp_path / "must-not-exist"
    result = subprocess.run(
        [sys.executable, str(output / "install.py"), "--profile", "full", "--offline", "--venv", str(target)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2 and "profile" in result.stderr
    assert not target.exists()


def test_light_profile_rejects_native_wheel_argument(tmp_path):
    wheel = tmp_path / "cua_driver-fixture.whl"
    wheel.write_bytes(b"not needed for light")
    with pytest.raises(ValueError, match="light"):
        script("build_agent_bundle").build_bundle(tmp_path / "bundle", cua_wheel=wheel, profile="light")


@pytest.mark.parametrize("present,expected", [
    ({}, "light"),
    ({"cua-driver": "pinned"}, "desktop"),
    ({"browser-use": "pinned"}, "agent"),
    ({"cua-driver": "pinned", "browser-use": "pinned"}, "full"),
])
def test_report_observes_installed_profile_without_importing_backends(monkeypatch, present, expected):
    from jevdual import install_profile

    def version(name):
        if name not in present:
            raise install_profile.importlib.metadata.PackageNotFoundError(name)
        return present[name]

    monkeypatch.setattr(install_profile.importlib.metadata, "version", version)
    result = install_profile.installation()
    assert result["profile"] == expected
    assert result["runtime_qualification"] == "not_checked"
