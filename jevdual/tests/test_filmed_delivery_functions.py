"""The driver's two filmed delivery functions, executed (FP26).

The Rust tests give each function's receipt to a mock CDP; nothing there runs it. This takes the click
sequence and the filmed insert from the pinned driver source archive and runs them in Node on stand-in
elements, recording every event dispatched and every command run. It tests each function's own logic:
what it checks before it sends anything, and where it sends. It does not test Chrome: that an event
dispatched from an isolated world reaches a page's listeners, and that ``insertText`` acts on a focused
field from there, is ``scripts/probe_locate_world_headless.py`` (FP27).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = "libs/cua-driver/rust/crates/cua-driver-core/src/browser/tools.rs"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="needs Node to run the page functions")

RECT = [60, 330, 140, 44]
CENTRE = [130, 352]
POINT = [70.5, 340.25]  # on the control, away from its centre

HARNESS = r"""
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const fn = eval('(' + input.source + ')');
const out = input.cases.map((spec) => {
  const sent = [], commands = [];
  class Event { constructor(type, init) { this.type = type; Object.assign(this, init); } }
  // what a page listener can change while the sequence runs
  const page = { rect: spec.rect || [60, 330, 140, 44], hit: spec.hit || 'target', connected: spec.connected !== false,
                 cursor: ('cursor' in spec) ? spec.cursor : 'pointer', lock: spec.lock === true };
  const view = { PointerEvent: class extends Event {}, MouseEvent: class extends Event {},
                 screenX: 100, screenY: 50, getComputedStyle: () => ({ cursor: page.cursor }) };
  const doc = { defaultView: view, get pointerLockElement() { return page.lock ? {} : null; },
                execCommand: (...args) => { commands.push(args); return spec.accepts !== false; } };
  const make = (name, parent, root, extra) => {
    const el = Object.assign({
      name, parentElement: parent, ownerDocument: doc,
      get isConnected() { return page.connected; },
      getBoundingClientRect: () => {
        const [left, top, width, height] = page.rect;
        return { left, top, width, height, right: left + width, bottom: top + height };
      },
      getRootNode: () => root,
      contains: (other) => { for (let o = other; o; o = o.parentElement) if (o === el) return true; return false; },
      dispatchEvent: (event) => {
        sent.push({ to: name, type: event.type, at: [event.clientX, event.clientY],
                    screen: [event.screenX, event.screenY], kind: event.constructor === view.PointerEvent ? 'P' : 'M' });
        // a page listener on this event: it moves the control, covers it or removes it
        if (spec.on && spec.on.event === event.type) Object.assign(page, spec.on.then);
        return true;
      },
      // the press focuses the control when the case says it is focusable, and focus can move it too
      closest: () => spec.focus ? node : null,
      focus: () => { sent.push({ to: name, type: 'focus()' }); Object.assign(page, spec.focus.then || {}); },
    }, extra || {});
    return el;
  };
  // the node's root: the document, or a shadow root with its own hit test and active element
  const root = spec.shadow ? {} : doc;
  const node = make('target', null, root, spec.node);
  const child = make('icon', node, root);
  const second = make('label', node, root);
  const other = make('other', null, root);
  const hits = { target: node, descendant: child, second, other, none: null };
  root.elementFromPoint = () => hits[page.hit];
  if (spec.blind) delete root.elementFromPoint;
  root.activeElement = hits[spec.active || 'target'];
  const receipt = fn.apply(node, spec.args || []);
  return { receipt, sent, commands };
});
process.stdout.write(JSON.stringify(out));
"""


def _function(name: str) -> str:
    """One page function as JavaScript, from the pinned archive's tools.rs."""
    with tarfile.open(ROOT / "vendor/cua-driver/native-source.tar.gz") as archive:
        source = archive.extractfile(TOOLS).read().decode()
    literal = re.search(rf'const {name}: &str = "(.*?)";\n', source, re.DOTALL)
    assert literal, f"{name} is not in the pinned tools.rs"
    text = re.sub(r"\\\n\s*", "", literal.group(1))
    # besides the line continuation the literals escape only a double quote
    assert "\\\\" not in text and "\\n" not in text
    return text.replace('\\"', '"')


