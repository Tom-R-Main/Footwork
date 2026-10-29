"""Producer evidence from native result and bounded Preview UI transitions."""

import asyncio
import dataclasses
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from jevdual.native import NativeBridge, effect_from_action_result, menu_from_snapshot


def test_direct_action_error_is_retained_without_fabricating_delivery():
    result = SimpleNamespace(effect="REFUSED", delivery=None, error=SimpleNamespace(code="stale_token"))
    effect = effect_from_action_result("click", 1, "asset", result)
    assert effect.error_code == "stale_token"
    assert effect.dispatched is False


def test_nested_error_does_not_invent_no_send_for_ambiguous_action():
    result = SimpleNamespace(
        effect="UNVERIFIABLE", delivery=None, error=SimpleNamespace(code="transport_lost")
    )
    effect = effect_from_action_result("click", 1, "asset", result)
    assert effect.error_code == "transport_lost"
    assert effect.dispatched is True
    assert effect.delivered_count is None


def state(edited, undo=()):
    return {
        "pid": 77,
        "window_id": 12,
        "document": "/owned/asset.png",
        "identity": {"device": 1, "inode": 2},
        "edited": edited,
        "undo": list(undo),
    }


def test_preview_rotation_requires_new_exact_undo_marker():
    from jevdual.native import preview_menu_readback

    proof = preview_menu_readback(["Tools", "Rotate Right"], state(False), state(True, ["Undo Rotate Right"]))
    assert proof and proof["predicate"] == "preview_rotate_right_ui_transition"
    assert (
        preview_menu_readback(
            ["Tools", "Rotate Right"], state(True, ["Undo Rotate Right"]), state(True, ["Undo Rotate Right"])
        )
        is None
    )
    assert (
        preview_menu_readback(["Tools", "Rotate Right"], state(False), state(True, ["Undo Rotate Left"]))
        is None
    )


@pytest.mark.parametrize(
    "change",
    [
        {"document": "/other/asset.png"},
        {"identity": {"device": 1, "inode": 3}},
        {"undo": []},
    ],
)
def test_preview_transition_refuses_wrong_or_incomplete_document(change):
    from jevdual.native import preview_menu_readback

    after = {**state(True, ["Undo Rotate Right"]), **change}
    assert preview_menu_readback(["Tools", "Rotate Right"], state(False), after) is None


def test_preview_save_requires_same_document_dirty_to_clean():
    from jevdual.native import preview_menu_readback

    assert (
        preview_menu_readback(["File", "Save"], state(True), state(False))["predicate"]
        == "preview_save_ui_transition"
    )
    assert preview_menu_readback(["File", "Save"], state(False), state(False)) is None
    assert preview_menu_readback(["File", "Save As"], state(True), state(False)) is None


def test_preview_save_file_transition_retains_atomic_replacement():
    from jevdual.native import preview_menu_readback

    before = {**state(None), "sha256": "a" * 64}
    after = {**state(None), "sha256": "b" * 64, "identity": {"device": 1, "inode": 3}}
    assert (
        preview_menu_readback(["File", "Save"], before, after)["predicate"] == "preview_save_file_transition"
    )
    assert preview_menu_readback(["File", "Save"], before, {**after, "sha256": "a" * 64}) is None
    assert preview_menu_readback(["File", "Save"], before, {**after, "document": "/other/asset.png"}) is None


@pytest.mark.parametrize(
    "new_undo, expected", [("Undo Rotate Right", "confirmed"), ("Undo Rotate Left", "unverifiable")]
)
def test_preview_menu_ack_requires_observed_contract(new_undo, expected):
    from jevdual.ax import AXError

    class PreviewAX:
        def __init__(self):
            self.pressed = False

        def preview_document_state(self, pid, window_id):
            return state(None, [new_undo] if self.pressed else [])

        def press_menu(self, pid, path):
            self.pressed = True

    PreviewAX.AXError = AXError

    class Bridge(NativeBridge):
        async def _front_and_key(self):
            pass

        async def _foreground(self, operation, target, label, call, *, why):
            return self._effect(operation, target, label, await call(), "foreground")

    snapshot = json.loads((Path(__file__).parent / "fixtures/native/calculator.json").read_text())
    nm = dataclasses.replace(menu_from_snapshot(snapshot), app_name="Preview")
    bridge = Bridge(None, nm.pid, nm.window_id, ax=PreviewAX())
    bridge.last = nm
    effect = asyncio.run(bridge.menu(nm, ["Tools", "Rotate Right"]))
    assert effect.effect == expected
    assert effect.delivered_count == 1
    assert effect.delivery_basis == (
        "ax_menu_effect_readback" if expected == "confirmed" else "ax_menu_press_ack"
    )
    assert bool(effect.native_readback) == (expected == "confirmed")


@pytest.mark.parametrize("predicate", ["preview_save_ui_transition", "preview_save_file_transition"])
def test_public_preview_binary_save_preserves_qualified_native_predicate(predicate):
    from jevdual.ax import AXError

    class BinaryPreviewAX:
        saved = False

        def preview_document_state(self, pid, window_id):
            if predicate == "preview_save_ui_transition":
                return state(not self.saved)
            return {**state(None), "sha256": ("b" if self.saved else "a") * 64}

        def press_menu(self, pid, path):
            assert path == ["File", "Save"]
            self.saved = True

        def text_area_values(self, pid, window_id):
            raise AssertionError("a qualified binary save must not enter the text save verifier")

    BinaryPreviewAX.AXError = AXError

    class Bridge(NativeBridge):
        async def _front_and_key(self):
            pass

        async def _foreground(self, operation, target, label, call, *, why):
            return self._effect(operation, target, label, await call(), "foreground")

    snapshot = json.loads((Path(__file__).parent / "fixtures/native/calculator.json").read_text())
    nm = dataclasses.replace(menu_from_snapshot(snapshot), app_name="Preview")
    bridge = Bridge(None, nm.pid, nm.window_id, ax=BinaryPreviewAX())
    bridge.last = nm
    effect = asyncio.run(bridge.menu(nm, ["File", "Save"]))
    assert effect.effect == "confirmed"
    assert effect.native_readback["predicate"] == predicate
    assert effect.delivery_basis == "ax_menu_effect_readback"
    assert effect.readback is None


