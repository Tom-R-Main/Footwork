"""Prerequisite diagnostics do not grant native authority or mutate recovery state."""

from __future__ import annotations

import builtins
import json
import os
import sys
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import pytest
from jevdual.capability import cli, setup
from jevdual.capability.journal import Journal


@pytest.fixture
def prerequisites(monkeypatch, tmp_path):
    monkeypatch.setattr(setup.sys, "platform", "darwin")
    monkeypatch.setattr(
        setup,
        "permission_status",
        lambda: {
            "accessibility": "granted",
            "screen_recording": "not_granted",
        },
    )
    monkeypatch.setattr(setup.importlib.metadata, "requires", lambda name: ["psutil==7.2.2"])
    monkeypatch.setattr(setup.importlib.metadata, "version", lambda name: "7.2.2")
    monkeypatch.setattr(
        setup.importlib.metadata,
        "distribution",
        lambda name: SimpleNamespace(
            version="0.0.1" if name == "jevdual" else "7.2.2",
            metadata={"Requires-Python": ">=3.11,<4.0"},
            locate_file=lambda value: tmp_path / "installed",
        ),
    )


def make_scope(tmp_path):
    doc = tmp_path / "doc.txt"
    doc.write_text("prefix")
    scope = {
        "task": "task_doctor",
        "source": {"pid": os.getpid(), "window_id": 1, "url": "http://127.0.0.1:8000/"},
        "destination": {"pid": os.getpid(), "window_id": 2, "document": str(doc)},
    }
    path = tmp_path / "scope.json"
    path.write_text(json.dumps(scope))
    return path, scope


def test_met_prerequisites_are_only_prerequisites(prerequisites):
    checked = setup.doctor()
    assert checked["prerequisite_status"] == "met" and checked["blockers"] == []
    assert checked["permissions"]["screen_recording"] == "not_granted"
    assert any("pixels" in warning for warning in checked["warnings"])
    runtime = checked["runtime"]
    assert runtime["interpreter"] == str(Path(sys.executable).absolute())
    assert runtime["python_compatible"] is True and runtime["architecture"]
    assert runtime["distribution"]["version"] == "0.0.1"
    assert Path(runtime["distribution"]["location"]).is_absolute()
    assert "Window identity" in checked["qualification"]



@pytest.mark.parametrize(
    ("requirement", "version", "compatible", "blockers"),
    [
        (">=3.11, <4.0", "3.12.6", True, []),
        (">=3.11, <4.0", "3.10.14", False, ["python_incompatible"]),
        (">=3.11, <4.0", "4.0.0", False, ["python_incompatible"]),
        ("not a requirement", "3.12.6", "unparsed", ["python_requirement_unparsed"]),
        (None, "3.12.6", "unparsed", ["python_requirement_unparsed"]),
        ("", "3.12.6", "unparsed", ["python_requirement_unparsed"]),
        ("   ", "3.12.6", "unparsed", ["python_requirement_unparsed"]),
        (">=3.11, <4.0", "unknown", "unparsed", ["python_requirement_unparsed"]),
    ],
)
def test_python_metadata_uses_standard_specifiers(
    prerequisites, monkeypatch, requirement, version, compatible, blockers
):
    original = setup.importlib.metadata.distribution

    def distribution(name):
        installed = original(name)
        if name == "jevdual":
            installed.metadata = {"Requires-Python": requirement}
        return installed

    monkeypatch.setattr(setup.importlib.metadata, "distribution", distribution)
    monkeypatch.setattr(setup.platform, "python_version", lambda: version)
    checked = setup.doctor()
    assert checked["runtime"]["python_compatible"] == compatible
    assert checked["blockers"] == blockers
    assert checked["prerequisite_status"] == ("blocked" if blockers else "met")
    assert checked["dependencies"]["psutil"]["compatible"] is True


def test_missing_python_specifier_parser_blocks(prerequisites, monkeypatch):
    original = builtins.__import__

    def without_parser(name, *args, **kwargs):
        if name == "packaging.specifiers":
            raise ImportError("not installed")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_parser)
    checked = setup.doctor()
    assert checked["runtime"]["python_compatible"] == "unparsed"
    assert checked["blockers"] == ["python_requirement_unparsed"]
    assert checked["prerequisite_status"] == "blocked"

