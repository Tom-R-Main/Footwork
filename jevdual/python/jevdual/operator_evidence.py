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
        "ax_fullscreen_state_readback",
        "ax_infobar_disappearance_readback",
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


def fullscreen_readback_effect(proof: Any, control: Any, pid: Any, window_id: Any) -> str:
    """Validate a fixed fullscreen predicate, independently of generic visible UI changes."""
    required = {"schema_version", "producer", "predicate", "before", "after", "press_acknowledged", "transition_observed"}
    if (not isinstance(proof, dict) or set(proof) not in (required, required | {"error"})
            or type(proof.get("schema_version")) is not int or proof["schema_version"] != 1
            or proof.get("producer") != "footwork.ax.fullscreen"
            or proof.get("predicate") != "native_fullscreen_state_transition"
            or type(proof.get("press_acknowledged")) is not bool
            or type(proof.get("transition_observed")) is not bool
            or ("error" in proof and (not isinstance(proof["error"], str) or not proof["error"]))):
        raise EvidenceError("unsupported fullscreen readback")
    before = proof["before"]
    fields = {"pid", "window_id", "window_hash", "button_hash", "subrole", "fullscreen"}
    if (not isinstance(before, dict) or set(before) != fields or not isinstance(control, dict)
            or set(control) != fields or before != control
            or any(type(control[key]) is not type(before[key]) for key in fields)
            or any(type(before[key]) is not int or before[key] < 0 for key in fields - {"subrole", "fullscreen"})
            or type(pid) is not int or pid <= 0 or type(window_id) is not int or window_id <= 0
            or before["pid"] != pid or before["window_id"] != window_id
            or before["subrole"] != "AXFullScreenButton" or type(before["fullscreen"]) is not bool):
        raise EvidenceError("fullscreen target differs from admitted binding")
    after = proof["after"]
    transition = False
    if after is not None:
        if (not isinstance(after, dict) or set(after) != {"pid", "window_id", "fullscreen", "bounds"}
                or type(after["pid"]) is not int or type(after["window_id"]) is not int
                or after["pid"] != pid or after["window_id"] != window_id
                or type(after["fullscreen"]) is not bool):
            raise EvidenceError("fullscreen after-state differs from bound window")
        frame = after["bounds"]
        if frame is not None and (not isinstance(frame, dict) or set(frame) != {"x", "y", "w", "h"}
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in frame.values())
                or frame["w"] <= 0 or frame["h"] <= 0):
            raise EvidenceError("invalid fullscreen window bounds")
        transition = after["fullscreen"] is not before["fullscreen"]
    if proof["transition_observed"] != transition or (transition and "error" in proof):
        raise EvidenceError("contradictory fullscreen transition")
    return "confirmed" if proof["press_acknowledged"] and transition else "unverifiable"


def _validate_fullscreen_execution(proof: Any, binding: dict[str, Any], effect: str,
                                   op: Any, projection: dict[str, Any], basis: str, count: Any) -> None:
    identity = projection.get("target_identity")
    if not isinstance(identity, dict):
        raise EvidenceError("missing fullscreen target identity")
    control = identity.get("native_window_control")
    expected = fullscreen_readback_effect(proof, control, binding["pid"], binding["window_id"])
    label = "Exit Full Screen" if control["fullscreen"] else "Enter Full Screen"
    arguments = getattr(op, "args", {})
    if not isinstance(arguments, dict):
        raise EvidenceError("missing fullscreen admission arguments")
    words = arguments.get("words", [])
    if (op.move != "click" or op.target != "-2" or projection.get("op") != "click"
            or type(projection.get("target_id")) is not int or projection["target_id"] != -2
            or identity.get("role") != "button" or identity.get("section") != "Native window"
            or identity.get("label") != label or projection.get("target_label") != label
            or not isinstance(words, list) or len(words) != 2 or words[0] != "click"
            or not isinstance(words[1], str)
            or words[1].strip().casefold() not in {"-2", label.casefold(), "button:" + label.casefold()}
            or effect != expected or projection.get("driver_effect") != effect
            or projection.get("dispatched") is not True):
        raise EvidenceError("fullscreen proof differs from admitted click or effect")
    if proof["press_acknowledged"]:
        if basis != "ax_fullscreen_state_readback" or type(count) is not int or count != 1:
            raise EvidenceError("fullscreen acknowledgement lacks exact delivery evidence")
    elif basis != "unknown" or count is not None or effect != "unverifiable":
        raise EvidenceError("unacknowledged fullscreen press cannot confirm delivery")


