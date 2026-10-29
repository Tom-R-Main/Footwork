"""Versioned runtime evidence. Records qualify only their declared predicate.

These validators enforce a cooperative runtime protocol, not authentication of
arbitrary supplied files. Execution receipts are retained by SessionOperations;
current agreement cannot manufacture a historical execution receipt.
"""

from __future__ import annotations

import json
import math
import time
from typing import Any

VERSION = "1"
BASES = frozenset({"sdk_delivery_count", "ax_insert_ack", "ax_menu_press_ack", "qualified_gate", "unknown"})
EFFECTS = frozenset({"confirmed", "partial", "unverifiable", "suspected_noop", "refused"})
MAX_RECORD_BYTES = 1_048_576


class EvidenceError(ValueError):
    """Unsupported, incomplete or contradictory evidence must not confer authority."""


def canonical(record: Any) -> str:
    try:
        raw = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise EvidenceError("evidence must be finite JSON") from exc
    if len(raw.encode()) > MAX_RECORD_BYTES:
        raise EvidenceError("evidence exceeds retention bound")
    return raw


def _text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise EvidenceError(f"missing {name}")


def _interval(value: Any) -> None:
    if not isinstance(value, dict) or set(value) != {"start", "end"}:
        raise EvidenceError("unsupported capture interval")
    for point in value.values():
        if type(point) not in (int, float) or not math.isfinite(point) or point < 0:
            raise EvidenceError("invalid capture time")
    if value["end"] < value["start"]:
        raise EvidenceError("capture interval reversed")


def validate_binding(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"boot", "pid", "start", "window_id"}:
        raise EvidenceError("unsupported native binding")
    _text(value["boot"], "boot identity")
    _text(value["start"], "process incarnation")
    if any(type(value[k]) is not int or value[k] <= 0 for k in ("pid", "window_id")):
        raise EvidenceError("invalid native binding")
    return value


def validate_execution(record: Any, op: Any, *, binding: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict) or set(record) != {
        "schema_version",
        "kind",
        "protocol",
        "operation_id",
        "session_id",
        "request_digest",
        "resource",
        "observation",
        "target",
        "move",
        "binding",
        "interval",
        "custody",
        "producer",
        "dispatched",
        "effect",
        "phase",
        "projection",
        "error",
    }:
        raise EvidenceError("unsupported execution record")
    canonical(record)
    if (
        record["schema_version"] != VERSION
        or record["kind"] != "execution"
        or type(record["protocol"]) is not int
        or record["protocol"] != 1
    ):
        raise EvidenceError("unsupported execution protocol")
    expected = {
        "operation_id": op.id,
        "session_id": op.task,
        "request_digest": op.request_digest,
        "resource": op.resource,
        "observation": op.observation,
        "target": op.target,
        "move": op.move,
    }
    if any(record.get(key) != value for key, value in expected.items()):
        raise EvidenceError("execution receipt belongs to another attempt")
    validate_binding(binding)
    validate_binding(record["binding"])
    if record["binding"] != binding:
        raise EvidenceError("execution binding differs from admission")
    from jevdual.session_operations import native_resource

    if native_resource(binding) != op.resource:
        raise EvidenceError("execution resource differs from native binding")
    _interval(record["interval"])
    if record["interval"]["start"] < op.created or record["interval"]["end"] > time.time():
        raise EvidenceError("execution interval does not follow admission")
    if record["custody"] != "returned":
        raise EvidenceError("execution custody is not settled")
    producer = record["producer"]
    if not isinstance(producer, dict) or set(producer) != {
        "name",
        "version",
        "delivery_basis",
        "delivered_count",
    }:
        raise EvidenceError("unsupported execution producer")
    if (
        producer["name"] != "footwork.native"
        or type(producer["version"]) is not int
        or producer["version"] != 1
    ):
        raise EvidenceError("unsupported execution producer version")
    basis, count = producer["delivery_basis"], producer["delivered_count"]
    if (
        not isinstance(basis, str)
        or basis not in BASES
        or (count is not None and (type(count) is not int or count < 0))
    ):
        raise EvidenceError("invalid delivery evidence")
    dispatched, phase, effect = record["dispatched"], record["phase"], record["effect"]
    if dispatched is not None and type(dispatched) is not bool:
        raise EvidenceError("invalid dispatch metadata")
    if (
        not isinstance(effect, str)
        or not isinstance(phase, str)
        or effect not in EFFECTS
        or phase not in {"not_sent", "sent", "ambiguous"}
    ):
        raise EvidenceError("unsupported execution outcome")
    if phase == "not_sent":
        if (
            dispatched is not False
            or basis != "qualified_gate"
            or count not in (None, 0)
            or effect != "refused"
        ):
            raise EvidenceError("no-send lacks qualified gate evidence")
    elif phase == "sent":
        if (
            dispatched is not True
            or basis not in {"sdk_delivery_count", "ax_insert_ack", "ax_menu_press_ack"}
            or not count
        ):
            raise EvidenceError("sent phase lacks delivery evidence")
        if basis == "ax_menu_press_ack" and effect in {"confirmed", "partial"}:
            raise EvidenceError("menu acknowledgement does not establish its application effect")
    elif dispatched is False or basis != "unknown" or count not in (None, 0):
        raise EvidenceError("ambiguous phase contradicts delivery evidence")
    if (
        not isinstance(record["projection"], dict)
        or record["error"] is not None
        and not isinstance(record["error"], str)
    ):
        raise EvidenceError("invalid execution projection/error")
    projection = record["projection"]
    arguments = getattr(op, "args", {})
    if not isinstance(arguments, dict) or projection.get("native_scope", {}) != arguments.get(
        "native_scope", {}
    ):
        raise EvidenceError("projection native scope differs from admitted request")
    for key, expected_value in (("operation_id", op.id), ("binding", binding)):
        if key in projection and projection[key] != expected_value:
            raise EvidenceError("projection differs from execution identity")
    if "binding" in projection:
        validate_binding(projection["binding"])
    if "op" in projection and projection["op"] != op.move:
        raise EvidenceError("projection move differs from execution")
    if "observation" in projection and projection["observation"] != op.observation:
        raise EvidenceError("projection observation differs from execution")
    if (
        "target_id" in projection
        and (None if projection["target_id"] is None else str(projection["target_id"])) != op.target
    ):
        raise EvidenceError("projection target differs from execution")
    if "dispatched" in projection and (
        type(projection["dispatched"]) is not type(dispatched) or projection["dispatched"] != dispatched
    ):
        raise EvidenceError("projection dispatch differs from execution")
    return record


