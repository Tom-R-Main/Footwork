"""Consumer artifact and per-job setup checks; no native input or permission requests."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from jevdual.capability.contracts import CapabilityError
from jevdual.capability.journal import Journal
from jevdual.capability.setup import doctor, make_config

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("wheel_builder", ROOT / "scripts/build_capability_wheel.py")
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def configure(tmp_path: Path, name: str = "run") -> dict:
    document = tmp_path / "document.txt"
    if not document.exists():
        document.write_text("prefix")
    return make_config(
        tmp_path / name,
        source_pid=os.getpid(),
        source_window=101,
        source_url="http://127.0.0.1:8000/",
        destination_pid=os.getpid(),
        destination_window=202,
        document=document,
    )


def test_wheel_reproducible_inventory_record_and_install_origin(tmp_path):
    first = BUILDER.build(ROOT, tmp_path / "one")
    second = BUILDER.build(ROOT, tmp_path / "two")
    assert first.read_bytes() == second.read_bytes()
    verified = BUILDER.verify(first, ROOT)
    assert verified["verified"]
    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
        assert not any(
            name.endswith((".so", ".pyc")) or "/tests/" in name or "/evals/" in name for name in names
        )
        metadata = archive.read("jevdual-0.0.1.dist-info/METADATA").decode()
        assert "Requires-Dist: mcp==2.1.1" in metadata
        assert "Requires-Dist: cua-driver==0.28.2" in metadata
        assert "Requires-Dist: browser-use==0.13.10" in metadata
        assert "License-File: LICENSE" in metadata
        assert "MIT" in archive.read("jevdual-0.0.1.dist-info/licenses/LICENSE").decode()
        assert (
            "footwork-capability = jevdual.capability.cli:main"
            in archive.read("jevdual-0.0.1.dist-info/entry_points.txt").decode()
        )
        target = tmp_path / "installed"
        archive.extractall(target)
    # Pure import path does not depend on site-packages. Arbiter itself needs external deps,
    # so inspect the installed data via the package location instead.
    code = "import sys,json,pathlib;sys.path.insert(0,sys.argv[1]);import jevdual,jevdual.capability.cli as cli,jevdual.capability.setup as setup;print(json.dumps({'package':jevdual.__file__,'cli':cli.__file__,'backend':jevdual.BACKEND,'policy_exists':pathlib.Path(jevdual.__file__).with_name('arbiter.toml').exists(),'browser_use_imported':'browser_use' in sys.modules}))"
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", code, str(target)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert Path(data["package"]).is_relative_to(target)
    assert Path(data["cli"]).is_relative_to(target)
    assert data["backend"] == "pure-python" and data["policy_exists"]
    assert not data["browser_use_imported"]


def test_wheel_verifier_rejects_changed_bytes_and_extra_members(tmp_path):
    good = BUILDER.build(ROOT, tmp_path / "good")
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    bad = bad_dir / good.name
    with zipfile.ZipFile(good) as source, zipfile.ZipFile(bad, "w") as destination:
        for name in source.namelist():
            data = source.read(name)
            destination.writestr(name, data + b"tampered" if name.endswith("arbiter.toml") else data)
    with pytest.raises(ValueError, match="bytes differ"):
        BUILDER.verify(bad, ROOT)
    with zipfile.ZipFile(bad, "a") as destination:
        destination.writestr("jevdual/.env", "forbidden")
    with pytest.raises(ValueError, match="inventory"):
        BUILDER.verify(bad, ROOT)


def test_builder_rejects_source_symlink(tmp_path):
    root = tmp_path / "project"
    source = root / "python/jevdual"
    source.mkdir(parents=True)
    (root / "pyproject.toml").write_bytes((ROOT / "pyproject.toml").read_bytes())
    (tmp_path / "LICENSE").write_text("MIT")
    (source / "escape.py").symlink_to(ROOT / "python/jevdual/__init__.py")
    with pytest.raises(ValueError, match="symlink"):
        BUILDER.build(root, tmp_path / "wheel")


def test_config_unique_private_durable_and_no_overwrite(tmp_path):
    one = configure(tmp_path)
    two = configure(tmp_path, "second")
    assert one["task"] != two["task"]
    scope = json.loads((tmp_path / "run/scope.json").read_text())
    assert scope["task"] == one["task"]
    host = json.loads((tmp_path / "run/host.json").read_text())
    command = host["mcpServers"]["footwork"]
    assert command["command"] == str(Path(sys.executable).absolute())
    assert "-m" in command["args"] and "jevdual.capability.cli" in command["args"]
    assert (tmp_path / "run").stat().st_mode & 0o777 == 0o700
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in (tmp_path / "run").iterdir())
    before = (tmp_path / "run/scope.json").read_bytes()
    with pytest.raises(FileExistsError):
        configure(tmp_path)
    assert (tmp_path / "run/scope.json").read_bytes() == before
    assert not (tmp_path / "run/operations.sqlite").exists()


def test_config_rejects_remote_scope_before_creating_run(tmp_path):
    document = tmp_path / "document.txt"
    document.write_text("prefix")
    with pytest.raises(CapabilityError, match="loopback"):
        make_config(
            tmp_path / "run",
            source_pid=1,
            source_window=1,
            source_url="https://example.org/",
            destination_pid=2,
            destination_window=2,
            document=document,
        )
    assert not (tmp_path / "run").exists()


def test_doctor_never_requests_permissions_or_creates_resources(tmp_path, monkeypatch):
    from jevdual.capability import setup

    calls = []

    class PermissionAPI:
        def AXIsProcessTrusted(self):
            calls.append("AX-status")
            return True

        def CGPreflightScreenCaptureAccess(self):
            calls.append("screen-status")
            return False

        def __getattr__(self, name):
            pytest.fail(f"Unexpected permission method: {name}")

    monkeypatch.setattr(setup.sys, "platform", "darwin")
    monkeypatch.setitem(sys.modules, "ApplicationServices", PermissionAPI())
    monkeypatch.setitem(sys.modules, "Quartz", PermissionAPI())
    before = list(tmp_path.iterdir())
    result = doctor(journal_path=tmp_path / "missing.sqlite")
    assert calls == ["AX-status", "screen-status"]
    assert result["permissions"] == {"accessibility": "granted", "screen_recording": "not_granted"}
    assert result["journal"] == "not_created" and list(tmp_path.iterdir()) == before


def test_doctor_existing_task_warns_without_recovery(tmp_path):
    manifest = configure(tmp_path)
    journal_path = tmp_path / "run/operations.sqlite"
    journal = Journal(journal_path)
    try:
        operation, _ = journal.begin(
            task=manifest["task"],
            resource="resource",
            observation="obs",
            target="target",
            move="append",
            args={"text": "x"},
            client_token=None,
        )
        before = journal.get(operation.id)
        result = doctor(Path(manifest["scope"]), journal_path)
        assert result["warnings"] and result["journal"]["operations"] == 1
        assert result["journal"]["operation_completion"] == "unknown"
        assert journal.get(operation.id) == before
    finally:
        journal.close()


def test_doctor_invalid_scope_and_cli_new_commands(tmp_path):
    scope_path = tmp_path / "bad.json"
    scope_path.write_text('{"task":"only"}')
    assert doctor(scope_path)["scope"] == {"valid": False}
    result = subprocess.run(
        [sys.executable, "-m", "jevdual.capability.cli", "doctor"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["provider_account_required"] is False


def test_doctor_bounded_or_recursive_scope_is_unavailable(tmp_path):
    scope_path = tmp_path / "scope.json"
    scope_path.write_text("[" * 2000 + "]" * 2000)
    assert doctor(scope_path)["scope"] == {"valid": False}
    scope_path.write_text(" " * 65537)
    assert doctor(scope_path)["scope"] == {"valid": False}


def test_dependency_ranges_detect_incompatible_versions(monkeypatch):
    from jevdual.capability import setup

    # Model the installed artifact's metadata, independent of this development
    # environment's older editable distribution (which lacks direct MCP).
    monkeypatch.setattr(
        setup.importlib.metadata,
        "requires",
        lambda name: ["typesafe-sdk>=0.7,<1", "orjson>=3.10", "mcp==2.1.1"],
    )

    monkeypatch.setattr(
        setup.importlib.metadata, "version", lambda name: "99.0" if name == "typesafe-sdk" else "0.1"
    )
    monkeypatch.setattr(setup, "permission_status", dict)
    result = doctor()
    assert not result["dependencies"]["typesafe-sdk"]["compatible"]
    assert not result["dependencies"]["orjson"]["compatible"]
    assert not result["dependencies"]["mcp"]["compatible"]


def test_config_rejects_symlink_destination(tmp_path):
    document = tmp_path / "document.txt"
    document.write_text("prefix")
    link = tmp_path / "link.txt"
    link.symlink_to(document)
    with pytest.raises(ValueError, match="regular"):
        make_config(
            tmp_path / "run",
            source_pid=1,
            source_window=1,
            source_url="http://127.0.0.1:8000/",
            destination_pid=2,
            destination_window=2,
            document=link,
        )
    assert not (tmp_path / "run").exists()


def test_doctor_uses_installed_requirements_and_marks_unknown_specs(monkeypatch):
    from jevdual.capability import setup

    monkeypatch.setattr(
        setup.importlib.metadata,
        "requires",
        lambda name: ["cua-driver==99.0.0", "future-lib~=1.0", "ignored-lib>=1; sys_platform == 'never'"],
    )
    monkeypatch.setattr(setup.importlib.metadata, "version", lambda name: "0.28.2")
    checked = doctor()
    assert checked["dependencies"]["cua-driver"]["requirement"] == "==99.0.0"
    assert checked["dependencies"]["cua-driver"]["compatible"] is False
    assert checked["dependencies"]["future-lib"]["compatible"] == "unparsed"
    assert "ignored-lib" not in checked["dependencies"]
    assert any("unparsed" in warning for warning in checked["warnings"])