def _run(name: str, *cases: dict) -> list[dict]:
    done = subprocess.run(["node", "-e", HARNESS], input=json.dumps({"source": _function(name), "cases": list(cases)}),
                          capture_output=True, text=True, timeout=30, check=False)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


def _click(*cases: dict) -> list[dict]:
    return _run("DOM_EVENT_CLICK_SEQUENCE", *cases)


def _insert(*cases: dict) -> list[dict]:
    return _run("DOM_FILMED_INSERT", *cases)


SEQUENCE = ["pointerover", "pointerenter", "mouseover", "mouseenter", "pointermove", "mousemove", "pointerdown",
            "mousedown", "pointerup", "mouseup", "click"]
NOTHING = {"complete": False, "stopped": "not_under_pointer", "count": 0, "last": "", "retargeted": False,
           "hidden": False}


def test_a_filmed_click_on_its_point_sends_the_whole_sequence_at_that_point():
    (on,) = _click({"args": POINT})
    assert on["receipt"] == {"complete": True, "stopped": None, "count": 11, "last": "click", "retargeted": False,
                             "unfocused": False}
    assert [e["type"] for e in on["sent"]] == SEQUENCE
    assert {e["to"] for e in on["sent"]} == {"target"}
    assert {tuple(e["at"]) for e in on["sent"]} == {tuple(POINT)}
    # screen coordinates follow the point too
    assert {tuple(e["screen"]) for e in on["sent"]} == {(POINT[0] + 100, POINT[1] + 50)}


def test_a_filmed_click_goes_to_what_is_under_the_point_inside_the_control():
    (inner,) = _click({"args": POINT, "hit": "descendant"})
    assert inner["receipt"]["complete"] is True
    assert {e["to"] for e in inner["sent"]} == {"icon"} and {tuple(e["at"]) for e in inner["sent"]} == {tuple(POINT)}


@pytest.mark.parametrize("case", [
    {"args": POINT, "hit": "other"},  # something else is on top at the point
    {"args": POINT, "hit": "none"},  # nothing of the page is there
    {"args": POINT, "blind": True},  # a root that cannot hit-test
    {"args": [59.9, 340]},  # left of the rectangle, though the hit test names the control
    {"args": [200.1, 340]},
    {"args": [70, 329.9]},
    {"args": [70, 374.1]},
    {"args": POINT, "rect": [60, 630, 140, 44]},  # the control has moved from under the point
], ids=["covered", "nothing-there", "no-hit-test", "left", "right", "above", "below", "moved"])
def test_a_filmed_click_off_its_control_sends_nothing(case):
    """Sol round 6: with a point, the sequence never falls back to the control when its hit test finds
    something else, and never acts anywhere but the point."""
    (off,) = _click(case)
    assert off["receipt"] == NOTHING and off["sent"] == []


def test_a_filmed_click_on_the_rectangles_edge_is_on_it():
    edges = _click({"args": [60, 330]}, {"args": [200, 374]})
    assert [e["receipt"]["complete"] for e in edges] == [True, True]


def test_a_filmed_click_on_a_detached_control_says_detached_before_anything_else():
    (gone,) = _click({"args": POINT, "connected": False, "hit": "other"})
    assert gone["receipt"]["stopped"] == "detached" and gone["sent"] == []


HOVER = SEQUENCE[:6]
MOVED = {"rect": [60, 630, 140, 44]}
COMPLETE = {"complete": True, "stopped": None, "count": 11, "last": "click", "retargeted": False}
#: a filmed click that completes also says whether its press gave the focus a press gives (FP53)
FILMED_COMPLETE = COMPLETE | {"unfocused": False}


def _types(run: dict) -> list[str]:
    return [e["type"] for e in run["sent"] if e["type"] != "focus()"]


def _left(count: int, last: str, hidden: bool = False) -> dict:
    return {"complete": False, "stopped": "left_pointer", "count": count, "last": last, "retargeted": False,
            "hidden": hidden}


