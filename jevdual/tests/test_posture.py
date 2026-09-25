"""The execution posture and the promises the native bridge makes under it (2026-09-25).

Each test names the promise it backs; ``docs/plans/legible-harness.md`` lists them as the conformance
rows for running alongside a person. These run against a fake Driver and a fake AX store; the same
promises are measured on real apps by ``tests/live/test_coexistence.py`` (Q15).
"""

from __future__ import annotations

import asyncio
import json
import sys
from types import SimpleNamespace

import pytest
from jevdual.authorize import action_for
from jevdual.native import AMBIGUITY, NativeBridge, NativeBridgeError, menu_from_snapshot
from jevdual.posture import ExecutionPolicy


class Activity:
    """Idle seconds, a scripted sequence of front pids (the last repeats), the fronts a foreground step
    would sample while it runs, and the activations the bridge asked for."""

    def __init__(self, idle: float = 60.0, fronts: tuple[int, ...] = (77,), during: tuple[int, ...] = ()):
        self.idle = idle
        self.fronts = list(fronts)
        self.during = list(during)
        self.activated: list[int] = []

    def idle_seconds(self) -> float:
        return self.idle

    def frontmost_pid(self) -> int:
        return self.fronts.pop(0) if len(self.fronts) > 1 else self.fronts[0]

    def activate(self, pid: int) -> bool:
        self.activated.append(pid)
        return True

    def watch(self):
        during = self.during

        class W:
            fronts = list(during)

            def stop(self):
                return list(during)

        return W()


def _ok(effect: str = "CONFIRMED", route: str = "ACCESSIBILITY", mode: str = "BACKGROUND"):
    return SimpleNamespace(
        action=SimpleNamespace(
            effect=SimpleNamespace(name=effect),
            route=SimpleNamespace(name=route),
            evidence=None,
            summary="done",
            delivery=SimpleNamespace(mode=SimpleNamespace(name=mode)),
        ),
        text="",
        is_error=False,
        error_code=None,
    )


def _refused(text: str):
    return SimpleNamespace(action=None, text=text, is_error=True, error_code=None)


AMBIG = _refused(f"Background input refused ({AMBIGUITY}): pid 1 owns 1 other eligible top-level window(s)")


def doc_snapshot(value: str, *, snap: str = "s00000001", label: str = "text area", extra: list | None = None):
    elements = [
        {"element_index": 0, "role": "AXWindow", "label": "doc.txt", "element_token": f"{snap}:0"},
        {
            "element_index": 1,
            "role": "AXTextArea",
            "label": label,
            "value": value,
            "element_token": f"{snap}:1",
            "frame": {"x": 10.0, "y": 40.0, "w": 600.0, "h": 400.0},
            "actions": ["AXShowMenu"],
        },
        {
            "element_index": 2,
            "role": "AXTextField",
            "label": "Search",
            "value": "",
            "element_token": f"{snap}:2",
            "frame": {"x": 10.0, "y": 5.0, "w": 200.0, "h": 20.0},
        },
        {
            "element_index": 3,
            "role": "AXScrollArea",
            "label": "Document",
            "element_token": f"{snap}:3",
            "frame": {"x": 10.0, "y": 40.0, "w": 600.0, "h": 400.0},
        },
        {
            "element_index": 4,
            "role": "AXButton",
            "label": "Bold",
            "element_token": f"{snap}:4",
            "actions": ["AXPress"],
            "frame": {"x": 300.0, "y": 5.0, "w": 20.0, "h": 20.0},
        },
        *(extra or []),
    ]
    return {
        "snapshot_id": snap,
        "pid": 1,
        "window_id": 2,
        "app_name": "TextEdit",
        "window_title": "doc.txt",
        "elements_complete": True,
        "tree_markdown": "",
        "elements": elements,
    }


