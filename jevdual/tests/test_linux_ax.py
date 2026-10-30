"""Exact-text AT-SPI contract with adversarial bus/window boundaries; no live qualification."""

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from jevdual import linux_ax as ax


class FakeBus(ax._Bus):
    def __init__(self):
        self.identity = "original-bus"
        self.closed = 0
        self.writes = []
        self.fail_write = False
        self.short_read = False
        self.change_count = False
        self.text = "α🙂\tfirst  \n\n"
        self.state = (1 << 7) | (1 << 8) | (1 << 24)
        self.nodes = {
            "/registry": {"role": "desktop", "children": ["/app"]},
            "/app": {"role": "application", "children": ["/window"]},
            "/window": {"role": "frame", "children": ["/editor"],
                        "parent": "/app", "frame": (10, 20, 600, 400)},
            "/editor": {"role": "text", "children": [], "parent": "/window",
                        "frame": (20, 40, 580, 360)},
        }

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.closed += 1

    def call(self, ref, interface, method, signature="", body=()):
        if ref == ax._DBUS:
            if method == "GetNameOwner":
                return (":1.0" if body[0] == "org.a11y.atspi.Registry" else body[0],)
            if method == "GetConnectionUnixProcessID":
                return (42 if body[0] == ":1.1" else 99,)
        path = "/registry" if ref[1] == ax._ROOT[1] else ref[1]
        if path not in self.nodes:
            raise ax.AXError("accessibility_reply_unavailable", "object disappeared")
        node = self.nodes[path]
        if method == "Get":
            if body == (ax._ACCESSIBLE, "ChildCount"):
                return (("i", len(node["children"])),)
            if body == (ax._ACCESSIBLE, "Parent"):
                return (("(so)", (":1.1", node["parent"])),)
            if body == (ax._TEXT, "CharacterCount"):
                count = len(self.text)
                if self.change_count:
                    self.text += "!"
                return (("i", count),)
        if method == "GetChildren":
            return ([(":1.1", child) for child in node["children"]],)
        if method == "GetRoleName":
            return (node["role"],)
        if method == "GetExtents":
            return (node["frame"],)
        if method == "GetState":
            return ([self.state, 0],)
        if method == "GetInterfaces":
            return ([ax._TEXT, ax._EDITABLE, ax._COMPONENT, ax._ACCESSIBLE],)
        if method == "GetText":
            assert signature == "ii" and body == (0, len(self.text))
            return (self.text[:-1] if self.short_read else self.text,)
        if method == "InsertText":
            self.writes.append((method, signature, body))
            offset, text, length = body
            assert length == len(text.encode("utf-8"))
            self.text = self.text[:offset] + text + self.text[offset:]
            if self.fail_write:
                raise ax.AXError("accessibility_reply_unavailable", "lost response after accepted mutation")
            return (True,)
        if method == "SetTextContents":
            self.writes.append((method, signature, body))
            self.text = body[0]
            if self.fail_write:
                raise ax.AXError("accessibility_reply_unavailable", "lost response after accepted mutation")
            return (True,)
        raise AssertionError((ref, interface, method, signature, body))


@pytest.fixture
def world(monkeypatch):
    bus = FakeBus()
    monkeypatch.setattr(ax, "_Bus", lambda: bus)
    monkeypatch.setattr(ax, "_process_start", lambda pid: "start-1")
    monkeypatch.setattr(ax, "_x11_window", lambda pid, window: ax.WindowGeometry(ax.Frame(10, 20, 600, 400)))
    return bus


def element():
    return ax.resolve(42, 123, "text", ax.Frame(20, 40, 580, 360))


def test_exact_long_unicode_and_whitespace_read_append(world):
    world.text = ("α🙂e\u0301\t  \n" * 1000) + "\n  "
    original = world.text
    target = element()
    assert ax.value(target) == original
    before, after = ax.insert_at_end(target, "🧪\t  \n", expect=original)
    assert before == original and after == original + "🧪\t  \n"
    assert world.writes == [("InsertText", "isi", (len(original), "🧪\t  \n", 8))]
    assert world.closed == 3


def test_short_read_count_change_and_bound_refuse(world):
    target = element()
    world.short_read = True
    with pytest.raises(ax.AXError, match="incomplete"):
        ax.value(target)
    world.short_read = False
    world.text = "x" * 65537
    with pytest.raises(ax.AXError, match="exceeds"):
        ax.value(target)
    assert not world.writes


