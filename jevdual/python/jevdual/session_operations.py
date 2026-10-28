"""Durable admission for explicitly enrolled native CLI sessions.

Uses the capability Journal's operation rows, SQLite transaction and ownership lock.
The first operator protocol serializes admission across this authority database;
unknown outcomes block the domain. It does not coordinate other databases or MCP
workers. Callers must hold this object before loading mutable session state.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Self

from jevdual import grants
from jevdual.capability.journal import Busy, Journal, JournalError, Operation, TokenConflict

PROTOCOL = 1
_SCHEMA = """
CREATE TABLE IF NOT EXISTS operator_metadata (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS operator_grants (
    session TEXT NOT NULL, id TEXT NOT NULL, resource TEXT NOT NULL,
    body TEXT NOT NULL, available INTEGER NOT NULL CHECK(available >= 0),
    PRIMARY KEY(session,id)
);
CREATE TABLE IF NOT EXISTS operator_reservations (
    operation TEXT PRIMARY KEY, session TEXT NOT NULL, grant_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('held','spent','released'))
);
CREATE TABLE IF NOT EXISTS operator_admissions (
    operation TEXT PRIMARY KEY, protocol INTEGER NOT NULL, request TEXT NOT NULL,
    authorization TEXT NOT NULL, projection TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS operator_execution_receipts (
    operation TEXT PRIMARY KEY, body TEXT NOT NULL, digest TEXT NOT NULL, recorded REAL NOT NULL
);
"""


class GrantRequired(JournalError):
    code = "grant_required"


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(session: str, request: dict[str, Any]) -> str:
    return hashlib.sha256(_json({"session": session, "request": request}).encode()).hexdigest()


def native_identity(pid: int, window_id: int) -> dict[str, Any]:
    """Process incarnation and bound window number; not a window-birth oracle."""
    from jevdual.capability.recovery import process_identity

    try:
        if sys.platform != "darwin" or pid <= 0 or window_id <= 0:
            raise ValueError("qualified native identity requires a live macOS process/window")
        boot = subprocess.check_output(["sysctl", "-n", "kern.bootsessionuuid"], text=True, timeout=2).strip()
        identity = {**process_identity(pid), "boot": boot, "window_id": window_id}
        if not boot or not identity.get("start"):
            raise ValueError("missing process incarnation")
        return identity
    except Exception as exc:
        raise JournalError(f"native_identity_unavailable: {type(exc).__name__}") from exc


def native_resource(identity: dict[str, Any]) -> str:
    if not identity.get("boot") or not identity.get("start") or not isinstance(identity.get("pid"), int):
        raise JournalError("native_identity_unavailable")
    return "native:" + _json({k: identity[k] for k in ("boot", "pid", "start")})


def native_binding(identity: dict[str, Any]) -> str:
    native_resource(identity)
    if not isinstance(identity.get("window_id"), int) or identity["window_id"] <= 0:
        raise JournalError("native_identity_unavailable")
    return _json(identity)


class SessionOperations(Journal):
    def __init__(self, path: Path):
        path = Path(path)
        if not path.is_absolute():
            raise JournalError("authority path must be absolute")
        super().__init__(path.resolve())
        try:
            self._db.executescript(_SCHEMA)
            with self._tx() as db:
                if db.execute("SELECT version FROM operator_metadata").fetchone() is None:
                    db.execute("INSERT INTO operator_metadata VALUES (?)", (PROTOCOL,))
        except BaseException:
            self.close()
            raise

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _recover(self) -> None:
        exists = self._db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='operator_metadata'"
        ).fetchone()
        if exists:
            versions = self._db.execute("SELECT version FROM operator_metadata").fetchall()
            if len(versions) != 1 or versions[0][0] != PROTOCOL:
                raise JournalError("unsupported operator authority version")
        super()._recover()
        if not exists:
            return
        with self._tx() as db:
            rows = db.execute(
                "SELECT o.id, a.request, a.protocol FROM operations o JOIN operator_admissions a "
                "ON a.operation=o.id WHERE o.state='unknown' AND o.execution_stage='prepared'"
            ).fetchall()
            for row in rows:
                op = self._get(db, row["id"])
                try:
                    valid = (
                        row["protocol"] == PROTOCOL
                        and _digest(op.task, json.loads(row["request"])) == op.request_digest
                    )
                except (ValueError, TypeError):
                    valid = False
                if not valid:
                    continue
                db.execute(
                    "UPDATE operations SET state='final', disposition='not_sent', phase='not_sent', "
                    "resolved_by='recovery', evidence=?, error=NULL, updated=? WHERE id=?",
                    (_json({"protocol": PROTOCOL, "prepared_only": True}), time.time(), op.id),
                )
                self._settle(db, op.id, "released")
                self._event(db, op.id, "resolve", {"by": "prepared_protocol", "disposition": "not_sent"})

    def by_request(self, session_id: str, token: str | None, request: dict[str, Any]) -> Operation | None:
        if token is None:
            return None
        prior = self.by_token(session_id, token)
        if prior is not None and prior.request_digest != _digest(session_id, request):
            raise TokenConflict(prior.id)
        return prior

    def assert_available(self) -> None:
        row = self._db.execute(
            "SELECT id FROM operations WHERE state IN ('dispatching','unknown') ORDER BY created LIMIT 1"
        ).fetchone()
        if row is not None:
            raise Busy(row[0])

    def issue_grant(self, session_id: str, grant: grants.Grant, *, resource: str) -> None:
        if grant.uses_left < 1 or not resource:
            raise GrantRequired("grant requires available uses and qualified resource binding")
        with self._tx() as db:
            db.execute(
                "INSERT INTO operator_grants VALUES (?,?,?,?,?)",
                (session_id, grant.id, resource, _json(asdict(grant)), grant.uses_left),
            )

    def matching_grant(
        self, session_id: str, proposal: grants.Proposal, *, resource: str
    ) -> tuple[grants.Grant | None, list[str]]:
        return self._matching(self._db, session_id, proposal, resource)

    @staticmethod
    def _matching(
        db: Any, session_id: str, proposal: grants.Proposal, resource: str
    ) -> tuple[grants.Grant | None, list[str]]:
        reasons = []
        for row in db.execute("SELECT * FROM operator_grants WHERE session=? ORDER BY rowid", (session_id,)):
            body = json.loads(row["body"])
            body["selection"] = tuple(body.get("selection") or ())
            grant = replace(grants.Grant(**body), uses_left=row["available"])
            why = (
                "resource binding changed" if row["resource"] != resource else grants.why_not(grant, proposal)
            )
            if why is None:
                return grant, []
            reasons.append(f"grant {grant.id}: {why}")
        return None, reasons

    def admit(
        self,
        *,
        session_id: str,
        token: str | None,
        request: dict[str, Any],
        resource: str,
        observation: str,
        target: str | None,
        move: str,
        proposal: grants.Proposal | None = None,
        authorization_basis: str,
        projection: dict[str, Any],
        grant_resource: str | None = None,
    ) -> Operation:
        digest = _digest(session_id, request)
        raw_request, raw_projection = _json(request), _json(projection)
        if not session_id or not resource or not authorization_basis:
            raise JournalError("admission requires session, resource and authorization basis")
        with self._tx() as db:
            if token is not None:
                prior = self._by_token(db, session_id, token)
                if prior is not None:
                    if prior.request_digest != digest:
                        raise TokenConflict(prior.id)
                    return prior
            blocking = db.execute(
                "SELECT id FROM operations WHERE state IN ('dispatching','unknown') ORDER BY created LIMIT 1"
            ).fetchone()
            if blocking is not None:
                raise Busy(blocking[0])
            grant = None
            if proposal is not None:
                grant, reasons = self._matching(db, session_id, proposal, grant_resource or resource)
                if grant is None:
                    raise GrantRequired("; ".join(reasons) or "no matching grant")
            now, op_id = time.time(), "op_" + uuid.uuid4().hex[:12]
            db.execute(
                "INSERT INTO operations (id,task,resource,observation,target,move,args,request_digest,client_token,"
                "state,created,updated,execution_stage) VALUES (?,?,?,?,?,?,?,?,?,'dispatching',?,?,'prepared')",
                (
                    op_id,
                    session_id,
                    resource,
                    observation,
                    target,
                    move,
                    raw_request,
                    digest,
                    token,
                    now,
                    now,
                ),
            )
            db.execute(
                "INSERT INTO operator_admissions VALUES (?,?,?,?,?)",
                (op_id, PROTOCOL, raw_request, authorization_basis, raw_projection),
            )
            if grant is not None:
                db.execute(
                    "UPDATE operator_grants SET available=available-1 WHERE session=? AND id=?",
                    (session_id, grant.id),
                )
                db.execute(
                    "INSERT INTO operator_reservations VALUES (?,?,?,'held')", (op_id, session_id, grant.id)
                )
            self._event(db, op_id, "intent", {"protocol": PROTOCOL, "authorization": authorization_basis})
            return self._get(db, op_id)

    def start(self, op_id: str) -> Operation:
        self._owned(op_id)
        return super().start(op_id)

    def _owned(self, op_id: str) -> Operation:
        row = self._db.execute(
            "SELECT protocol FROM operator_admissions WHERE operation=?", (op_id,)
        ).fetchone()
        if row is None or row[0] != PROTOCOL:
            raise JournalError("not an operator protocol operation")
        op = self.get(op_id)
        if op is None:
            raise JournalError("missing operator operation")
        return op

    @staticmethod
    def _settle(db: Any, op_id: str, state: str) -> None:
        row = db.execute("SELECT * FROM operator_reservations WHERE operation=?", (op_id,)).fetchone()
        if row is None or row["state"] != "held":
            return
        if state == "released":
            db.execute(
                "UPDATE operator_grants SET available=available+1 WHERE session=? AND id=?",
                (row["session"], row["grant_id"]),
            )
        db.execute("UPDATE operator_reservations SET state=? WHERE operation=?", (state, op_id))

    def finish(
        self,
        op_id: str,
        *,
        dispatched: bool | None,
        effect: str,
        evidence: dict[str, Any],
        error: str | None = None,
        delivered: bool | None = None,
        phase: str | None = None,
    ) -> Operation:
        op = self._owned(op_id)
        if op.state != "dispatching" or op.execution_stage != "started":
            raise JournalError("only a started operator attempt can finish")
        if dispatched is False and delivered is True:
            raise JournalError("contradictory no-send/delivery")
        if phase not in (None, "not_sent", "sent", "ambiguous"):
            raise JournalError("unsupported delivery phase")
        phase = phase or ("not_sent" if dispatched is False else "sent" if delivered is True else "ambiguous")
        if (phase == "not_sent") != (dispatched is False) or (phase == "sent" and dispatched is not True):
            raise JournalError("delivery phase contradicts dispatch metadata")
        if delivered is True and phase != "sent":
            raise JournalError("qualified delivery contradicts phase")
        if effect not in ("confirmed", "partial", "unverifiable", "suspected_noop", "refused"):
            raise JournalError("unsupported effect")
        if dispatched is False:
            disposition, phase, state, settlement = "not_sent", "not_sent", "final", "released"
        elif phase == "sent" and effect in ("confirmed", "partial") and not error:
            disposition, phase, state, settlement = (
                ("applied" if effect == "confirmed" else "partial"),
                "sent",
                "final",
                "spent",
            )
        else:
            disposition, state = "unknown", "unknown"
            settlement = "spent" if phase == "sent" else "held"
        with self._tx() as db:
            db.execute(
                "UPDATE operations SET state=?,disposition=?,phase=?,evidence=?,error=?,updated=? WHERE id=?",
                (state, disposition, phase, _json(evidence), error, time.time(), op_id),
            )
            if settlement != "held":
                self._settle(db, op_id, settlement)
            self._event(db, op_id, "finish", {"disposition": disposition, "phase": phase})
            return self._get(db, op_id)

    def resolve(self, *_: Any, **__: Any) -> Operation:
        raise JournalError(
            "operator unknowns require a qualified reconciliation producer; manual resolution is unsupported"
        )

    def _execution_binding(self, op_id: str) -> dict[str, Any]:
        row = self._db.execute(
            "SELECT projection FROM operator_admissions WHERE operation=?", (op_id,)
        ).fetchone()
        if row is None:
            raise JournalError("missing admission binding")
        from jevdual.operator_evidence import EvidenceError, validate_binding

        try:
            return validate_binding(json.loads(row[0]).get("binding"))
        except (ValueError, TypeError, AttributeError) as exc:
            raise EvidenceError("admission lacks qualified execution binding") from exc

    def record_execution(self, op_id: str, capsule: dict[str, Any]) -> None:
        """Retain the returned runtime result before finalization; never import caller assertions."""
        from jevdual.operator_evidence import canonical, validate_execution

        op = self._owned(op_id)
        if op.state != "dispatching" or op.execution_stage != "started":
            raise JournalError("execution receipt requires a started, owned attempt")
        validate_execution(capsule, op, binding=self._execution_binding(op_id))
        body = canonical(capsule)
        digest = hashlib.sha256(body.encode()).hexdigest()
        with self._tx() as db:
            prior = db.execute(
                "SELECT body,digest FROM operator_execution_receipts WHERE operation=?", (op_id,)
            ).fetchone()
            if prior is not None:
                if (prior["body"], prior["digest"]) != (body, digest):
                    raise JournalError("execution receipt is immutable")
                return
            db.execute(
                "INSERT INTO operator_execution_receipts VALUES (?,?,?,?)",
                (op_id, body, digest, time.time()),
            )
            self._event(db, op_id, "execution_retained", {"schema_version": "1"})

    def _retained_execution(self, op: Operation) -> dict[str, Any] | None:
        from jevdual.operator_evidence import EvidenceError, validate_execution

        row = self._db.execute(
            "SELECT * FROM operator_execution_receipts WHERE operation=?", (op.id,)
        ).fetchone()
        if row is None:
            return None
        if hashlib.sha256(row["body"].encode()).hexdigest() != row["digest"]:
            raise EvidenceError("retained execution receipt integrity failed")
        record = json.loads(row["body"])
        validate_execution(record, op, binding=self._execution_binding(op.id))
        if record["interval"]["end"] > row["recorded"]:
            raise EvidenceError("execution receipt predates its capture")
        return record

    def finish_from_execution(self, op_id: str) -> Operation:
        """Finalize from the same validated retained producer record used by reconciliation."""
        op = self._owned(op_id)
        record = self._retained_execution(op)
        if record is None:
            raise JournalError("no retained execution receipt")
        return self.finish(
            op_id,
            dispatched=record["dispatched"],
            effect=record["effect"],
            phase=record["phase"],
            evidence={**record["projection"], "execution_receipt": record},
            error=record["error"],
        )

    def reconcile(self, op_id: str) -> Operation:
        """Resolve only from a retained returned execution record; never dispatch or read the app."""
        from jevdual.operator_evidence import EvidenceError

        op = self._owned(op_id)
        if op.state == "final":
            return op
        if op.state != "unknown" or op.execution_stage != "started":
            return op
        try:
            record = self._retained_execution(op)
        except (EvidenceError, ValueError, TypeError, KeyError):
            return op  # invalid evidence cannot release custody or settle authority
        if record is None:
            return op
        phase, effect, error = record["phase"], record["effect"], record["error"]
        if op.evidence.get("execution_receipt") == record and op.phase == phase:
            return op  # preserve original uncertainty history on repeated unknown reconciliation
        if phase == "not_sent":
            disposition, state, settlement = "not_sent", "final", "released"
        elif phase == "sent" and effect in ("confirmed", "partial") and not error:
            disposition, state, settlement = (
                ("applied" if effect == "confirmed" else "partial"),
                "final",
                "spent",
            )
        else:
            disposition, state, settlement = "unknown", "unknown", "spent" if phase == "sent" else "held"
        with self._tx() as db:
            current = self._get(db, op_id)
            if current.state != "unknown":
                raise JournalError("reconciliation requires unresolved custody")
            evidence = {**record["projection"], "execution_receipt": record}
            evidence["prior_uncertainty"] = {"phase": current.phase, "error": current.error}
            db.execute(
                "UPDATE operations SET state=?,disposition=?,phase=?,evidence=?,error=?,resolved_by=?,updated=? WHERE id=?",
                (
                    state,
                    disposition,
                    phase,
                    _json(evidence),
                    error,
                    "execution" if state == "final" else None,
                    time.time(),
                    op_id,
                ),
            )
            if settlement != "held":
                self._settle(db, op_id, settlement)
            self._event(db, op_id, "execution_reconciled", {"disposition": disposition, "phase": phase})
            return self._get(db, op_id)

    def status(self, session_id: str | None = None) -> list[Operation]:
        if session_id is not None:
            return self.recent(session_id, limit=100)
        return [
            Operation._from_row(row)
            for row in self._db.execute("SELECT * FROM operations ORDER BY created DESC LIMIT 100")
        ]

    def projection(self, op: Operation) -> dict[str, Any]:
        row = self._db.execute(
            "SELECT projection FROM operator_admissions WHERE operation=?", (op.id,)
        ).fetchone()
        if row is None:
            raise JournalError("missing operator projection")
        result = {**json.loads(row[0]), **op.evidence, "operation_id": op.id}
        if op.phase == "not_sent":
            result.update(dispatched=False, driver_effect="not sent", error=op.error)
        elif op.unresolved:
            result.update(
                dispatched=op.evidence.get("dispatched"),
                driver_effect="unverifiable",
                error=op.error or "operation outcome unknown; inspect status, do not repeat input",
            )
        return result

    def receipt(self, op: Operation) -> dict[str, Any]:
        row = self._db.execute(
            "SELECT state FROM operator_reservations WHERE operation=?", (op.id,)
        ).fetchone()
        return {
            "operation_id": op.id,
            "client_token": op.client_token,
            "state": op.state,
            "disposition": op.disposition,
            "phase": op.phase,
            "reservation": row[0] if row is not None else None,
            "projection": self.projection(op),
            "error": op.error,
        }