class FakeDriver:
    """Serves snapshots in order (the last one repeats) and records every call; ``replies`` maps a tool
    name to a list of results served in order."""

    def __init__(self, *snapshots, replies: dict[str, list] | None = None):
        self.snapshots = list(snapshots)
        self.replies = {k: list(v) for k, v in (replies or {}).items()}
        self.calls: list[tuple[str, object]] = []

    async def get_window_state(self, inp):
        self.calls.append(("get_window_state", None))
        return self.snapshots.pop(0) if len(self.snapshots) > 1 else self.snapshots[0]

    def _reply(self, name):
        q = self.replies.get(name)
        if q:
            r = q.pop(0) if len(q) > 1 else q[0]
            if isinstance(r, BaseException):
                raise r
            return r
        return _ok()

    async def click(self, inp):
        self.calls.append(("click", inp))
        return self._reply("click")

    async def call_tool(self, name, args_json):
        self.calls.append((name, json.loads(args_json)))
        return self._reply(name)

    async def invoke_menu(self, inp):
        self.calls.append(("invoke_menu", inp))
        return self._reply("invoke_menu")

    def names(self) -> list[str]:
        return [n for n, _ in self.calls if n != "get_window_state"]


class FakeAX:
    """An AX text store: ``resolve`` finds the one element, ``insert_at_end`` edits the exact string. An
    optional ``interfere`` callback edits the store between the read and the insertion (another actor)."""

    AXError = __import__("jevdual.ax", fromlist=["AXError"]).AXError
    Frame = __import__("jevdual.ax", fromlist=["Frame"]).Frame

    def __init__(self, text: str, *, interfere=None, corrupt=None):
        self.text = text
        self.interfere = interfere
        self.corrupt = corrupt
        self.inserts: list[str] = []

    focused = 2
    menu_error: str | None = None
    pressed: list = []

    def focused_window_id(self, pid):
        return self.focused

    def press_menu(self, pid, path):
        if self.menu_error:
            raise self.AXError(self.menu_error, "no such item")
        self.pressed = [*self.pressed, list(path)]

    def resolve(self, pid, window_id, role, frame):
        assert (pid, window_id, role) == (1, 2, "AXTextArea")
        return "el"

    def value(self, el):
        return self.text

    def insert_at_end(self, el, text, *, expect=None):
        if self.interfere is not None:
            self.text = self.interfere(self.text)
        before = self.text
        if expect is not None and before != expect:
            raise self.AXError("precondition_changed", "changed")
        self.inserts.append(text)
        self.text = before + text
        if self.corrupt is not None:
            self.text = self.corrupt(self.text)
        return before, self.text


@pytest.fixture(autouse=True)
def sdk_stub(monkeypatch):
    stub = SimpleNamespace(
        GetWindowStateInput=lambda **kw: kw,
        ClickInput=lambda **kw: kw,
        ClickPosition=SimpleNamespace(ELEMENT=lambda element_token: ("element", element_token)),
        InputDeliveryMode=SimpleNamespace(BACKGROUND="background", FOREGROUND="foreground"),
        ActionTarget=SimpleNamespace(WINDOW=lambda pid, window_id: ("window", pid, window_id)),
        InvokeMenuInput=lambda **kw: kw,
    )
    monkeypatch.setitem(sys.modules, "cua_driver", stub)


def run(coro):
    return asyncio.run(coro)


def bridge_for(
    driver, mode="background_only", *, idle=60.0, fronts=(77,), during=(), ax=None, live_check=False
):
    policy = ExecutionPolicy(mode, activity=Activity(idle, fronts, during))
    return NativeBridge(driver, 1, 2, policy=policy, ax=ax, live_check=live_check)


# ---- the policy ---------------------------------------------------------------------------------


