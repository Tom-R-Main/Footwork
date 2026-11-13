"""The filmed click's invariant, over every boundary of the sequence (FP44).

The invariant (``vendor/cua-driver/PROVENANCE.md``, "Filmed delivery"): every event the sequence
dispatches, and the focus it gives, goes to an element that is under the pointer in the same turn,
immediately before. Three reviews each found one more place between two events where it did not hold,
so this file does not list cases: it builds every cell of

    boundary     before the first event, after each event the sequence sends, and after the focus
  x disturbance  what a page listener does there (``DISTURBANCES``)
  x start        the pointer is on the control itself, or on a child of it
  x press        ordinary, or a ``pointerdown`` the page cancels (no mouse events follow)

and makes three assertions in each, on the click sequence taken from the pinned driver archive and run
in Node on a stand-in page:

1. the receipt and the events are what ``oracle`` gives, a second statement of the rule written here
   from the provenance record's two tables and sharing no code with the driver;
2. independently of the oracle, the stand-in page itself saw no event, and no focus, go to an element
   it did not have under the pointer at that moment;
3. without a point, the same cell sends exactly what the sequence sent before the step that added the
   point (the pinned source with the step's patch taken back out).

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
  // the page's own answer, by its state and none of the function's code
  const underPointer = (receiver, withinNode) => {
    const [left, top, width, height] = page.rect;
    const hit = hits[page.hit] || null;
    return page.connected && px >= left && px <= left + width && py >= top && py <= top + height
      && !!hit && holds(node, hit) && shown() && holds(receiver, hit) && (!withinNode || holds(node, receiver));
  };
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
        sent.push({ type: event.type, to: name, under: spec.filmed ? underPointer(el, true) : null,
                    at: [event.clientX, event.clientY] });
        if (spec.at === dispatched) change();
        return !(spec.cancel && event.type === 'pointerdown');
      },
      // the control is a button: the press focuses it, whichever part of it was pressed
      closest: () => node,
      focus: () => {
        sent.push({ type: 'focus()', to: name, under: spec.filmed ? underPointer(el, false) : null });
        if (spec.at === 'focus') change();
      },
    };
    return el;
  };
  node = make('target', null);
  Object.assign(hits, { target: node, icon: make('icon', node), label: make('label', node), other: make('other', null) });
  doc.elementFromPoint = () => hits[page.hit] || null;
  const receipt = fn.apply(node, spec.filmed ? spec.point : []);
  return { receipt, sent };
};
process.stdout.write(JSON.stringify(input.cases.map((spec) => run(input.sources[spec.source], spec))));
"""


def _literal(source: str) -> str:
    literal = re.search(r'const DOM_EVENT_CLICK_SEQUENCE: &str = "(.*?)";\n', source, re.DOTALL)
    assert literal, "the click sequence is not in tools.rs"
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
    return {"pinned": _literal(pinned.decode()), "before": _literal(before.decode())}


# ---- the oracle: the rule again, from the provenance record's tables


class _Left(Exception):
    pass


class _Detached(Exception):
    pass


def oracle(start: str, at, then: dict, cancel: bool) -> tuple[dict, list[tuple[str, str]]]:
    """The receipt and the (event, receiver) list of a filmed click on the stand-in page."""
    page = {"rect": RECT, "hit": start, "connected": True, "cursor": "pointer", "lock": False, "gone": []}
    sent: list[tuple[str, str]] = []
    told = {"count": 0, "last": "", "hidden": False}

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
        if not cancel:
            send("mousedown", down)  # the pair is not split
            under(down)
            sent.append(("focus()", "target"))
            if at == "focus":
                page.update(then)
        up = under("target")  # a fresh hit at the release
        send("pointerup", up)
        if not cancel:
            send("mouseup", up)
        # the nearest ancestor holding both; the control itself when the pressed child has left it
        send("click", down if down == up and holds("target", down) else "target")
    except _Detached:
        return receipt(stopped="detached"), sent
    except _Left:
        return receipt(stopped="left_pointer", hidden=told["hidden"]), sent
    return {"complete": True, "stopped": None, "count": told["count"], "last": told["last"], "retargeted": False}, sent


def _cells() -> list[dict]:
    cells = []
    for start, cancel in itertools.product(STARTS, (False, True)):
        events = 9 if cancel else 11
        boundaries = [*range(events + 1), *([] if cancel else ["focus"])]
        for at, (name, then) in itertools.product(boundaries, DISTURBANCES.items()):
            if name == "child_removed" and start != "icon":
                continue  # there is no receiving child to remove
            cells.append({"start": start, "cancel": cancel, "at": at, "name": name, "then": then, "point": POINT})
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
        cell["id"] = f"{cell['start']}{'/cancelled' if cell['cancel'] else ''} {cell['name']} at {cell['at']}"
    return cells


def _pairs(run: dict) -> list[tuple[str, str]]:
    return [(e["type"], e["to"]) for e in run["sent"]]


def test_the_matrix_covers_every_boundary_and_every_disturbance(matrix):
    assert len(matrix) == 2 * (13 + 10) * len(DISTURBANCES) - (13 + 10)  # child_removed needs a child
    assert {cell["at"] for cell in matrix} == {*range(12), "focus"}
    assert {cell["name"] for cell in matrix} == set(DISTURBANCES)


def test_every_cell_is_what_the_rule_gives(matrix):
    """(1): the receipt and the events of the pinned function against the oracle's."""
    wrong = []
    for cell in matrix:
        receipt, sent = oracle(cell["start"], cell["at"], cell["then"], cell["cancel"])
        if cell["filmed"]["receipt"] != receipt or _pairs(cell["filmed"]) != sent:
            wrong.append((cell["id"], cell["filmed"]["receipt"], receipt, _pairs(cell["filmed"])[6:], sent[6:]))
    assert not wrong, f"{len(wrong)} of {len(matrix)} cells differ; first: {wrong[0]}"


def test_no_event_and_no_focus_goes_to_an_element_that_is_not_under_the_pointer(matrix):
    """(2): the invariant itself, by the stand-in page's own state and not the oracle's."""
    off = [(cell["id"], e["type"], e["to"]) for cell in matrix for e in cell["filmed"]["sent"] if e["under"] is not True]
    assert not off, f"{len(off)} events off the pointer; first: {off[0]}"
    # and every event is at the point
    assert {tuple(e["at"]) for cell in matrix for e in cell["filmed"]["sent"] if "at" in e} == {tuple(POINT)}


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


def _cell(matrix, start, name, at, cancel=False) -> dict:
    return next(c for c in matrix if (c["start"], c["name"], c["at"], c["cancel"]) == (start, name, at, cancel))


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


def test_the_dispatch_function_is_the_only_place_an_event_is_sent(sources):
    """The check cannot be bypassed by a dispatch written somewhere else in the sequence."""
    pinned = sources["pinned"]
    assert pinned.count(".dispatchEvent(") == 1
    send = "const send = (type, event) => { if (filmed) under(target); else live(); const kept = target.dispatchEvent(event);"
    assert send in pinned
    # and the focus is given straight after the same check
    assert re.search(r"if \(filmed\) under\(target\); else live\(\); const focusable = target\.closest\(", pinned)
