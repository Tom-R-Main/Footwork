"""The filmed click's invariant, over every boundary of the sequence (FP44, FP53).

The invariant (``vendor/cua-driver/PROVENANCE.md``, "Filmed delivery"): everything the sequence does
to the page (it dispatches events, and it gives focus) goes to an element that is under the pointer in
the same turn, immediately before. Three reviews each found one more place between two events where
it did not hold, and a fourth found the focus going to an element nobody had checked, so this file
does not list cases: it builds every cell of

    boundary     before the first event, after each event the sequence sends, and after the focus
  x disturbance  what a page listener does there (``DISTURBANCES``)
  x start        the pointer is on the control itself, or on a child of it
  x press        ordinary, a ``pointerdown`` the page cancels (no mouse events follow), or a
                 ``mousedown`` it cancels (no focus follows)
  x focusable    where the nearest focusable element of what is pressed is (``FOCUSABLE``)

and makes three assertions in each, on the click sequence taken from the pinned driver archive and run
in Node on a stand-in page:

1. the receipt and the events are what ``oracle`` gives, a second statement of the rule written here
   from the provenance record's two tables and sharing no code with the driver;
2. independently of the oracle, the stand-in page itself saw no event, and no focus, go to an element
   it did not have under the pointer at that moment;
3. without a point, the same cell sends exactly what the sequence sent before the step that added the
   point (the pinned source with the step's patch taken back out).

It also reads the function's text for every call it makes and requires each to be named here as one
that reads or one that acts, so a new way of touching the page cannot be added unseen
(``test_every_call_the_functions_make_is_a_read_or_a_checked_act``).

It tests the function's logic. That Chrome's hit test, events and isolated world behave as the
stand-ins do is ``scripts/probe_locate_world_headless.py``.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
import shutil
import subprocess
import tarfile
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor/cua-driver"
TOOLS = "libs/cua-driver/rust/crates/cua-driver-core/src/browser/tools.rs"

pytestmark = pytest.mark.skipif(shutil.which("node") is None or shutil.which("patch") is None,
                                reason="needs Node to run the page function and patch to recover the one before it")

RECT = [60, 330, 140, 44]
POINT = [70.5, 340.25]
HOVER = ["pointerover", "pointerenter", "mouseover", "mouseenter", "pointermove", "mousemove"]

#: what a page listener can do to a control while a click is being sent to it, as changes to the stand-in
#: page's state. ``sibling`` and ``onto_control`` change what is under the point without the control
#: leaving it; ``child_removed`` takes away the child that was receiving and leaves another there.
DISTURBANCES = {
    "moved": {"rect": [60, 630, 140, 44]},
    "covered": {"hit": "other"},
    "nothing_there": {"hit": "none"},
    "sibling": {"hit": "label"},
    "onto_control": {"hit": "target"},
    "child_removed": {"gone": ["icon"], "hit": "label"},
    "removed": {"connected": False},
    "cursor_none": {"cursor": "none"},
    "cursor_image": {"cursor": 'url("blank.png"), auto'},
    "pointer_lock": {"lock": True},
}
STARTS = ("target", "icon")
#: the event whose default the page prevents, if any
PRESSES = (None, "pointerdown", "mousedown")
#: where the nearest focusable element of the pressed one is: the pressed element itself, the control
#: (the ref's node), a container of the control that the ref does not name, or nowhere
FOCUSABLE = ("node", "self", "outside", "none")

# The stand-in page. ``page`` is its state; a listener (``spec.at``, ``spec.then``) changes it after the
# n-th dispatched event, or in the focus. Each dispatch and the focus record ``under``: whether, by the
# page's own state at that moment and before any listener ran, the receiver was under the pointer.
HARNESS = r"""
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const run = (source, spec) => {
  const fn = eval('(' + source + ')');
  const sent = [];
  let dispatched = 0;
  class Event { constructor(type, init) { this.type = type; Object.assign(this, init); } }
  const page = { rect: [60, 330, 140, 44], hit: spec.start, connected: true, cursor: 'pointer', lock: false, gone: [] };
  const change = () => Object.assign(page, spec.then);
  if (spec.at === 0) change();
  const [px, py] = spec.point;
  const shown = () => !page.lock && /^[a-z-]+$/.test(page.cursor) && page.cursor !== 'none';
  const view = { PointerEvent: class extends Event {}, MouseEvent: class extends Event {}, screenX: 100, screenY: 50,
                 getComputedStyle: () => ({ cursor: page.cursor }) };
  const doc = { defaultView: view, get pointerLockElement() { return page.lock ? {} : null; } };
  let node = null;
  const hits = {};
  const holds = (outer, inner) => { for (let o = inner; o; o = o.parentElement) if (o === outer) return true; return false; };
  // the page's own answer, by its state and none of the function's code: the whole check, for an
  // event's receiver and for the focus's alike
  const underPointer = (receiver) => {
    const [left, top, width, height] = page.rect;
    const hit = hits[page.hit] || null;
    return page.connected && px >= left && px <= left + width && py >= top && py <= top + height
      && !!hit && holds(node, hit) && shown() && holds(receiver, hit) && holds(node, receiver);
  };
  let outer = null;
  const make = (name, parent) => {
    const el = {
      name, ownerDocument: doc,
      get parentElement() { return (parent && !page.gone.includes(name)) ? parent : null; },
      get isConnected() { return page.connected && !page.gone.includes(name); },
      getBoundingClientRect: () => {
        const [left, top, width, height] = page.rect;
        return { left, top, width, height, right: left + width, bottom: top + height };
      },
      getRootNode: () => doc,
      contains: (other) => holds(el, other),
      dispatchEvent: (event) => {
        dispatched += 1;
        sent.push({ type: event.type, to: name, under: spec.filmed ? underPointer(el) : null,
                    at: [event.clientX, event.clientY] });
        if (spec.at === dispatched) change();
        return event.type !== spec.cancel;
      },
      // the nearest focusable element of this one, wherever this cell puts it
      closest: () => ({ node, self: el, outside: outer, none: null })[spec.focusable],
      focus: () => {
        sent.push({ type: 'focus()', to: name, under: spec.filmed ? underPointer(el) : null });
        if (spec.at === 'focus') change();
      },
    };
    return el;
  };
  // a container of the control: it holds whatever the control holds and is not part of it
  outer = make('outer', null);
  node = make('target', outer);
  Object.assign(hits, { target: node, icon: make('icon', node), label: make('label', node), other: make('other', null) });
  doc.elementFromPoint = () => hits[page.hit] || null;
  const receipt = fn.apply(node, spec.filmed ? spec.point : []);
  return { receipt, sent };
};
process.stdout.write(JSON.stringify(input.cases.map((spec) => run(input.sources[spec.source], spec))));
"""


def _literal(source: str, name: str = "DOM_EVENT_CLICK_SEQUENCE") -> str:
    raw = re.search(rf'const {name}: &str = r#"(.*?)"#;\n', source, re.DOTALL)
    if raw:
        return raw.group(1)
    literal = re.search(rf'const {name}: &str = "(.*?)";\n', source, re.DOTALL)
    assert literal, f"{name} is not in tools.rs"
    text = re.sub(r"\\\n\s*", "", literal.group(1))
    assert "\\\\" not in text and "\\n" not in text
    return text.replace('\\"', '"')


@pytest.fixture(scope="module")
def sources(tmp_path_factory) -> dict:
    """The click sequence as pinned, and as it was before the step that gave it a point: the pinned
    tools.rs with that step's patch reversed, which must be the file the step's manifest says it began
    from."""
    with tarfile.open(VENDOR / "native-source.tar.gz") as archive:
        pinned = archive.extractfile(TOOLS).read()
    work = tmp_path_factory.mktemp("before")
    (work / TOOLS).parent.mkdir(parents=True)
    (work / TOOLS).write_bytes(pinned)
    wanted = f"--- a/{TOOLS}"
    patch = (VENDOR / "patches/ref-locate.patch").read_text()
    start = patch.index(wanted)
    following = patch.find("\n--- a/", start + 1)
    one_file = patch[start:following + 1 if following != -1 else len(patch)]
    done = subprocess.run(["patch", "--batch", "--silent", "-R", "-p1"], input=one_file, cwd=work, text=True,
                          capture_output=True, timeout=60, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    before = (work / TOOLS).read_bytes()
    record = json.loads((VENDOR / "patches/ref-locate.json").read_text())["files"][TOOLS]
    assert hashlib.sha256(before).hexdigest() == record["before"]
    assert hashlib.sha256(pinned).hexdigest() == record["after"]
    return {"pinned": _literal(pinned.decode()), "before": _literal(before.decode()),
            **{name: _literal(pinned.decode(), name) for name in (
                "DOM_FILMED_INSERT", "DOM_NODE_LOCATE", "DOM_NODE_CONNECTED_CHECK", "DOM_CLICK_READBACK")},
            "rust": re.sub(r"\\\n\s*", "", pinned.decode())}


# ---- the oracle: the rule again, from the provenance record's tables


class _Left(Exception):
    pass


class _Detached(Exception):
    pass


def oracle(start: str, at, then: dict, cancel: str | None, focusable: str = "node") -> tuple[dict, list[tuple[str, str]]]:
    """The receipt and the (event, receiver) list of a filmed click on the stand-in page. ``cancel``
    names the event whose default the page prevents: ``pointerdown`` (no mouse events follow, and so no
    focus), ``mousedown`` (no focus follows), or neither."""
    page = {"rect": RECT, "hit": start, "connected": True, "cursor": "pointer", "lock": False, "gone": []}
    sent: list[tuple[str, str]] = []
    told = {"count": 0, "last": "", "hidden": False, "unfocused": False}

    def holds(outer: str, inner: str) -> bool:
        return outer == inner or (outer == "target" and inner in ("icon", "label") and inner not in page["gone"])

    def aim() -> str | None:
        """What is under the point, when the point is on the control and the pointer shows."""
        x, y, w, h = page["rect"]
        hit = page["hit"]
        if not (x <= POINT[0] <= x + w and y <= POINT[1] <= y + h) or hit in ("other", "none") or not holds("target", hit):
            return None
        if page["lock"] or page["cursor"] == "none" or not re.fullmatch(r"[a-z-]+", page["cursor"]):
            told["hidden"] = True
            return None
        return hit

    def under(receiver: str) -> str:
        if not page["connected"]:
            raise _Detached
        hit = aim()
        if hit is None or not holds("target", receiver) or not holds(receiver, hit):
            raise _Left
        return hit

    def send(event: str, receiver: str) -> None:
        under(receiver)
        sent.append((event, receiver))
        told["count"], told["last"] = told["count"] + 1, event
        if at == told["count"]:
            page.update(then)

    def receipt(**fields) -> dict:
        return {"complete": False, "count": told["count"], "last": told["last"], "retargeted": False, **fields}

    if at == 0:
        page.update(then)
    if not page["connected"]:
        return receipt(stopped="detached"), sent
    first = aim()
    if first is None:
        return receipt(stopped="not_under_pointer", hidden=told["hidden"]), sent
    try:
        for event in HOVER:
            send(event, first)  # one hit test for the six, as one move of a pointer gives
        down = under("target")  # a fresh hit at the press
        send("pointerdown", down)
        if cancel != "pointerdown":
            send("mousedown", down)  # the pair is not split
        if cancel is None:
            under(down)
            # the focus goes where a press gives it only when that is the node or inside it, and under
            # the same check; a container of the node gets nothing, and the receipt says so
            receiver = {"node": "target", "self": down, "outside": "outer", "none": None}[focusable]
            if receiver == "outer":
                told["unfocused"] = True
            elif receiver is not None:
                under(receiver)
                sent.append(("focus()", receiver))
                if at == "focus":
                    page.update(then)
        up = under("target")  # a fresh hit at the release
        send("pointerup", up)
        if cancel != "pointerdown":
            send("mouseup", up)
        # the nearest ancestor holding both; the control itself when the pressed child has left it
        send("click", down if down == up and holds("target", down) else "target")
    except _Detached:
        return receipt(stopped="detached"), sent
    except _Left:
        return receipt(stopped="left_pointer", hidden=told["hidden"]), sent
    return {"complete": True, "stopped": None, "count": told["count"], "last": told["last"], "retargeted": False,
            "unfocused": told["unfocused"]}, sent


def _cells() -> list[dict]:
    cells = []
    for start, cancel in itertools.product(STARTS, PRESSES):
        events = 9 if cancel == "pointerdown" else 11
        boundaries = [*range(events + 1), *([] if cancel else ["focus"])]
        for at, (name, then) in itertools.product(boundaries, DISTURBANCES.items()):
            if name == "child_removed" and start != "icon":
                continue  # there is no receiving child to remove
            # without mouse events there is nothing about the focus to vary; with a mousedown the page
            # cancels there is: no focus is given wherever the focusable element is
            for focusable in (("node",) if cancel == "pointerdown" else FOCUSABLE):
                cells.append({"start": start, "cancel": cancel, "at": at, "name": name, "then": then, "point": POINT,
                              "focusable": focusable})
    return cells


@pytest.fixture(scope="module")
def matrix(sources) -> list[dict]:
    cells = _cells()
    cases = [dict(cell, source=source, filmed=filmed) for cell in cells
             for source, filmed in (("pinned", True), ("pinned", False), ("before", False))]
    done = subprocess.run(["node", "-e", HARNESS], input=json.dumps({"sources": sources, "cases": cases}),
                          capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 0, done.stderr[-3000:]
    runs = json.loads(done.stdout)
    for i, cell in enumerate(cells):
        cell["filmed"], cell["unfilmed"], cell["before"] = runs[3 * i:3 * i + 3]
        cell["id"] = (f"{cell['start']}{'/' + cell['cancel'] + ' cancelled' if cell['cancel'] else ''} "
                      f"{cell['name']} at {cell['at']}"
                      + (f", focusable {cell['focusable']}" if cell["focusable"] != "node" else ""))
    return cells


def _pairs(run: dict) -> list[tuple[str, str]]:
    return [(e["type"], e["to"]) for e in run["sent"]]


def test_the_matrix_covers_every_boundary_and_every_disturbance(matrix):
    pressed, cancelled = 2 * 13 * len(DISTURBANCES) - 13, 2 * 10 * len(DISTURBANCES) - 10  # child_removed needs a child
    unfocusing = 2 * 12 * len(DISTURBANCES) - 12  # a cancelled mousedown: eleven events and no focus boundary
    assert len(matrix) == len(FOCUSABLE) * (pressed + unfocusing) + cancelled == 2090
    assert Counter(cell["cancel"] for cell in matrix) == {None: 4 * pressed, "pointerdown": cancelled,
                                                          "mousedown": 4 * unfocusing}
    assert {cell["at"] for cell in matrix} == {*range(12), "focus"}
    assert {cell["name"] for cell in matrix} == set(DISTURBANCES)
    assert Counter(cell["focusable"] for cell in matrix) == {
        "node": pressed + unfocusing + cancelled, "self": pressed + unfocusing, "outside": pressed + unfocusing,
        "none": pressed + unfocusing}


def test_every_cell_is_what_the_rule_gives(matrix):
    """(1): the receipt and the events of the pinned function against the oracle's."""
    wrong = []
    for cell in matrix:
        receipt, sent = oracle(cell["start"], cell["at"], cell["then"], cell["cancel"], cell["focusable"])
        if cell["filmed"]["receipt"] != receipt or _pairs(cell["filmed"]) != sent:
            wrong.append((cell["id"], cell["filmed"]["receipt"], receipt, _pairs(cell["filmed"])[6:], sent[6:]))
    assert not wrong, f"{len(wrong)} of {len(matrix)} cells differ; first: {wrong[0]}"