def test_policy_matrix():
    """Promise: each mode permits exactly its deliveries; foreground yields to recent human input."""
    idle = Activity(60.0)
    for mode, allowed in (
        ("background_only", {"background"}),
        ("foreground_permitted", {"background", "foreground"}),
        ("exclusive_desktop", {"background", "foreground", "desktop"}),
    ):
        p = ExecutionPolicy(mode, activity=idle)
        for d in ("background", "foreground", "desktop"):
            r = p.permits(d)
            assert (r is None) == (d in allowed), (mode, d)
            if r is not None:
                assert r.code == ("requires_desktop" if d == "desktop" else "requires_foreground")
    busy = ExecutionPolicy("foreground_permitted", activity=Activity(0.4))
    r = busy.permits("foreground")
    assert r is not None and r.code == "human_active"
    assert ExecutionPolicy("exclusive_desktop", activity=Activity(0.0)).permits("foreground") is None
    with pytest.raises(ValueError):
        ExecutionPolicy("whenever")


# ---- foreground only when the posture allows it ---------------------------------------------------


def test_background_only_never_fronts_hotkey_or_menu():
    """Promise: in background_only nothing is sent for a step that needs the foreground; the result is a
    typed refusal with dispatched=False."""
    d = FakeDriver(doc_snapshot("hello"))
    b = bridge_for(d)
    nm = run(b.observe())
    eff = run(b.hotkey(nm, ["cmd", "s"]))
    assert (eff.effect, eff.error_code, eff.dispatched, eff.delivery) == (
        "refused",
        "requires_foreground",
        False,
        "foreground",
    )
    nm = run(b.observe())
    eff = run(b.menu(nm, ["File", "Save"]))
    assert eff.error_code == "requires_foreground" and not eff.dispatched
    assert d.names() == []  # no hotkey, no bring_to_front, no invoke_menu


def test_ambiguity_is_not_silently_escalated():
    """Promise: a background key the Driver refuses for same-process ambiguity becomes requires_foreground
    in background_only; only the refused background attempt reached the Driver."""
    d = FakeDriver(doc_snapshot("hello"), replies={"press_key": [AMBIG]})
    b = bridge_for(d)
    nm = run(b.observe())
    eff = run(b.key(nm, "s", ["cmd"]))
    assert eff.error_code == "requires_foreground" and not eff.dispatched
    assert any(AMBIGUITY in e for e in eff.evidence)
    assert [(n, a["delivery_mode"]) for n, a in d.calls if n == "press_key"] == [("press_key", "background")]


def test_foreground_permitted_escalates_only_when_idle():
    """Promise: in foreground_permitted the ambiguity escalates to foreground when the person is idle, and
    yields (human_active, nothing sent) when they gave input recently."""
    d = FakeDriver(
        doc_snapshot("hello"), replies={"press_key": [AMBIG, _ok("UNVERIFIABLE", mode="FOREGROUND")]}
    )
    b = bridge_for(d, "foreground_permitted", idle=30.0, fronts=(77, 77))
    nm = run(b.observe())
    eff = run(b.key(nm, "s", ["cmd"]))
    modes = [a["delivery_mode"] for n, a in d.calls if n == "press_key"]
    assert modes == ["background", "foreground"]
    assert eff.dispatched and eff.delivery == "foreground" and eff.foreground["restored"] is True
    assert eff.driver_delivery == "foreground"

    d = FakeDriver(doc_snapshot("hello"), replies={"press_key": [AMBIG]})
    b = bridge_for(d, "foreground_permitted", idle=0.2)
    nm = run(b.observe())
    eff = run(b.key(nm, "s", ["cmd"]))
    assert eff.error_code == "human_active" and not eff.dispatched
    assert [a["delivery_mode"] for n, a in d.calls if n == "press_key"] == ["background"]


def test_foreground_receipt_reports_front_app_not_restored():
    """Promise: a foreground step records the front app before and after; a change is reported, never
    hidden and never fought (the bridge does not re-activate anything)."""
    d = FakeDriver(doc_snapshot("hello"))
    b = bridge_for(d, "foreground_permitted", fronts=(77, 88))
    nm = run(b.observe())
    eff = run(b.hotkey(nm, ["cmd", "s"]))
    assert eff.foreground["front_before"] == 77 and eff.foreground["front_after"] == 88
    assert eff.foreground["restored"] is False and "front app changed" in eff.summary
    assert d.names() == ["hotkey"]


