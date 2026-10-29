"""Public commands over a simulated Finder's real low-level AX boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from jevdual.app_oracles import check_finder

from tests import test_session_file_targets as file_tests


class MoveCLIWorld(file_tests.FinderWorld):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.destination_window_id = self.window_id + 88
        self.active_window = "window"
        self.edit_open = False
        self.copy_generation = 0
        self.copy_paths = []
        self.stale_copy = False
        self.bad_destination = False
        self.lose_destination_on_copy = False
        self.duplicate_destination = False

    async def list_windows(self, inp):
        result = await super().list_windows(inp)
        if inp.pid == 77:
            result.windows.append(
                SimpleNamespace(
                    window_id=self.destination_window_id,
                    title="organized",
                    bounds=SimpleNamespace(width=500, height=400),
                )
            )
            if self.duplicate_destination:
                result.windows.append(
                    SimpleNamespace(
                        window_id=self.destination_window_id + 1,
                        title="organized",
                        bounds=SimpleNamespace(width=500, height=400),
                    )
                )
        return result

    def window_element(self, pid, wid):
        if wid == self.destination_window_id or (
            self.duplicate_destination and wid == self.destination_window_id + 1
        ):
            assert pid == 77
            return "destination_window"
        return super().window_element(pid, wid)

    def attributes(self, element):
        if element == "application":
            return {
                **super().attributes(element),
                "AXMainWindow": self.active_window,
                "AXFocusedWindow": self.active_window,
            }
        if element == "window":
            return {"AXRole": "AXWindow", "AXTitle": "inbox", "AXChildren": ["outline"]}
        if element == "destination_window":
            return {"AXRole": "AXWindow", "AXTitle": "organized", "AXChildren": ["destination_keep"]}
        if element == "destination_keep":
            directory = "decoy" if self.bad_destination else "organized"
            return {
                "AXRole": "AXTextField",
                "AXValue": "keep.bin",
                "AXURL": (Path(self.manifest["root"]) / directory / "keep.bin").as_uri(),
                "AXChildren": [],
                "AXWindow": "destination_window",
                "AXParent": "destination_window",
            }
        if element == "menubar":
            return {"AXRole": "AXMenuBar", "AXChildren": ["file_menu", "edit_menu"]}
        menus = {
            "edit_menu": {"AXRole": "AXMenuBarItem", "AXTitle": "Edit", "AXChildren": ["edit_items"]},
            "edit_items": {"AXRole": "AXMenu", "AXChildren": ["copy_item", "copy_path_item", "move_item"]},
            "copy_item": {
                "AXRole": "AXMenuItem",
                "AXTitle": f"Copy “{self.current_path.name}”",
                "AXEnabled": self.edit_open and self.selected == "asset_row",
                "AXChildren": [],
            },
            "copy_path_item": {
                "AXRole": "AXMenuItem",
                "AXTitle": f"Copy “{self.current_path.name}” as Pathname",
                "AXEnabled": True,
                "AXChildren": [],
            },
            "move_item": {
                "AXRole": "AXMenuItem",
                "AXTitle": "Move Item Here",
                "AXEnabled": self.edit_open and bool(self.copy_paths),
                "AXChildren": [],
            },
        }
        if element in menus:
            return menus[element]
        return super().attributes(element)

    def settable(self, element, name, _):
        if (element, name) == ("destination_window", "AXMain"):
            return 0, True
        return super().settable(element, name, _)

    def set_attribute(self, element, name, value):
        if element in {"window", "destination_window"} and name == "AXMain":
            self.active_window = element
            return 0
        return super().set_attribute(element, name, value)

    def perform_action(self, element, action):
        if element in {"window", "destination_window"} and action == "AXRaise":
            self.active_window = element
            return 0
        if element in {"edit_menu", "copy_item", "move_item"}:
            assert action == "AXPress"
            self.inputs.append(("AXPress", element))
            if element == "edit_menu":
                self.edit_open = True
            elif element == "copy_item":
                assert self.active_window == "window" and self.selected == "asset_row" and self.edit_open
                if not self.stale_copy:
                    self.copy_generation += 1
                self.copy_paths = [str(self.current_path)]
                self.bad_destination = self.lose_destination_on_copy
            elif element == "move_item":
                assert self.active_window == "destination_window"
                assert self.copy_paths == [str(self.current_path)]
                destination = Path(self.manifest["root"]) / "organized" / self.current_path.name
                self.current_path.rename(destination)  # Simulated Finder's UI boundary.
                self.current_path = destination
            return 0
        return super().perform_action(element, action)

    async def call_tool(self, name, arguments):
        args = json.loads(arguments)
        if name == "bring_to_front" and args["window_id"] == self.destination_window_id:
            assert args["pid"] == 77 and args["session"].endswith("-destination")
            self.active_window = "destination_window"
            self.tool_calls.append((name, args))
            return SimpleNamespace(
                action=None, text="", is_error=False, error_code=None, structured_json=None
            )
        return await super().call_tool(name, arguments)

    def install(self, monkeypatch):
        super().install(monkeypatch)

        def get_window(element_id, pointer):
            pointer._obj.value = element_id
            return 0

        ids = {"window": self.window_id, "destination_window": self.destination_window_id}
        monkeypatch.setattr(file_tests.ax, "_hi", lambda: get_window)
        monkeypatch.setitem(sys.modules, "objc", SimpleNamespace(pyobjc_id=lambda el: ids.get(el, id(el))))
        base_frame = file_tests.ax.frame_of
        monkeypatch.setattr(
            file_tests.ax,
            "frame_of",
            lambda el: file_tests.ax.Frame(200, 20, 100, 20) if el == "destination_keep" else base_frame(el),
        )

        class URL:
            def __init__(self, path):
                self._path = path

            def isFileURL(self):
                return True

            def host(self):
                return None

            def filePathURL(self):
                return self

            def path(self):
                return self._path

        board = SimpleNamespace(
            changeCount=lambda: self.copy_generation,
            readObjectsForClasses_options_=lambda classes, options: [URL(p) for p in self.copy_paths],
        )
        monkeypatch.setitem(
            sys.modules,
            "AppKit",
            SimpleNamespace(
                NSPasteboard=SimpleNamespace(generalPasteboard=lambda: board),
                NSPasteboardURLReadingFileURLsOnlyKey="files-only",
            ),
        )
        monkeypatch.setitem(sys.modules, "Foundation", SimpleNamespace(NSURL=URL))


@pytest.fixture
def move_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(file_tests, "FinderWorld", MoveCLIWorld)
    return file_tests.finder_cli.__wrapped__(tmp_path, monkeypatch, capsys)


def renamed(world, run):
    file_tests.start(run)
    code, out, err = run("do", "type", run.selector, "renamed.png", "--no-judge", "--token", "rename")
    assert code == 0, (out, err)
    assert check_finder(world.manifest, "inbox/renamed.png").ok


def test_public_owned_move_records_applied_receipt_and_replay_sends_nothing(move_cli):
    world, run = move_cli
    renamed(world, run)
    selector = "file:" + str(world.current_path)
    directory = str(Path(world.manifest["root"]) / "organized")
    code, out, err = run("do", "move", selector, directory, "--no-judge", "--token", "move-once")
    assert code == 0, (out, err)
    assert check_finder(world.manifest, "organized/renamed.png").ok, (out, err)
    code, out, err = run("status")
    assert code == 0, (out, err)
    status = json.loads(out)
    moved = next(row for row in status["operations"] if row["client_token"] == "move-once")
    assert moved["state"] == "final" and moved["disposition"] == "applied"
    before = list(world.inputs)
    code, out, err = run("do", "move", selector, directory, "--no-judge", "--token", "move-once")
    assert code == 0, (out, err)
    assert world.inputs == before


def test_public_move_stale_copy_blocks_navigation_and_retry(move_cli):
    world, run = move_cli
    renamed(world, run)
    world.stale_copy = True
    before = len(world.inputs)
    selector = "file:" + str(world.current_path)
    directory = str(Path(world.manifest["root"]) / "organized")
    run("do", "move", selector, directory, "--no-judge", "--token", "stale-move")
    assert ("AXPress", "copy_item") in world.inputs[before:]
    assert ("AXPress", "goto_item") not in world.inputs[before:]
    inputs = list(world.inputs)
    run("do", "move", selector, directory, "--no-judge", "--token", "new-unsafe-token")
    assert world.inputs == inputs


def test_public_move_rejects_destination_changed_after_copy_before_focus(move_cli):
    world, run = move_cli
    renamed(world, run)
    world.lose_destination_on_copy = True
    start_inputs = len(world.inputs)
    selector = "file:" + str(world.current_path)
    directory = str(Path(world.manifest["root"]) / "organized")
    run("do", "move", selector, directory, "--no-judge", "--token", "foreign-modal")
    assert ("AXPress", "copy_item") in world.inputs[start_inputs:]
    assert not any(event[:2] == ("AXValue", "folder_field") for event in world.inputs[start_inputs:])
    assert ("hotkey", "Go Return") not in world.inputs[start_inputs:]
    assert ("AXPress", "move_item") not in world.inputs[start_inputs:]


def test_public_move_missing_destination_binding_refuses_without_input(move_cli):
    world, run = move_cli
    renamed(world, run)
    state_path = run.session / "session.json"
    state = json.loads(state_path.read_text())
    del state["finder_scope"]["destination_window"]
    state_path.write_text(json.dumps(state))
    before = list(world.inputs)
    run(
        "do",
        "move",
        "file:" + str(world.current_path),
        str(Path(world.manifest["root"]) / "organized"),
        "--no-judge",
        "--token",
        "missing-destination",
    )
    assert world.inputs == before
    assert check_finder(world.manifest, "inbox/renamed.png").ok


def test_public_changed_destination_window_refuses_before_copy(move_cli):
    world, run = move_cli
    renamed(world, run)
    world.bad_destination = True
    before = list(world.inputs)
    run(
        "do",
        "move",
        "file:" + str(world.current_path),
        str(Path(world.manifest["root"]) / "organized"),
        "--no-judge",
        "--token",
        "changed-destination",
    )
    assert world.inputs == before
    assert check_finder(world.manifest, "inbox/renamed.png").ok


def test_public_duplicate_destination_windows_refuse_session_start(move_cli):
    world, run = move_cli
    world.duplicate_destination = True
    file_tests.start(run, expected=2)
    assert world.inputs == []
    assert not (run.session / "session.json").exists()
