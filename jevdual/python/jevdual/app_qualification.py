"""Owned loopback ticket fixture and read-only cross-app handoff gates.

HTTP requests in unit tests qualify this fixture, not browser UI behavior. The
handoff controller dispatches no app input and never repairs an app's effects.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import html
import json
import os
import socket
import sqlite3
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote

from jevdual.session_operations import SessionOperations

FIELDS = ("request_id", "artifact", "orientation", "digest")
STAGES = ("finder", "preview", "chrome")
APP_NAMES = {
    "finder": {"Finder"},
    "preview": {"Preview"},
    "chrome": {"Google Chrome", "Google Chrome (footwork)"},
}
MAX_BYTES = 4 * 1024 * 1024


class QualificationError(ValueError):
    """Missing proof must not advance a handoff."""


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def artifact_identity(root: Path, artifact: Path) -> dict[str, Any]:
    """Bounded descriptor read; reject symlinks at every path component."""
    root = root.resolve(strict=True)
    artifact = artifact.absolute()
    if not artifact.is_relative_to(root):
        raise QualificationError("artifact is outside owned root")
    current = root
    for component in artifact.relative_to(root).parts:
        if component in (".", ".."):
            raise QualificationError("artifact traversal")
        current /= component
        if current.is_symlink():
            raise QualificationError("artifact symlink")
    fd = os.open(artifact, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        import stat

        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
            raise QualificationError("artifact must be a bounded regular file")
        data = os.read(fd, MAX_BYTES + 1)
        after = os.fstat(fd)
        named = artifact.stat()
        keys = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
        if any(getattr(before, key) != getattr(after, key) for key in keys) or any(
            getattr(after, key) != getattr(named, key) for key in keys
        ):
            raise QualificationError("artifact changed during read")
        if len(data) != after.st_size:
            raise QualificationError("artifact read incomplete")
        return {
            "path": str(artifact),
            "device": after.st_dev,
            "inode": after.st_ino,
            "size": after.st_size,
            "mtime_ns": after.st_mtime_ns,
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    finally:
        os.close(fd)


class TicketStore:
    """Independent persistent ingress and deduplicated row observations."""

    def __init__(self, path: Path):
        self.path = Path(path).absolute()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.is_symlink():
            raise QualificationError("ticket database symlink")
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS ingress (
                    id INTEGER PRIMARY KEY, received REAL NOT NULL, body_sha TEXT NOT NULL,
                    fields TEXT NOT NULL, error TEXT
                );
                CREATE TABLE IF NOT EXISTS tickets (
                    request_id TEXT PRIMARY KEY, fields TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS fixture_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS responses (
                    ingress_id INTEGER PRIMARY KEY, completed REAL NOT NULL,
                    mode TEXT NOT NULL, boundary TEXT NOT NULL
                );
            """)
            columns = {row[1] for row in db.execute("PRAGMA table_info(ingress)")}
            if "origin" not in columns:
                db.execute("ALTER TABLE ingress ADD COLUMN origin TEXT")
            if "response_mode" not in columns:
                db.execute("ALTER TABLE ingress ADD COLUMN response_mode TEXT")
            db.execute("INSERT OR IGNORE INTO fixture_state VALUES ('fixture_id',?)", (uuid.uuid4().hex,))
            # Legacy populated ledgers are never upgraded into response provenance.
            if not db.execute("SELECT 1 FROM ingress LIMIT 1").fetchone():
                db.execute("INSERT OR IGNORE INTO fixture_state VALUES ('response_mode','normal')")
        self.path.chmod(0o600)

    def bind_origin(self, origin: str) -> None:
        """Register this fixture server's current origin without replacing its durable identity."""
        from jevdual.ticket_evidence import normalize_origin

        origin = normalize_origin(origin)
        with self._db() as db:
            db.execute("INSERT OR REPLACE INTO fixture_state VALUES ('origin',?)", (origin,))

    def bind_response_mode(self, mode: str) -> None:
        """Configure the response protocol before enrollment; never rewrite populated evidence."""
        if mode not in ("normal", "truncated", "disconnect"):
            raise QualificationError("unsupported response mode")
        with self._db() as db:
            previous = db.execute("SELECT value FROM fixture_state WHERE key='response_mode'").fetchone()
            if previous is not None and previous[0] == mode:
                return
            if db.execute("SELECT 1 FROM ingress LIMIT 1").fetchone():
                raise QualificationError("response mode cannot change after ingress")
            db.execute("INSERT OR REPLACE INTO fixture_state VALUES ('response_mode',?)", (mode,))

    @contextlib.contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db
        finally:
            db.close()

    def record(
        self,
        body: bytes,
        *,
        lose_reply_once: bool = False,
        origin: str | None = None,
        include_ingress_id: bool = False,
    ) -> tuple:
        error = None
        fields: dict[str, str] = {}
        try:
            parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True, strict_parsing=True)
            if set(parsed) != set(FIELDS) or any(len(v) != 1 for v in parsed.values()):
                raise ValueError("wrong fields")
            fields = {key: parsed[key][0] for key in FIELDS}
            if any(not value or len(value) > 256 for value in fields.values()):
                raise ValueError("field bounds")
            if (
                fields["orientation"] != "clockwise90"
                or len(fields["digest"]) != 64
                or any(char not in "0123456789abcdef" for char in fields["digest"])
            ):
                raise ValueError("invalid orientation/digest")
        except (UnicodeError, ValueError):
            error = "invalid_fields"
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            mode = db.execute("SELECT value FROM fixture_state WHERE key='response_mode'").fetchone()
            mode = mode[0] if mode is not None else None
            cursor = db.execute(
                "INSERT INTO ingress(received,body_sha,fields,error,origin,response_mode) VALUES (?,?,?,?,?,?)",
                (time.time(), hashlib.sha256(body).hexdigest(), _json(fields), error, origin, mode),
            )
            ingress_id = cursor.lastrowid
            if error is None:
                db.execute(
                    "INSERT OR IGNORE INTO tickets VALUES (?,?)", (fields["request_id"], _json(fields))
                )
            lost = False
            if (
                lose_reply_once
                and error is None
                and not db.execute("SELECT 1 FROM fixture_state WHERE key='reply_lost'").fetchone()
            ):
                db.execute("INSERT INTO fixture_state VALUES ('reply_lost','1')")
                lost = True
        result = (fields, error, lost)
        return (*result, ingress_id) if include_ingress_id else result

    def record_response(self, ingress_id: int, boundary: str) -> None:
        """Append the producer's acknowledged response boundary after its actual flush.

        Component tests generate the same explicit event after a simulated flush.
        Ingress alone, and every pre-header disconnect, remain insufficient.
        """
        with self._db() as db:
            row = db.execute("SELECT response_mode,error FROM ingress WHERE id=?", (ingress_id,)).fetchone()
            if (
                type(ingress_id) is not int
                or row is None
                or row["error"] is not None
                or (row["response_mode"], boundary)
                not in (
                    ("normal", "headers_flushed"),
                    ("truncated", "headers_flushed"),
                )
            ):
                raise QualificationError("unsupported response boundary")
            prior = db.execute("SELECT * FROM responses WHERE ingress_id=?", (ingress_id,)).fetchone()
            if prior is not None:
                if (prior["mode"], prior["boundary"]) != (row["response_mode"], boundary):
                    raise QualificationError("response evidence is immutable")
                return
            db.execute(
                "INSERT INTO responses VALUES (?,?,?,?)",
                (ingress_id, time.time(), row["response_mode"], boundary),
            )

    def snapshot(self) -> dict:
        with self._db() as db:
            db.execute("BEGIN")
            return {
                "ingress": [
                    {**dict(row), "fields": json.loads(row["fields"])}
                    for row in db.execute("SELECT * FROM ingress ORDER BY id")
                ],
                "tickets": [
                    json.loads(row[0]) for row in db.execute("SELECT fields FROM tickets ORDER BY request_id")
                ],
                "responses": [dict(row) for row in db.execute("SELECT * FROM responses ORDER BY ingress_id")],
            }

    def reject(self, body: bytes, error: str) -> None:
        with self._db() as db:
            db.execute(
                "INSERT INTO ingress(received,body_sha,fields,error) VALUES (?,?,?,?)",
                (time.time(), hashlib.sha256(body).hexdigest(), "{}", error),
            )

    def check(self, expected: dict[str, str]) -> dict:
        return self._checked(self.snapshot(), expected, self.path)

    @staticmethod
    def _checked(snapshot: dict, expected: dict[str, str], path: Path) -> dict:
        from jevdual.ticket_evidence import response_matches

        ok = (
            set(expected) == set(FIELDS)
            and len(snapshot["ingress"]) == 1
            and snapshot["ingress"][0]["error"] is None
            and snapshot["ingress"][0]["fields"] == expected
            and snapshot["tickets"] == [expected]
            and response_matches(snapshot, ended=time.time())
        )
        return {
            "schema_version": 1,
            "kind": "ticket_oracle",
            "database": str(path),
            "expected": dict(expected),
            "checked_at": time.time(),
            "ok": ok,
            "detail": "exactly one ingress and matching durable row"
            if ok
            else "ticket fields, row or independent ingress count differ",
            **snapshot,
        }

    @staticmethod
    def readonly_check(path: Path, expected: dict[str, str]) -> dict:
        """Recheck an already-existing fixture DB without initializing or writing it."""
        db = sqlite3.connect(f"file:{quote(str(path))}?mode=ro", uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN")
            snapshot = {
                "ingress": [
                    {**dict(row), "fields": json.loads(row["fields"])}
                    for row in db.execute("SELECT * FROM ingress ORDER BY id")
                ],
                "tickets": [
                    json.loads(row[0]) for row in db.execute("SELECT fields FROM tickets ORDER BY request_id")
                ],
                "responses": [dict(row) for row in db.execute("SELECT * FROM responses ORDER BY ingress_id")],
            }
            return TicketStore._checked(snapshot, expected, path)
        finally:
            db.close()


class TicketFixture:
    """Loopback-only actual POST form with a persistent independent ledger."""

    def __init__(
        self,
        root: Path,
        *,
        lose_reply_once: bool = False,
        port: int = 0,
        reply_loss: str = "disconnect",
        submission_route: str = "navigation",
    ):
        if not isinstance(reply_loss, str) or reply_loss not in {"disconnect", "truncated"}:
            raise QualificationError("unsupported reply-loss mode")
        if reply_loss != "disconnect" and not lose_reply_once:
            raise QualificationError("truncated reply loss requires lose_reply_once")
        if not isinstance(submission_route, str) or submission_route not in {"navigation", "fetch"}:
            raise QualificationError("unsupported submission route")
        self.submission_route = submission_route
        self.root = Path(root).resolve()
        self.store = TicketStore(self.root / "tickets.sqlite")
        self.lose_reply_once = lose_reply_once
        self.reply_loss = reply_loss
        self.store.bind_response_mode(reply_loss if lose_reply_once else "normal")
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != "/":
                    self.send_error(404)
                    return
                inputs = "".join(
                    f'<label>{html.escape(key)}<input name="{key}" aria-label="{key}" required></label>'
                    for key in FIELDS
                )
                submission = ""
                if fixture.submission_route == "fetch":
                    submission = """<p id="submission-result" role="status"></p><script>
const form = document.querySelector('form');
const result = document.getElementById('submission-result');
let attempted = false;
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (attempted) return;
  attempted = true;
  form.querySelector('button').disabled = true;
  const body = new URLSearchParams(new FormData(form));
  try {
    const response = await fetch(form.action, {method: 'POST', body});
    result.textContent = await response.text();
  } catch {
    result.textContent = 'Submission result unavailable; reconcile before another attempt.';
  }
});
</script>"""
                data = (
                    f"<!doctype html><title>Footwork owned ticket fixture</title><h1>Register asset</h1>"
                    f'<form method="post" action="/tickets">{inputs}<button type="submit">Register asset</button></form>'
                    + submission
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                if self.path != "/tickets":
                    self.send_error(404)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "-1"))
                except ValueError:
                    length = -1
                if not 0 <= length <= 4096:
                    fixture.store.reject(b"", "length_refused")
                    self.send_error(413)
                    return
                self.connection.settimeout(3)
                body = self.rfile.read(length)
                origin = self.headers.get("Origin")
                if origin is not None and origin != fixture.url:
                    fixture.store.reject(body, "origin_refused")
                    self.send_error(403)
                    return
                fields, error, lost, ingress_id = fixture.store.record(
                    body, lose_reply_once=fixture.lose_reply_once, origin=fixture.url, include_ingress_id=True
                )
                data = _json({"recorded": error is None, "fields": fields, "error": error}).encode()
                if lost:
                    if fixture.reply_loss == "truncated":
                        # This is an incomplete application response after known
                        # status/headers, distinct from the legacy zero-byte TCP
                        # disconnect that a browser can automatically replay.
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(data)))
                        self.end_headers()
                        self.wfile.flush()
                        fixture.store.record_response(ingress_id, "headers_flushed")
                    with contextlib.suppress(OSError):
                        self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                    return
                self.send_response(400 if error else 200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.flush()
                if error is None and not (fixture.lose_reply_once and fixture.reply_loss == "disconnect"):
                    fixture.store.record_response(ingress_id, "headers_flushed")
                self.wfile.write(data)

            def log_message(self, *_):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.store.bind_origin(self.url)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class HandoffRun:
    """Persistent stage gates; records proof, never performs the app operation."""

    def __init__(self, root: Path, authority: Path, epoch: str):
        self.root = Path(root).resolve(strict=True)
        authority = Path(authority)
        if not authority.is_absolute():
            raise QualificationError("explicit absolute authority required")
        self.authority = authority.resolve()
        self.path = self.root / "handoff.json"
        self.lock = self.root / "handoff.lock"
        if not isinstance(epoch, str) or not epoch:
            raise QualificationError("explicit epoch and authority required")
        self.epoch = epoch

    @contextlib.contextmanager
    def _owned(self):
        # Same lock order on every call: authority first, workflow second.
        with SessionOperations(self.authority) as operations:
            fd = os.open(self.lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                if self.path.is_symlink():
                    raise QualificationError("handoff manifest symlink")
                state = (
                    json.loads(self.path.read_text())
                    if self.path.exists()
                    else {
                        "version": 1,
                        "epoch": self.epoch,
                        "authority": str(self.authority),
                        "completed": [],
                        "active": None,
                    }
                )
                if self.path.exists():
                    digest = state.pop("integrity", None)
                    if digest != hashlib.sha256(_json(state).encode()).hexdigest():
                        raise QualificationError("handoff manifest integrity mismatch")
                if (
                    state.get("version") != 1
                    or state.get("epoch") != self.epoch
                    or state.get("authority") != str(self.authority)
                ):
                    raise QualificationError("handoff epoch/version/authority mismatch")
                self._validate_completed(operations, state)
                yield operations, state
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)

    def _save(self, state: dict) -> None:
        temporary = self.root / f".handoff-{os.getpid()}.tmp"
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(fd, "w") as stream:
                body = {**state, "integrity": hashlib.sha256(_json(state).encode()).hexdigest()}
                stream.write(_json(body) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            directory = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _validate_completed(operations: SessionOperations, state: dict) -> None:
        if not isinstance(state.get("completed"), list) or len(state["completed"]) > len(STAGES):
            raise QualificationError("invalid completed stages")
        for index, row in enumerate(state["completed"]):
            if row.get("stage") != STAGES[index] or not row.get("operations"):
                raise QualificationError("invalid recorded stage order")
            current = []
            for op_id in row["operations"]:
                op = operations.get(op_id)
                if (
                    op is None
                    or op.state != "final"
                    or op.phase != "sent"
                    or op.disposition not in ("applied", "partial")
                    or op.task != row.get("session_id")
                    or op.created < row.get("began", float("inf"))
                ):
                    raise QualificationError("recorded execution proof changed")
                retained = operations.qualified_receipt(op)
                if retained is None or retained["projection"].get("app") not in APP_NAMES[row["stage"]]:
                    raise QualificationError("recorded application proof changed")
                current.append(operations.receipt(op))
            if current != row.get("receipts"):
                raise QualificationError("recorded receipt differs from authority")

    def begin(self, stage: str, *, session_id: str) -> dict:
        if stage not in STAGES:
            raise QualificationError("unsupported stage")
        if not isinstance(session_id, str) or not session_id:
            raise QualificationError("stage requires its bound runtime session")
        with self._owned() as (operations, state):
            operations.assert_available()
            if state["active"] is not None:
                if state["active"]["stage"] != stage or state["active"]["session_id"] != session_id:
                    raise QualificationError("another handoff is active")
                previous = state["active"].get("input")
                if previous and artifact_identity(self.root, Path(previous["path"])) != previous:
                    raise QualificationError("active input changed; do not re-dispatch")
                return state["active"]
            index = len(state["completed"])
            if index >= len(STAGES) or stage != STAGES[index]:
                raise QualificationError("handoff order differs")
            previous = state["completed"][-1]["artifact"] if state["completed"] else None
            if previous and artifact_identity(self.root, Path(previous["path"])) != previous:
                raise QualificationError("prior artifact changed before handoff")
            state["active"] = {
                "stage": stage,
                "session_id": session_id,
                "input": previous,
                "began": time.time(),
            }
            self._save(state)
            return state["active"]

    def complete(self, stage: str, operation_ids: list[str], verify: Any, artifact: Path) -> dict:
        with self._owned() as (operations, state):
            operations.assert_available()
            old = next((row for row in state["completed"] if row["stage"] == stage), None)
            if old is not None:
                if (
                    old["operations"] != operation_ids
                    or artifact_identity(self.root, artifact) != old["artifact"]
                ):
                    raise QualificationError("completed handoff differs")
                return old
            if (
                not state["active"]
                or state["active"]["stage"] != stage
                or not operation_ids
                or len(set(operation_ids)) != len(operation_ids)
            ):
                raise QualificationError("handoff must be begun and name distinct operation receipts")
            receipts = []
            ticket_scope = None
            for op_id in operation_ids:
                op = operations.get(op_id)
                if (
                    op is None
                    or op.state != "final"
                    or op.phase != "sent"
                    or op.disposition not in ("applied", "partial")
                ):
                    raise QualificationError("operation has no settled sent custody")
                if op.task != state["active"]["session_id"]:
                    raise QualificationError("operation belongs to another runtime session")
                if op.created < state["active"]["began"]:
                    raise QualificationError("operation predates this handoff")
                try:
                    retained = operations.qualified_receipt(op)
                except (ValueError, TypeError, KeyError, AttributeError) as error:
                    raise QualificationError("invalid retained execution proof") from error
                if (
                    retained is None
                    or retained["phase"] != "sent"
                    or retained["effect"] not in ("confirmed", "partial")
                ):
                    raise QualificationError("operation lacks qualified retained execution")
                if retained["projection"].get("app") not in APP_NAMES[stage]:
                    raise QualificationError("operation belongs to another app")
                if stage == "chrome":
                    from jevdual import ticket_evidence

                    if (
                        len(operation_ids) != 1
                        or retained.get("kind") != "ticket_submission"
                        or type(retained.get("schema_version")) is not int
                        or retained["schema_version"] != ticket_evidence.VERSION
                    ):
                        raise QualificationError("Chrome requires its admitted v2 ticket service receipt")
                    ticket_scope = retained["projection"]["ticket_submission"]["scope"]
                receipts.append(operations.receipt(op))
            before = artifact_identity(self.root, artifact)
            check = verify()
            passed = check.get("ok") if isinstance(check, dict) else getattr(check, "ok", False)
            if passed is not True:
                raise QualificationError("independent postcondition failed")
            after = artifact_identity(self.root, artifact)
            if before != after:
                raise QualificationError("artifact changed during oracle check")
            active_input = state["active"].get("input")
            if stage == "preview" and (not active_input or after["path"] != active_input["path"]):
                raise QualificationError("Preview output is not its bound input path")
            if stage == "chrome" and after != active_input:
                raise QualificationError("Chrome changed or replaced the handoff artifact")
            if stage == "chrome":
                if (
                    not isinstance(check, dict)
                    or type(check.get("schema_version")) is not int
                    or check["schema_version"] not in (1, 2)
                    or check.get("kind") != "ticket_oracle"
                ):
                    raise QualificationError("Chrome requires a bound independent ticket oracle")
                expected = check.get("expected")
                if (
                    not isinstance(expected, dict)
                    or set(expected) != set(FIELDS)
                    or expected.get("artifact") != Path(after["path"]).name
                    or expected.get("digest") != after["sha256"]
                    or expected.get("orientation") != "clockwise90"
                ):
                    raise QualificationError("ticket oracle names a different artifact or transformation")
                if (
                    ticket_scope is None
                    or expected != ticket_scope["expected"]
                    or check.get("database") != ticket_scope["source"]["database"]
                    or ticket_scope["artifact"] != after
                    or "source" in check
                    and check["source"] != ticket_scope["source"]
                ):
                    raise QualificationError("ticket oracle differs from the admitted submission")
                try:
                    check = ticket_evidence.check_bound(ticket_scope, began=state["active"]["began"])
                except (ValueError, TypeError, KeyError, AttributeError, OSError) as error:
                    raise QualificationError("admitted ticket source no longer qualifies") from error
                if check["ok"] is not True:
                    raise QualificationError("independent ticket readback no longer matches")
                if check["ingress"][0]["received"] < state["active"]["began"]:
                    raise QualificationError("ticket ingress predates this browser handoff")
            else:
                identity = getattr(check, "identity", None)
                checked_artifact = getattr(check, "artifact", None)
                if (
                    not isinstance(identity, dict)
                    or checked_artifact != after["path"]
                    or any(identity.get(key) != value for key, value in after.items())
                ):
                    raise QualificationError("oracle checked a different artifact identity")
                if stage == "preview" and "rotation_clockwise90" not in getattr(check, "claims", ()):
                    raise QualificationError("Preview oracle does not check the intended clockwise transform")
            if artifact_identity(self.root, artifact) != after:
                raise QualificationError("artifact changed before handoff commit")
            row = {
                "stage": stage,
                "session_id": state["active"]["session_id"],
                "began": state["active"]["began"],
                "operations": operation_ids,
                "receipts": receipts,
                "artifact": after,
                "oracle": check
                if isinstance(check, dict)
                else check.to_record()
                if hasattr(check, "to_record")
                else {"ok": check.ok, "detail": check.detail},
                "completed": time.time(),
            }
            state["completed"].append(row)
            state["active"] = None
            self._save(state)
            return row

    def snapshot(self) -> dict:
        with self._owned() as (_, state):
            return state


def main() -> None:
    """Run only the owned local web fixture; UI actions belong to Footwork."""
    import argparse
    import signal

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--lose-reply-once", action="store_true")
    parser.add_argument("--reply-loss", choices=("disconnect", "truncated"))
    parser.add_argument("--submission-route", choices=("navigation", "fetch"), default="navigation")
    args = parser.parse_args()
    if args.reply_loss is not None and not args.lose_reply_once:
        parser.error("--reply-loss requires --lose-reply-once")

    def stop(*_):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    try:
        with TicketFixture(
            args.root,
            port=args.port,
            lose_reply_once=args.lose_reply_once,
            reply_loss=args.reply_loss or "disconnect",
            submission_route=args.submission_route,
        ) as fixture:
            print(
                _json(
                    {
                        "url": fixture.url,
                        "pid": os.getpid(),
                        "database": str(fixture.store.path),
                        "lose_reply_once": fixture.lose_reply_once,
                        "reply_loss": fixture.reply_loss,
                        "submission_route": fixture.submission_route,
                    }
                ),
                flush=True,
            )
            while True:
                signal.pause()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