# ---- target identity through compound steps -------------------------------------------------------


def test_enter_is_one_driver_call_carrying_the_element():
    """Promise: focus-then-Return cannot come apart; the element token and the key travel in one call and
    there is no separate, unchecked focusing click."""
    d = FakeDriver(doc_snapshot("hello"))
    b = bridge_for(d)
    nm = run(b.observe())
    eff = run(b.act(nm, "enter", 2))
    assert d.names() == ["press_key"]
    args = d.calls[-1][1]
    assert args["element_token"] == nm.tokens[2] and args["key"] == "return"
    assert args["delivery_mode"] == "background" and args["window_id"] == 2
    assert eff.delivery == "background"


def test_scroll_is_aimed_at_the_element_and_falls_back_through_the_posture():
    """Promise: a scroll names its element (no bare screen point with no target); when the Driver will not
    aim a wheel there, Page Down goes to that element by the key route, under the same posture."""
    d = FakeDriver(doc_snapshot("hello"))
    b = bridge_for(d)
    nm = run(b.observe())
    run(b.act(nm, "scroll", 3))
    name, args = d.calls[-1]
    assert (
        name == "scroll" and args["element_token"] == nm.tokens[3] and args["delivery_mode"] == "background"
    )
    assert "x" not in args and "y" not in args

    d = FakeDriver(doc_snapshot("hello"), replies={"scroll": [_refused("no frame")], "press_key": [AMBIG]})
    b = bridge_for(d)
    nm = run(b.observe())
    eff = run(b.act(nm, "scroll", 3))
    assert d.names() == ["scroll", "press_key"]
    assert d.calls[-1][1]["key"] == "pagedown" and d.calls[-1][1]["element_token"] == nm.tokens[3]
    assert eff.error_code == "requires_foreground" and not eff.dispatched


def test_hover_is_desktop_scoped():
    """Promise: an action that moves the real pointer declares itself desktop-scoped and runs only in
    exclusive_desktop."""
    extra = [
        {
            "element_index": 5,
            "role": "AXLink",
            "label": "Help",
            "element_token": "s00000001:5",
            "frame": {"x": 5.0, "y": 5.0, "w": 10.0, "h": 10.0},
        }
    ]
    d = FakeDriver(doc_snapshot("hello", extra=extra))
    b = bridge_for(d, "foreground_permitted")
    nm = run(b.observe())
    object.__setattr__(nm.menu.candidate(5), "operations", ("click", "hover"))
    eff = run(b.act(nm, "hover", 5))
    assert eff.error_code == "requires_desktop" and not eff.dispatched and d.names() == []
    b = bridge_for(d, "exclusive_desktop")
    nm = run(b.observe())
    object.__setattr__(nm.menu.candidate(5), "operations", ("click", "hover"))
    eff = run(b.act(nm, "hover", 5))
    assert d.calls[-1][0] == "move_cursor" and d.calls[-1][1]["scope"] == "desktop"
    assert eff.delivery == "desktop"


# ---- no data rebuilt from a preview ---------------------------------------------------------------

LONG = "A" * 1000
CODE = "def f():\n\tif x:\n\t\treturn  1\n"
TRAIL = "a\n\tb  \n\n  "


@pytest.mark.parametrize("original", [LONG, CODE, TRAIL, "", "ends with newline\n", "emoji 🧪 twice 🧪"])
def test_append_preserves_existing_content_exactly(original):
    """Promise: append keeps the old text byte for byte (long, indented, trailing whitespace, astral
    characters) and adds exactly one separator and the new text; it never writes the whole field."""
    shown = original.rstrip()  # the Driver strips trailing whitespace (measured 2026-09-25)
    d = FakeDriver(doc_snapshot(shown))
    ax = FakeAX(original)
    b = bridge_for(d, ax=ax)
    nm = run(b.observe())
    eff = run(b.act(nm, "append", 1, "Second line."))
    sep = "" if original == "" or original.endswith("\n") else "\n"
    assert ax.text == original + sep + "Second line."
    assert eff.effect == "confirmed" and eff.delivery == "background"
    assert "set_value" not in d.names()  # no whole-field write
    assert (
        nm.menu.candidate(1).value is None or len(nm.menu.candidate(1).value) <= 480
    )  # the preview stays small