def test_no_event_and_no_focus_goes_to_an_element_that_is_not_under_the_pointer(matrix):
    """(2): the invariant itself, by the stand-in page's own state and not the oracle's."""
    off = [(cell["id"], e["type"], e["to"]) for cell in matrix for e in cell["filmed"]["sent"] if e["under"] is not True]
    assert not off, f"{len(off)} events off the pointer; first: {off[0]}"
    # and every event is at the point
    assert {tuple(e["at"]) for cell in matrix for e in cell["filmed"]["sent"] if "at" in e} == {tuple(POINT)}


def test_the_focus_goes_only_to_an_element_of_the_node(matrix):
    """Sol round 9: the focus was given to the nearest focusable element after a check of the pressed
    one. For a control inside a focusable container that element is the container, which the ref does
    not name. Now the focus has the events' check, on the element it is given to."""
    inside = {"target", "icon", "label"}
    focused = [(cell, e) for cell in matrix for e in cell["filmed"]["sent"] if e["type"] == "focus()"]
    assert focused and all(e["to"] in inside and e["under"] is True for _, e in focused)
    assert {cell["focusable"] for cell, _ in focused} == {"node", "self"}
    # Sol round 10: a press whose mousedown the page cancels gives no focus, as one whose pointerdown it
    # cancels gives none, wherever the focusable element is; and neither says it withheld one, because
    # a pointer would have given none either
    assert {cell["cancel"] for cell, _ in focused} == {None}
    unfocusing = [cell for cell in matrix if cell["cancel"] == "mousedown"]
    assert {cell["focusable"] for cell in unfocusing} == set(FOCUSABLE)
    whole = [cell for cell in unfocusing if cell["filmed"]["receipt"]["complete"]]
    assert whole and all(len(cell["filmed"]["sent"]) == 11 and cell["filmed"]["receipt"]["unfocused"] is False
                         for cell in whole)
    assert all("mousedown" in [e["type"] for e in cell["filmed"]["sent"]] for cell in whole)
    # which element: the control, or the element that was pressed, as the cell says
    assert all(e["to"] == "target" for cell, e in focused if cell["focusable"] == "node")
    for cell, e in ((c, e) for c, e in focused if c["focusable"] == "self"):
        pairs = _pairs(cell["filmed"])
        assert e["to"] == pairs[pairs.index(("focus()", e["to"])) - 1][1], cell["id"]  # the mousedown before it
    # a completed click says whether the press gave the focus a press would give
    for cell in matrix:
        receipt = cell["filmed"]["receipt"]
        if receipt["complete"]:
            assert receipt["unfocused"] is (cell["focusable"] == "outside" and not cell["cancel"]), cell["id"]
        else:
            assert "unfocused" not in receipt, cell["id"]
    # and without a point the same cells do focus the container: the difference is the point's
    outside = [cell for cell in matrix if cell["focusable"] == "outside" and cell["cancel"] is None]
    assert sum(("focus()", "outer") in _pairs(cell["unfilmed"]) for cell in outside) > len(outside) // 2
    # (and gives none where the page cancelled the mousedown, as before the step)
    assert not any(e["type"] == "focus()" for cell in matrix if cell["cancel"] for e in cell["unfilmed"]["sent"])
    assert not any("unfocused" in cell["unfilmed"]["receipt"] for cell in matrix)