def test_strict_blocks_but_default_diagnostics_exit_zero(prerequisites, monkeypatch, capsys):
    def missing(name):
        raise setup.importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(setup.importlib.metadata, "version", missing)
    assert cli.main(["doctor"]) == 0
    normal = json.loads(capsys.readouterr().out)
    assert normal["prerequisite_status"] == "blocked"
    assert normal["blockers"] == ["dependency_missing"]
    assert cli.main(["doctor", "--strict"]) == 1
    strict = json.loads(capsys.readouterr().out)
    assert strict["blockers"] == normal["blockers"]


def test_unparsed_and_incompatible_requirements_block(prerequisites, monkeypatch):
    monkeypatch.setattr(
        setup.importlib.metadata,
        "requires",
        lambda name: [
            "psutil==999.0",
            "future-lib~=1.0",
            "this is not metadata",
        ],
    )
    checked = setup.doctor()
    assert set(checked["blockers"]) == {"dependency_incompatible", "dependency_unparsed"}
    assert checked["dependencies"]["future-lib"]["compatible"] == "unparsed"


def test_missing_parser_never_reports_prerequisites_met(prerequisites, monkeypatch):
    original = builtins.__import__

    def without_parser(name, *args, **kwargs):
        if name == "packaging.requirements":
            raise ImportError("not installed")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_parser)
    checked = setup.doctor()
    assert "dependency_metadata_unavailable" in checked["blockers"]
    assert checked["prerequisite_status"] == "blocked"


def test_platform_and_ax_block_without_driver_or_permission_request(prerequisites, monkeypatch):
    monkeypatch.setattr(setup.sys, "platform", "linux")
    monkeypatch.setattr(
        setup,
        "permission_status",
        lambda: {
            "accessibility": "unsupported",
            "screen_recording": "unsupported",
        },
    )
    assert setup.doctor()["blockers"] == ["platform_unsupported"]
    monkeypatch.setattr(setup.sys, "platform", "darwin")
    monkeypatch.setattr(
        setup,
        "permission_status",
        lambda: {
            "accessibility": "not_granted",
            "screen_recording": "not_granted",
        },
    )
    assert setup.doctor()["blockers"] == ["accessibility_not_granted"]
    monkeypatch.setattr(
        setup.ScopedBackend, "__init__", lambda *args, **kwargs: pytest.fail("driver creation")
    )
    assert setup.doctor()["prerequisite_status"] == "blocked"


def test_scope_checks_missing_document_and_pid(prerequisites, tmp_path, monkeypatch):
    path, scope = make_scope(tmp_path)
    Path(scope["destination"]["document"]).unlink()
    monkeypatch.setitem(sys.modules, "psutil", SimpleNamespace(pid_exists=lambda pid: False))
    checked = setup.doctor(path)
    assert checked["scope"]["valid"]
    assert set(checked["blockers"]) == {"scope_document_unavailable", "scope_pids_unavailable"}
    path.write_text("{}")
    assert setup.doctor(path)["blockers"] == ["scope_invalid"]


def test_unknown_ledger_blocks_without_recovery(prerequisites, tmp_path, monkeypatch):
    path, scope = make_scope(tmp_path)
    journal_path = tmp_path / "operations.sqlite"
    with closing(Journal(journal_path)) as journal:
        operation, _ = journal.begin(
            task=scope["task"],
            resource="native",
            observation="obs",
            target="target",
            move="append",
            args={"text": "x"},
            client_token=None,
        )
        before = journal.get(operation.id)
        monkeypatch.setattr(Journal, "__init__", lambda *args, **kwargs: pytest.fail("journal startup"))
        checked = setup.doctor(path, journal_path)
        assert checked["blockers"] == ["journal_unknown_operations"]
        assert journal.get(operation.id) == before
        assert checked["journal"]["operation_completion"] == "unknown"


def test_applied_history_warns_and_missing_scope_blocks(prerequisites, tmp_path):
    path, scope = make_scope(tmp_path)
    journal_path = tmp_path / "operations.sqlite"
    with closing(Journal(journal_path)) as journal:
        operation, _ = journal.begin(
            task=scope["task"],
            resource="native",
            observation="obs",
            target="target",
            move="append",
            args={"text": "x"},
            client_token=None,
        )
        journal.finish(operation.id, disposition="applied", phase="verified", evidence={})
        checked = setup.doctor(path, journal_path)
        assert checked["prerequisite_status"] == "met" and checked["warnings"]
        assert setup.doctor(journal_path=journal_path)["blockers"] == ["journal_scope_required"]
    journal_path.chmod(0o644)
    assert setup.doctor(path, journal_path)["blockers"] == ["journal_unavailable"]