def execution_record(
    op: Any,
    *,
    binding: dict[str, Any],
    started_at: float,
    ended_at: float,
    producer_evidence: dict[str, Any],
    dispatched: bool | None,
    effect: str,
    phase: str,
    projection: dict[str, Any],
    error: str | None = None,
) -> dict[str, Any]:
    record = {
        "schema_version": VERSION,
        "kind": "execution",
        "protocol": 1,
        "operation_id": op.id,
        "session_id": op.task,
        "request_digest": op.request_digest,
        "resource": op.resource,
        "observation": op.observation,
        "target": op.target,
        "move": op.move,
        "binding": binding,
        "interval": {"start": started_at, "end": ended_at},
        "custody": "returned",
        "producer": producer_evidence,
        "dispatched": dispatched,
        "effect": effect,
        "phase": phase,
        "projection": projection,
        "error": error,
    }
    return validate_execution(record, op, binding=binding)


def fact_record(
    *,
    kind: str,
    predicate: str,
    resource: str,
    binding: dict[str, Any],
    observation: str,
    started_at: float,
    ended_at: float,
    values: Any = (),
    evidence_refs: Any = (),
    limits: Any = (),
    parameters: dict[str, Any] | None = None,
    producer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if any(not isinstance(items, (tuple, list)) for items in (values, evidence_refs, limits)):
        raise EvidenceError("fact values/references/limits must be sequences")
    return validate_fact(
        {
            "schema_version": VERSION,
            "producer": producer or {"name": "footwork.session", "version": 1},
            "kind": kind,
            "predicate": predicate,
            "resource": resource,
            "binding": binding,
            "observation": observation,
            "interval": {"start": started_at, "end": ended_at},
            "values": list(values),
            "evidence_refs": list(evidence_refs),
            "limits": list(limits),
            "parameters": parameters or {},
        }
    )


def validate_fact(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict) or set(record) != {
        "schema_version",
        "producer",
        "kind",
        "predicate",
        "resource",
        "binding",
        "observation",
        "interval",
        "values",
        "evidence_refs",
        "limits",
        "parameters",
    }:
        raise EvidenceError("unsupported fact record")
    canonical(record)
    producer = record["producer"]
    if (
        record["schema_version"] != VERSION
        or not isinstance(producer, dict)
        or set(producer) != {"name", "version"}
        or producer["name"] != "footwork.session"
        or type(producer["version"]) is not int
        or producer["version"] != 1
    ):
        raise EvidenceError("unsupported fact producer/version")
    predicates = {
        "current_state": {"field_equals", "projection_field"},
        "persistence": {"disk_equals_window"},
        "task": {"task_postcondition"},
    }
    if (
        not isinstance(record["kind"], str)
        or not isinstance(record["predicate"], str)
        or record["predicate"] not in predicates.get(record["kind"], set())
    ):
        raise EvidenceError("predicate and evidence kind differ")
    validate_binding(record["binding"])
    _text(record["resource"], "fact resource")
    _text(record["observation"], "fact observation")
    _interval(record["interval"])
    if any(
        not isinstance(record[k], list) or any(not isinstance(v, str) for v in record[k])
        for k in ("values", "evidence_refs", "limits")
    ):
        raise EvidenceError("invalid fact values/references/limits")
    if not isinstance(record["parameters"], dict):
        raise EvidenceError("invalid fact parameters")
    return record
