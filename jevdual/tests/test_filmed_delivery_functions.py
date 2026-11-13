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
  const view = { PointerEvent: class extends Event {}, MouseEvent: class extends Event {},
                 screenX: 100, screenY: 50 };
  const doc = { defaultView: view,
                execCommand: (...args) => { commands.push(args); return spec.accepts !== false; } };
  // what a page listener can change while the sequence runs
  const page = { rect: spec.rect || [60, 330, 140, 44], hit: spec.hit || 'target', connected: spec.connected !== false };
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
      closest: () => null,
    }, extra || {});
    return el;
  };
  // the node's root: the document, or a shadow root with its own hit test and active element
  const root = spec.shadow ? {} : doc;
  const node = make('target', null, root, spec.node);
  const child = make('icon', node, root);
  const other = make('other', null, root);
  const hits = { target: node, descendant: child, other, none: null };
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
NOTHING = {"complete": False, "stopped": "not_under_pointer", "count": 0, "last": "", "retargeted": False}


def test_a_filmed_click_on_its_point_sends_the_whole_sequence_at_that_point():
    (on,) = _click({"args": POINT})
    assert on["receipt"] == {"complete": True, "stopped": None, "count": 11, "last": "click", "retargeted": False}
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


@pytest.mark.parametrize(("on", "left_after"), [
    ({"event": "pointerover", "then": MOVED}, "mousemove"),
    ({"event": "mousemove", "then": MOVED}, "mousemove"),
    ({"event": "mouseenter", "then": {"hit": "other"}}, "mousemove"),
    ({"event": "pointermove", "then": {"hit": "none"}}, "mousemove"),
], ids=["moved-on-pointerover", "moved-on-mousemove", "covered-on-mouseenter", "gone-from-under-on-pointermove"])
def test_a_control_that_leaves_the_point_while_hovered_is_not_pressed(on, left_after):
    """FP30: page listeners run on the six hover and move events; the point is checked again in the
    same turn as the press. Without a point the same page receives the whole sequence, as before."""
    filmed, unfilmed = _click({"args": POINT, "on": on}, {"on": on})
    assert filmed["receipt"] == {"complete": False, "stopped": "left_pointer", "count": 6, "last": left_after,
                                 "retargeted": False}
    assert [e["type"] for e in filmed["sent"]] == HOVER
    assert unfilmed["receipt"]["complete"] is True and [e["type"] for e in unfilmed["sent"]] == SEQUENCE


def test_a_control_removed_while_hovered_is_reported_detached_and_one_moved_by_the_press_is_still_released():
    """FP30: removal keeps its own receipt, and from the press on the sequence follows the control, as
    the press of a real pointer already has (a field that moves when the press focuses it)."""
    removed, pressed, released = _click(
        {"args": POINT, "on": {"event": "mouseover", "then": {"connected": False}}},
        {"args": POINT, "on": {"event": "pointerdown", "then": MOVED}},
        {"args": POINT, "on": {"event": "mouseup", "then": {"hit": "other"}}})
    assert removed["receipt"] == {"complete": False, "stopped": "detached", "count": 3, "last": "mouseover",
                                  "retargeted": False}
    assert "pointerdown" not in [e["type"] for e in removed["sent"]]
    for run in (pressed, released):
        assert run["receipt"]["complete"] is True and [e["type"] for e in run["sent"]] == SEQUENCE
    # and the check before the press is what stops the first case of the test above, not the removal
    (hovered,) = _click({"args": POINT, "on": {"event": "pointerover", "then": MOVED}})
    assert hovered["receipt"]["stopped"] == "left_pointer"


def test_an_unfilmed_click_acts_at_the_centre_and_falls_back_to_the_control_as_before():
    """The request without a point is the one this route has always sent (FP26, against)."""
    plain, covered, inner, half = _click({}, {"hit": "other"}, {"hit": "descendant"}, {"args": [70.5]})
    for run, to in ((plain, "target"), (covered, "target"), (inner, "icon"), (half, "target")):
        assert run["receipt"] == {"complete": True, "stopped": None, "count": 11, "last": "click", "retargeted": False}
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