def test_mutation_requires_fresh_precondition(world):
    target = element()
    with pytest.raises(ax.AXError) as error:
        ax.insert_at_end(target, "append", expect="old")
    assert error.value.reason == "precondition_changed" and not world.writes


@pytest.mark.parametrize("change", ["process", "bus", "window", "parent", "role", "frame", "object", "owner"])
def test_identity_changes_never_retarget_or_write(world, monkeypatch, change):
    target = element()
    if change == "process":
        monkeypatch.setattr(ax, "_process_start", lambda pid: "start-2")
    elif change == "bus":
        world.identity = "replacement-bus"
    elif change == "window":
        monkeypatch.setattr(ax, "_x11_window", lambda pid, window: ax.WindowGeometry(ax.Frame(11, 20, 600, 400)))
    elif change == "parent":
        world.nodes["/editor"]["parent"] = "/other-window"
    elif change == "role":
        world.nodes["/editor"]["role"] = "password text"
    elif change == "frame":
        world.nodes["/editor"]["frame"] = (21, 40, 580, 360)
    elif change == "object":
        world.nodes["/editor2"] = world.nodes.pop("/editor")
        world.nodes["/window"]["children"] = ["/editor2"]
    else:
        target = replace(target, chain=(*target.chain[:-1], (":1.9", "/editor")))
    with pytest.raises(ax.AXError):
        ax.insert_at_end(target, "must-not-write")
    assert not world.writes


def test_ambiguous_window_and_element_are_refused(world):
    world.nodes["/window2"] = dict(world.nodes["/window"])
    world.nodes["/app"]["children"].append("/window2")
    with pytest.raises(ax.AXError) as error:
        element()
    assert error.value.reason == "window_ambiguous"
    world.nodes["/app"]["children"].remove("/window2")
    world.nodes["/editor2"] = dict(world.nodes["/editor"])
    world.nodes["/window"]["children"].append("/editor2")
    with pytest.raises(ax.AXError) as error:
        element()
    assert error.value.reason == "element_ambiguous"


def test_defunct_or_readonly_objects_never_receive_writes(world):
    target = element()
    world.state &= ~(1 << 7)
    assert not ax.can_insert(target)
    with pytest.raises(ax.AXError, match="writable"):
        ax.set_value_ack(target, "x")
    world.state |= 1 << 6
    with pytest.raises(ax.AXError, match="defunct"):
        ax.value(target)
    assert not world.writes


@pytest.mark.parametrize("operation", ["insert", "set"])
def test_lost_write_reply_is_not_retried_or_rerouted(world, operation):
    target = element()
    before = world.text
    world.fail_write = True
    with pytest.raises(ax.AXError) as error:
        if operation == "insert":
            ax.insert_at_end(target, "尾", expect=before)
        else:
            ax.set_value_ack(target, "尾")
    assert error.value.reason == "accessibility_reply_unavailable"
    assert len(world.writes) == 1
    assert world.text == (before + "尾" if operation == "insert" else "尾")
    assert world.closed == 2


def test_no_title_derived_document_path(world):
    assert ax.document_path(42, 123) is None


def test_explicit_x11_frame_extents_match_decorated_accessible(world, monkeypatch):
    client = ax.Frame(11, 38, 598, 377)
    geometry = ax._window_geometry(client, (1, 1, 18, 5))
    assert geometry.decorated == ax.Frame(10, 20, 600, 400)
    monkeypatch.setattr(ax, "_x11_window", lambda pid, window: geometry)
    target = element()
    assert target.window_geometry == geometry
    assert target.window_frame == geometry.decorated
    assert ax.value(target) == world.text
    monkeypatch.setattr(ax, "_x11_window", lambda pid, window: ax.WindowGeometry(client))
    with pytest.raises(ax.AXError, match="geometry changed"):
        ax.value(target)


def test_absent_frame_extents_do_not_enable_geometry_heuristic(world, monkeypatch):
    monkeypatch.setattr(ax, "_x11_window", lambda pid, window: ax.WindowGeometry(ax.Frame(11, 38, 598, 377)))
    with pytest.raises(ax.AXError, match="top-level"):
        element()


@pytest.mark.parametrize("extents", [(1, 2, 3), (1, 1, -1, 1), (1, 1, "18", 5), (1, 1, 65537, 5)])
def test_malformed_frame_extents_refused(extents):
    with pytest.raises(ax.AXError, match="malformed"):
        ax._window_geometry(ax.Frame(10, 20, 600, 400), extents)