def test_without_a_point_every_cell_sends_what_it_sent_before_the_step(matrix):
    """(3): the unfilmed sequence, against the source with the step's patch reversed."""
    changed = [cell["id"] for cell in matrix
               if cell["unfilmed"]["sent"] != cell["before"]["sent"] or cell["unfilmed"]["receipt"] != cell["before"]["receipt"]]
    assert not changed, changed[:5]
    # which is not vacuous: without a point the sequence goes on where the filmed one stops
    assert sum(cell["unfilmed"]["receipt"]["complete"] for cell in matrix) > sum(
        cell["filmed"]["receipt"]["complete"] for cell in matrix)


def test_a_stopped_click_stops_exactly_where_the_page_changed(matrix):
    """A click that stops for the pointer sends nothing after the listener that took the control from
    it: the count in its receipt is the boundary the disturbance was applied at."""
    for cell in matrix:
        receipt = cell["filmed"]["receipt"]
        if receipt["stopped"] in ("left_pointer", "detached") and cell["at"] != "focus":
            assert receipt["count"] == cell["at"], cell["id"]
        if receipt["stopped"] == "left_pointer" and cell["at"] == "focus":
            assert (receipt["count"], receipt["last"]) == (8, "mousedown"), cell["id"]
        if receipt["stopped"] in ("not_under_pointer", "detached") and receipt["count"] == 0:
            assert cell["filmed"]["sent"] == [], cell["id"]