def preview_execution(proof, *, words=None):
    from jevdual.operator_evidence import execution_record
    from jevdual.session_operations import native_resource

    binding = {"boot": "test", "pid": 77, "start": "test", "window_id": 12}
    now = time.time()
    op = SimpleNamespace(
        id="op_preview",
        task="session",
        request_digest="digest",
        resource=native_resource(binding),
        observation="obs",
        target=None,
        move="menu",
        created=now - 1,
        args={"words": words or ["menu", "Tools > Rotate Right"]},
    )
    return execution_record(
        op,
        binding=binding,
        started_at=now - 0.5,
        ended_at=now,
        producer_evidence={
            "name": "footwork.native",
            "version": 1,
            "delivery_basis": "ax_menu_effect_readback",
            "delivered_count": 1,
        },
        dispatched=True,
        effect="confirmed",
        phase="sent",
        projection={"app": "Preview", "native_readback": proof},
    )


def test_qualified_preview_receipt_accepts_own_window_and_predicate():
    from jevdual.native import preview_menu_readback

    proof = preview_menu_readback(["Tools", "Rotate Right"], state(None), state(None, ["Undo Rotate Right"]))
    assert preview_execution(proof)["effect"] == "confirmed"


@pytest.mark.parametrize("window_id", [99, True])
def test_qualified_preview_receipt_rejects_cross_window(window_id):
    from jevdual.native import preview_menu_readback
    from jevdual.operator_evidence import EvidenceError

    before, after = state(None), state(None, ["Undo Rotate Right"])
    before["window_id"] = after["window_id"] = window_id
    proof = preview_menu_readback(["Tools", "Rotate Right"], before, after)
    with pytest.raises(EvidenceError):
        preview_execution(proof)


def test_qualified_preview_receipt_rejects_cross_predicate():
    from jevdual.native import preview_menu_readback
    from jevdual.operator_evidence import EvidenceError

    proof = preview_menu_readback(["Tools", "Rotate Left"], state(None), state(None, ["Undo Rotate Left"]))
    with pytest.raises(EvidenceError):
        preview_execution(proof)


def test_qualified_preview_receipt_rejects_ack_only():
    from jevdual.operator_evidence import EvidenceError

    proof = {
        "schema_version": 1,
        "producer": "footwork.ax.preview",
        "predicate": "preview_rotate_right_ui_transition",
    }
    with pytest.raises(EvidenceError):
        preview_execution(proof)


def finder_execution(proof):
    from jevdual.operator_evidence import execution_record
    from jevdual.session_operations import native_resource

    binding = {"boot": "test", "pid": 77, "start": "test", "window_id": 12}
    now = time.time()
    op = SimpleNamespace(
        id="op_finder",
        task="session",
        request_digest="digest",
        resource=native_resource(binding),
        observation="obs",
        target="61",
        move="type",
        created=now - 1,
        args={
            "words": ["type", "file:/owned/inbox/asset.png", "renamed.png"],
            "finder_scope": {"binding": finder_proof()["before"]["binding"]},
        },
    )
    return execution_record(
        op,
        binding=binding,
        started_at=now - 0.5,
        ended_at=now,
        producer_evidence={
            "name": "footwork.native",
            "version": 1,
            "delivery_basis": "ax_finder_rename_readback",
            "delivered_count": 4,
        },
        dispatched=True,
        effect="confirmed",
        phase="sent",
        projection={"app": "Finder", "native_readback": proof},
    )


def finder_proof():
    old = {
        "manifest_sha256": "a" * 64,
        "root": "/owned",
        "root_device": 1,
        "root_inode": 10,
        "path": "/owned/inbox/asset.png",
        "device": 1,
        "inode": 20,
    }
    destination = "/owned/inbox/renamed.png"
    return {
        "schema_version": 1,
        "producer": "footwork.ax.finder",
        "predicate": "finder_rename_same_inode",
        "before": {"pid": 77, "window_id": 12, "binding": old},
        "after": {**old, "path": destination},
        "destination": destination,
        "acknowledgements": [
            "exact_row_selected",
            "file_menu_opened",
            "rename_menu_pressed",
            "editor_value_set",
        ],
        "rename_enabled": True,
        "editor": {"pid": 77, "window_id": 12, "role": "AXTextField", "before_value": "asset.png"},
        "commit": {"route": "sdk_foreground_return", "effect": "unverifiable", "delivered_count": None},
    }


def test_qualified_finder_receipt_accepts_ack_lower_bound_without_key_count():
    assert finder_execution(finder_proof())["producer"]["delivered_count"] == 4


@pytest.mark.parametrize("corruption", ["moved_parent", "refused_commit", "invalid_commit_count", "ack_only"])
def test_qualified_finder_receipt_rejects_contradictory_rename(corruption):
    from jevdual.operator_evidence import EvidenceError

    proof = finder_proof()
    if corruption == "moved_parent":
        proof["after"]["path"] = proof["destination"] = "/owned/organized/renamed.png"
    elif corruption == "refused_commit":
        proof["commit"]["effect"] = "refused"
    elif corruption == "invalid_commit_count":
        proof["commit"]["delivered_count"] = True
    else:
        proof.pop("after")
    with pytest.raises(EvidenceError):
        finder_execution(proof)
