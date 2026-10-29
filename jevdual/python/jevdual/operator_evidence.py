"""Versioned runtime evidence. Records qualify only their declared predicate.

These validators enforce a cooperative runtime protocol, not authentication of
arbitrary supplied files. Execution receipts are retained by SessionOperations;
current agreement cannot manufacture a historical execution receipt.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

VERSION = "1"
BASES = frozenset(
    {
        "sdk_delivery_count",
        "ax_insert_ack",
        "ax_menu_press_ack",
        "ax_menu_effect_readback",
        "ax_finder_rename_readback",
        "ax_finder_move_readback",
        "qualified_gate",
        "unknown",
    }
)
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


def _validate_native_readback(
    proof: Any, basis: str, binding: dict[str, Any], effect: str, op: Any, projection: dict[str, Any]
) -> None:
    if not isinstance(proof, dict) or (
        type(proof.get("schema_version")) is not int or proof.get("schema_version") != 1
    ):
        raise EvidenceError("missing qualified native readback")
    if basis == "ax_finder_move_readback":
        _validate_finder_move(proof, binding, effect, op, projection)
        return
    if basis == "ax_menu_effect_readback":
        from jevdual.native import preview_menu_readback

        paths = {
            "preview_rotate_right_ui_transition": ["Tools", "Rotate Right"],
            "preview_rotate_left_ui_transition": ["Tools", "Rotate Left"],
            "preview_save_ui_transition": ["File", "Save"],
            "preview_save_file_transition": ["File", "Save"],
        }
        path = paths.get(proof.get("predicate"))
        if (
            path is None
            or proof.get("producer") != "footwork.ax.preview"
            or preview_menu_readback(path, proof.get("before"), proof.get("after")) != proof
        ):
            raise EvidenceError("unqualified Preview readback")
        words = getattr(op, "args", {}).get("words", [])
        if (
            op.move != "menu"
            or not words
            or words[0] != "menu"
            or [p.strip() for p in " ".join(words[1:]).split(">") if p.strip()] != path
            or projection.get("app") != "Preview"
        ):
            raise EvidenceError("Preview predicate differs from admitted menu")
        for state in (proof["before"], proof["after"]):
            if any(
                type(state.get(key)) is not int or state[key] != binding[key] for key in ("pid", "window_id")
            ):
                raise EvidenceError("Preview readback window differs")
    else:
        from jevdual.finder_targets import FinderBinding

        if (
            proof.get("producer") != "footwork.ax.finder"
            or proof.get("predicate") != "finder_rename_same_inode"
        ):
            raise EvidenceError("unqualified Finder readback")
        before = proof.get("before")
        if (
            not isinstance(before, dict)
            or type(before.get("pid")) is not int
            or type(before.get("window_id")) is not int
            or before.get("pid") != binding["pid"]
            or before.get("window_id") != binding["window_id"]
        ):
            raise EvidenceError("Finder readback window differs")
        if effect in {"confirmed", "partial"}:
            try:
                old = FinderBinding.from_record(before["binding"])
                new = FinderBinding.from_record(proof["after"])
            except Exception as exc:
                raise EvidenceError("invalid Finder identity readback") from exc
            if (
                new.path != proof.get("destination")
                or old.path == new.path
                or {**old.to_record(), "path": new.path} != new.to_record()
            ):
                raise EvidenceError("Finder identity transition differs")
            if (
                proof.get("acknowledgements")
                != ["exact_row_selected", "file_menu_opened", "rename_menu_pressed", "editor_value_set"]
                or proof.get("rename_enabled") is not True
                or proof.get("editor")
                != {
                    "pid": binding["pid"],
                    "window_id": binding["window_id"],
                    "role": "AXTextField",
                    "before_value": Path(old.path).name,
                }
                or not isinstance(proof.get("commit"), dict)
                or proof["commit"].get("route") != "sdk_foreground_return"
                or proof["commit"].get("effect")
                not in {"confirmed", "unverifiable", "partial", "suspected_noop"}
                or (
                    proof["commit"].get("delivered_count") is not None
                    and (
                        type(proof["commit"]["delivered_count"]) is not int
                        or proof["commit"]["delivered_count"] < 0
                    )
                )
            ):
                raise EvidenceError("Finder rename lacks qualified editor input")
            words = getattr(op, "args", {}).get("words", [])

            if (
                op.move != "type"
                or len(words) < 3
                or words[:2] != ["type", "file:" + old.path]
                or " ".join(words[2:]) != Path(new.path).name
                or new.path != str(Path(old.path).with_name(" ".join(words[2:])))
                or projection.get("app") != "Finder"
            ):
                raise EvidenceError("Finder predicate differs from admitted rename")
            scope = getattr(op, "args", {}).get("finder_scope", {})
            original = scope.get("binding", {})
            if not original or {**original, "path": old.path} != old.to_record():
                raise EvidenceError("Finder readback differs from admitted file identity")


def _validate_finder_move(
    proof: dict[str, Any], binding: dict[str, Any], effect: str, op: Any, projection: dict[str, Any]
) -> None:
    from jevdual.finder_targets import FinderBinding

    try:
        before = proof["before"]
        old = FinderBinding.from_record(before["binding"])
        args = op.args
        words = args["words"]
        manifest = args["finder_scope"]["manifest"]
        original = args["finder_scope"]["binding"]
        directory = " ".join(words[2:])
        expected_directory = str(Path(manifest["root"]) / Path(manifest["paths"]["organized"]).parent)
        if (
            proof.get("producer") != "footwork.ax.finder"
            or proof.get("predicate") != "finder_move_same_inode"
            or op.move != "move"
            or projection.get("app") != "Finder"
            or len(words) < 3
            or words[:2] != ["move", "file:" + old.path]
            or directory != expected_directory
            or proof.get("destination") != str(Path(directory) / Path(old.path).name)
            or {**original, "path": old.path} != old.to_record()
            or any(
                type(before.get(key)) is not int or before[key] != binding[key]
                for key in ("pid", "window_id")
            )
        ):
            raise EvidenceError("Finder move differs from admitted identity or destination")
        if effect not in {"confirmed", "partial"}:
            return
        new = FinderBinding.from_record(proof["after"])
        if (
            new.path != proof["destination"]
            or old.path == new.path
            or {**old.to_record(), "path": new.path} != new.to_record()
        ):
            raise EvidenceError("Finder move did not preserve file identity")
        source, after = proof["source_identity"], proof["after_identity"]
        for item, path in ((source, old.path), (after, new.path)):
            if (
                not isinstance(item, dict)
                or set(item) != {"path", "device", "inode", "size", "mtime_ns", "sha256"}
                or item["path"] != path
                or any(
                    type(item[k]) is not int or item[k] < 0 for k in ("device", "inode", "size", "mtime_ns")
                )
                or not isinstance(item["sha256"], str)
                or len(item["sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in item["sha256"])
            ):
                raise EvidenceError("invalid Finder move byte proof")
        if any(source[k] != after[k] for k in ("device", "inode", "size", "sha256")) or (
            source["device"],
            source["inode"],
        ) != (old.device, old.inode):
            raise EvidenceError("Finder move changed bytes or inode")
        destination = proof["destination_directory"]
        marker_path = str(Path(directory) / "keep.bin")
        marker = destination["sentinel_identity"]
        if (
            destination["path"] != directory
            or destination["sentinel_path"] != marker_path
            or any(type(destination[k]) is not int or destination[k] < 0 for k in ("device", "inode"))
            or marker["path"] != marker_path
            or marker["sha256"]
            != manifest["protected"][str(Path(manifest["paths"]["organized"]).parent / "keep.bin")]
        ):
            raise EvidenceError("Finder destination marker differs")
        navigation = proof["navigation"]
        registered = args["finder_scope"]["destination_window"]
        if (
            proof.get("transfer_route") != "prebound_destination_window"
            or proof.get("destination_window_binding") != registered
            or type(registered.get("pid")) is not int
            or registered["pid"] != binding["pid"]
            or type(registered.get("window_id")) is not int
            or registered["window_id"] <= 0
            or registered["window_id"] == binding["window_id"]
            or navigation != registered
        ):
            raise EvidenceError("Finder destination registration differs")
        if (
            navigation.get("basis") != "fresh_ax_destination_marker_and_owned_directory"
            or navigation.get("window_title") != Path(directory).name
            or not isinstance(navigation.get("ax_url"), str)
            or not navigation["ax_url"].startswith("file:")
            or any(
                type(navigation.get(k)) is not int or navigation[k] != registered[k]
                for k in ("pid", "window_id")
            )
            or any(navigation.get(k) != v for k, v in destination.items())
        ):
            raise EvidenceError("Finder destination window differs")
        clipboard = proof["clipboard"]
        if (
            clipboard.get("paths") != [old.path]
            or any(
                type(clipboard.get(k)) is not int or clipboard[k] < 0
                for k in ("before_change_count", "after_change_count")
            )
            or clipboard["after_change_count"] <= clipboard["before_change_count"]
            or proof.get("copy_menu_path")
            not in (
                ["Edit", "Copy"],
                ["Edit", f"Copy “{Path(old.path).name}”"],
                ["Edit", f'Copy "{Path(old.path).name}"'],
            )
        ):
            raise EvidenceError("Finder clipboard identity differs")
        acks = [
            "exact_row_selected",
            "edit_menu_opened_for_copy",
            "copy_menu_pressed",
            "edit_menu_opened_for_move",
            "move_item_here_pressed",
        ]
        if proof.get("acknowledgements") != acks:
            raise EvidenceError("Finder move lacks qualified input sequence")
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        if isinstance(exc, EvidenceError):
            raise
        raise EvidenceError("invalid Finder move readback") from exc


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
            or basis
            not in {
                "sdk_delivery_count",
                "ax_insert_ack",
                "ax_menu_press_ack",
                "ax_menu_effect_readback",
                "ax_finder_rename_readback",
                "ax_finder_move_readback",
            }
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
    if basis in {"ax_menu_effect_readback", "ax_finder_rename_readback", "ax_finder_move_readback"}:
        _validate_native_readback(projection.get("native_readback"), basis, binding, effect, op, projection)
        if (
            basis in {"ax_finder_rename_readback", "ax_finder_move_readback"}
            and effect in {"confirmed", "partial"}
            and count < len(projection["native_readback"]["acknowledgements"])
        ):
            raise EvidenceError("acknowledged input count contradicts native readback")
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