def test_the_matrix_reaches_every_outcome_at_every_boundary(matrix):
    """The matrix is not passing because its cells are all alike."""
    seen = Counter((cell["filmed"]["receipt"]["stopped"], cell["filmed"]["receipt"]["last"]) for cell in matrix)
    events = [*HOVER, "pointerdown", "mousedown", "pointerup", "mouseup"]
    assert {last for stopped, last in seen if stopped == "left_pointer"} == set(events)
    assert {last for stopped, last in seen if stopped == "detached"} == {"", *events}
    assert seen["not_under_pointer", ""] and seen[None, "click"]
    hidden = Counter(cell["filmed"]["receipt"].get("hidden") for cell in matrix)
    assert hidden[True] and hidden[False]


def _cell(matrix, start, name, at, cancel=None, focusable="node") -> dict:
    return next(c for c in matrix if (c["start"], c["name"], c["at"], c["cancel"], c["focusable"])
                == (start, name, at, cancel, focusable))


def test_the_cells_the_reviews_found(matrix):
    """Each review's counterexample is a cell; these pin them by name so that the matrix cannot lose one
    by a change to how it is built."""
    # round 6: a control that moves when hovered is not pressed (now after the first event, not the sixth)
    shy = _cell(matrix, "target", "moved", 1)
    assert (shy["filmed"]["receipt"]["stopped"], shy["filmed"]["receipt"]["count"]) == ("left_pointer", 1)
    # round 7: one that moves when pressed, or when the press focuses it, is not released or clicked
    for at in (8, "focus"):
        dodge = _cell(matrix, "target", "moved", at)
        assert (dodge["filmed"]["receipt"]["stopped"], dodge["filmed"]["receipt"]["last"]) == ("left_pointer", "mousedown")
        assert [e[0] for e in _pairs(dodge["filmed"])][6:8] == ["pointerdown", "mousedown"]
    # round 7: a child the hover moved inside an unchanged control is not pressed where it was
    swapped = _cell(matrix, "icon", "sibling", 1)
    assert _pairs(swapped["filmed"]) == [("pointerover", "icon")]
    # round 8: a child pressed and released whose mouseup listener moves it away gets no click
    late = _cell(matrix, "icon", "sibling", 10)
    assert late["filmed"]["receipt"] == {"complete": False, "stopped": "left_pointer", "count": 10, "last": "mouseup",
                                         "retargeted": False, "hidden": False}
    assert _pairs(late["filmed"])[6:] == [("pointerdown", "icon"), ("mousedown", "icon"), ("focus()", "target"),
                                          ("pointerup", "icon"), ("mouseup", "icon")]
    # ... and without a point the same page is clicked on that child, where it went
    assert _pairs(late["unfilmed"])[-1] == ("click", "icon")
    # round 8: a mouse event is not sent apart from its pointer event
    split = _cell(matrix, "icon", "sibling", 7)
    assert split["filmed"]["receipt"]["last"] == "pointerdown" and "mousedown" not in [e[0] for e in _pairs(split["filmed"])]
    # round 8: the click goes to what holds the pointerdown and pointerup targets, and only if it is
    # under the pointer then: here the focus bared the sibling, which is released on, and the control
    # holding both is clicked
    both = _cell(matrix, "icon", "sibling", "focus")
    assert both["filmed"]["receipt"]["complete"] is True
    assert _pairs(both["filmed"])[-3:] == [("pointerup", "label"), ("mouseup", "label"), ("click", "target")]
    # a pressed child that its own mouseup listener removed: the click goes to the control, which is
    # under the pointer, as a browser sends it to the surviving ancestor
    rerendered = _cell(matrix, "icon", "child_removed", 10)
    assert rerendered["filmed"]["receipt"]["complete"] is True and _pairs(rerendered["filmed"])[-1] == ("click", "target")
    # ... while one removed by its pointerdown listener is not sent the mousedown at all
    early = _cell(matrix, "icon", "child_removed", 7)
    assert early["filmed"]["receipt"]["last"] == "pointerdown" and early["filmed"]["receipt"]["stopped"] == "left_pointer"
    # a pointer the page hides part way stops it, and says so
    hidden = _cell(matrix, "target", "cursor_none", 9)
    assert (hidden["filmed"]["receipt"]["stopped"], hidden["filmed"]["receipt"]["hidden"]) == ("left_pointer", True)
    # round 9: a control in a focusable container. Nothing moves; the click completes on the control,
    # the container is given no focus, and the receipt says so. Without a point it is focused.
    nested = _cell(matrix, "icon", "covered", 11, focusable="outside")
    assert nested["filmed"]["receipt"] == {"complete": True, "stopped": None, "count": 11, "last": "click",
                                           "retargeted": False, "unfocused": True}
    assert "focus()" not in [e[0] for e in _pairs(nested["filmed"])] and len(nested["filmed"]["sent"]) == 11
    assert ("focus()", "outer") in _pairs(nested["unfilmed"])
    # ... and a focusable child of the control is focused itself, being inside it
    child = _cell(matrix, "icon", "covered", 11, focusable="self")
    assert ("focus()", "icon") in _pairs(child["filmed"]) and child["filmed"]["receipt"]["unfocused"] is False


