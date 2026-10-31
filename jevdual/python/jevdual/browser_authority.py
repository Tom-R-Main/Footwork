"""Durable custody for the bounded owned-CDP native-button route.

This is a cooperative runtime protocol, not authentication of caller-supplied
evidence. The owned holder runs the guard and calls this journal before input.
An activation acknowledgement establishes no application postcondition. Neither
it nor a changed DOM can resolve an admitted operation as completed.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import asdict
from typing import Any

from jevdual.capability.journal import JournalError, Operation
from jevdual.session_operations import SessionOperations, _digest

PROTOCOL = "footwork.browser.cdp"
VERSION = 1
ROUTE = "dom_event_native_button"
MAX_RECORD_BYTES = 1_048_576
_BINDING = frozenset({
    "boot", "pid", "start", "browser_context", "target", "cdp_session", "frame", "loader",
    "backend_node", "execution_context", "document_token", "fingerprint",
})
_NO_SEND = frozenset({
    "stale_ref", "target_changed", "document_changed", "browser_route_unqualified",
    "browser_mutation_unqualified", "document_unavailable", "browser_validation_unavailable",
    "browser_connection_closed", "button_changed", "button_disabled", "button_hidden",
    "button_validation_unavailable",
})


class BrowserEvidenceError(JournalError):
    """Unsupported browser records cannot confer authority or settle custody."""

    code = "browser_evidence_invalid"


def canonical(value: Any) -> str:
    try:
        body = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise BrowserEvidenceError("browser evidence must be finite JSON") from exc
    if len(body.encode()) > MAX_RECORD_BYTES:
        raise BrowserEvidenceError("browser evidence exceeds retention bound")
    return body


def _text(value: Any, name: str, *, empty: bool = False) -> None:
    if not isinstance(value, str) or (not value and not empty) or len(value) > 8192:
        raise BrowserEvidenceError(f"invalid browser {name}")


def validate_binding(binding: Any) -> dict[str, Any]:
    """Validate browser v1 identity independently of native window identity."""
    if not isinstance(binding, dict) or set(binding) != _BINDING:
        raise BrowserEvidenceError("unsupported browser binding")
    canonical(binding)
    for key in _BINDING - {"pid", "backend_node", "execution_context"}:
        _text(binding[key], key, empty=key == "browser_context")
    for key in ("pid", "backend_node", "execution_context"):
        if type(binding[key]) is not int or binding[key] <= 0:
            raise BrowserEvidenceError(f"invalid browser {key}")
    try:
        incarnation = float(binding["start"])
        fingerprint = json.loads(binding["fingerprint"])
    except (ValueError, TypeError) as exc:
        raise BrowserEvidenceError("invalid browser incarnation or fingerprint") from exc
    if not math.isfinite(incarnation) or incarnation <= 0 or repr(incarnation) != binding["start"]:
        raise BrowserEvidenceError("invalid browser incarnation")
    if not isinstance(fingerprint, dict) or set(fingerprint) != {"tag", "attrs", "text", "ancestors"}:
        raise BrowserEvidenceError("unsupported button fingerprint")
    if (fingerprint["tag"] != "button" or not isinstance(fingerprint["attrs"], list)
            or not isinstance(fingerprint["text"], str) or not isinstance(fingerprint["ancestors"], list)):
        raise BrowserEvidenceError("invalid button fingerprint")
    canonical(fingerprint)
    return binding


def browser_resource(binding: dict[str, Any]) -> str:
    validate_binding(binding)
    return "browser:" + canonical({
        key: binding[key] for key in ("boot", "pid", "start", "browser_context", "target")
    })


def _request(request: Any) -> None:
    if not isinstance(request, dict) or set(request) != {"ref", "route"} or request["route"] != ROUTE:
        raise BrowserEvidenceError("unsupported browser request")
    _text(request["ref"], "ref")


def guard_digest(session_id: str, request: dict[str, Any], binding: dict[str, Any]) -> str:
    return hashlib.sha256(canonical({"session": session_id, "request": request, "binding": binding}).encode()).hexdigest()


def _guard(guard: Any, session_id: str, request: dict[str, Any], binding: dict[str, Any]) -> None:
    if (not isinstance(guard, dict) or set(guard) != {"producer", "version", "decision", "digest"}
            or guard["producer"] != "footwork.browser.guard" or type(guard["version"]) is not int
            or guard["version"] != VERSION or guard["decision"] != "allow"
            or not isinstance(guard["digest"], str) or not re.fullmatch("[0-9a-f]{64}", guard["digest"])
            or guard["digest"] != guard_digest(session_id, request, binding)):
        raise BrowserEvidenceError("browser admission requires its bound configured guard decision")


def _outcome(reply: Any) -> tuple[str, str, str]:
    if (not isinstance(reply, dict) or set(reply) != {"status", "dispatched", "route", "code"}
            or reply["status"] not in ("ok", "refused", None)
            or (reply["dispatched"] is not None and type(reply["dispatched"]) is not bool)
            or reply["route"] not in (ROUTE, None)
            or (reply["code"] is not None and not isinstance(reply["code"], str))):
        raise BrowserEvidenceError("unsupported browser runtime reply")
    if (reply["status"] == "refused" and reply["dispatched"] is False
            and reply["code"] in _NO_SEND):
        return "not_sent", "refused", "qualified_gate"
    if (reply["status"] == "ok" and reply["dispatched"] is True
            and reply["route"] == ROUTE and reply["code"] is None):
        return "sent", "unverifiable", "activation_ack"
    return "ambiguous", "unverifiable", "unknown"


def operation_record(op: Operation) -> dict[str, Any]:
    """Expose custody without turning activation or replay into completion."""
    return {**asdict(op), "completion": "unverified", "retryable": False}


class BrowserAuthority(SessionOperations):
    """Reuse the shared authority domain; keep browser evidence a separate protocol."""

    def _admission(self, op: Operation) -> dict[str, Any]:
        row = self._db.execute(
            "SELECT projection FROM operator_admissions WHERE operation=?", (op.id,)
        ).fetchone()
        try:
            projection = json.loads(row[0]) if row else None
            if (not isinstance(projection, dict)
                    or set(projection) != {"protocol", "version", "binding", "guard"}
                    or projection["protocol"] != PROTOCOL or type(projection["version"]) is not int
                    or projection["version"] != VERSION):
                raise BrowserEvidenceError("not a browser authority admission")
            _request(op.args)
            binding = validate_binding(projection["binding"])
            _guard(projection["guard"], op.task, op.args, binding)
            if (op.resource != browser_resource(binding) or op.observation != op.args["ref"]
                    or op.target != str(binding["backend_node"]) or op.move != "click"
                    or op.request_digest != _digest(op.task, op.args)):
                raise BrowserEvidenceError("browser identity differs from admission")
            return projection
        except (ValueError, TypeError, KeyError) as exc:
            raise BrowserEvidenceError("invalid retained browser admission") from exc

    def _is_browser(self, op: Operation) -> bool:
        # The resource namespace selects validation; malformed browser admissions must
        # fail closed rather than falling through to a native validator.
        return op.resource.startswith("browser:")

    def admit_click(self, *, session_id: str, token: str, request: dict[str, Any],
                    binding: dict[str, Any], guard: dict[str, Any]) -> Operation:
        _text(session_id, "session")
        _text(token, "client token")
        _request(request)
        prior = self.by_request(session_id, token, request)
        if prior is not None:
            self._admission(prior)
            return prior
        validate_binding(binding)
        _guard(guard, session_id, request, binding)
        return super().admit(
            session_id=session_id, token=token, request=request, resource=browser_resource(binding),
            observation=request["ref"], target=str(binding["backend_node"]), move="click",
            authorization_basis="configured_browser_guard",
            projection={"protocol": PROTOCOL, "version": VERSION, "binding": binding, "guard": guard},
        )

    def start(self, op_id: str) -> Operation:
        op = self._owned(op_id)
        if self._is_browser(op):
            self._admission(op)
        return super().start(op_id)

    def mark_unknown(self, op_id: str) -> Operation:
        """Retain interruption without pretending that the effector returned a reply."""
        op = self._owned(op_id)
        if not self._is_browser(op):
            raise BrowserEvidenceError("not a browser authority operation")
        if op.state != "dispatching":
            return op
        if op.execution_stage != "started":
            raise BrowserEvidenceError("unknown input requires a started admission")
        try:
            record = self._retained_execution(op)
        except (BrowserEvidenceError, ValueError, TypeError, KeyError):
            record = None
        if record is not None:
            return self.finish_from_execution(op.id)
        # No returned receipt exists. This writes uncertainty only and deliberately
        # bypasses browser finalization, which requires a valid returned record.
        return super().finish(
            op.id, dispatched=None, effect="unverifiable", phase="ambiguous",
            evidence={"protocol": PROTOCOL, "version": VERSION, "completion": "unverified"},
            error="browser execution outcome unavailable; do not retry",
        )

    def finish(self, op_id: str, *, dispatched: bool | None, effect: str, evidence: dict[str, Any],
               error: str | None = None, delivered: bool | None = None,
               phase: str | None = None) -> Operation:
        op = self._owned(op_id)
        if self._is_browser(op):
            # Generic native finalization must not confer browser no-send or effect proof.
            if effect in {"confirmed", "partial"} or delivered is True:
                raise BrowserEvidenceError("browser activation cannot establish application completion")
            record = self._retained_execution(op)
            if dispatched is False and (record is None or record["phase"] != "not_sent"):
                raise BrowserEvidenceError("browser no-send requires its retained qualified gate")
            if record is not None and any(
                value != record[key] for key, value in
                (("dispatched", dispatched), ("effect", effect), ("phase", phase), ("error", error))
            ):
                raise BrowserEvidenceError("browser finalization differs from its retained runtime reply")
        return super().finish(op_id, dispatched=dispatched, effect=effect, evidence=evidence,
                              error=error, delivered=delivered, phase=phase)

    def _validate_record(self, record: Any, op: Operation) -> dict[str, Any]:
        admission = self._admission(op)
        expected = {
            "protocol": PROTOCOL, "schema_version": VERSION, "kind": "browser_execution",
            "operation_id": op.id, "session_id": op.task, "request_digest": op.request_digest,
            "resource": op.resource, "observation": op.observation, "target": op.target, "move": op.move,
            "binding": admission["binding"], "guard": admission["guard"], "custody": "returned",
            "producer": {"name": PROTOCOL, "version": VERSION},
        }
        keys = {*expected, "interval", "reply", "dispatched", "phase", "effect", "basis", "projection", "error"}
        if not isinstance(record, dict) or set(record) != keys:
            raise BrowserEvidenceError("unsupported browser execution record")
        canonical(record)
        if (any(record[key] != value for key, value in expected.items())
                or type(record["schema_version"]) is not int
                or type(record["producer"].get("version")) is not int):
            raise BrowserEvidenceError("browser execution belongs to another attempt")
        interval = record["interval"]
        if (not isinstance(interval, dict) or set(interval) != {"start", "end"}
                or any(type(v) not in (float, int) or not math.isfinite(v) for v in interval.values())
                or not op.created <= interval["start"] <= interval["end"] <= time.time()):
            raise BrowserEvidenceError("invalid browser execution interval")
        phase, effect, basis = _outcome(record["reply"])
        dispatched = False if phase == "not_sent" else True if phase == "sent" else None
        if (record["phase"] != phase or record["effect"] != effect or record["basis"] != basis
                or type(record["dispatched"]) is not type(dispatched) or record["dispatched"] != dispatched
                or record["projection"] != admission or record["error"] is not None):
            raise BrowserEvidenceError("browser execution contradicts its qualified outcome")
        return record

    def record_execution(self, op_id: str, capsule: dict[str, Any]) -> None:
        op = self._owned(op_id)
        if not self._is_browser(op):
            return super().record_execution(op_id, capsule)
        if op.state != "dispatching" or op.execution_stage != "started":
            raise BrowserEvidenceError("browser receipt requires a started owned attempt")
        self._validate_record(capsule, op)
        body = canonical(capsule)
        digest = hashlib.sha256(body.encode()).hexdigest()
        with self._tx() as db:
            prior = db.execute(
                "SELECT body,digest FROM operator_execution_receipts WHERE operation=?", (op.id,)
            ).fetchone()
            if prior is not None:
                if (prior["body"], prior["digest"]) != (body, digest):
                    raise BrowserEvidenceError("browser execution receipt is immutable")
                return
            db.execute("INSERT INTO operator_execution_receipts VALUES (?,?,?,?)",
                       (op.id, body, digest, time.time()))
            self._event(db, op.id, "browser_execution_retained", {"protocol": PROTOCOL, "version": VERSION})

    def _retained_execution(self, op: Operation) -> dict[str, Any] | None:
        if not self._is_browser(op):
            return super()._retained_execution(op)
        self._admission(op)
        row = self._db.execute(
            "SELECT * FROM operator_execution_receipts WHERE operation=?", (op.id,)
        ).fetchone()
        if row is None:
            return None
        if hashlib.sha256(row["body"].encode()).hexdigest() != row["digest"]:
            raise BrowserEvidenceError("browser execution receipt integrity failed")
        record = self._validate_record(json.loads(row["body"]), op)
        if record["interval"]["end"] > row["recorded"]:
            raise BrowserEvidenceError("browser execution receipt predates capture")
        return record

    def record_reply(self, op_id: str, reply: dict[str, Any]) -> Operation:
        op = self._owned(op_id)
        admission = self._admission(op)
        phase, effect, basis = _outcome(reply)
        now = time.time()
        record = {
            "protocol": PROTOCOL, "schema_version": VERSION, "kind": "browser_execution",
            "operation_id": op.id, "session_id": op.task, "request_digest": op.request_digest,
            "resource": op.resource, "observation": op.observation, "target": op.target, "move": op.move,
            "binding": admission["binding"], "guard": admission["guard"], "custody": "returned",
            "producer": {"name": PROTOCOL, "version": VERSION},
            "interval": {"start": op.updated, "end": now}, "reply": reply,
            "dispatched": False if phase == "not_sent" else True if phase == "sent" else None,
            "phase": phase, "effect": effect, "basis": basis, "projection": admission, "error": None,
        }
        self.record_execution(op_id, record)
        return self.finish_from_execution(op_id)

    def _reconcile_execution(self, op_id: str) -> Operation:
        op = self._owned(op_id)
        if not self._is_browser(op):
            return super()._reconcile_execution(op_id)
        try:
            return super()._reconcile_execution(op_id)
        except (BrowserEvidenceError, ValueError, TypeError, KeyError):
            # A missing, foreign or tampered retained result never releases custody.
            return op

    def reconcile(self, op_id: str) -> Operation:
        op = self._owned(op_id)
        if not self._is_browser(op):
            return super().reconcile(op_id)
        return self._reconcile_execution(op_id)
