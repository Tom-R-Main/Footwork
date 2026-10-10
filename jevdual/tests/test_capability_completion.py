"""Public report invariants and real readonly CLI boundary; no native/model access."""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from jevdual.capability.completion import ReportError, ReportUnavailable, validate_from_journal
from jevdual.capability.journal import Journal
from jevdual.capability.mcp_server import ToolFacade
from jevdual.capability.service import CapabilityService


def operation(journal, token, disposition="applied", task="test"):
    op, _ = journal.begin(
        task=task,
        resource=f"native:{token}:2",
        observation="obs",
        target="target",
        move="append",
        args={"text": "fixture"},
        client_token=token,
    )
    if disposition != "dispatching":
        journal.finish(
            op.id,
            disposition=disposition,
            phase="ambiguous"
            if disposition == "unknown"
            else "sent"
            if disposition == "applied"
            else "not_sent",
            evidence={},
        )
    return op.id


def report(op_id, disposition="applied", completion="completed", persistence="not_checked"):
    return {
        "completion": completion,
        "operations": [{"operation": op_id, "disposition": disposition}],
        "persistence": persistence,
    }


@pytest.fixture
def journal(tmp_path):
    j = Journal(tmp_path / "operations.sqlite")
    yield j
    j.close()


@pytest.mark.parametrize("state", ["unknown", "dispatching"])
def test_unknown_never_certifies_completed_and_does_not_reconcile(journal, state):
    op_id = operation(journal, "one", state)
    history = journal.events(op_id)
    result = validate_from_journal(journal.path, "test", report(op_id))
    assert not result["validation"]["accepted"]
    assert result["operation_completion"] == "unknown"
    assert "Execution remains unknown" in result["trusted_summary"]
    assert journal.get(op_id).state == state and journal.events(op_id) == history


@pytest.mark.parametrize("disposition", ["applied", "unknown", "partial", "refused", "not_sent"])
def test_accurate_reports_and_live_owner_readonly_access(journal, disposition):
    op_id = operation(journal, "one", disposition)
    expected = (
        "completed"
        if disposition == "applied"
        else "unknown"
        if disposition == "unknown"
        else "not_completed"
    )
    result = validate_from_journal(journal.path, "test", report(op_id, disposition, expected))
    assert result["validation"]["accepted"]
    assert result["operation_completion"] == expected
    assert result["current_state"] == result["persistence"] == "not_checked"
    second = validate_from_journal(journal.path, "test", report(op_id, disposition, expected))
    assert second["snapshot_digest"] == result["snapshot_digest"]


def test_old_unknown_cannot_hide_behind_ten_recent_applied_rows(journal):
    operation(journal, "old", "unknown")
    recent = [operation(journal, str(i), "applied") for i in range(12)]
    host = {
        "completion": "completed",
        "persistence": "not_checked",
        "operations": [{"operation": op_id, "disposition": "applied"} for op_id in recent],
    }
    result = validate_from_journal(journal.path, "test", host)
    assert not result["validation"]["accepted"]
    assert result["operation_completion"] == "unknown" and len(result["operations"]) == 13
    assert "operation_set_mismatch" in result["validation"]["reasons"]


def test_task_binding_and_zero_operations(journal):
    foreign = operation(journal, "foreign", task="other")
    result = validate_from_journal(journal.path, "test", report(foreign))
    assert not result["validation"]["accepted"] and result["operations"] == []
    assert result["operation_completion"] != "completed"


@pytest.mark.parametrize("persistence", ["saved", "unsaved"])
def test_applied_never_certifies_saved_or_unsaved(journal, persistence):
    op_id = operation(journal, "one")
    result = validate_from_journal(journal.path, "test", report(op_id, persistence=persistence))
    assert not result["validation"]["accepted"]
    assert result["persistence"] == "not_checked"
    assert "disk_persistence_not_checked" in result["validation"]["reasons"]


def test_public_facade_report_never_calls_backend(journal):
    op_id = operation(journal, "one", "unknown")

    class Backend:
        task = "test"

        def __getattr__(self, name):
            raise AssertionError("Report must not drive, observe or reconcile")

    backend = Backend()
    facade = ToolFacade(backend, CapabilityService(journal, backend))
    result = asyncio.run(facade.call("report", report(op_id)))
    assert result["operation_completion"] == "unknown" and not result["validation"]["accepted"]


def test_duplicate_or_prose_report_is_not_publishable(journal):
    op_id = operation(journal, "one")
    duplicate = report(op_id)
    duplicate["operations"] *= 2
    for host in (duplicate, {**report(op_id), "text": "Done!"}):
        with pytest.raises(ReportError):
            validate_from_journal(journal.path, "test", host)