def test_new_ambiguous_window_after_binding_refuses_input(world):
    target = element()
    world.nodes["/window2"] = dict(world.nodes["/window"])
    world.nodes["/app"]["children"].append("/window2")
    with pytest.raises(ax.AXError, match="top-level"):
        ax.insert_at_end(target, "x")
    assert not world.writes


def test_isolated_x11_query_limits_environment_and_keeps_identity(monkeypatch):
    captured = {}
    monkeypatch.setenv("DISPLAY", ":99")
    monkeypatch.setenv("HOME", "/example-home")
    monkeypatch.setenv("XAUTHORITY", "/example-auth")
    monkeypatch.setenv("DO_NOT_PASS_SECRET", "private")
    monkeypatch.setenv("LD_PRELOAD", "/must-not-load")

    def run(args, **kwargs):
        captured.update(args=args, **kwargs)
        return SimpleNamespace(returncode=0, stdout=json.dumps({"schema_version": 1,
                               "client": [320, 216, 640, 480], "frame_extents": [1, 1, 18, 5]}))

    monkeypatch.setattr(ax.subprocess, "run", run)
    geometry = ax._x11_window(42, 123)
    assert geometry.client == ax.Frame(320, 216, 640, 480)
    assert geometry.decorated == ax.Frame(319, 198, 642, 503)
    assert captured["args"][:2] == [sys.executable, "-I"]
    assert captured["args"][-2:] == ["42", "123"]
    assert Path(captured["args"][2]).name == "linux_x11.py"
    assert captured["timeout"] == 3 and captured["stdin"] == subprocess.DEVNULL
    assert captured["env"] == {"DISPLAY": ":99", "HOME": "/example-home", "XAUTHORITY": "/example-auth"}


def test_isolated_x11_timeout_is_typed(monkeypatch):
    def timeout(args, **kwargs):
        raise subprocess.TimeoutExpired(args, kwargs["timeout"])

    monkeypatch.setattr(ax.subprocess, "run", timeout)
    with pytest.raises(ax.AXError) as error:
        ax._x11_window(42, 123)
    assert error.value.reason == "x11_timeout"


@pytest.mark.parametrize("reply", ["not json", "x" * 4097, "null", '{}',
                                   '{"schema_version":true}',
                                   '{"schema_version":1,"client":[1,2,0,4],"frame_extents":null}',
                                   '{"schema_version":1,"client":[1,2,3,true],"frame_extents":null}',
                                   '{"schema_version":1,"client":[1,2,3,4],"frame_extents":"none"}'])
def test_isolated_x11_invalid_reply_refuses(monkeypatch, reply):
    monkeypatch.setattr(ax.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=reply))
    with pytest.raises(ax.AXError) as error:
        ax._x11_window(42, 123)
    assert error.value.reason == "geometry_unavailable"


def test_isolated_x11_failure_preserves_refusal_code(monkeypatch):
    monkeypatch.setattr(ax.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=1, stdout=json.dumps({"schema_version": 1,
                                        "error": {"code": "lost_identity", "message": "untrusted detail"}})))
    with pytest.raises(ax.AXError) as error:
        ax._x11_window(42, 123)
    assert error.value.reason == "lost_identity"
    assert "untrusted detail" not in str(error.value)


def test_x11_helper_runs_standalone_and_refuses_without_display(tmp_path):
    source = Path(ax.__file__).with_name("linux_x11.py")
    helper = tmp_path / "linux_x11.py"
    helper.write_bytes(source.read_bytes())
    result = subprocess.run([sys.executable, "-I", "-S", str(helper), "42", "123"], env={},
                            capture_output=True, text=True, timeout=3, check=False)
    assert result.returncode == 1
    assert json.loads(result.stdout)["error"]["code"] == "x11_unavailable"


def test_text_capabilities_require_interfaces_and_states(world):
    target = element()
    assert ax.text_capabilities(target) == {"readable": True, "writable": True, "multiline": None}
    world.state |= 1 << 17
    assert ax.text_capabilities(target)["multiline"] is True
    world.state |= 1 << 26
    assert ax.text_capabilities(target)["multiline"] is None
    world.state &= ~(1 << 17)
    assert ax.text_capabilities(target)["multiline"] is False
    world.state &= ~(1 << 7)
    assert ax.text_capabilities(target)["writable"] is False
