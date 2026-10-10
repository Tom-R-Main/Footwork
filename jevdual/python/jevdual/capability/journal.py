"""The operation journal: every mutating call is recorded before it can reach a window.

One SQLite table holds one row per operation, with its own bounded transition history. :meth:`Journal.begin` commits a ``dispatching`` row before
the backend is called, so a process that dies mid-dispatch leaves a durable record. The next process to
open the journal turns every ``dispatching`` row into ``unknown``: it may or may not have landed, and
nothing here can say which. An unresolved operation (``dispatching`` or ``unknown``) blocks further
mutation of its resource until evidence resolves it; the history of an unknown is kept, never deleted.

A process owns the journal through an exclusive non-blocking lock on ``<db>.lock``, taken before the
recovery step, so a second server process cannot rewrite an attempt the first one still has in flight.
This is a duplicate-startup guard, not a resource-lock system.

Exactly-once GUI effects are not promised: SQLite and the window server share no transaction. The
journal prevents Footwork's own blind redispatch and keeps the uncertainty visible.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Disposition = Literal["applied", "partial", "refused", "not_sent", "unknown"]
Phase = Literal["not_sent", "sent", "ambiguous"]
State = Literal["dispatching", "unknown", "final"]

UNRESOLVED = ("dispatching", "unknown")
HISTORY_LIMIT = 50

_SCHEMA = """
CREATE TABLE IF NOT EXISTS operations (
    id TEXT PRIMARY KEY,
    task TEXT NOT NULL,
    resource TEXT NOT NULL,
    observation TEXT NOT NULL,
    target TEXT,
    move TEXT NOT NULL,
    args TEXT NOT NULL DEFAULT '{}',
    request_digest TEXT NOT NULL,
    client_token TEXT,
    state TEXT NOT NULL,
    disposition TEXT,
    phase TEXT,
    evidence TEXT NOT NULL DEFAULT '{}',
    error TEXT,
    resolved_by TEXT,
    history TEXT NOT NULL DEFAULT '[]',
    created REAL NOT NULL,
    updated REAL NOT NULL,
    recovery TEXT,
    execution_stage TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS operations_token ON operations (task, client_token)
    WHERE client_token IS NOT NULL;
CREATE INDEX IF NOT EXISTS operations_resource ON operations (resource, state);
"""


class JournalError(Exception):
    code = "journal_error"


class JournalLocked(JournalError):
    """Another process owns this journal."""

    code = "journal_in_use"


class Busy(JournalError):
    """The resource has an unresolved operation; nothing new may be dispatched to it."""

    code = "busy"

    def __init__(self, op_id: str) -> None:
        super().__init__(f"operation {op_id} on this resource is unresolved; inspect it with status first")
        self.op_id = op_id


class TokenConflict(JournalError):
    """The client token was already used for a different request."""

    code = "token_conflict"

    def __init__(self, op_id: str) -> None:
        super().__init__(f"client token already names operation {op_id}, with different arguments")
        self.op_id = op_id


def request_digest(
    *, task: str, resource: str, observation: str, target: str | None, move: str, args: dict[str, Any]
) -> str:
    """The identity of a request: the same token may only ever name the same digest."""
    canon = json.dumps(
        {
            "task": task,
            "resource": resource,
            "observation": observation,
            "target": target,
            "move": move,
            "args": args,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canon.encode()).hexdigest()


@dataclass(frozen=True)
class Operation:
    id: str
    task: str
    resource: str
    observation: str
    target: str | None
    move: str
    args: dict[str, Any]
    request_digest: str
    client_token: str | None
    state: State
    disposition: Disposition | None
    phase: Phase | None
    evidence: dict[str, Any]
    error: str | None
    resolved_by: str | None
    history: list[dict[str, Any]]
    created: float
    updated: float
    recovery: dict[str, Any] | None = None
    execution_stage: str | None = None

    @property
    def unresolved(self) -> bool:
        return self.state in UNRESOLVED

    @classmethod
    def _from_row(cls, row: sqlite3.Row) -> Operation:
        d = dict(row)
        d["evidence"] = json.loads(d["evidence"] or "{}")
        d["args"] = json.loads(d["args"] or "{}")
        d["history"] = json.loads(d["history"] or "[]")
        try:
            d["recovery"] = json.loads(d["recovery"]) if d.get("recovery") else None
        except json.JSONDecodeError:
            d["recovery"] = {"invalid": True}  # preserve blocking; never confer execution authority
        return cls(**d)


class Journal:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._lock_fd = os.open(str(self.path) + ".lock", os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(self._lock_fd)
            raise JournalLocked(f"{self.path} is owned by another process") from None
        try:
            _private(self.path)  # operation args and readback text are task content: owner-only
            self._db = sqlite3.connect(self.path, isolation_level=None)
            try:
                self._db.row_factory = sqlite3.Row
                self._db.execute("PRAGMA journal_mode=WAL")
                self._db.execute("PRAGMA synchronous=FULL")
                self._db.executescript(_SCHEMA)
                columns = {row[1] for row in self._db.execute("PRAGMA table_info(operations)")}
                for name in ("recovery", "execution_stage"):
                    if name not in columns:
                        self._db.execute(f"ALTER TABLE operations ADD COLUMN {name} TEXT")
                for side in ("-wal", "-shm"):
                    _private(Path(str(self.path) + side), create=False)
                self._recover()
            except BaseException:
                self._db.close()
                raise
        except BaseException:
            fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            os.close(self._lock_fd)
            raise

    def close(self) -> None:
        self._db.close()
        fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
        os.close(self._lock_fd)

    # ---- transitions ---------------------------------------------------------------------------

    def _recover(self) -> None:
        """A ``dispatching`` row at open means its process died after the intent commit."""
        with self._tx() as db:
            rows = db.execute("SELECT id FROM operations WHERE state = 'dispatching'").fetchall()
            for (op_id,) in rows:
                db.execute(
                    "UPDATE operations SET state = 'unknown', disposition = 'unknown', updated = ?, "
                    "phase = COALESCE(phase, 'ambiguous'), "
                    "error = COALESCE(error, 'process ended during dispatch') WHERE id = ?",
                    (time.time(), op_id),
                )
                self._event(db, op_id, "recovered_unknown", {})
                current = self._get(db, op_id)
                if current.recovery is not None and current.execution_stage == "prepared":
                    from .recovery import packet_for

                    try:
                        packet_for(current)
                    except (ValueError, TypeError, KeyError):
                        continue  # unsupported envelopes never acquire no-send authority
                    db.execute(
                        "UPDATE operations SET state='final', disposition='not_sent', phase='not_sent', "
                        "resolved_by='recovery', evidence=?, error=NULL, updated=? WHERE id=?",
                        (
                            json.dumps({"recovery": "prepared_only", "input_admitted": False}),
                            time.time(),
                            op_id,
                        ),
                    )
                    self._event(db, op_id, "resolve", {"disposition": "not_sent", "by": "recovery"})

    def begin(
        self,
        *,
        task: str,
        resource: str,
        observation: str,
        target: str | None,
        move: str,
        args: dict[str, Any],
        client_token: str | None,
        recovery: dict[str, Any] | None = None,
    ) -> tuple[Operation, bool]:
        """Commit the intent for one dispatch. Returns ``(operation, created)``.

        ``created`` is False when the token already names this exact request: the caller must return
        that operation's record and not dispatch again. Raises :class:`TokenConflict` when the token
        names a different request, :class:`Busy` when the resource has an unresolved operation.
        """
        digest = request_digest(
            task=task, resource=resource, observation=observation, target=target, move=move, args=args
        )
        if recovery is not None:
            from .recovery import validate_recovery

            validate_recovery(recovery)
        with self._tx() as db:
            if client_token is not None:
                prior = self._by_token(db, task, client_token)
                if prior is not None:
                    if prior.request_digest != digest:
                        raise TokenConflict(prior.id)
                    return prior, False
            blocking = db.execute(
                "SELECT id FROM operations WHERE resource = ? AND state IN ('dispatching', 'unknown') "
                "ORDER BY created LIMIT 1",
                (resource,),
            ).fetchone()
            if blocking is not None:
                raise Busy(blocking[0])
            now = time.time()
            op_id = "op_" + uuid.uuid4().hex[:12]
            db.execute(
                "INSERT INTO operations (id, task, resource, observation, target, move, args, request_digest, "
                "client_token, state, created, updated, recovery, execution_stage) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'dispatching', ?, ?, ?, ?)",
                (
                    op_id,
                    task,
                    resource,
                    observation,
                    target,
                    move,
                    json.dumps(args, sort_keys=True, default=str),
                    digest,
                    client_token,
                    now,
                    now,
                    json.dumps(recovery) if recovery is not None else None,
                    "prepared" if recovery is not None else None,
                ),
            )
            self._event(db, op_id, "intent", {"args_digest": digest})
            return self._get(db, op_id), True

    def start(self, op_id: str) -> Operation:
        """Commit launch admission before spawning; this transition is never retried."""
        with self._tx() as db:
            current = self._get(db, op_id)
            if current.state != "dispatching" or current.execution_stage != "prepared":
                raise JournalError("attempt is not prepared for launch")
            db.execute(
                "UPDATE operations SET execution_stage='started', updated=? WHERE id=?", (time.time(), op_id)
            )
            self._event(db, op_id, "dispatch_started", {})
            return self._get(db, op_id)

    def finish(
        self,
        op_id: str,
        *,
        disposition: Disposition,
        phase: Phase,
        evidence: dict[str, Any],
        error: str | None = None,
    ) -> Operation:
        """Record what the dispatch is known to have done. ``unknown`` keeps the resource blocked."""
        state: State = "unknown" if disposition == "unknown" else "final"
        with self._tx() as db:
            current = self._get(db, op_id)
            if current.state != "dispatching":
                raise JournalError(f"operation {op_id} is {current.state}, not dispatching")
            db.execute(
                "UPDATE operations SET state = ?, disposition = ?, phase = ?, evidence = ?, error = ?, "
                "updated = ? WHERE id = ?",
                (state, disposition, phase, json.dumps(evidence, default=str), error, time.time(), op_id),
            )
            self._event(db, op_id, "finish", {"disposition": disposition, "phase": phase})
            return self._get(db, op_id)

    def resolve(
        self,
        op_id: str,
        *,
        disposition: Disposition,
        evidence: dict[str, Any],
        by: Literal["readback", "operator", "execution", "recovery"],
        phase: Phase | None = None,
    ) -> Operation:
        """Turn an ``unknown`` into a known disposition on new evidence. The unknown stays in the history."""
        if disposition == "unknown":
            raise JournalError("resolving to unknown changes nothing")
        with self._tx() as db:
            current = self._get(db, op_id)
            if current.state != "unknown":
                raise JournalError(f"operation {op_id} is {current.state}, not unknown")
            merged = {**current.evidence, "resolution": evidence}
            if by == "execution" and "readback" in evidence:
                merged["readback"] = evidence[
                    "readback"
                ]  # stable historical receipt summary for existing callers
            db.execute(
                "UPDATE operations SET state = 'final', disposition = ?, evidence = ?, resolved_by = ?, "
                "phase = COALESCE(?, phase), updated = ? WHERE id = ?",
                (disposition, json.dumps(merged, default=str), by, phase, time.time(), op_id),
            )
            self._event(db, op_id, "resolve", {"disposition": disposition, "by": by})
            return self._get(db, op_id)

    # ---- reads ---------------------------------------------------------------------------------

    def get(self, op_id: str) -> Operation | None:
        row = self._db.execute("SELECT * FROM operations WHERE id = ?", (op_id,)).fetchone()
        return Operation._from_row(row) if row else None

    def by_token(self, task: str, client_token: str) -> Operation | None:
        return self._by_token(self._db, task, client_token)

    def unresolved(self, task: str) -> list[Operation]:
        rows = self._db.execute(
            "SELECT * FROM operations WHERE task = ? AND state IN ('dispatching', 'unknown') ORDER BY created",
            (task,),
        ).fetchall()
        return [Operation._from_row(r) for r in rows]

    def recent(self, task: str, limit: int = 10) -> list[Operation]:
        """The task's latest operations, newest first: how a caller without a token recovers a lost reply."""
        rows = self._db.execute(
            "SELECT * FROM operations WHERE task = ? ORDER BY created DESC LIMIT ?", (task, limit)
        ).fetchall()
        return [Operation._from_row(r) for r in rows]

    def events(self, op_id: str) -> list[dict[str, Any]]:
        op = self.get(op_id)
        return op.history if op is not None else []

    # ---- internals -----------------------------------------------------------------------------

    def _tx(self) -> _Tx:
        return _Tx(self._db)

    @staticmethod
    def _get(db: sqlite3.Connection, op_id: str) -> Operation:
        row = db.execute("SELECT * FROM operations WHERE id = ?", (op_id,)).fetchone()
        if row is None:
            raise JournalError(f"no operation {op_id}")
        return Operation._from_row(row)

    @staticmethod
    def _by_token(db: sqlite3.Connection, task: str, client_token: str) -> Operation | None:
        row = db.execute(
            "SELECT * FROM operations WHERE task = ? AND client_token = ?", (task, client_token)
        ).fetchone()
        return Operation._from_row(row) if row else None

    @staticmethod
    def _event(db: sqlite3.Connection, op_id: str, kind: str, data: dict[str, Any]) -> None:
        """Append to the row's bounded history, so an unknown that is later resolved stays visible."""
        (raw,) = db.execute("SELECT history FROM operations WHERE id = ?", (op_id,)).fetchone()
        history = [*json.loads(raw or "[]"), {"t": time.time(), "kind": kind, **data}][-HISTORY_LIMIT:]
        db.execute(
            "UPDATE operations SET history = ? WHERE id = ?", (json.dumps(history, default=str), op_id)
        )


def _private(path: Path, *, create: bool = True) -> None:
    """Make ``path`` readable by its owner only, creating it empty when asked; no global umask change."""
    if create:
        os.close(os.open(path, os.O_RDWR | os.O_CREAT, 0o600))
    if path.exists():
        os.chmod(path, 0o600)


class _Tx:
    """``BEGIN IMMEDIATE`` ... ``COMMIT``, rolled back on any exception."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def __enter__(self) -> sqlite3.Connection:
        self.db.execute("BEGIN IMMEDIATE")
        return self.db

    def __exit__(self, exc_type: type[BaseException] | None, *_: object) -> None:
        self.db.execute("ROLLBACK" if exc_type else "COMMIT")
