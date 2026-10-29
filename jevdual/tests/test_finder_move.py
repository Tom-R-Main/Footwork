"""Native move producer over simulated UI boundaries; no live apps are controlled."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from jevdual import ax, finder_targets
from jevdual.app_oracles import check_finder, create_fixture
from jevdual.native import NativeBridge, NativeBridgeError, menu_from_snapshot


class MoveAX:
    AXError = ax.AXError
    Frame = ax.Frame

    def __init__(self, manifest, binding):
        self.manifest, self.binding = manifest, binding
        self.folder = Path(binding.path).parent
        self.selected = False
        self.clipboard = []
        self.clipboard_count = 10
        self.inputs = []
        self.enabled = True
        self.stale_clipboard = False
        self.wrong_marker = False
        self.fail_move = False
        self.current_window_id = 12
        self.focuses = []

    def raise_window(self, pid, wid):
        assert (pid, wid) == (77, 88)
        self.current_window_id = wid
        self.folder = Path(self.manifest["root"]) / "organized"

    def focused_window_id(self, pid):
        return self.current_window_id

    def title_bar_point(self, pid, wid):
        return None

    def select_finder_row_ack(self, element):
        assert element == "source"
        self.selected = True
        self.inputs.append("select")

    def finder_selection_state(self, element):
        return {
            "exact_row_only": self.selected,
            "exact_row_selected": self.selected,
            "selected_row_count": int(self.selected),
        }

    def finder_window_context(self, pid):
        wid = self.current_window_id
        return {
            "main_window_id": wid,
            "focused_window_id": wid,
            "focused_role": "AXOutline",
        }

    def pasteboard_change_count(self):
        return self.clipboard_count

    def pasteboard_file_paths(self):
        return list(self.clipboard)

    def press_menu(self, pid, path):
        assert pid == 77
        self.inputs.append(" > ".join(path))
        if path == ["Edit", "Copy"]:
            self.clipboard = [self.binding.path]
            if not self.stale_clipboard:
                self.clipboard_count += 1
        elif path == ["Edit", "Move Item Here"] and not self.fail_move:
            Path(self.binding.path).rename(Path(self.manifest["root"]) / "organized/renamed.png")

    def menu_item_enabled(self, pid, path):
        return self.enabled

    def menu_paths(self, pid):
        return ["Edit > Copy"]

    async def call_tool(self, name, arguments):
        args = json.loads(arguments)
        assert name == "bring_to_front"
        assert (args["pid"], args["window_id"]) == (77, 88)
        assert args["session"].endswith("-destination")
        self.focuses.append(88)
        return SimpleNamespace(action=None, text="", is_error=False, error_code=None, structured_json=None)


class Bridge(NativeBridge):
    async def _front_and_key(self):
        pass

    async def _foreground(self, operation, target, label, call, *, why):
        return self._effect(operation, target, label, await call(), "foreground")

    async def observe(self, **_):
        self.last = self.nm
        return self.nm


@pytest.fixture
def move_world(tmp_path, monkeypatch):
    manifest = create_fixture(tmp_path / "owned")
    source = Path(manifest["root"]) / "inbox/asset.png"
    binding = finder_targets.bind(manifest, "file:" + str(source))
    renamed = source.with_name("renamed.png")
    source.rename(renamed)  # Fixture setup models a previously settled rename.
    binding = finder_targets.rebind(binding, manifest, "file:" + str(renamed))
    fake = MoveAX(manifest, binding)
    snap = {
        "snapshot_id": "s1",
        "pid": 77,
        "window_id": 12,
        "app_name": "Finder",
        "window_title": "inbox",
        "elements_complete": True,
        "elements": [
            {
                "element_index": 1,
                "element_token": "s1:1",
                "role": "AXTextField",
                "label": "textbox",
                "value": "renamed.png",
                "frame": {"x": 0, "y": 0, "w": 100, "h": 20},
            }
        ],
    }
    nm = menu_from_snapshot(snap)
    target = finder_targets.FinderTarget(
        "source", 77, 12, binding, renamed.as_uri(), "AXTextField", "renamed.png", ax.Frame(0, 0, 100, 20)
    )
    monkeypatch.setattr(finder_targets, "resolve", lambda *a, **k: target)

    def marker(*args, **kwargs):
        if fake.wrong_marker or args[1] != 88:
            raise ax.AXError("file_destination_unverified", "wrong current folder")
        return {
            "pid": 77,
            "window_id": 88,
            "window_title": "organized",
            **finder_targets.move_destination(manifest, args[3]),
            "ax_url": (Path(manifest["root"]) / "organized/keep.bin").as_uri(),
            "basis": "fresh_ax_destination_marker_and_owned_directory",
        }

    monkeypatch.setattr(finder_targets, "resolve_marker", marker, raising=False)
    policy = SimpleNamespace(
        _activity=lambda: SimpleNamespace(frontmost_pid=lambda: 77, activate=lambda pid: True)
    )
    bridge = Bridge(
        SimpleNamespace(call_tool=fake.call_tool),
        77,
        12,
        ax=fake,
        policy=policy,
        finder_scope={
            "manifest": manifest,
            "binding": binding.to_record(),
            "destination_window": marker(77, 88, manifest, str(Path(manifest["root"]) / "organized")),
        },
    )
    bridge.nm, bridge.last = nm, nm
    return bridge, fake, manifest, binding


def act(world):
    bridge, _, manifest, binding = world
    return asyncio.run(
        bridge.act_file(bridge.nm, "move", "file:" + binding.path, str(Path(manifest["root"]) / "organized"))
    )


def test_native_move_uses_ui_and_qualifies_same_inode_with_unchanged_bytes(move_world):
    effect = act(move_world)
    assert effect.effect == "confirmed", effect.summary
    assert effect.delivery_basis == "ax_finder_move_readback"
    assert check_finder(move_world[2], "organized/renamed.png").ok
    assert effect.native_readback["before"]["binding"]["inode"] == effect.native_readback["after"]["inode"]
    assert move_world[1].inputs[-1] == "Edit > Move Item Here"
    assert effect.delivered_count == 5
    assert effect.native_readback["transfer_route"] == "prebound_destination_window"
    assert effect.native_readback["navigation"]["window_id"] == 88
    assert effect.native_readback["destination_window_binding"]["window_id"] == 88
    assert move_world[1].focuses == [88]
    assert not any("Go" in event for event in move_world[1].inputs)


@pytest.mark.parametrize("changed", [None, {"pid": 77, "window_id": 12}, {"pid": 99, "window_id": 88}])
def test_missing_or_wrong_prebound_destination_refuses_before_input(move_world, changed):
    move_world[0].finder_scope["destination_window"] = changed
    with pytest.raises(NativeBridgeError):
        act(move_world)
    assert move_world[1].inputs == [] and move_world[1].focuses == []


def test_stale_clipboard_never_navigates_or_moves(move_world):
    move_world[1].stale_clipboard = True
    effect = act(move_world)
    assert effect.effect == "unverifiable"
    assert "Go > Go to Folder" not in move_world[1].inputs
    assert Path(move_world[3].path).exists()


def test_wrong_destination_marker_never_presses_move(move_world):
    move_world[1].wrong_marker = True
    with pytest.raises(ax.AXError):
        act(move_world)
    assert move_world[1].inputs == []


def test_changed_registered_destination_refuses_before_input(move_world):
    move_world[0].finder_scope["destination_window"]["inode"] += 1
    with pytest.raises(NativeBridgeError, match="identity changed"):
        act(move_world)
    assert move_world[1].inputs == [] and move_world[1].focuses == []


def test_destination_changed_after_copy_never_focuses_or_moves(move_world, monkeypatch):
    fake = move_world[1]
    original = fake.press_menu

    def changed(pid, path):
        original(pid, path)
        if path == ["Edit", "Copy"]:
            fake.wrong_marker = True

    monkeypatch.setattr(fake, "press_menu", changed)
    effect = act(move_world)
    assert effect.effect == "unverifiable" and effect.delivered_count == 3
    assert fake.focuses == [] and "Edit > Move Item Here" not in fake.inputs


def test_destination_changed_during_move_menu_never_presses_leaf(move_world, monkeypatch):
    fake = move_world[1]
    original = fake.menu_item_enabled

    def changed(pid, path):
        if path == ["Edit", "Move Item Here"]:
            fake.wrong_marker = True
        return original(pid, path)

    monkeypatch.setattr(fake, "menu_item_enabled", changed)
    effect = act(move_world)
    assert effect.effect == "unverifiable" and effect.delivered_count == 4
    assert "Edit > Move Item Here" not in fake.inputs


def test_destination_focus_failure_never_presses_move(move_world, monkeypatch):
    fake = move_world[1]
    monkeypatch.setattr(fake, "raise_window", lambda pid, wid: None)
    effect = act(move_world)
    assert effect.effect == "unverifiable" and effect.delivered_count == 3
    assert "Edit > Move Item Here" not in fake.inputs


def test_occupied_destination_refuses_before_input(move_world):
    destination = Path(move_world[2]["root"]) / "organized/renamed.png"
    destination.write_bytes(b"external")
    with pytest.raises(NativeBridgeError, match="destination must be empty"):
        act(move_world)
    assert move_world[1].inputs == []
    assert destination.read_bytes() == b"external"


def test_acknowledged_move_without_path_transition_remains_unknown(move_world):
    move_world[1].fail_move = True
    effect = act(move_world)
    assert effect.effect == "unverifiable"
    assert effect.delivered_count > 0
    assert Path(move_world[3].path).exists()


def test_clipboard_change_while_opening_move_menu_prevents_leaf_press(move_world, monkeypatch):
    fake = move_world[1]
    original = fake.menu_item_enabled

    def changed(pid, path):
        if path == ["Edit", "Move Item Here"]:
            fake.clipboard_count += 1
            fake.clipboard = ["/unowned/private-file"]
        return original(pid, path)

    monkeypatch.setattr(fake, "menu_item_enabled", changed)
    effect = act(move_world)
    assert effect.effect == "unverifiable"
    assert "Edit > Move Item Here" not in fake.inputs
    assert "/unowned/private-file" not in str(effect.native_readback)


@pytest.mark.parametrize("directory", ["inbox", "decoy", "organized/..", "organized/../organized"])
def test_destination_helper_refuses_wrong_or_aliased_folder(move_world, directory):
    manifest = move_world[2]
    with pytest.raises(ax.AXError):
        finder_targets.move_destination(manifest, manifest["root"] + "/" + directory)


def test_destination_helper_binds_inode_and_protected_marker(move_world):
    manifest = move_world[2]
    directory = Path(manifest["root"]) / "organized"
    record = finder_targets.move_destination(manifest, str(directory))
    assert record["inode"] == directory.stat().st_ino
    assert record["sentinel_identity"]["sha256"] == manifest["protected"]["organized/keep.bin"]
    (directory / "keep.bin").write_bytes(b"changed")
    with pytest.raises(ax.AXError):
        finder_targets.move_destination(manifest, str(directory))