@pytest.mark.parametrize("on", [
    {"event": "pointerover", "then": MOVED},
    {"event": "mousemove", "then": MOVED},
    {"event": "mouseenter", "then": {"hit": "other"}},
    {"event": "pointermove", "then": {"hit": "none"}},
], ids=["moved-on-pointerover", "moved-on-mousemove", "covered-on-mouseenter", "gone-from-under-on-pointermove"])
def test_a_control_that_leaves_the_point_while_hovered_is_not_pressed(on):
    """FP30, FP44: page listeners run on the six hover and move events, and every one of them is sent
    only to an element under the pointer: the sequence stops at the event whose listener took the
    control away, and nothing is pressed. Without a point the same page receives the whole sequence,
    as before. tests/test_filmed_click_invariant.py has every boundary; these are four of its cells."""
    filmed, unfilmed = _click({"args": POINT, "on": on}, {"on": on})
    sent = HOVER.index(on["event"]) + 1
    assert filmed["receipt"] == _left(sent, on["event"]) and _types(filmed) == HOVER[:sent]
    assert unfilmed["receipt"] == COMPLETE and _types(unfilmed) == SEQUENCE


@pytest.mark.parametrize(("case", "count", "last"), [
    ({"on": {"event": "pointerdown", "then": MOVED}}, 7, "pointerdown"),
    ({"on": {"event": "pointerdown", "then": {"hit": "other"}}}, 7, "pointerdown"),
    ({"on": {"event": "mousedown", "then": MOVED}}, 8, "mousedown"),
    ({"focus": {"then": MOVED}}, 8, "mousedown"),
    ({"focus": {"then": {"rect": [60, 370, 140, 30]}}}, 8, "mousedown"),
    ({"on": {"event": "pointerup", "then": MOVED}}, 9, "pointerup"),
    ({"on": {"event": "mouseup", "then": MOVED}}, 10, "mouseup"),
    ({"on": {"event": "mouseup", "then": {"hit": "other"}}}, 10, "mouseup"),
], ids=["moved-on-pointerdown", "covered-on-pointerdown", "moved-on-mousedown", "moved-by-focus",
        "a-field-40px-down-on-focus", "moved-on-pointerup", "moved-on-mouseup", "covered-on-mouseup"])
def test_a_control_that_leaves_the_point_once_pressed_is_not_clicked(case, count, last):
    """Sol round 7: from the press on, every event is aimed again. A control that moves on mousedown,
    or when the press focuses it, is pressed and not released or clicked, and the receipt names the
    last event sent. Without a point the same page receives the whole sequence, as before."""
    filmed, unfilmed = _click({"args": POINT, **case}, case)
    assert filmed["receipt"] == _left(count, last)
    assert _types(filmed) == SEQUENCE[:count] and "click" not in _types(filmed)
    assert unfilmed["receipt"] == COMPLETE and _types(unfilmed) == SEQUENCE


def test_a_child_that_leaves_at_a_hover_event_gets_no_further_event():
    """Sol round 7 and 8: a child that the hover moved inside an unchanged container is not pressed
    where it no longer is, and is not sent the rest of the hover events there either. A control whose
    other child is under the point from the start is pressed on that child."""
    swap = {"hit": "descendant", "on": {"event": "pointerover", "then": {"hit": "second"}}}
    filmed, unfilmed, already = _click({"args": POINT, **swap}, swap, {"args": POINT, "hit": "second"})
    assert filmed["receipt"] == _left(1, "pointerover")
    assert [(e["type"], e["to"]) for e in filmed["sent"]] == [("pointerover", "icon")]
    # without a point the sequence keeps its first target, as it always has
    assert unfilmed["receipt"] == COMPLETE and {e["to"] for e in unfilmed["sent"]} == {"icon"}
    assert already["receipt"] == FILMED_COMPLETE and {e["to"] for e in already["sent"]} == {"label"}


def test_a_press_and_a_release_on_two_children_click_what_holds_both():
    """As a real click does: its target is the nearest common ancestor of what was pressed and what was
    released. Here the focus the press gives rearranges the control; a listener of the press's own
    events doing the same stops the sequence, because the mouse event is not sent apart from its
    pointer event."""
    by_focus, by_pointerdown = _click(
        {"args": POINT, "hit": "descendant", "focus": {"then": {"hit": "second"}}},
        {"args": POINT, "hit": "descendant", "on": {"event": "pointerdown", "then": {"hit": "second"}}})
    assert by_focus["receipt"] == FILMED_COMPLETE
    assert [(e["type"], e["to"]) for e in by_focus["sent"]][6:] == [
        ("pointerdown", "icon"), ("mousedown", "icon"), ("focus()", "target"), ("pointerup", "label"),
        ("mouseup", "label"), ("click", "target")]
    assert by_pointerdown["receipt"] == _left(7, "pointerdown")
    assert [(e["type"], e["to"]) for e in by_pointerdown["sent"]][6:] == [("pointerdown", "icon")]