#: every method the two delivery functions call, by what it does. A call that acts on the page must
#: come directly after the check of the element it acts on; everything else only reads, or makes an
#: object the function then dispatches. A method not named here fails the test below.
CLICK_READS = {"getBoundingClientRect", "getRootNode", "elementFromPoint", "contains", "getComputedStyle", "test",
               "closest", "PointerEvent", "MouseEvent"}
CLICK_ACTS = {
    "dispatchEvent": "const send = (type, event) => { if (filmed) under(target); else live(); "
                     "const kept = target.dispatchEvent(event);",
    "focus": "if (filmed && !el.contains(focusable)) unfocused = true; "
             "else { if (filmed) under(focusable); focusable.focus({ preventScroll: true }); }",
}
INSERT_READS = {"getRootNode", "getBoundingClientRect", "elementFromPoint", "contains", "getComputedStyle", "test",
                "toLowerCase", "includes"}
INSERT_ACTS = {"execCommand": "return { inserted: false, why: 'pointer_hidden' }; "
                              "const done = doc.execCommand('insertText', false, text) === true;"}
#: the other functions a filmed action runs on the page, all in the isolated world: the locate read, the
#: check that the node is in its document, and the click's read of the node before and after. They act
#: on nothing.
LOCATE_READS = {"getBoundingClientRect", "getRootNode", "elementFromPoint", "contains", "getComputedStyle", "hasFocus",
                "abs", "map", "slice", "some", "split", "startsWith"}