def test_append_refuses_when_the_field_changed_since_the_decision():
    """Promise: a field another actor edited since the observation is refused before any write."""
    d = FakeDriver(doc_snapshot("one\ntwo"))
    ax = FakeAX("one\ntwo\nthree (typed by the person)")
    b = bridge_for(d, ax=ax)
    nm = run(b.observe())
    eff = run(b.act(nm, "append", 1, "four"))
    assert eff.error_code == "precondition_changed" and not eff.dispatched
    assert ax.text == "one\ntwo\nthree (typed by the person)" and ax.inserts == []


def test_append_refuses_an_edit_between_read_and_insert():
    """Promise: an edit that lands between the exact read and the insertion is refused, nothing written."""
    d = FakeDriver(doc_snapshot("one"))
    ax = FakeAX("one", interfere=lambda t: t + " (person)")
    b = bridge_for(d, ax=ax)
    nm = run(b.observe())
    eff = run(b.act(nm, "append", 1, "two"))
    assert eff.error_code == "precondition_changed" and not eff.dispatched and ax.inserts == []


def test_append_reports_partial_when_readback_differs():
    """Promise: an append whose readback is not old + inserted is `partial` with the first difference,
    never `confirmed`."""
    d = FakeDriver(doc_snapshot("one"))
    ax = FakeAX("one", corrupt=lambda t: t.replace("one", "on"))
    b = bridge_for(d, ax=ax)
    nm = run(b.observe())
    eff = run(b.act(nm, "append", 1, "two"))
    assert eff.effect == "partial" and eff.error_code == "content_mismatch"
    assert "first difference at 2" in eff.evidence[0]


def test_values_are_whole_and_the_preview_is_not_execution_data():
    """Promise: the menu's preview is capped for the model; the whole value is kept apart for execution and
    the replacement check reads the whole value."""
    body = "\n".join(f"line {i}" for i in range(200))
    nm = menu_from_snapshot(doc_snapshot(body))
    assert len(nm.menu.candidate(1).value) <= 480 and nm.values[1] == body
    act = action_for("type", nm, "s2", target=nm.menu.candidate(1), text=body[:600])
    assert act.current == body and act.replaces_content


# ---- live identity and preconditions --------------------------------------------------------------


def test_live_check_acts_on_the_fresh_token_when_unchanged():
    """Promise: with live_check the target is found again in a fresh observation and the fresh token is
    used."""
    d = FakeDriver(doc_snapshot("hello"), doc_snapshot("hello", snap="s00000002"))
    b = bridge_for(d, live_check=True)
    nm = run(b.observe())
    run(b.act(nm, "click", 4))
    assert d.calls[-1][0] == "click" and d.calls[-1][1]["position"] == ("element", "s00000002:4")


def test_live_check_refuses_a_changed_target_or_state():
    """Promise: a target that is gone, relabelled or holding different text is refused before dispatch."""
    moved = doc_snapshot("hello", snap="s00000002")
    moved["elements"][4]["label"] = "Italic"
    d = FakeDriver(doc_snapshot("hello"), moved)
    b = bridge_for(d, live_check=True)
    nm = run(b.observe())
    with pytest.raises(NativeBridgeError) as e:
        run(b.act(nm, "click", 4))
    assert e.value.reason == "target_changed" and "click" not in d.names()

    d = FakeDriver(doc_snapshot("hello"), doc_snapshot("hello, edited", snap="s00000002"))
    b = bridge_for(d, live_check=True, ax=FakeAX("hello, edited"))
    nm = run(b.observe())
    with pytest.raises(NativeBridgeError) as e:
        run(b.act(nm, "type", 1, "replacement"))
    assert e.value.reason == "precondition_changed" and "set_value" not in d.names()


