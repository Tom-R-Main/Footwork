"""The operation journal: intent before dispatch, unknown on recovery, one owner (capability slice)."""

from __future__ import annotations

import sqlite3

import pytest
from jevdual.capability.journal import Busy, Journal, JournalError, JournalLocked, TokenConflict

REQ = {"task": "fixture", "resource": "native:1:2", "observation": "obs_1", "target": "t_1", "move": "append"}


def begin(j: Journal, token: str | None = "tok-1", text: str = "624", **over):
    return j.begin(**{**REQ, **over}, args={"text": text}, client_token=token)


def test_begin_commits_dispatching_and_blocks_the_resource(tmp_path):
    j = Journal(tmp_path / "ops.db")
    op, created = begin(j)
    assert created and op.state == "dispatching"
    with pytest.raises(Busy) as exc:
        begin(j, token=None)
    assert exc.value.op_id == op.id
    _, created = begin(j, token=None, resource="native:1:3")
    assert created, "another resource is not blocked"


def test_a_repeated_token_returns_the_original_and_a_changed_request_conflicts(tmp_path):
    j = Journal(tmp_path / "ops.db")
    op, _ = begin(j)
    j.finish(op.id, disposition="applied", phase="sent", evidence={})
    again, created = begin(j)
    assert not created and again.id == op.id
    with pytest.raises(TokenConflict):
        begin(j, text="625")
    with pytest.raises(TokenConflict):
        begin(j, target="t_2")  # the digest covers the target and move, not only the args


def test_a_dispatching_row_becomes_unknown_when_the_journal_is_reopened(tmp_path):
    j = Journal(tmp_path / "ops.db")
    op, _ = begin(j)
    j.close()  # the process "died" after the intent commit
    j2 = Journal(tmp_path / "ops.db")
    recovered = j2.get(op.id)
    assert recovered is not None
    assert recovered.state == "unknown" and recovered.disposition == "unknown"
    assert "process ended during dispatch" in (recovered.error or "")
    assert recovered.phase == "ambiguous", "a recovered attempt is not evidence that nothing was sent"
    assert [e["kind"] for e in j2.events(op.id)] == ["intent", "recovered_unknown"]
    with pytest.raises(Busy):
        begin(j2, token=None)


def test_a_second_process_cannot_own_the_journal(tmp_path):
    j = Journal(tmp_path / "ops.db")
    with pytest.raises(JournalLocked):
        Journal(tmp_path / "ops.db")
    j.close()
    Journal(tmp_path / "ops.db").close()


def test_resolving_an_unknown_needs_evidence_and_keeps_its_history(tmp_path):
    j = Journal(tmp_path / "ops.db")
    op, _ = begin(j)
    j.finish(op.id, disposition="unknown", phase="ambiguous", evidence={}, error="boom")
    with pytest.raises(JournalError):
        j.resolve(op.id, disposition="unknown", evidence={}, by="readback")
    done = j.resolve(op.id, disposition="applied", evidence={"text": "Result:\n624"}, by="readback")
    assert done.state == "final" and done.resolved_by == "readback"
    assert [e["kind"] for e in j.events(op.id)] == ["intent", "finish", "resolve"]
    begin(j, token=None)  # the resource is free again


def test_the_journal_files_are_private_to_their_owner(tmp_path):
    db = tmp_path / "ops.db"
    db.write_text("")
    db.chmod(0o644)  # an existing, readable file is tightened, not trusted
    j = Journal(db)
    begin(j)
    for f in (db, tmp_path / "ops.db.lock", tmp_path / "ops.db-wal"):
        assert f.stat().st_mode & 0o777 == 0o600, f


def test_a_failed_open_releases_the_owner_lock(tmp_path, monkeypatch):
    import jevdual.capability.journal as journal_mod

    def boom(*a, **k):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(journal_mod.sqlite3, "connect", boom)
    with pytest.raises(sqlite3.OperationalError):
        Journal(tmp_path / "ops.db")
    monkeypatch.undo()
    Journal(tmp_path / "ops.db").close()  # not JournalLocked