READBACK_READS = {"getAttribute", "slice"}
FUNCTIONS = [("pinned", CLICK_READS, CLICK_ACTS), ("DOM_FILMED_INSERT", INSERT_READS, INSERT_ACTS),
             ("DOM_NODE_LOCATE", LOCATE_READS, {}), ("DOM_NODE_CONNECTED_CHECK", set(), {}),
             ("DOM_CLICK_READBACK", READBACK_READS, {})]


#: names of methods and functions that act on a page or run other code. However one is reached (called,
#: called through a parenthesised or quoted member, taken as a value and called later), its name has
#: to be in the text, so each function may contain each name only as many times as it is accounted for
#: in ``NAMED``; any other occurrence fails.
ACTING = frozenset({
    "dispatchEvent", "focus", "blur", "click", "select", "submit", "reset", "requestSubmit", "remove",
    "removeChild", "appendChild", "append", "prepend", "insertBefore", "replaceChild", "replaceWith",
    "replaceChildren", "insertAdjacentHTML", "insertAdjacentElement", "insertAdjacentText", "setAttribute",
    "removeAttribute", "toggleAttribute", "scrollIntoView", "scrollIntoViewIfNeeded", "scrollTo", "scrollBy",
    "scroll", "setSelectionRange", "setRangeText", "execCommand", "showModal", "showPicker", "show", "close",
    "open", "write", "writeln", "assign", "reload", "pushState", "replaceState", "postMessage", "setProperty",
    "removeProperty", "defineProperty", "defineProperties", "setPrototypeOf", "call", "apply", "bind",
    "Reflect", "eval", "Function", "setTimeout", "setInterval", "requestAnimationFrame", "queueMicrotask",
    "fetch", "XMLHttpRequest", "sendBeacon", "attachShadow", "adoptNode", "importNode", "cloneNode",
    "createElement", "createRange", "getSelection", "removeAllRanges", "addRange", "collapse", "extend",
    "selectNodeContents", "deleteContents", "insertNode", "normalize", "requestPointerLock", "exitPointerLock",
    "requestFullscreen", "setPointerCapture", "releasePointerCapture", "animate", "play", "pause", "load",
    "innerHTML", "outerHTML",
})
#: every occurrence of an acting name in each function's text, and what it is
NAMED = {
    "pinned": {"dispatchEvent": 1,  # the one dispatch
               "focus": 2,  # ``typeof focusable.focus === 'function'`` and the one focus
               "click": 1,  # the event's type, a string
               "select": 1},  # in the selector of focusable elements, a string
    "DOM_FILMED_INSERT": {"execCommand": 1,  # the one insertion
                          "reset": 1, "submit": 1},  # input types that are not editable, strings
    "DOM_NODE_LOCATE": {"focus": 1},  # the key of the block's own report of the document's focus
    "DOM_NODE_CONNECTED_CHECK": {},
    "DOM_CLICK_READBACK": {},
}


