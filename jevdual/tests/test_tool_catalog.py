"""Exercise installed auxiliary entrypoints, path fences and real parser discovery."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from jevdual import tool_catalog as tools


def test_discovery_has_all_operational_families_without_starting_anything(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rows = {row["name"]: row for row in tools.catalog()}
    assert set(rows) == {"camera", "inbox", "workbench", "workcell", "browser-inspection", "inspection-experiments", "inspection-transport"}
    assert rows["browser-inspection"]["capture"] == "adapter_required"
    assert not list(tmp_path.iterdir())


def test_inbox_status_uses_chosen_state_root_and_needs_no_device(tmp_path, monkeypatch, capfd):
    monkeypatch.setenv("FOOTWORK_TOOL_OUTPUT_ROOT", str(tmp_path / "state"))
    run = tmp_path / "state" / "desk-inbox-experiment" / "one"
    assert tools.run_tool("inbox", ["status", "--run-dir", str(run)]) == 0
    result = json.loads(capfd.readouterr().out)
    assert result["state"] == "absent"
    assert run.is_dir()
    assert not (tools.resource_root() / "desk-inbox-experiment/output/one").exists()


def test_inbox_retains_its_output_fence(tmp_path, monkeypatch, capfd):
    monkeypatch.setenv("FOOTWORK_TOOL_OUTPUT_ROOT", str(tmp_path / "state"))
    outside = tmp_path / "unbound"
    assert tools.run_tool("inbox", ["status", "--run-dir", str(outside)]) == 2
    assert json.loads(capfd.readouterr().out)["state"] == "refused"
    assert not outside.exists()


def test_schema_reports_real_required_argument_without_creating_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    schema = tools.command_schema("inbox", "accept")
    arguments = {item["name"]: item for item in schema["arguments"]}
    assert arguments["approved_sha256"]["required"] is True
    assert arguments["approved_sha256"]["flags"] == ["--approved-sha256"]
    assert arguments["run_dir"]["required"] is True
    assert not list(tmp_path.iterdir())


def test_unknown_script_cannot_escape_allowlist(capfd):
    assert tools.run_tool("workcell", ["../../outside"]) == 2
    assert json.loads(capfd.readouterr().err)["error"] == "unknown_command"


def test_optional_workcell_dependency_has_explicit_refusal(monkeypatch, capfd):
    monkeypatch.setattr(tools.importlib.util, "find_spec", lambda name: None)
    assert tools.run_tool("workcell", ["episode", "doctor"]) == 2
    assert json.loads(capfd.readouterr().err)["error"] == "optional_dependencies_missing"


def test_research_freeze_does_not_silently_use_installed_tree(capfd):
    assert tools.run_tool("workcell", ["qualify-bench"]) == 2
    assert json.loads(capfd.readouterr().err)["error"] == "source_checkout_required"


def test_exported_browser_libraries_really_import(capfd):
    if not shutil.which("node"):
        pytest.skip("Node optional")
    assert tools.run_tool("browser-inspection", ["export"]) == 0
    exported = json.loads(capfd.readouterr().out)
    module = Path(exported["modules"]["capture.mjs"])
    assert exported["attaches_browser"] is False
    loaded = subprocess.run(["node", "--input-type=module", "-e", "const m=await import(process.argv[1]); console.log(typeof m.createCapture)", module.as_uri()], capture_output=True, text=True, check=True)
    assert loaded.stdout.strip() == "function"


def test_node_schema_and_unsupported_node_fail_closed(monkeypatch, capfd):
    assert tools.command_schema("inspection-experiments", "compare")["arguments"][0]["name"] == "control_run"
    monkeypatch.setattr(tools.shutil, "which", lambda name: None)
    assert tools.run_tool("inspection-experiments", ["compare", "x", "y"]) == 2
    assert json.loads(capfd.readouterr().err)["error"] == "optional_dependencies_missing"


def test_json_service_refuses_before_dispatch(monkeypatch, capfd):
    import contextlib
    import io
    def forbidden(*args, **kwargs):
        raise AssertionError("no process may start for JSON service wrapping")
    monkeypatch.setattr(tools.subprocess, "run", forbidden)
    with contextlib.redirect_stdout(io.StringIO()):
        assert tools.run_tool("workcell", ["body-network", "--root", "unused"]) == 2
    assert json.loads(capfd.readouterr().err)["error"] == "streaming_protocol_required"


def test_service_readiness_streams_before_process_exit(tmp_path):
    import os
    import select
    import signal
    import sys
    if os.name == "nt":
        pytest.skip("POSIX service adapter")
    folder = tmp_path / "physical-workcell"
    folder.mkdir()
    (folder / "controller.py").write_text("import time;print('READY',flush=True);time.sleep(60)")
    launcher = "from pathlib import Path;import sys;from jevdual import tool_catalog as t;t.resource_root=lambda:Path(sys.argv[1]);t.importlib.util.find_spec=lambda name:object();raise SystemExit(t.run_tool('workcell',['controller','serve']))"
    child = subprocess.Popen([sys.executable, "-c", launcher, str(tmp_path)], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        assert select.select([child.stdout], [], [], 10)[0], "readiness hidden until service terminates"
        assert child.stdout.readline().strip() == "READY"
        assert child.poll() is None
    finally:
        os.killpg(child.pid, signal.SIGTERM)
        child.wait(timeout=5)