def test_a_control_removed_while_hovered_or_pressed_is_reported_detached():
    hovered, pressed = _click({"args": POINT, "on": {"event": "mouseover", "then": {"connected": False}}},
                              {"args": POINT, "on": {"event": "mousedown", "then": {"connected": False}}})
    assert hovered["receipt"] == {"complete": False, "stopped": "detached", "count": 3, "last": "mouseover",
                                  "retargeted": False}
    assert pressed["receipt"]["stopped"] == "detached" and pressed["receipt"]["last"] == "mousedown"
    assert "click" not in _types(pressed)


SHOWN = ["auto", "default", "pointer", "text", "grab", "-webkit-grab", "not-allowed", "zoom-in"]
HIDDEN = ["none", 'url("x.png") 4 4, auto', "url(x.cur), pointer", "", "Pointer", "pointer, auto"]


@pytest.mark.parametrize("cursor", SHOWN)
def test_a_keyword_cursor_shows_the_pointer(cursor):
    click, insert = _click({"args": POINT, "cursor": cursor}), _insert({"args": [*POINT, "Ada"], "node": FIELD,
                                                                           "cursor": cursor})
    assert click[0]["receipt"] == FILMED_COMPLETE and insert[0]["receipt"] == INSERTED


@pytest.mark.parametrize("cursor", HIDDEN)
def test_a_pointer_the_page_hides_or_replaces_is_not_acted_under(cursor):
    """Sol round 7: with cursor none, or an image that may be empty, the pointer's position shows
    nothing on screen. Nothing is sent, and the receipt says the pointer was hidden."""
    click, unfilmed = _click({"args": POINT, "cursor": cursor}, {"cursor": cursor})
    assert click["receipt"] == {**NOTHING, "hidden": True} and click["sent"] == []
    assert unfilmed["receipt"] == COMPLETE
    (insert,) = _insert({"args": [*POINT, "Ada"], "node": FIELD, "cursor": cursor})
    assert insert["receipt"] == {"inserted": False, "why": "pointer_hidden"} and insert["commands"] == []


def test_a_pointer_lock_hides_the_pointer_whatever_the_style_says():
    (click,) = _click({"args": POINT, "lock": True})
    (insert,) = _insert({"args": [*POINT, "Ada"], "node": FIELD, "lock": True})
    assert click["receipt"] == {**NOTHING, "hidden": True} and click["sent"] == []
    assert insert["receipt"] == {"inserted": False, "why": "pointer_hidden"} and insert["commands"] == []


@pytest.mark.parametrize(("case", "receipt"), [
    ({"on": {"event": "pointerover", "then": {"cursor": "none"}}}, _left(1, "pointerover", hidden=True)),
    ({"on": {"event": "mousedown", "then": {"cursor": "none"}}}, _left(8, "mousedown", hidden=True)),
    ({"on": {"event": "mouseup", "then": {"lock": True}}}, _left(10, "mouseup", hidden=True)),
    ({"focus": {"then": {"cursor": 'url("blank.png"), auto'}}}, _left(8, "mousedown", hidden=True)),
], ids=["hidden-on-hover", "hidden-on-press", "locked-on-release", "replaced-on-focus"])
def test_a_pointer_hidden_while_the_click_runs_stops_it(case, receipt):
    (run,) = _click({"args": POINT, **case})
    assert run["receipt"] == receipt and _types(run) == SEQUENCE[:receipt["count"]]


def test_a_pointer_that_is_off_the_control_is_said_before_a_hidden_one():
    (click,) = _click({"args": POINT, "hit": "other", "cursor": "none"})
    (insert,) = _insert({"args": [*POINT, "Ada"], "node": FIELD, "hit": "other", "cursor": "none"})
    assert click["receipt"] == NOTHING and insert["receipt"] == {"inserted": False, "why": "not_under_pointer"}