def _calls(text: str) -> Counter:
    return Counter(re.findall(r"\.\s*([A-Za-z_$][\w$]*)\s*\(", text))


def _audit(text: str, reads: set, acts: dict, named: dict) -> list[str]:
    """What is wrong with a function's text, if anything. It is a check of the text and not a parser:
    it finds a method call written as one, any occurrence at all of the name of a method that acts, an
    assignment to a member written with a dot or with a bracket, an increment or a delete of one, and
    the call forms that hide a name (a computed member, a parenthesised callee, an optional call, a
    template). It does not follow values, and a member reached some other way is not seen."""
    wrong = []
    calls = _calls(text)
    if set(calls) != reads | set(acts):
        wrong.append(f"calls not classified: {sorted(set(calls) ^ (reads | set(acts)))}")
    for method, statement in acts.items():
        if calls[method] != 1 or statement not in text:
            wrong.append(f"{method} is not made once in the statement that checks its receiver")
    names = Counter(re.findall(r"[A-Za-z_$][\w$]*", text))
    for name in sorted(ACTING):
        if names[name] != named.get(name, 0):
            wrong.append(f"{name} occurs {names[name]} times, accounted for {named.get(name, 0)}")
    assigned = r"\s*(?:(?:[-+*/%|&^]|\*\*|<<|>>>?|&&|\|\||\?\?)?=(?![=>])|\+\+|--)"
    if re.search(r"\.\s*[A-Za-z_$][\w$]*" + assigned, text) or re.search(r"\]" + assigned, text):
        wrong.append("a member is assigned or incremented")
    if re.search(r"(?:\+\+|--)\s*[A-Za-z_$][\w$.]*[.\[]", text) or re.search(r"\bdelete\b", text):
        wrong.append("a member is incremented or deleted")
    for form, what in ((r"\]\s*\(", "a computed member is called"), (r"\)\s*\(", "a parenthesised callee is called"),
                       (r"\?\.\s*\(", "an optional call"), (r"`", "a template")):
        if re.search(form, text):
            wrong.append(what)
    return wrong