def test_live_check_append_compares_against_the_decided_text():
    """Promise: with live_check the append's precondition is the text the decision saw, not the fresh one."""
    d = FakeDriver(doc_snapshot("hello"), doc_snapshot("hello", snap="s00000002"))
    ax = FakeAX("hello")
    b = bridge_for(d, live_check=True, ax=ax)
    nm = run(b.observe())
    eff = run(b.act(nm, "append", 1, "world"))
    assert eff.effect == "confirmed" and ax.text == "hello\nworld"


def test_menu_hands_the_front_back_but_never_fights_the_person():
    """Promise: a menu step fronts the bound window, presses through AX (which never re-activates the
    app) and gives the front back, by exact pid, to the person's latest choice during the step; when
    their choice already holds the front, nothing is activated."""
    ax = FakeAX("")
    d = FakeDriver(doc_snapshot("hello"))
    b = bridge_for(d, "foreground_permitted", fronts=(77, 1, 1, 77), during=(77, 1), ax=ax)
    nm = run(b.observe())
    eff = run(b.menu(nm, ["Edit", "Select All"]))
    assert ax.pressed == [["Edit", "Select All"]] and eff.dispatched and eff.route == "accessibility"
    assert eff.foreground["handed_back"] == 77 and b.policy.activity.activated == [77]
    assert "invoke_menu" not in d.names() and [a for n, a in d.calls if n == "bring_to_front"] == [
        {"pid": 1, "window_id": 2}
    ]
    # something re-took the front after the person moved to 99: it goes to 99, not back to 77
    d = FakeDriver(doc_snapshot("hello"))
    b = bridge_for(d, "foreground_permitted", fronts=(77, 1, 1, 99), during=(77, 1, 99, 1), ax=FakeAX(""))
    nm = run(b.observe())
    eff = run(b.menu(nm, ["Edit", "Select All"]))
    assert eff.foreground["handed_back"] == 99 and b.policy.activity.activated == [99]
    # the person's choice already holds the front: nothing is activated
    d = FakeDriver(doc_snapshot("hello"))
    b = bridge_for(d, "foreground_permitted", fronts=(77, 1, 99, 99), during=(77, 1, 99), ax=FakeAX(""))
    nm = run(b.observe())
    eff = run(b.menu(nm, ["Edit", "Select All"]))
    assert "handed_back" not in eff.foreground and b.policy.activity.activated == []


def test_menu_is_not_pressed_unless_the_bound_window_is_key():
    """Promise: a menu press goes to the app's key window, so when the bound window does not become key
    (another window of the app is key, or the person took the front) nothing is pressed."""
    ax = FakeAX("")
    ax.focused = 999  # another window of the same app is key
    d = FakeDriver(doc_snapshot("hello"))
    b = bridge_for(d, "foreground_permitted", fronts=(77, 1), ax=ax)
    nm = run(b.observe())
    eff = run(b.menu(nm, ["Edit", "Select All"]))
    assert eff.error_code == "not_key" and not eff.dispatched and ax.pressed == []


def test_invoke_menu_only_in_exclusive_desktop():
    """Promise: the Driver's invoke_menu (which re-activates the app) is used only when the desktop is
    reserved, and only for a path AX cannot resolve."""
    for mode, used in (("foreground_permitted", False), ("exclusive_desktop", True)):
        ax = FakeAX("")
        ax.menu_error = "menu_missing"
        d = FakeDriver(doc_snapshot("hello"))
        b = bridge_for(d, mode, fronts=(77, 1, 1, 1), ax=ax)
        nm = run(b.observe())
        eff = run(b.menu(nm, ["Format", "Make Plain Text"]))
        assert ("invoke_menu" in d.names()) is used
        if not used:
            assert eff.error_code == "menu_missing" and not eff.dispatched