def test_new_admission_invalidates_old_claim_snapshot(journal):
    first = operation(journal, "one")
    host = report(first)
    before = validate_from_journal(journal.path, "test", host)
    operation(journal, "two", "unknown")
    after = validate_from_journal(journal.path, "test", host)
    assert before["validation"]["accepted"] and not after["validation"]["accepted"]
    assert after["snapshot_digest"] != before["snapshot_digest"]


@pytest.mark.parametrize("insecure", ["public", "symlink"])
def test_unsafe_journal_identity_is_unavailable(journal, tmp_path, insecure):
    op_id = operation(journal, "one")
    path = journal.path
    if insecure == "public":
        os.chmod(path, 0o644)
    else:
        path = tmp_path / "link.sqlite"
        path.symlink_to(journal.path)
    with pytest.raises(ReportUnavailable):
        validate_from_journal(path, "test", report(op_id))


def test_actual_cli_discards_optimistic_report_and_unavailable_fallback(journal, tmp_path):
    op_id = operation(journal, "one", "unknown")
    command = [
        sys.executable,
        "-m",
        "jevdual.capability.cli",
        "report",
        "--task",
        "test",
        "--journal",
        str(journal.path),
    ]
    project = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(project / "python")}
    run = subprocess.run(
        command,
        input=json.dumps(report(op_id)),
        text=True,
        capture_output=True,
        check=False,
        cwd=tmp_path,
        env=env,
        timeout=10,
    )
    result = json.loads(run.stdout)
    assert run.returncode == 1 and result["operation_completion"] == "unknown"
    assert result["trusted_summary"].startswith("Host completion report rejected (")
    bad = subprocess.run(
        command,
        input='{"text":"Done!"}',
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=10,
        check=False,
    )
    assert bad.returncode == 2 and json.loads(bad.stdout)["operation_completion"] == "unknown"
    assert "Done!" not in bad.stdout


def test_readonly_report_does_not_recover_started_journal(journal):
    op_id = operation(journal, "one", "dispatching")
    with sqlite3.connect(journal.path) as db:
        before = db.execute("SELECT state,history FROM operations WHERE id=?", (op_id,)).fetchone()
    validate_from_journal(journal.path, "test", report(op_id))
    with sqlite3.connect(journal.path) as db:
        after = db.execute("SELECT state,history FROM operations WHERE id=?", (op_id,)).fetchone()
    assert before == after


def test_safe_no_input_attempt_then_applied(journal):
    no_input = operation(journal, "refused", "refused")
    applied = operation(journal, "applied")
    host = report(applied)
    host["operations"].append({"operation": no_input, "disposition": "refused"})
    result = validate_from_journal(journal.path, "test", host)
    assert result["validation"]["accepted"]
    assert result["operation_completion"] == "completed"
    assert "1 attempts confirmed no input" in result["trusted_summary"]
    assert "not certification of the host job" in result["trusted_summary"]


@pytest.mark.parametrize("completion", ["unknown", "not_completed"])
def test_honest_host_downgrade_is_accepted(journal, completion):
    op_id = operation(journal, "applied")
    result = validate_from_journal(journal.path, "test", report(op_id, completion=completion))
    assert result["validation"]["accepted"]
    assert result["operation_completion"] == "completed"
    assert "not certification of the host job" in result["trusted_summary"]


def test_owner_crash_retains_readable_wal_and_unrecovered_dispatching(tmp_path):
    path = tmp_path / "crash.sqlite"
    code = """
import sys
from jevdual.capability.journal import Journal
j = Journal(sys.argv[1])
op, _ = j.begin(task="crash", resource="native:1:2", observation="o", target="t", move="append", args={"text":"x"}, client_token=None)
print(op.id, flush=True)
sys.stdin.read()
"""
    proc = subprocess.Popen(
        [sys.executable, "-c", code, str(path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    )
    try:
        import select

        assert select.select([proc.stdout], [], [], 10)[0]
        op_id = proc.stdout.readline().strip()
        assert Path(str(path) + "-wal").exists()
        proc.kill()
        proc.wait(timeout=10)
        result = validate_from_journal(path, "crash", report(op_id))
        assert result["operation_completion"] == "unknown"
        assert result["operations"][0]["state"] == "dispatching"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10)


def test_clean_exit_journal_remains_reportable(tmp_path):
    path = tmp_path / "clean.sqlite"
    j = Journal(path)
    op_id = operation(j, "one")
    j.close()
    assert validate_from_journal(path, "test", report(op_id))["validation"]["accepted"]


def test_overflow_fails_closed(journal):
    for i in range(257):
        operation(journal, str(i))
    with pytest.raises(ReportUnavailable):
        validate_from_journal(journal.path, "test", report("invented"))