@pytest.mark.parametrize(("name", "reads", "acts"), FUNCTIONS, ids=[name for name, _, _ in FUNCTIONS])
def test_every_call_the_functions_make_is_a_read_or_a_checked_act(sources, name, reads, acts):
    """Sol round 9: the events were checked in the one function that sends them and the focus was a
    second path beside it. This reads the function instead of trusting a list of what it does: every
    method call in its text is one named above, each acting call is made once, in the statement that
    checks its receiver, the name of a method that acts occurs nowhere else, and nothing is done to
    the page by assignment or by a call form that hides what is called."""
    text = sources[name]
    assert _audit(text, reads, acts, NAMED[name]) == []
    # the insert makes all its checks before its one act
    if name == "DOM_FILMED_INSERT":
        act = text.index("doc.execCommand(")
        refusals = [m.start() for m in re.finditer(r"return \{ inserted: false, why: '(\w+)' \}", text)]
        assert len(refusals) == 5 and all(at < act for at in refusals)


@pytest.mark.parametrize("added", [
    "(el.parentElement.focus)();",  # Sol round 10: a parenthesised member passes a count of ``.focus(``
    "el.parentElement['focus'] ();",  # Sol round 10: a quoted name, and a space before the call
    "el.parentElement?.focus?.();",
    "const give = el.parentElement.focus; give.call(el.parentElement);",
    "Reflect.apply(el.focus, el.parentElement, []);",
    "el.parentElement.blur();",
    "el.parentElement.click();",
    "el.parentElement.dispatchEvent(new view.MouseEvent('click', base));",
    "el.parentElement[`fo${'cus'}`]();",
    "el.parentElement.tabIndex = 0;",
    "el.parentElement['textContent'] = '';",  # Sol check 11: an assignment through a quoted name
    "el.parentElement.tabIndex++;",
    "++el.parentElement.tabIndex;",
    "el.parentElement.scrollTop += 40;",
    "el.parentElement['scrollTop'] ||= 40;",
    "delete el.parentElement.dataset.state;",
    "view.setTimeout(() => {}, 0);",
])
def test_the_audit_fails_on_an_act_added_any_of_these_ways(sources, added):
    """The audit is only worth what it catches. Each line here does something to the page from inside
    the click sequence without the check; the pinned text passes and the text with the line fails."""
    text = sources["pinned"]
    assert _audit(text, CLICK_READS, CLICK_ACTS, NAMED["pinned"]) == []
    at = text.index("const DETACHED = {}, LEFT = {};")
    assert _audit(text[:at] + added + " " + text[at:], CLICK_READS, CLICK_ACTS, NAMED["pinned"]) != []


def test_these_are_the_functions_a_filmed_action_runs(sources):
    """The audit above is of five functions by name. This reads tools.rs for every function text it
    declares and requires each to be audited here or named as one the filmed routes do not pass, and
    every function the file passes to the page to be one of those constants (or the one variable that
    carries the locate read and the connected check).

    What this does not establish: that nothing else in the driver sends script to the page during a
    filmed action. Other modules do send script (the binding's and the snapshot's probes, dialog
    handling, the cursor overlay, downloads), and whether a filmed click reaches them is the driver's
    own mock-CDP test's subject (``filmed_click_runs_wholly_in_the_isolated_world_and_scrolls_nothing``
    holds every function call of a filmed click to isolated-world objects), not this test's."""
    defined = set(re.findall(r'const (\w+): &str = r?#?"function', sources["rust"]))
    audited = {"DOM_EVENT_CLICK_SEQUENCE" if name == "pinned" else name for name, _, _ in FUNCTIONS}
    unfilmed_only = {"EDITABLE_AND_FOCUSED_CHECK", "FOCUS_EMULATION_READY_CHECK", "SELECT_ALL_IN_ELEMENT",
                     "SELECT_NATIVE_OPTION"}
    assert defined == audited | unfilmed_only, sorted(defined ^ (audited | unfilmed_only))
    passed = set(re.findall(r'"functionDeclaration":\s*(\w+)', sources["rust"]))
    assert passed == (defined - {"DOM_NODE_LOCATE"}) | {"declaration"}, sorted(passed)
    assert "Runtime.evaluate" not in sources["rust"]
    rust = sources["rust"]
    # the filmed insert returns from its own branch before the unfilmed route's focus, selection and
    # focus emulation; and filmed_point is refused with any mode that would need them
    branch = rust[rust.index("if let Some((x, y)) = filmed_point {", rust.index("DOM_FILMED_INSERT: &str")):]
    assert branch.index('"functionDeclaration": DOM_FILMED_INSERT') < branch.index("EDITABLE_AND_FOCUSED_CHECK")
    assert 'if filmed_point.is_some() && (mode != "insert_text" || replace)' in rust