def test_navigate_never_types_into_the_current_tab_when_new_tab_is_not_sent(monkeypatch):
    """Promise: when Command-T is not sent (background_only), the URL is not typed into the current tab
    (the person's), and the reason reaches the operator."""
    from jevdual.native import navigate_in_window, new_window

    extra = [
        {
            "element_index": 6,
            "role": "AXTextField",
            "label": "Address and search bar",
            "value": "https://example.com/the-persons-tab",
            "element_token": "s00000001:6",
        }
    ]
    d = FakeDriver(doc_snapshot("", extra=extra))
    b = bridge_for(d)
    with pytest.raises(RuntimeError) as e:
        run(navigate_in_window(b, "https://example.org"))
    assert "requires_foreground" in str(e.value)
    assert d.names() == []  # no set_value into the address bar, no Return

    async def windows(driver, app):
        return 1, [(2, "doc.txt", 1.0)]

    monkeypatch.setattr("jevdual.native.app_windows", windows)
    with pytest.raises(RuntimeError) as e:
        run(new_window(b, "TextEdit"))
    assert "requires_foreground" in str(e.value)


def test_empty_text_view_reads_as_empty_only_when_it_says_so(monkeypatch):
    """Promise: a text view with no AXValue is empty only when AXNumberOfCharacters is 0; otherwise the
    append refuses rather than guess."""
    from jevdual import ax

    attrs = {"AXValue": None, "AXNumberOfCharacters": 0}
    monkeypatch.setattr(ax, "_attr", lambda el, name: attrs.get(name))
    assert ax.value("el") == ""
    attrs["AXNumberOfCharacters"] = 12
    with pytest.raises(ax.AXError):
        ax.value("el")


def _web_snapshot(value: str, snap: str = "s00000001"):
    s = doc_snapshot("", snap=snap)
    s["elements"].append(
        {
            "element_index": 7,
            "role": "AXTextField",
            "label": "Customer name",
            "value": value,
            "element_token": f"{snap}:7",
            "in_web_content": True,
        }
    )
    return s


def test_web_fields_are_typed_by_insertion_and_read_back():
    """Promise: a field inside web content is never 'typed' by an AXValue write WebKit ignores: the text
    is inserted with type_text on that element and `confirmed` only when the field reads back the text."""
    d = FakeDriver(_web_snapshot(""), _web_snapshot("Ada", snap="s00000002"))
    b = bridge_for(d)
    nm = run(b.observe())
    assert 7 in nm.web
    eff = run(b.act(nm, "type", 7, "Ada"))
    assert d.names() == ["type_text"] and d.calls[-2][1]["element_token"] == nm.tokens[7]
    assert eff.effect == "confirmed" and "set_value" not in d.names()

    d = FakeDriver(_web_snapshot(""), _web_snapshot("", snap="s00000002"))
    b = bridge_for(d)
    nm = run(b.observe())
    assert run(b.act(nm, "type", 7, "Ada")).effect == "suspected_noop"


def test_web_field_with_text_is_selected_first_under_the_posture():
    """Promise: replacing web-field text selects it on that element first (Command-A with the token), and
    when the process has other windows that selection is not sent and nothing is typed."""
    d = FakeDriver(
        _web_snapshot("old"), _web_snapshot("old", snap="s00000002"), _web_snapshot("Ada", snap="s00000003")
    )
    b = bridge_for(d)
    nm = run(b.observe())
    eff = run(b.act(nm, "type", 7, "Ada"))
    keys = [a for n, a in d.calls if n == "press_key"]
    assert (
        keys[0]["key"] == "a" and keys[0]["modifiers"] == ["cmd"] and keys[0]["element_token"] == nm.tokens[7]
    )
    assert d.names() == ["press_key", "type_text"] and eff.effect == "confirmed"

    d = FakeDriver(_web_snapshot("old"), replies={"press_key": [AMBIG]})
    b = bridge_for(d)
    nm = run(b.observe())
    eff = run(b.act(nm, "type", 7, "Ada"))
    assert eff.error_code == "requires_foreground" and not eff.dispatched and "type_text" not in d.names()