def infobar_readback_effect(proof: Any, control: Any, pid: Any, window_id: Any) -> str:
    """Validate a fixed infobar predicate, independently of generic visible UI changes."""
    required = {"schema_version", "producer", "predicate", "before", "after", "press_acknowledged", "transition_observed"}
    if (not isinstance(proof, dict) or set(proof) not in (required, required | {"error"})
            or type(proof.get("schema_version")) is not int or proof["schema_version"] != 1
            or proof.get("producer") != "footwork.ax.infobar"
            or proof.get("predicate") != "native_infobar_disappearance"
            or type(proof.get("press_acknowledged")) is not bool
            or type(proof.get("transition_observed")) is not bool
            or ("error" in proof and (not isinstance(proof["error"], str) or not proof["error"]))):
        raise EvidenceError("unsupported infobar readback")
    before = proof["before"]
    from jevdual.menu import qualified_control_identity

    if (qualified_control_identity({"role": "button", "native_infobar_control": before}) is None
            or qualified_control_identity({"role": "button", "native_infobar_control": control}) is None
            or canonical(before) != canonical(control)
            or type(pid) is not int or pid <= 0 or type(window_id) is not int or window_id <= 0
            or before["pid"] != pid or before["window_id"] != window_id):
        raise EvidenceError("infobar target differs from admitted binding")
    after = proof["after"]
    transition = False
    if after is not None:
        fields = {"pid", "window_id", "window_hash", "tab_hashes", "infobar_absent", "window_retained", "tabs_retained"}
        if (not isinstance(after, dict) or set(after) != fields
                or any(type(after[k]) is not int or after[k] != before[k] for k in ("pid", "window_id", "window_hash"))
                or canonical(after["tab_hashes"]) != canonical(before["tab_hashes"])
                or any(type(after[k]) is not bool for k in ("infobar_absent", "window_retained", "tabs_retained"))):
            raise EvidenceError("infobar after-state differs from bound window/tabs")
        transition = after["infobar_absent"] and after["window_retained"] and after["tabs_retained"]
    if proof["transition_observed"] != transition or (transition and "error" in proof):
        raise EvidenceError("contradictory infobar transition")
    return "confirmed" if proof["press_acknowledged"] and transition else "unverifiable"


def infobar_action_identity(projection: Any, pid: Any, window_id: Any) -> Any:
    """One action-family binding shared by ordinary and durable consumers."""
    from jevdual.menu import qualified_control_identity

    if not isinstance(projection, dict):
        raise EvidenceError("missing infobar projection")
    identity = projection.get("target_identity")
    label = "Dismiss browser infobar"
    if (not isinstance(identity, dict) or projection.get("op") != "click"
            or type(projection.get("target_id")) is not int or projection["target_id"] != -3
            or projection.get("target_label") != label or identity.get("label") != label
            or identity.get("role") != "button" or identity.get("section") != "Native browser"
            or identity.get("native_window_control") is not None):
        raise EvidenceError("infobar action identity inconsistent")
    control = identity.get("native_infobar_control")
    if (qualified_control_identity(identity) is None or not isinstance(control, dict)
            or type(pid) is not int or type(window_id) is not int
            or control.get("pid") != pid or control.get("window_id") != window_id):
        raise EvidenceError("infobar action binding missing or different")
    return control


def _infobar_delivery_agreement(projection: dict[str, Any], *, dispatched: Any,
                                effect: str, basis: Any, count: Any) -> None:
    """Check every retained copy against one execution outcome, including no-send/unknown.

    Older/minimal execution projections can omit optional delivery metadata. If
    retained, its three delivery facts must all be present, strictly typed and
    agree; absent facts are never treated as zero or as acknowledgement.
    """
    if type(dispatched) not in (bool, type(None)):
        raise EvidenceError("invalid infobar dispatch type")
    if not isinstance(basis, str) or basis not in BASES or (count is not None and type(count) is not int):
        raise EvidenceError("invalid infobar delivery facts")
    if "dispatched" in projection and (
        type(projection["dispatched"]) is not type(dispatched) or projection["dispatched"] != dispatched
    ):
        raise EvidenceError("infobar projection dispatch differs")
    if "driver_effect" in projection:
        word = projection["driver_effect"]
        normalized = "refused" if word in ("not sent", "not dispatched") else word
        if normalized != effect:
            raise EvidenceError("infobar projection effect differs")
    if "native_delivery" in projection:
        delivery = projection["native_delivery"]
        if not isinstance(delivery, dict) or not set(delivery) <= {
            "dispatched", "delivery_basis", "delivered_count", "delivery", "driver_delivery", "route"
        }:
            raise EvidenceError("invalid retained infobar delivery")
        # These are the only route/posture facts the fixed AX producer can
        # emit. Historical records may omit optional fields, but a retained
        # invalid value is never treated as absence.
        acknowledged = basis == "ax_infobar_disappearance_readback"
        permitted = {
            "delivery": ("foreground",) if acknowledged else (None, "foreground"),
            "driver_delivery": (None,),
            "route": ("accessibility",) if acknowledged else ((None,) if dispatched is False else (None, "accessibility")),
        }
        for key, allowed in permitted.items():
            if key in delivery and not any(type(delivery[key]) is type(value) and delivery[key] == value for value in allowed):
                raise EvidenceError("infobar delivery route/posture contradicts fixed AX producer")
        for key, expected in (("dispatched", dispatched), ("delivery_basis", basis), ("delivered_count", count)):
            if key not in delivery or type(delivery[key]) is not type(expected) or delivery[key] != expected:
                raise EvidenceError("infobar nested delivery contradicts execution")


