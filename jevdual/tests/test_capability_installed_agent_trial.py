"""Pure host output, isolation and readonly completion boundary checks."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def harness(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "installed_agent_trial", scripts / "capability_installed_agent_trial.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def generated_job(tmp_path):
    python = tmp_path / "install/venv/bin/python"
    job = tmp_path / "job"
    job.mkdir()
    scope, journal, host = job / "scope.json", job / "operations.sqlite", job / "host.json"
    scope.write_text(json.dumps({"task": "task_fixture"}))
    config = {
        "mcpServers": {
            "footwork": {
                "command": str(python),
                "args": [
                    "-I",
                    "-m",
                    "jevdual.capability.cli",
                    "server",
                    "--scope",
                    str(scope),
                    "--journal",
                    str(journal),
                ],
                "env": {
                    "PYTHONPATH": "",
                    "PYTHONHOME": "",
                    "PYTHONNOUSERSITE": "1",
                    "ANONYMIZED_TELEMETRY": "false",
                    "BROWSER_USE_CLOUD_SYNC": "false",
                },
            }
        }
    }
    host.write_text(json.dumps(config))
    manifest = {
        "task": "task_fixture",
        "scope": str(scope),
        "host_config": str(host),
        "report_schema": str(job / "report-schema.json"),
        "report_adapter": [
            str(python),
            "-I",
            "-m",
            "jevdual.capability.cli",
            "report",
            "--journal",
            str(journal),
            "--task",
            "task_fixture",
        ],
    }
    (job / "run.json").write_text(json.dumps(manifest))
    (job / "report-schema.json").write_text(json.dumps({"type": "object"}))
    return python, scope, journal, host


def test_emitted_mcp_environment_contains_only_public_overrides(harness, monkeypatch, tmp_path):
    python, scope, journal, host = generated_job(tmp_path)
    monkeypatch.setenv("QUALIFICATION_OPAQUE", "opaque-not-for-serialization")
    monkeypatch.setenv("QUALIFICATION_TOKEN", "opaque-not-for-serialization")
    config, _, _ = harness.installed_configuration(
        python, scope, journal, host, tmp_path / "install", tmp_path / "audit"
    )
    encoded = json.dumps(config)
    assert "opaque-not-for-serialization" not in encoded
    assert "QUALIFICATION_OPAQUE" not in encoded
    env = config["mcpServers"]["footwork"]["env"]
    assert env["HOME"] == str(tmp_path / "install/private-home")
    assert env["PYTHONPATH"] == ""
    assert env["FOOTWORK_RUNTIME_AUDIT_DIR"] == str(tmp_path / "audit")
    assert env["QUALIFICATION_TOKEN"] == ""


@pytest.mark.parametrize("cost", [None, "0.25", True, -0.01, float("nan"), float("inf"), 2.01])
def test_unavailable_or_invalid_cost_cannot_qualify_trial(harness, cost):
    evidence = harness.cost_evidence(cost)
    assert not evidence["valid"]
    assert evidence["configured_softcap_usd"] == 1.0
    assert evidence["scheduling_reserve_usd"] == 2.0


@pytest.mark.parametrize("cost", [0, 0.25, 1.5, 2.0])
def test_actual_finite_cost_uses_scheduling_reserve_not_softcap(harness, cost):
    evidence = harness.cost_evidence(cost)
    assert evidence["valid"]
    assert evidence["reported_cost_usd"] == cost


def test_changed_adapter_is_rejected_before_dispatch(harness, tmp_path):
    python, scope, journal, host = generated_job(tmp_path)
    path = host.parent / "run.json"
    manifest = json.loads(path.read_text())
    manifest["report_adapter"] = [str(python), "-c", "effect()"]
    path.write_text(json.dumps(manifest))
    with pytest.raises(RuntimeError, match="report adapter"):
        harness.installed_configuration(python, scope, journal, host, tmp_path, tmp_path)


@pytest.mark.parametrize("extra", [[], ["StructuredOutput"], ["Bash"], ["StructuredOutput", "Bash"]])
def test_schema_finalizer_does_not_admit_effect_tools(harness, tmp_path, extra):
    path = tmp_path / "transcript.jsonl"
    events = [
        {
            "type": "system",
            "subtype": "init",
            "tools": [*harness.TOOLS, *extra],
            "model": "claude-opus-5-5",
            "mcp_servers": [{"name": "footwork"}],
        },
        {
            "type": "assistant",
            "message": {
                "content": [{"type": "tool_use", "name": name} for name in [harness.TOOLS[0], *extra]]
            },
        },
        {"type": "result", "is_error": False, "structured_output": {"completion": "completed"}},
    ]
    path.write_text("\n".join(json.dumps(event) for event in events))
    evidence, claims = harness.transcript_evidence(path)
    assert evidence["valid_environment"] is ("Bash" not in extra)
    assert evidence["out_of_arm"] == (["Bash"] if "Bash" in extra else [])
    assert "StructuredOutput" not in evidence["effect_calls"]
    assert claims == {"completion": "completed"}


def test_completed_host_prose_cannot_replace_rejected_structured_claims(harness, monkeypatch, tmp_path):
    rejection = {
        "validation": {"accepted": False},
        "operation_completion": "unknown",
        "trusted_summary": "Unavailable",
    }
    monkeypatch.setattr(
        harness.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=json.dumps(rejection), stderr=""),
    )
    result = harness.validate_report(["installed-readonly-adapter"], None, {}, tmp_path, tmp_path)
    assert not result["accepted"]
    assert json.loads((tmp_path / "structured-output.json").read_text()) is None
    assert json.loads((tmp_path / "validated.json").read_text()) == rejection
    assert not (tmp_path / "published.txt").exists()


def test_runtime_audit_rejects_borrowed_module_even_with_private_home(harness, tmp_path):
    audit = tmp_path / "audit"
    audit.mkdir()
    python = tmp_path / "install/venv/bin/python"
    prefix = python.parent.parent
    journal = tmp_path / "job/operations.sqlite"
    registrations = Path(str(journal) + ".executions") / "op_fixture"
    registrations.mkdir(parents=True)
    (registrations / "registration.json").write_text(json.dumps({"pid": 1234}))
    for role in ("server", "worker"):
        context = {
            "role": role,
            "pid": 1234,
            "prefix": str(prefix),
            "python": str(python),
            "home": str(tmp_path / "install/private-home"),
            "user_site_disabled": True,
            "browser_telemetry_disabled": True,
            "browser_cloud_sync_disabled": True,
            "cua_library": str(prefix / "lib/libcua.dylib"),
            "modules": {
                "jevdual": [str(tmp_path / "source/jevdual/__init__.py")],
                "cua_driver": [str(prefix / "lib/cua_driver/__init__.py")],
                "ApplicationServices": [str(prefix / "lib/ApplicationServices/__init__.py")],
            },
        }
        (audit / (role + ".json")).write_text(json.dumps(context))
    evidence = harness.runtime_evidence(audit, python, tmp_path / "install", journal)
    assert evidence["failures"] == ["module outside installed prefix"] * 2
