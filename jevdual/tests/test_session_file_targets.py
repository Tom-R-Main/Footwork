"""Real operator commands over a simulated Finder with renumbering filename fields.

Filesystem mutations below model the app at its AX boundary; production target
resolution and native producers remain real. No live application is controlled.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

cd = pytest.importorskip("cua_driver")

from jevdual import ax, cli, finder_targets
from jevdual.app_oracles import check_finder, create_fixture
from jevdual.posture import ExecutionPolicy

from tests.fixtures.native_world import World


class FinderWorld(World):
    def __init__(self, manifest):
        super().__init__(apps=[("Finder", 77, True)])
        self.manifest = manifest
        self.current_path = Path(manifest["root"]) / manifest["paths"]["source"]
        self.cell_value = None
        self.editor_value = None
        self.rename_open = False
        self.file_menu_open = False
        self.rename_enabled = True
        self.selected = None
        self.occupy_destination = False
        self.extra_window = None
        self.inputs = []
        self.fields = {}
        self.retain_editor_after_commit = False
        self.rename_committed = False
        self.dismiss_editor_on_reacquire = True
        self.null_focused_window_after_commit = False

    async def list_windows(self, inp):
        windows = [
            SimpleNamespace(
                window_id=self.window_id,
                title="inbox",
                bounds=SimpleNamespace(width=500, height=400),
            )
        ]
        if self.extra_window is not None:
            # Same title and larger than the owned window: the previous title/
            # area discovery picked this unrelated window before checking AXURL.
            windows.insert(
                0,
                SimpleNamespace(
                    window_id=self.window_id + 1,
                    title="inbox",
                    bounds=SimpleNamespace(width=800, height=600),
                ),
            )
        return SimpleNamespace(windows=windows if inp.pid == 77 else [])

    def window_element(self, pid, wid):
        assert pid == 77
        if wid == self.window_id:
            return "window"
        assert wid == self.window_id + 1 and self.extra_window is not None
        return "other_window"

    async def get_window_state(self, inp):
        assert (inp.pid, inp.window_id) == (77, self.window_id)
        self.n += 1
        sid = f"s{self.n:08x}"
        self.fields = {"asset": 60 + self.n % 2, "keep": 61 - self.n % 2}
        return {
            "snapshot_id": sid,
            "pid": 77,
            "window_id": self.window_id,
            "app_name": "Finder",
            "window_title": "inbox",
            "elements_complete": False,
            "tree_markdown": "",
            "elements": [
                {
                    "element_index": self.fields[name],
                    "element_token": f"{sid}:{self.fields[name]}",
                    "role": "AXTextField",
                    "label": "textbox",
                    "value": value,
                    "enabled": True,
                    "frame": {"x": x, "y": 20, "w": 100, "h": 20},
                }
                for name, value, x in (
                    ("asset", self.cell_value or self.current_path.name, 10),
                    ("keep", "keep.bin", 200),
                )
            ],
        }

    def attributes(self, element):
        if element == "application":
            return {
                "AXRole": "AXApplication",
                "AXTitle": "Finder",
                "AXFocusedUIElement": "editor" if self.rename_open else "asset",
                "AXFocusedWindow": (
                    None
                    if self.null_focused_window_after_commit and self.rename_committed and self.rename_open
                    else "window"
                ),
                "AXMainWindow": "window",
                "AXMenuBar": "menubar",
            }
        if element == "window":
            return {"AXRole": "AXWindow", "AXChildren": ["outline"]}
        if element == "other_window":
            return {
                "AXRole": "AXWindow",
                "AXChildren": ["asset" if self.extra_window == "duplicate" else "decoy"],
            }
        if element == "outline":
            return {
                "AXRole": "AXOutline",
                "AXChildren": ["asset_row", "keep_row", "decoy_row"],
                "AXSelectedRows": [self.selected] if self.selected is not None else [],
            }
        if element.endswith("_row"):
            return {
                "AXRole": "AXRow",
                "AXChildren": [element.removesuffix("_row")],
                "AXSelected": self.selected == element,
                "AXParent": "outline",
            }
        if element == "editor":
            return {
                "AXRole": "AXTextField",
                "AXValue": self.editor_value,
                "AXFocused": self.rename_open,
                "AXWindow": None,  # Actual Finder transient editor is parented under the application.
                "AXParent": "application",
                "AXChildren": [],
            }
        menus = {
            "menubar": {"AXRole": "AXMenuBar", "AXChildren": ["file_menu"]},
            "file_menu": {"AXRole": "AXMenuBarItem", "AXTitle": "File", "AXChildren": ["file_items"]},
            "file_items": {"AXRole": "AXMenu", "AXChildren": ["rename_menu"]},
            "rename_menu": {
                "AXRole": "AXMenuItem",
                "AXTitle": "Rename",
                "AXChildren": [],
                "AXEnabled": self.file_menu_open and self.rename_enabled and self.selected == "asset_row",
            },
        }
        if element in menus:
            return menus[element]
        path = {
            "asset": self.current_path,
            "keep": self.current_path.parent / "keep.bin",
            "decoy": Path(self.manifest["root"]) / "decoy/asset.png",
        }[element]
        attributes = {
            "AXRole": "AXTextField",
            "AXValue": self.cell_value if element == "asset" and self.cell_value is not None else path.name,
            "AXURL": path.as_uri(),
            "AXChildren": [],
            "AXParent": element + "_row",
            "AXWindow": "window",
        }
        if element == "asset" and self.retain_editor_after_commit and self.rename_open:
            del attributes["AXURL"]
        return attributes

    def attr(self, element, name):
        return self.attributes(element).get(name)

    def read_attribute(self, element, name, _):
        attributes = self.attributes(element)
        return (0, attributes[name]) if name in attributes else (-25205, None)

    def settable(self, element, name, _):
        return 0, (
            (element in {"asset", "editor"} and name == "AXValue")
            or (element == "editor" and name == "AXFocused")
            or (element == "asset_row" and name == "AXSelected")
            or (element == "window" and name == "AXMain")
        )

    def set_attribute(self, element, name, value):
        if (element, name) == ("editor", "AXFocused"):
            assert value is False and self.rename_open
            self.inputs.append(("AXFocused", "editor", False))
            self.rename_open = False
            self.editor_value = None
            return 0
        if (element, name) == ("window", "AXMain"):
            return 0
        if (element, name) == ("asset_row", "AXSelected"):
            assert value is True
            self.selected = element
            self.inputs.append(("AXSelected", "asset_row"))
            return 0
        assert name == "AXValue" and element in {"asset", "editor"}, "input reached the sibling field"
        self.inputs.append((name, element, str(value)))
        if element == "asset":
            # Observed Finder behavior: the ordinary cell accepts cached UI text
            # without entering the real rename editor or changing the disk name.
            self.cell_value = str(value)
        else:
            assert self.rename_open and self.selected == "asset_row"
            self.editor_value = str(value)
            if self.occupy_destination:
                self.current_path.with_name(self.editor_value).write_bytes(b"externally occupied")
        return 0

    def perform_action(self, element, name):
        if (element, name) == ("window", "AXRaise"):
            return 0
        if (element, name) == ("asset", "AXConfirm"):
            self.inputs.append(("AXConfirm", "asset"))
            return 0
        if (element, name) == ("file_menu", "AXPress"):
            self.inputs.append(("AXPress", "File"))
            self.file_menu_open = True
            return 0
        assert (element, name) == ("rename_menu", "AXPress")
        self.inputs.append(("AXPress", "File > Rename"))
        # Observed Finder behavior: leaf acknowledgement alone does not validate
        # menu state or enter editing. Opening File validates Rename first.
        if not self.file_menu_open or not self.rename_enabled:
            return 0
        assert self.selected == "asset_row", "Rename menu acted on the wrong row"
        self.rename_open = True
        self.editor_value = self.current_path.name
        return 0

    async def call_tool(self, name, args_json):
        arguments = json.loads(args_json)
        self.tool_calls.append((name, arguments))
        if name == "bring_to_front":
            assert arguments["pid"] == 77 and arguments["window_id"] == self.window_id
            assert arguments["session"]
            if (
                self.retain_editor_after_commit
                and self.rename_committed
                and self.rename_open
                and self.dismiss_editor_on_reacquire
            ):
                self.rename_open = False
                self.editor_value = None
            return SimpleNamespace(
                action=None, text="", is_error=False, error_code=None, structured_json=None
            )
        assert name == "hotkey"
        assert arguments["pid"] == 77 and arguments["window_id"] == self.window_id
        assert arguments["keys"] == ["Return"] and arguments["delivery_mode"] == "foreground"
        assert arguments["session"]
        self.inputs.append(("hotkey", "Return"))
        if self.rename_open and self.selected == "asset_row" and self.editor_value:
            destination = self.current_path.with_name(self.editor_value)
            self.current_path.rename(destination)  # External app at the actual commit boundary.
            self.current_path = destination
            self.rename_committed = True
            self.cell_value = None
            if not self.retain_editor_after_commit:
                self.editor_value = None
                self.rename_open = False
        # Match the live SDK's missing delivery count. Qualified AX acknowledgements
        # and the independent inode/path check must carry the execution evidence.
        return SimpleNamespace(action=None, text="", is_error=False, error_code=None, structured_json=None)

    def install(self, monkeypatch):
        monkeypatch.setattr(cd.CuaDriver, "create", staticmethod(self.create))
        monkeypatch.setattr(ExecutionPolicy, "locked", lambda _: False)
        activity = SimpleNamespace(
            idle_seconds=lambda: 60.0,
            frontmost_pid=lambda: 77,
            activate=lambda pid: pid == 77,
            watch=lambda: SimpleNamespace(fronts=[77], stop=lambda: [77]),
        )
        monkeypatch.setattr(ExecutionPolicy, "_activity", lambda _: activity)
        monkeypatch.setattr("jevdual.native.accessibility_status", lambda: "granted")
        monkeypatch.setattr("jevdual.keys.load_keys", dict)
        monkeypatch.setattr(ax, "window_element", self.window_element)
        monkeypatch.setattr(ax, "_attr", self.attr)
        monkeypatch.setattr(
            ax,
            "frame_of",
            lambda element: ax.Frame(
                {"asset": 10, "editor": 15, "keep": 200, "decoy": 350}[element],
                20,
                90 if element == "editor" else 100,
                20,
            ),
        )

        def get_window(element_id, pointer):
            assert element_id == self.window_id
            pointer._obj.value = self.window_id
            return 0

        monkeypatch.setattr(ax, "_hi", lambda: get_window)
        monkeypatch.setitem(
            sys.modules,
            "objc",
            SimpleNamespace(pyobjc_id=lambda el: self.window_id if el == "window" else id(el)),
        )
        monkeypatch.setattr(finder_targets, "_element_identity", id)
        monkeypatch.setattr(finder_targets, "file_url_path", lambda value: str(value).removeprefix("file://"))
        monkeypatch.setitem(
            sys.modules,
            "ApplicationServices",
            SimpleNamespace(
                AXUIElementCreateApplication=lambda pid: "application",
                AXUIElementSetAttributeValue=self.set_attribute,
                AXUIElementPerformAction=self.perform_action,
                AXUIElementIsAttributeSettable=self.settable,
                AXUIElementCopyActionNames=lambda element, _: (
                    0,
                    ["AXConfirm"] if element == "asset" else [],
                ),
                AXUIElementCopyAttributeNames=lambda element, _: (0, list(self.attributes(element))),
                AXUIElementCopyAttributeValue=self.read_attribute,
            ),
        )
        monkeypatch.setattr(
            "jevdual.session_operations.native_identity",
            lambda pid, window_id: {"boot": "test-boot", "pid": pid, "start": "1.0", "window_id": window_id},
        )


@pytest.fixture
def finder_cli(tmp_path, monkeypatch, capsys):
    manifest = create_fixture(tmp_path / "owned")
    world = FinderWorld(manifest)
    world.install(monkeypatch)
    session = tmp_path / "session"

    def run(*argv):
        extra = ["--settle", "0"] if argv[0] == "do" else []
        code = cli.main([*argv, "--session", str(session), *extra])
        output = capsys.readouterr()
        return code, output.out, output.err

    run.session = session
    run.authority = tmp_path / "authority.sqlite"
    run.manifest_path = Path(manifest["root"]) / "fixture.json"
    run.selector = "file:" + str(world.current_path)
    return world, run


def start(run, *, expected=0):
    code, out, err = run(
        "start",
        "Rename owned asset",
        "--app",
        "Finder",
        "--authority",
        str(run.authority),
        "--finder-manifest",
        str(run.manifest_path),
        "--mode",
        "foreground_permitted",
    )
    assert code == expected, (out, err)
    return out, err


def test_file_selector_renames_owned_asset_when_old_id_now_names_sibling(finder_cli):
    world, run = finder_cli
    start(run)
    original_id = world.fields["asset"]
    code, out, err = run("look")
    assert code == 0, (out, err)
    assert world.fields["keep"] == original_id  # The observed live defect, with identical labels.
    code, out, err = run("grant", "type", run.selector, "renamed.png")
    assert code == 0, (out, err)
    code, out, err = run("do", "type", run.selector, "renamed.png", "--no-judge", "--token", "rename-once")
    assert code == 0, (out, err)
    assert check_finder(world.manifest, "inbox/renamed.png").ok
    assert world.inputs == [
        ("AXSelected", "asset_row"),
        ("AXPress", "File"),
        ("AXPress", "File > Rename"),
        ("AXValue", "editor", "renamed.png"),
        ("hotkey", "Return"),
    ]
    state = json.loads((run.session / "session.json").read_text())
    assert state["finder_scope"]["binding"]["inode"] == world.current_path.stat().st_ino
    code, out, err = run("status")
    assert code == 0, (out, err)
    status = json.loads(out)
    assert len(status["operations"]) == 1
    assert status["operations"][0]["disposition"] == "applied"
    assert status["domain_unresolved"] == []
    # Replay the public command with the old pathname after the actual rename.
    code, out, err = run("do", "type", run.selector, "renamed.png", "--no-judge", "--token", "rename-once")
    assert code == 0, (out, err)
    assert len(world.inputs) == 5


def test_file_selector_refuses_same_basename_in_wrong_directory(finder_cli):
    world, run = finder_cli
    start(run)
    decoy = "file:" + str(Path(world.manifest["root"]) / "decoy/asset.png")
    code, _, _ = run("do", "type", decoy, "renamed.png", "--no-judge", "--token", "wrong-directory")
    assert code != 0
    assert world.inputs == []
    assert check_finder(world.manifest, "inbox/asset.png").ok


def test_file_selector_does_not_follow_same_path_to_replacement_inode(finder_cli):
    world, run = finder_cli
    start(run)
    code, out, err = run("grant", "type", run.selector, "renamed.png")
    assert code == 0, (out, err)
    source = world.current_path
    original_bytes = source.read_bytes()
    source.rename(source.with_name("retained.png"))  # Simulated external replacement after grant.
    source.write_bytes(original_bytes)
    code, _, _ = run("do", "type", run.selector, "renamed.png", "--no-judge", "--token", "replacement")
    assert code != 0
    assert world.inputs == []
    assert source.read_bytes() == original_bytes


def test_start_chooses_exact_owned_file_over_larger_same_title_window(finder_cli):
    world, run = finder_cli
    world.extra_window = "decoy"
    start(run)
    state = json.loads((run.session / "session.json").read_text())
    assert state["window_id"] == world.window_id
    assert state["native_binding"]["window_id"] == world.window_id
    code, out, err = run("grant", "type", run.selector, "renamed.png")
    assert code == 0, (out, err)
    assert world.inputs == []


def test_start_refuses_duplicate_windows_showing_exact_owned_file(finder_cli):
    world, run = finder_cli
    world.extra_window = "duplicate"
    _, err = start(run, expected=2)
    assert "exactly one complete window" in err
    assert not (run.session / "session.json").exists()
    assert world.inputs == []


def test_simulated_ordinary_cell_acknowledgements_do_not_commit_a_rename(finder_cli):
    from ApplicationServices import AXUIElementPerformAction

    world, _ = finder_cli
    before = world.current_path.read_bytes()
    ax.set_value_ack("asset", "renamed.png")
    assert AXUIElementPerformAction("asset", "AXConfirm") == 0
    assert ax.value("asset") == "renamed.png"  # Cached UI readback would falsely suggest success.
    assert world.current_path.read_bytes() == before
    assert not world.current_path.with_name("renamed.png").exists()
    assert check_finder(world.manifest, "inbox/asset.png").ok


def test_destination_appearing_after_editor_input_stops_before_return_and_blocks_retry(finder_cli):
    world, run = finder_cli
    start(run)
    code, out, err = run("grant", "type", run.selector, "renamed.png")
    assert code == 0, (out, err)
    world.occupy_destination = True
    run("do", "type", run.selector, "renamed.png", "--no-judge", "--token", "raced-name")
    assert world.inputs == [
        ("AXSelected", "asset_row"),
        ("AXPress", "File"),
        ("AXPress", "File > Rename"),
        ("AXValue", "editor", "renamed.png"),
    ]
    destination = world.current_path.with_name("renamed.png")
    assert destination.read_bytes() == b"externally occupied"
    assert world.current_path.is_file()
    code, out, err = run("status")
    assert code == 0, (out, err)
    status = json.loads(out)
    assert status["operations"][0]["disposition"] == "unknown"
    assert len(status["domain_unresolved"]) == 1
    code, _, _ = run("do", "type", run.selector, "renamed.png", "--no-judge", "--token", "retry-name")
    assert code != 0
    assert len(world.inputs) == 4
    assert destination.read_bytes() == b"externally occupied"


def test_disabled_rename_stops_after_menu_open_and_retains_unknown_barrier(finder_cli):
    world, run = finder_cli
    start(run)
    code, out, err = run("grant", "type", run.selector, "renamed.png")
    assert code == 0, (out, err)
    world.rename_enabled = False
    run("do", "type", run.selector, "renamed.png", "--no-judge", "--token", "disabled-rename")
    assert world.inputs == [("AXSelected", "asset_row"), ("AXPress", "File")]
    assert not world.rename_open
    assert check_finder(world.manifest, "inbox/asset.png").ok
    code, out, err = run("status")
    assert code == 0, (out, err)
    status = json.loads(out)
    assert status["operations"][0]["disposition"] == "unknown"
    assert len(status["domain_unresolved"]) == 1
    code, _, _ = run("do", "type", run.selector, "renamed.png", "--no-judge", "--token", "disabled-retry")
    assert code != 0
    assert world.inputs == [("AXSelected", "asset_row"), ("AXPress", "File")]


def test_simulated_rename_leaf_ack_without_file_menu_does_not_enter_editing(finder_cli):
    world, _ = finder_cli
    ax.select_finder_row_ack("asset")
    ax.press_menu(77, ["File", "Rename"])
    assert not world.file_menu_open
    assert not world.rename_open
    assert ax.value("asset") == "asset.png"
    assert check_finder(world.manifest, "inbox/asset.png").ok