def _infobar_provenance_agreement(copies: list[dict[str, Any]], pid: int, window_id: int) -> None:
    """Present provenance is typed and agrees; omitted historical copies add no claim.

    This compares cooperative retained records, not authenticated external input.
    A lone session/incarnation value cannot establish history absent another copy.
    """
    for key in ("binding", "operation_id", "observation", "session_id", "error"):
        retained = []
        for record in copies:
            if key not in record:
                continue
            value = record[key]
            if key == "binding":
                bound = validate_binding(value)
                if bound["pid"] != pid or bound["window_id"] != window_id:
                    raise EvidenceError("infobar provenance belongs to another binding")
            elif key == "error":
                if value is not None and not isinstance(value, str):
                    raise EvidenceError("invalid infobar provenance error")
            else:
                _text(value, "infobar " + key)
            retained.append(canonical(value))
        if retained and any(value != retained[0] for value in retained[1:]):
            raise EvidenceError("infobar retained provenance copies differ: " + key)


def infobar_projection_effect(projection: Any, pid: Any, window_id: Any) -> str:
    """Validate all retained delivery claims before ordinary effect/no-send reporting."""
    control = infobar_action_identity(projection, pid, window_id)
    _infobar_provenance_agreement([projection], pid, window_id)
    delivery = projection.get("native_delivery")
    if not isinstance(delivery, dict):
        raise EvidenceError("missing infobar delivery")
    dispatched = projection.get("dispatched")
    raw_effect = projection.get("driver_effect")
    effect = "refused" if raw_effect in ("not sent", "not dispatched") else raw_effect
    basis, count = delivery.get("delivery_basis"), delivery.get("delivered_count")
    _infobar_delivery_agreement(projection, dispatched=dispatched, effect=effect, basis=basis, count=count)
    execution = projection.get("execution_receipt")
    if execution is not None:
        if not isinstance(execution, dict) or not isinstance(execution.get("producer"), dict):
            raise EvidenceError("invalid infobar execution receipt")
        expected_envelope = {"schema_version": VERSION, "kind": "execution", "protocol": 1,
                             "custody": "returned", "move": "click", "target": "-3"}
        if any(canonical(execution.get(k)) != canonical(value) for k, value in expected_envelope.items()):
            raise EvidenceError("infobar execution provenance or operation differs")
        producer = execution["producer"]
        if (set(producer) != {"name", "version", "delivery_basis", "delivered_count"}
                or producer.get("name") != "footwork.native"
                or type(producer.get("version")) is not int or producer["version"] != 1):
            raise EvidenceError("unsupported attached infobar producer")
        if (type(execution.get("dispatched")) is not type(dispatched) or execution.get("dispatched") != dispatched
                or execution.get("effect") != effect or execution["producer"].get("delivery_basis") != basis
                or type(execution["producer"].get("delivered_count")) is not type(count)
                or execution["producer"].get("delivered_count") != count):
            raise EvidenceError("infobar execution contradicts projection")
        inner = execution.get("projection")
        if not isinstance(inner, dict) or any(canonical(inner.get(k)) != canonical(projection.get(k)) for k in (
            "op", "target_id", "target_label", "target_identity", "native_readback", "dispatched", "driver_effect"
        )):
            raise EvidenceError("infobar execution action differs")
        _infobar_delivery_agreement(inner, dispatched=dispatched, effect=effect, basis=basis, count=count)
        if "native_delivery" in inner:
            for key in inner["native_delivery"].keys() & delivery.keys():
                if canonical(inner["native_delivery"][key]) != canonical(delivery[key]):
                    raise EvidenceError("infobar retained delivery copies differ")
        _infobar_provenance_agreement([projection, execution, inner], pid, window_id)
        if "execution_receipt" in inner:
            raise EvidenceError("nested infobar execution envelope unsupported")
    proof = projection.get("native_readback")
    if dispatched is False:
        if (proof is not None or effect != "refused" or basis != "qualified_gate"
                or type(count) is not int or count != 0
                or (execution is not None and execution.get("phase") != "not_sent")):
            raise EvidenceError("infobar no-send contradicts retained delivery evidence")
        return "refused"
    if dispatched is not True:
        raise EvidenceError("infobar dispatch unknown")
    observed = infobar_readback_effect(proof, control, pid, window_id)
    if effect != observed:
        raise EvidenceError("infobar effect contradicts readback")
    if proof["press_acknowledged"]:
        if (basis != "ax_infobar_disappearance_readback" or type(count) is not int or count != 1
                or (execution is not None and execution.get("phase") != "sent")):
            raise EvidenceError("infobar acknowledgement lacks delivery agreement")
    elif (basis != "unknown" or count is not None
          or (execution is not None and execution.get("phase") != "ambiguous")):
        raise EvidenceError("unacknowledged infobar delivery inconsistent")
    return observed