def test_an_unfilmed_click_acts_at_the_centre_and_falls_back_to_the_control_as_before():
    """The request without a point is the one this route has always sent (FP26, against)."""
    plain, covered, inner, half = _click({}, {"hit": "other"}, {"hit": "descendant"}, {"args": [70.5]})
    for run, to in ((plain, "target"), (covered, "target"), (inner, "icon"), (half, "target")):
        assert run["receipt"] == COMPLETE
        assert [e["type"] for e in run["sent"]] == SEQUENCE
        assert {e["to"] for e in run["sent"]} == {to} and {tuple(e["at"]) for e in run["sent"]} == {tuple(CENTRE)}


FIELD = {"tagName": "INPUT", "type": "text", "disabled": False, "readOnly": False, "isContentEditable": False}
INSERTED = {"inserted": True, "why": None}


def _field(**changes) -> dict:
    return {**FIELD, **changes}


def test_a_filmed_insert_into_the_focused_field_under_the_point_runs_one_command():
    (done,) = _insert({"args": [*POINT, "Ada"], "node": FIELD})
    assert done["receipt"] == INSERTED
    assert done["commands"] == [["insertText", False, "Ada"]] and done["sent"] == []


@pytest.mark.parametrize("node", [
    _field(tagName="TEXTAREA", type="textarea"),
    _field(tagName="DIV", type=None, isContentEditable=True),
    _field(type="search"),
    _field(type=""),
], ids=["textarea", "contenteditable", "search", "no-type"])
def test_every_editable_kind_is_inserted_into(node):
    (done,) = _insert({"args": [*POINT, "Ada"], "node": node})
    assert done["receipt"] == INSERTED and len(done["commands"]) == 1


def test_a_filmed_insert_under_the_point_through_a_descendant_or_in_a_shadow_root():
    inner, shadow = _insert({"args": [*POINT, "Ada"], "node": _field(tagName="DIV", isContentEditable=True),
                             "hit": "descendant"},
                            {"args": [*POINT, "Ada"], "node": FIELD, "shadow": True})
    assert inner["receipt"] == INSERTED and shadow["receipt"] == INSERTED


@pytest.mark.parametrize(("case", "why"), [
    ({"connected": False, "active": "other", "hit": "other"}, "detached"),
    ({"active": "other"}, "not_focused"),
    ({"active": "none"}, "not_focused"),
    ({"active": "descendant"}, "not_focused"),
    ({"active": "other", "hit": "other"}, "not_focused"),  # focus is asked before the point
    ({"node": _field(readOnly=True)}, "not_editable"),
    ({"node": _field(disabled=True)}, "not_editable"),
    ({"node": _field(type="checkbox")}, "not_editable"),
    ({"node": _field(type="SUBMIT")}, "not_editable"),
    ({"node": _field(tagName="DIV", type=None)}, "not_editable"),
    ({"node": _field(tagName="TEXTAREA", readOnly=True)}, "not_editable"),
    ({"hit": "other"}, "not_under_pointer"),
    ({"hit": "none"}, "not_under_pointer"),
    ({"blind": True}, "not_under_pointer"),
    ({"rect": [60, 370, 140, 44]}, "not_under_pointer"),  # the field moved 40 px down, as one that gains focus may
    ({"point": [59.9, 340]}, "not_under_pointer"),
    ({"point": [70, 374.1]}, "not_under_pointer"),
])
def test_a_filmed_insert_that_fails_a_check_inserts_nothing_and_names_the_check(case, why):
    spec = {"node": FIELD, **case, "args": [*case.get("point", POINT), "Ada"]}
    (refused,) = _insert(spec)
    assert refused["receipt"] == {"inserted": False, "why": why}
    assert refused["commands"] == [] and refused["sent"] == []


def test_a_command_the_document_does_not_accept_is_reported_as_such():
    (refused,) = _insert({"args": [*POINT, "Ada"], "node": FIELD, "accepts": False})
    assert refused["receipt"] == {"inserted": False, "why": "command_refused"}
    assert refused["commands"] == [["insertText", False, "Ada"]]