def _validate_infobar_execution(proof: Any, binding: dict[str, Any], effect: str,
                                   op: Any, projection: dict[str, Any], basis: str, count: Any) -> None:
    control = infobar_action_identity(projection, binding["pid"], binding["window_id"])
    identity = projection["target_identity"]
    expected = infobar_readback_effect(proof, control, binding["pid"], binding["window_id"])
    label = "Dismiss browser infobar"
    arguments = getattr(op, "args", {})
    if not isinstance(arguments, dict):
        raise EvidenceError("missing infobar admission arguments")
    words = arguments.get("words", [])
    if (op.move != "click" or op.target != "-3" or projection.get("op") != "click"
            or type(projection.get("target_id")) is not int or projection["target_id"] != -3
            or identity.get("role") != "button" or identity.get("section") != "Native browser"
            or identity.get("label") != label or projection.get("target_label") != label
            or not isinstance(words, list) or len(words) != 2 or words[0] != "click"
            or not isinstance(words[1], str)
            or words[1].strip().casefold() not in {"-3", label.casefold(), "button:" + label.casefold()}
            or effect != expected or projection.get("driver_effect") != effect
            or projection.get("dispatched") is not True):
        raise EvidenceError("infobar proof differs from admitted click or effect")
    if proof["press_acknowledged"]:
        if basis != "ax_infobar_disappearance_readback" or type(count) is not int or count != 1:
            raise EvidenceError("infobar acknowledgement lacks exact delivery evidence")
    elif basis != "unknown" or count is not None or effect != "unverifiable":
        raise EvidenceError("unacknowledged infobar press cannot confirm delivery")


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
                "ax_fullscreen_state_readback",
                "ax_infobar_disappearance_readback",
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
    identity = projection.get("target_identity")
    fullscreen = identity.get("native_window_control") if isinstance(identity, dict) else None
    # The admitted reserved target carries semantic intent even if a producer
    # omits its optional projection or relabels the delivery basis. No-send and
    # interrupted unknown-dispatch receipts do not claim an observed effect.
    fullscreen_target = op.target == "-2" or fullscreen is not None
    if basis == "ax_fullscreen_state_readback" or (
        fullscreen_target and (dispatched is True or effect in {"confirmed", "partial"})
    ):
        _validate_fullscreen_execution(projection.get("native_readback"), binding, effect, op, projection, basis, count)
    infobar = identity.get("native_infobar_control") if isinstance(identity, dict) else None
    native_proof = projection.get("native_readback")
    infobar_intent = op.target == "-3" or infobar is not None
    infobar_proof = isinstance(native_proof, dict) and native_proof.get("predicate") == "native_infobar_disappearance"
    nested_delivery = projection.get("native_delivery")
    nested_infobar = isinstance(nested_delivery, dict) and nested_delivery.get("delivery_basis") == "ax_infobar_disappearance_readback"
    if infobar_intent or infobar_proof or nested_infobar or basis == "ax_infobar_disappearance_readback":
        _infobar_delivery_agreement(projection, dispatched=dispatched, effect=effect, basis=basis, count=count)
        _infobar_provenance_agreement([record, projection], binding["pid"], binding["window_id"])
        if "execution_receipt" in projection:
            raise EvidenceError("nested infobar execution envelope unsupported")
    if basis == "ax_infobar_disappearance_readback" or infobar_proof or (
        infobar_intent and (dispatched is True or effect in {"confirmed", "partial"} or native_proof is not None)
    ):
        _validate_infobar_execution(projection.get("native_readback"), binding, effect, op, projection, basis, count)
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
