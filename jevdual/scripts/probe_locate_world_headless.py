"""Headless check for notebook predictions FP22, FP27, FP30, FP36, FP45 and FP47: what the driver's locate page function reports
in a real Chrome, read in the page's own script world and in an isolated world, and whether its two
filmed delivery functions act on a real page from the isolated world.

No window, no pointer, no Footwork session and no driver: a headless Chrome on a temporary profile and
a port it chooses itself, started and ended by this script, which removes the profile afterwards. It
serves the filmed page pointer fixture, then repeats over CDP the calls the driver's locate makes
(``Page.getFrameTree``, ``Page.createIsolatedWorld``, ``DOM.resolveNode`` into that world,
``Runtime.callFunctionOn`` with the function text taken from the pinned source archive) for each control
of the fixture, and makes the same read on the page's own object for comparison.

It answers what the mock CDP and the Node stand-ins cannot: whether Chrome's isolated world is out of
reach of a page that replaced ``elementFromPoint`` or ``getBoundingClientRect``, and whether the
function decides the fixture's clip, transform and focus cases on Chrome's own computed styles. It says
nothing about the screen: device pixel ratio, the pointer, which part of the browser holds the keyboard
in a window, and the driver's own binding are the live probe's (FP28).

For FP27 it then loads a second page (``DELIVERY``) that has replaced ``getBoundingClientRect`` with a
wrapper that moves a button 300 px when it is called on it (the sixth review's counterexample) and
counts every call of the methods it replaced. On that page it runs, with the text and the arguments
the driver uses: the filmed click on the button from the isolated world, at its centre; the same click
after the button has been moved away; the filmed click on a second button that moves itself 300 px when
a pointer comes over it (FP30); on a button that moves on mousedown, on a container whose two children
swap when hovered, and on buttons whose cursor is none or an image (FP36); on a container whose top
child leaves when released (FP45); on two buttons inside a shadow root, one of them covered by an
element outside it (FP47); on a control inside a focusable container, and on a node that holds a
focusable button (FP55, after the inserts), and the insert into an editable region whose selection a
script has put elsewhere (FP56); the filmed insert into a focused field with the point off it, into a
field without focus, and into the focused field at its centre; and last, as controls that the two
counterexamples are real, the click sequence without a point on the page's own object, which is what
the driver did before the filmed delivery, on each button.

Run from ``jevdual/``::

    PYTHONPATH=python .venv/bin/python scripts/probe_locate_world_headless.py --out /abs/fresh/out/dir
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import itertools
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_filmed_page_pointer
import probe_page_effects
from probe_browser_holder import _front_pid

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TOOLS = "libs/cua-driver/rust/crates/cua-driver-core/src/browser/tools.rs"
WORLD = "cua-driver-locate"
CONTROLS = ("alpha", "beta", "covered", "forged", "edge", "clipped", "turned", "note", "gamma")
#: in the page's own world, after the fixture's reads: every rectangle is a lie
REPLACE_RECT = ("Element.prototype.getBoundingClientRect = () => "
                "({left: 0, top: 0, width: 10, height: 10, right: 10, bottom: 10, x: 0, y: 0})")


def function_text(name: str = "DOM_NODE_LOCATE") -> str:
    """One page function as JavaScript, from the pinned archive's tools.rs."""
    with tarfile.open(ROOT / "vendor/cua-driver/native-source.tar.gz") as archive:
        source = archive.extractfile(TOOLS).read().decode()
    literal = re.search(rf'const {name}: &str = "(.*?)";\n', source, re.DOTALL)
    if literal is None:
        raise SystemExit(f"{name} is not in the pinned tools.rs")
    # the literals use a line continuation and, in the click sequence, an escaped double quote
    return re.sub(r"\\\n\s*", "", literal.group(1)).replace('\\"', '"')


#: the second page (FP27). It replaces four methods in its own world and counts their calls; the
#: rectangle wrapper moves Mover 300 px down whenever it is called on it. Its capturing listeners record
#: what reached the page without calling any of the four.
DELIVERY = """<!doctype html>
<meta charset="utf-8">
<title>Footwork filmed delivery fixture</title>
<body style="font: 16px system-ui; margin: 0">
<button type="button" id="mover" style="position: absolute; left: 40px; top: 60px; width: 140px; height: 44px">Mover</button>
<button type="button" id="shy" style="position: absolute; left: 40px; top: 160px; width: 140px; height: 44px">Shy</button>
<button type="button" id="dodge" style="position: absolute; left: 40px; top: 260px; width: 140px; height: 44px">Dodge</button>
<div id="pair" role="button" style="position: absolute; left: 300px; top: 260px; width: 140px; height: 44px">
  <span id="second" style="position: absolute; left: 0; top: 0; width: 140px; height: 44px; background: #cde">Second</span>
  <span id="first" style="position: absolute; left: 0; top: 0; width: 140px; height: 44px; background: #edc">First</span>
</div>
<div id="late" role="button" style="position: absolute; left: 300px; top: 360px; width: 140px; height: 44px">
  <span id="beneath" style="position: absolute; left: 0; top: 0; width: 140px; height: 44px; background: #cde">Beneath</span>
  <span id="above" style="position: absolute; left: 0; top: 0; width: 140px; height: 44px; background: #edc">Above</span>
</div>
<div id="host" style="position: absolute; left: 560px; top: 260px; width: 200px; height: 120px"></div>
<div id="row" tabindex="0" style="position: absolute; left: 800px; top: 60px; width: 300px; height: 60px">
  <div id="inrow" role="button" style="position: absolute; left: 10px; top: 8px; width: 140px; height: 44px">In row</div>
</div>
<div id="eda" contenteditable="true" style="position: absolute; left: 800px; top: 260px; width: 300px; height: 40px">one</div>
<div id="edb" contenteditable="true" style="position: absolute; left: 800px; top: 320px; width: 300px; height: 40px">two</div>
<p id="plaintext" style="position: absolute; left: 800px; top: 380px; width: 300px; height: 30px; margin: 0">plain</p>
<div id="group" style="position: absolute; left: 800px; top: 160px; width: 300px; height: 60px">
  <button type="button" id="ingroup" style="position: absolute; left: 10px; top: 8px; width: 140px; height: 44px">In group</button>
</div>
<div id="veil" style="position: absolute; left: 600px; top: 325px; width: 60px; height: 34px; background: #c33"></div>
<button type="button" id="ghost" style="position: absolute; left: 560px; top: 60px; width: 140px; height: 44px; cursor: none">Ghost</button>
<button type="button" id="drawn" style="position: absolute; left: 560px; top: 160px; width: 140px; height: 44px; cursor: url('data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=='), auto">Drawn</button>
<input type="text" id="field" style="position: absolute; left: 300px; top: 60px; width: 140px; height: 30px; box-sizing: border-box">
<input type="text" id="other" style="position: absolute; left: 300px; top: 160px; width: 140px; height: 30px; box-sizing: border-box">
<script>
const log = window.__log = {rect_calls: 0, hit_calls: 0, dispatch_calls: 0, command_calls: 0, events: []};
const mover = document.getElementById('mover');
const nativeRect = Element.prototype.getBoundingClientRect;
Element.prototype.getBoundingClientRect = function () {
  log.rect_calls += 1;
  if (this === mover) mover.style.top = '360px';
  return nativeRect.call(this);
};
const nativeHit = Document.prototype.elementFromPoint;
Document.prototype.elementFromPoint = function (x, y) { log.hit_calls += 1; return nativeHit.call(this, x, y); };
const nativeDispatch = EventTarget.prototype.dispatchEvent;
EventTarget.prototype.dispatchEvent = function (e) { log.dispatch_calls += 1; return nativeDispatch.call(this, e); };
const nativeCommand = Document.prototype.execCommand;
Document.prototype.execCommand = function (...a) { log.command_calls += 1; return nativeCommand.apply(this, a); };
// Shy moves away whenever a pointer comes over it
const shy = document.getElementById('shy');
shy.addEventListener('pointerover', () => { shy.style.top = '460px'; });
// Dodge moves away when it is pressed
const dodge = document.getElementById('dodge');
dodge.addEventListener('mousedown', () => { dodge.style.top = '560px'; });
// Pair keeps its place; when hovered its top child shrinks to the right quarter and bares the other
const first = document.getElementById('first');
document.getElementById('pair').addEventListener('pointerover', () => { first.style.left = '105px'; first.style.width = '35px'; });
// two buttons inside a shadow root; the veil, which is outside it, covers the centre of the second
const shadow = document.getElementById('host').attachShadow({mode: 'open'});
shadow.innerHTML = '<button type="button" id="plain" style="position: absolute; left: 0; top: 0; width: 140px; height: 44px">Plain</button>'
  + '<button type="button" id="veiled" style="position: absolute; left: 0; top: 60px; width: 140px; height: 44px">Veiled</button>';
// Late keeps its place too; its top child leaves when the release reaches it, after the press and the
// release went to that child
const above = document.getElementById('above');
document.getElementById('late').addEventListener('mouseup', () => { above.style.left = '105px'; above.style.width = '35px'; });
for (const type of ['pointerover', 'pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'])
  shadow.addEventListener(type, (e) => log.events.push({type, target: e.target.id, trusted: e.isTrusted,
    x: e.clientX, y: e.clientY, top: e.target.style.top, data: null}), true);
for (const type of ['pointerover', 'pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click', 'beforeinput', 'input'])
  document.addEventListener(type, (e) => e.target.id === 'host' ? null : log.events.push({type, target: e.target.id, trusted: e.isTrusted,
    x: 'clientX' in e ? e.clientX : null, y: 'clientY' in e ? e.clientY : null,
    top: e.target.style.top, data: 'data' in e ? e.data : null}), true);
</script>
"""
MOVER_CENTRE = (110.0, 82.0)  # of (40, 60, 140, 44)
SHY_CENTRE = (110.0, 182.0)  # of (40, 160, 140, 44)
DODGE_CENTRE = (110.0, 282.0)  # of (40, 260, 140, 44)
PAIR_CENTRE = (370.0, 282.0)  # of (300, 260, 140, 44): on First before the hover, on Second after it
LATE_CENTRE = (370.0, 382.0)  # of (300, 360, 140, 44): on Above until the release, on Beneath after it
PLAIN_CENTRE = (630.0, 282.0)  # of (560, 260, 140, 44), inside the shadow root
VEILED_CENTRE = (630.0, 342.0)  # of (560, 320, 140, 44); the veil (600, 325, 60, 34) covers it
INROW_CENTRE = (880.0, 90.0)  # of (810, 68, 140, 44): a control that is not focusable, in a row that is
EDA_CENTRE = (950.0, 280.0)  # of (800, 260, 300, 40): an editable region
INGROUP_CENTRE = (880.0, 190.0)  # of (810, 168, 140, 44): a button, inside the group that is the ref's node
GHOST_CENTRE = (630.0, 82.0)
DRAWN_CENTRE = (630.0, 182.0)
PRESS = ("pointerdown", "mousedown", "mouseup", "click")
WHOLE = ("pointerover", "pointerdown", "mousedown", "pointerup", "mouseup", "click")  # what the page logs of a click
FIELD_CENTRE = (370.0, 75.0)  # of (300, 60, 140, 30)
OTHER_CENTRE = (370.0, 175.0)
INSERTED = "footwork"


class Cdp:
    def __init__(self, socket) -> None:
        self.socket, self.ids, self.session = socket, itertools.count(1), None

    async def call(self, method: str, params: dict | None = None, *, browser: bool = False) -> dict:
        message = {"id": next(self.ids), "method": method, "params": params or {}}
        if self.session and not browser:
            message["sessionId"] = self.session
        await self.socket.send(json.dumps(message))
        while True:
            reply = json.loads(await asyncio.wait_for(self.socket.recv(), timeout=20))
            if reply.get("id") == message["id"]:
                if "error" in reply:
                    raise RuntimeError(f"{method}: {reply['error'].get('message')}")
                return reply["result"]


async def read(cdp: Cdp, source: str, object_id: str, *arguments) -> dict:
    reply = await cdp.call("Runtime.callFunctionOn", {"objectId": object_id, "functionDeclaration": source,
                                                      "arguments": [{"value": value} for value in arguments],
                                                      "returnByValue": True})
    if "exceptionDetails" in reply:
        return {"exception": reply["exceptionDetails"].get("text"),
                "description": (reply["exceptionDetails"].get("exception") or {}).get("description")}
    return reply["result"].get("value")


async def _open(cdp: Cdp, url: str) -> tuple[str, int]:
    """A new tab on ``url``, attached and loaded, and the isolated world of its main frame."""
    cdp.session = None
    target = (await cdp.call("Target.createTarget", {"url": url}, browser=True))["targetId"]
    cdp.session = (await cdp.call("Target.attachToTarget", {"targetId": target, "flatten": True},
                                  browser=True))["sessionId"]
    await cdp.call("Page.enable")
    for _ in range(100):
        state = await cdp.call("Runtime.evaluate", {"expression": "document.readyState", "returnByValue": True})
        if state["result"].get("value") == "complete":
            break
        await asyncio.sleep(0.1)
    frame = (await cdp.call("Page.getFrameTree"))["frameTree"]["frame"]["id"]
    world = (await cdp.call("Page.createIsolatedWorld", {"frameId": frame, "worldName": WORLD}))["executionContextId"]
    return target, world


async def deliver(cdp: Cdp, url: str) -> dict:
    """FP27: the two filmed delivery functions, run as the driver runs them, on the ``DELIVERY`` page."""
    click, insert = function_text("DOM_EVENT_CLICK_SEQUENCE"), function_text("DOM_FILMED_INSERT")
    rect = "function() { const r = this.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }"
    target, world = await _open(cdp, url)

    async def page(expression: str):
        reply = await cdp.call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
        return reply["result"].get("value")

    async def objects(control: str, within: str = "document") -> tuple[str, str]:
        mine = (await cdp.call("Runtime.evaluate", {"expression": f"{within}.getElementById('{control}')"}))["result"]["objectId"]
        backend = (await cdp.call("DOM.describeNode", {"objectId": mine}))["node"]["backendNodeId"]
        isolated = (await cdp.call("DOM.resolveNode", {"backendNodeId": backend, "executionContextId": world}))["object"]["objectId"]
        return mine, isolated

    async def state() -> dict:
        return await page("({...window.__log, events: window.__log.events.slice(), mover_top: mover.style.top, "
                          "shy_top: shy.style.top, dodge_top: dodge.style.top, first_left: first.style.left, "
                          "above_left: above.style.left, "
                          "field: document.getElementById('field').value, other: document.getElementById('other').value, "
                          "active: document.activeElement && document.activeElement.id, page_focused: document.hasFocus()})")

    out: dict = {"click_sha256": hashlib.sha256(click.encode()).hexdigest(),
                 "insert_sha256": hashlib.sha256(insert.encode()).hexdigest(), "loaded": await state()}
    mover_page, mover = await objects("mover")
    out["mover_rect_isolated"] = await read(cdp, rect, mover)
    # 1: the filmed click, as the driver sends it, at the button's centre
    out["click"] = {"receipt": await read(cdp, click, mover, *MOVER_CENTRE), "after": await state(),
                    "mover_rect_isolated": await read(cdp, rect, mover)}
    # 2: the button is somewhere else now (moved by the page, not through its wrapper): nothing may be sent
    await page("mover.style.top = '360px'")
    out["click_after_move"] = {"receipt": await read(cdp, click, mover, *MOVER_CENTRE), "after": await state()}
    # 2b (FP30): a button that moves away when a pointer comes over it. The sequence's own hover events
    # run that listener; the press must not follow.
    shy_page, shy = await objects("shy")
    out["shy_click"] = {"receipt": await read(cdp, click, shy, *SHY_CENTRE), "after": await state()}
    # 2c (FP36): pressed, it moves away: the press goes, the release and the click must not
    dodge_page, dodge = await objects("dodge")
    out["dodge_click"] = {"receipt": await read(cdp, click, dodge, *DODGE_CENTRE), "after": await state()}
    # 2d: its top child leaves the point at the click's first hover event: nothing more is sent
    pair_page, pair = await objects("pair")
    out["pair_click"] = {"receipt": await read(cdp, click, pair, *PAIR_CENTRE), "after": await state()}
    # 2d' (FP45): its top child, pressed and released, leaves at the release: no click event
    late_page, late = await objects("late")
    out["late_click"] = {"receipt": await read(cdp, click, late, *LATE_CENTRE), "after": await state()}
    # 2d'' (FP47): inside a shadow root, one button in the open and one that an element outside the
    # shadow tree covers: what the hit test of the node's own root says, and what the click does
    locate = function_text()
    out["shadow"] = {}
    for control, centre in (("plain", PLAIN_CENTRE), ("veiled", VEILED_CENTRE)):
        _, isolated = await objects(control, "document.getElementById('host').shadowRoot")
        located = await read(cdp, locate, isolated, *centre)
        before = await state()
        out["shadow"][control] = {"locate": located, "receipt": await read(cdp, click, isolated, *centre),
                                  "events": (await state())["events"][len(before["events"]):]}
    out["shadow"]["after"] = await state()
    # 2e, 2f: the page hides the pointer, or replaces it with an image: nothing may be sent
    out["cursors"] = {}
    for control in ("mover", "field", "ghost", "drawn"):
        _, isolated = await objects(control)
        out["cursors"][control] = (await read(cdp, locate, isolated) or {}).get("cursor")
    ghost_page, ghost = await objects("ghost")
    out["ghost_click"] = {"receipt": await read(cdp, click, ghost, *GHOST_CENTRE), "after": await state()}
    _, drawn = await objects("drawn")
    out["drawn_click"] = {"receipt": await read(cdp, click, drawn, *DRAWN_CENTRE), "after": await state()}
    # 3: the filmed insert. The field is focused by the page; first with the point off it, ...
    await page("mover.style.top = '60px'; shy.style.top = '160px'; dodge.style.top = '260px'; "
               "first.style.left = '0'; first.style.width = '140px'; above.style.left = '0'; "
               "above.style.width = '140px'; document.getElementById('field').focus()")
    _, field = await objects("field")
    _, other = await objects("other")
    out["insert_off_point"] = {"receipt": await read(cdp, insert, field, 10.0, 10.0, INSERTED), "after": await state()}
    # ... then into the field that does not have focus, at its own centre, ...
    out["insert_unfocused"] = {"receipt": await read(cdp, insert, other, *OTHER_CENTRE, INSERTED), "after": await state()}
    # ... then into the focused field at its centre
    out["insert"] = {"receipt": await read(cdp, insert, field, *FIELD_CENTRE, INSERTED), "after": await state()}
    # 3b (FP55): where the press's focus goes. A control that is not focusable, inside a row that is: a
    # press would focus the row, which the ref does not name. Then a node that holds a button, with the
    # point on the button: the button is inside the node and is focused.
    inrow_page, inrow = await objects("inrow")
    before = await state()
    out["inrow_click"] = {"before": before, "receipt": await read(cdp, click, inrow, *INROW_CENTRE), "after": await state()}
    _, group = await objects("group")
    before = await state()
    out["group_click"] = {"before": before, "receipt": await read(cdp, click, group, *INGROUP_CENTRE), "after": await state()}
    # 3c (FP56): the insert goes where the selection is. An editable region, focused, with its caret
    # in it; then the selection put inside another region; then in text that cannot be edited. Each
    # time the insert is asked for on the first region, with the point on it.
    _, eda = await objects("eda")

    async def regions() -> dict:
        return await page("({eda: eda.textContent, edb: edb.textContent, plain: plaintext.textContent, "
                          "active: document.activeElement && document.activeElement.id, "
                          "anchor: (() => { const n = getSelection().anchorNode; "
                          "return n && (n.id || (n.parentElement && n.parentElement.id)); })()})")

    out["editable"] = {}
    for name, arrange in (
            ("plain", "eda.focus(); getSelection().collapse(eda.firstChild, 3)"),
            ("selection_in_another_region", "eda.focus(); getSelection().collapse(edb.firstChild, 3)"),
            ("selection_in_plain_text", "eda.focus(); getSelection().collapse(plaintext.firstChild, 2)")):
        await page("eda.textContent = 'one'; edb.textContent = 'two'; " + arrange)
        before = await regions()
        out["editable"][name] = {"before": before, "receipt": await read(cdp, insert, eda, *EDA_CENTRE, INSERTED),
                                 "after": await regions()}
    # 4: the control. Without a point, on the page's own object, as the driver clicked before the filmed delivery:
    # the page's wrapper answers the sequence's rectangle read and moves the button under it.
    out["page_world_click"] = {"before": await state(), "receipt": await read(cdp, click, mover_page),
                               "after": await state()}
    # and on the button that moves when hovered: without the check before the press it is pressed anyway
    out["page_world_shy_click"] = {"before": await state(), "receipt": await read(cdp, click, shy_page),
                                   "after": await state()}
    # FP36's controls: each of these the sequence without a point still clicks
    for name, mine in (("dodge", dodge_page), ("pair", pair_page), ("late", late_page), ("ghost", ghost_page),
                       ("inrow", inrow_page)):
        out[f"page_world_{name}_click"] = {"before": await state(), "receipt": await read(cdp, click, mine),
                                           "after": await state()}
    await cdp.call("Target.closeTarget", {"targetId": target}, browser=True)
    return out


def delivery_verdict(found: dict) -> dict:
    """Each expectation of FP27 against what the page recorded; ``held`` only when every one holds."""
    def events(step: str, since: str | None = None) -> list[dict]:
        seen = found[step]["after"]["events"]
        return seen[len(found[since]["after"]["events"]) if since else 0:]

    def untouched(step: str) -> bool:
        after = found[step]["after"]
        return (after["rect_calls"], after["hit_calls"], after["dispatch_calls"], after["command_calls"]) == (0, 0, 0, 0)

    clicked = events("click")
    presses = [e for e in clicked if e["type"] in PRESS]
    hovered = events("shy_click", "click_after_move")
    shy_control = found["page_world_shy_click"]
    shy_control_events = shy_control["after"]["events"][len(shy_control["before"]["events"]):]
    typed = events("insert", "insert_unfocused")
    control = found["page_world_click"]
    control_clicks = [e for e in control["after"]["events"][len(control["before"]["events"]):] if e["type"] == "click"]
    nothing = {"complete": False, "stopped": "not_under_pointer", "count": 0, "last": "", "retargeted": False,
               "hidden": False}
    from jevdual.browser_driver import pointer_shown

    def seen(step: str, since: str) -> list[tuple[str, str]]:
        return [(e["type"], e["target"]) for e in events(step, since)]

    def control_seen(name: str) -> list[tuple[str, str]]:
        run = found[f"page_world_{name}_click"]
        return [(e["type"], e["target"]) for e in run["after"]["events"][len(run["before"]["events"]):]]

    def during(step: str) -> list[tuple[str, str]]:
        run = found[step]
        return [(e["type"], e["target"]) for e in run["after"]["events"][len(run["before"]["events"]):]]

    cursors = found["cursors"]
    shadow = found["shadow"]
    inrow, group = found["inrow_click"], found["group_click"]
    editable = found["editable"]

    def unchanged(name: str) -> bool:
        after = editable[name]["after"]
        return (after["eda"], after["edb"], after["plain"]) == ("one", "two", "plain")
    done = {"complete": True, "stopped": None, "count": 11, "last": "click", "retargeted": False}
    checks = {
        "the page's wrappers were in place and unused at load": found["loaded"]["rect_calls"] == 0,
        "the filmed click completed": (found["click"]["receipt"] or {}).get("complete") is True,
        "it ran the page's click listener once, on the button": [e["target"] for e in clicked if e["type"] == "click"] == ["mover"],
        "its press and click carried the point": bool(presses) and all((e["x"], e["y"]) == MOVER_CENTRE for e in presses),
        "the button did not move": (found["click"]["after"]["mover_top"] == "60px"
                                    and found["click"]["mover_rect_isolated"] == found["mover_rect_isolated"] == [40, 60, 140, 44]),
        "no method the page replaced was called by the click": untouched("click"),
        "after the move the click sent nothing": (found["click_after_move"]["receipt"] == nothing
                                                  and not events("click_after_move", "click")
                                                  and untouched("click_after_move")),
        # FP30
        "the click on the button that moves when hovered stopped before the press": (
            found["shy_click"]["receipt"] == {"complete": False, "stopped": "left_pointer", "count": 1,
                                              "last": "pointerover", "retargeted": False, "hidden": False}),
        "it reached the page as hover events only, and the button had moved": (
            [(e["type"], e["target"]) for e in hovered] == [("pointerover", "shy")]
            and found["shy_click"]["after"]["shy_top"] == "460px" and untouched("shy_click")),
        # FP36
        "the button that moves when pressed was pressed and not released or clicked": (
            found["dodge_click"]["receipt"] == {"complete": False, "stopped": "left_pointer", "count": 8,
                                                "last": "mousedown", "retargeted": False, "hidden": False}
            and seen("dodge_click", "shy_click") == [("pointerover", "dodge"), ("pointerdown", "dodge"),
                                                     ("mousedown", "dodge")]
            and found["dodge_click"]["after"]["dodge_top"] == "560px" and untouched("dodge_click")),
        # FP45 (the third run's expectation, that the press then went to the child laid bare, is
        # replaced: the hover events after the first would have gone to a child no longer there)
        "the child that leaves at the first hover event gets nothing more, and nothing is pressed": (
            found["pair_click"]["receipt"] == {"complete": False, "stopped": "left_pointer", "count": 1,
                                               "last": "pointerover", "retargeted": False, "hidden": False}
            and seen("pair_click", "dodge_click") == [("pointerover", "first")]
            and found["pair_click"]["after"]["first_left"] == "105px" and untouched("pair_click")),
        "the child pressed and released that leaves at the release is not clicked": (
            found["late_click"]["receipt"] == {"complete": False, "stopped": "left_pointer", "count": 10,
                                               "last": "mouseup", "retargeted": False, "hidden": False}
            and seen("late_click", "pair_click") == [(kind, "above") for kind in WHOLE[:-1]]
            and found["late_click"]["after"]["above_left"] == "105px" and untouched("late_click")),
        "an ordinary button and field show the pointer by the rule": (
            pointer_shown(cursors.get("mover")) and pointer_shown(cursors.get("field"))),
        "the isolated world reads the page's hidden and replaced cursors": (
            cursors.get("ghost") == "none" and "url(" in str(cursors.get("drawn"))
            and not pointer_shown(cursors.get("drawn"))),
        "nothing was sent under the hidden pointer or the replaced one": (
            found["ghost_click"]["receipt"] == found["drawn_click"]["receipt"] == {**nothing, "hidden": True}
            and found["ghost_click"]["after"]["events"] == found["shadow"]["after"]["events"]
            and not events("drawn_click", "ghost_click")
            and untouched("drawn_click")),
        # FP47
        "a button in the open inside a shadow root is located and clicked": (
            (shadow["plain"]["locate"] or {}).get("hit") == "target"
            and (shadow["plain"]["receipt"] or {}).get("complete") is True
            and [(e["type"], e["target"]) for e in shadow["plain"]["events"]] == [(kind, "plain") for kind in WHOLE]),
        "one that an element outside the shadow root covers is not located as the hit, and is sent nothing": (
            (shadow["veiled"]["locate"] or {}).get("hit") not in (None, "target")
            and shadow["veiled"]["receipt"] == nothing and shadow["veiled"]["events"] == []
            and (shadow["after"]["rect_calls"], shadow["after"]["dispatch_calls"]) == (0, 0)),
        "the field had focus for the inserts": found["insert_off_point"]["after"]["active"] == "field",
        "the insert with the point off the field left it empty": (
            found["insert_off_point"]["receipt"] == {"inserted": False, "why": "not_under_pointer"}
            and found["insert_off_point"]["after"]["field"] == "" and not events("insert_off_point", "drawn_click")),
        "the insert into the field without focus left it empty": (
            found["insert_unfocused"]["receipt"] == {"inserted": False, "why": "not_focused"}
            and found["insert_unfocused"]["after"]["other"] == "" and found["insert_unfocused"]["after"]["field"] == ""
            and not events("insert_unfocused", "insert_off_point")),
        "the insert put the text in": (found["insert"]["receipt"] == {"inserted": True, "why": None}
                                       and found["insert"]["after"]["field"] == INSERTED),
        "with one input event on the field": [(e["type"], e["target"]) for e in typed if e["type"] == "input"] == [("input", "field")],
        "no method the page replaced was called by the inserts": untouched("insert"),
        # the control: the fixture does defeat a click that reads its rectangle in the page's world
        "control: the page-world click called the page's wrapper": control["after"]["rect_calls"] > 0,
        "control: and was delivered to the button 300 px from where it was": (
            len(control_clicks) == 1 and control_clicks[0]["target"] == "mover" and control_clicks[0]["top"] == "360px"
            and control_clicks[0]["y"] == MOVER_CENTRE[1] + 300),
        "control: without the check the button that moved when hovered is pressed and clicked": (
            [e["type"] for e in shy_control_events if e["target"] == "shy"] == list(WHOLE)
            and shy_control["after"]["shy_top"] == "460px"),
        "control: without a point the button that moved when pressed is released and clicked": (
            control_seen("dodge") == [(kind, "dodge") for kind in WHOLE]
            and found["page_world_dodge_click"]["after"]["dodge_top"] == "560px"),
        "control: without a point the child that left is pressed where it no longer is": (
            control_seen("pair") == [(kind, "first") for kind in WHOLE]),
        "control: without a point the child that left at the release is clicked where it went": (
            control_seen("late") == [(kind, "above") for kind in WHOLE]
            and found["page_world_late_click"]["after"]["above_left"] == "105px"),
        "control: without a point the button under a hidden pointer is clicked": (
            control_seen("ghost") == [(kind, "ghost") for kind in WHOLE]),
        # FP55: the focus is given only to an element of the ref's node
        "a control inside a focusable container is clicked, the container is given no focus, and the receipt says so": (
            inrow["receipt"] == {**done, "unfocused": True}
            and during("inrow_click") == [(kind, "inrow") for kind in WHOLE]
            and inrow["after"]["active"] == inrow["before"]["active"] != "row"),
        "a focusable control inside the ref's node is focused by the press": (
            group["receipt"] == {**done, "unfocused": False}
            and during("group_click") == [(kind, "ingroup") for kind in WHOLE]
            and group["before"]["active"] != "ingroup" and group["after"]["active"] == "ingroup"),
        # FP56: the insert goes where the selection is, and the selection cannot be outside the node
        # while the node is the active element and the command still inserts
        "the insert into a focused editable region puts the text at its caret": (
            editable["plain"]["receipt"] == {"inserted": True, "why": None}
            and editable["plain"]["after"]["eda"] == "one" + INSERTED and editable["plain"]["after"]["edb"] == "two"),
        "with the selection in another editable region, that region is the active element and nothing is inserted": (
            editable["selection_in_another_region"]["before"]["active"] == "edb"
            and editable["selection_in_another_region"]["receipt"] == {"inserted": False, "why": "not_focused"}
            and unchanged("selection_in_another_region")),
        "with the selection in text that cannot be edited, the command inserts nothing and says so": (
            editable["selection_in_plain_text"]["receipt"] == {"inserted": False, "why": "command_refused"}
            and unchanged("selection_in_plain_text")),
        "control: without a point the container is focused": (
            control_seen("inrow") == [(kind, "inrow") for kind in WHOLE]
            and found["page_world_inrow_click"]["before"]["active"] != "row"
            and found["page_world_inrow_click"]["after"]["active"] == "row"),
    }
    return {"checks": checks, "held": all(checks.values()), "cursors": cursors,
            "page_focused": found["insert"]["after"]["page_focused"],
            "input_events": [(e["type"], e["trusted"], e["data"]) for e in typed]}


async def examine(endpoint: str, url: str) -> dict:
    import websockets

    source = function_text()
    out: dict = {"function_sha256": hashlib.sha256(source.encode()).hexdigest(), "controls": {}}
    async with websockets.connect(endpoint, max_size=None) as socket:
        cdp = Cdp(socket)
        out["browser"] = (await cdp.call("Browser.getVersion", browser=True)).get("product")
        target, world = await _open(cdp, url)
        frame = (await cdp.call("Page.getFrameTree"))["frameTree"]["frame"]["id"]
        again = (await cdp.call("Page.createIsolatedWorld", {"frameId": frame, "worldName": WORLD}))["executionContextId"]
        out["world"] = {"first": world, "again": again}

        async def objects(control: str) -> tuple[str, str, int]:
            mine = (await cdp.call("Runtime.evaluate", {"expression": f"document.getElementById('{control}')"}))["result"]["objectId"]
            backend = (await cdp.call("DOM.describeNode", {"objectId": mine}))["node"]["backendNodeId"]
            isolated = (await cdp.call("DOM.resolveNode", {"backendNodeId": backend, "executionContextId": world}))["object"]["objectId"]
            return mine, isolated, backend

        for control in CONTROLS:
            mine, isolated, backend = await objects(control)
            box = await cdp.call("DOM.getBoxModel", {"backendNodeId": backend})
            out["controls"][control] = {"page_world": await read(cdp, source, mine),
                                        "isolated_world": await read(cdp, source, isolated),
                                        "border_quad": box["model"]["border"]}
        # the field, once the page's script has focused it (what the driver's click sequence does)
        mine, isolated, _ = await objects("note")
        await cdp.call("Runtime.callFunctionOn", {"objectId": mine, "functionDeclaration": "function() { this.focus({preventScroll: true}); }"})
        out["note_after_focus"] = {"page_world": await read(cdp, source, mine),
                                   "isolated_world": await read(cdp, source, isolated)}
        # a page that lies about every rectangle: the isolated world must not see the lie
        await cdp.call("Runtime.evaluate", {"expression": REPLACE_RECT})
        mine, isolated, _ = await objects("alpha")
        out["alpha_after_rect_replaced"] = {"page_world": await read(cdp, source, mine),
                                            "isolated_world": await read(cdp, source, isolated)}
        # and one that says every node is still attached
        await cdp.call("Runtime.evaluate", {"expression":
            "Object.defineProperty(Node.prototype, 'isConnected', {get: () => 'forged'})"})
        connected = "function() { return this.isConnected; }"
        out["is_connected"] = {"page_world": await read(cdp, connected, mine),
                               "isolated_world": await read(cdp, connected, isolated)}
        await cdp.call("Target.closeTarget", {"targetId": target}, browser=True)
        # the second page is served in place of the first from here on
        probe_page_effects.FIXTURE = DELIVERY
        out["delivery"] = await deliver(cdp, url)
    return out


def verdict(found: dict) -> dict:
    """Each expectation of FP22 against what was read; ``held`` only when every one holds."""
    def iso(control: str, field: str):
        return ((found["controls"].get(control) or {}).get("isolated_world") or {}).get(field)

    def page(control: str, field: str):
        return ((found["controls"].get(control) or {}).get("page_world") or {}).get(field)

    inner = iso("alpha", "inner") or [0, 0]
    edge, gamma = iso("edge", "rect") or [0, 0, 0, 0], iso("gamma", "rect") or [0, 0, 0, 0]
    note_before, note_after = iso("note", "rect"), (found["note_after_focus"]["isolated_world"] or {}).get("rect")
    focus_after = (found["note_after_focus"]["isolated_world"] or {}).get("focus")
    lied = found["alpha_after_rect_replaced"]
    checks = {
        "one world per frame and name": found["world"]["first"] == found["world"]["again"],
        "alpha is located and hit in both worlds": (iso("alpha", "rect") == [40, 60, 140, 44] and iso("alpha", "hit") == "target"
                                                     and page("alpha", "hit") == "target"),
        "alpha is not clipped, turned or focused": (iso("alpha", "clipped") is False and iso("alpha", "transformed") is False
                                                    and (iso("alpha", "focus") or [None])[0] is False),
        "covered is other in both worlds": iso("covered", "hit") == "other" and page("covered", "hit") == "other",
        "the page's world says forged is hit": page("forged", "hit") == "target",
        "the isolated world says forged is covered": iso("forged", "hit") == "other",
        "edge reaches below the viewport": edge[1] + edge[3] > inner[1] > 0,
        "clipped is reported clipped with its centre hit": iso("clipped", "clipped") is True and iso("clipped", "hit") == "target",
        "turned is reported transformed": iso("turned", "transformed") is True,
        "gamma is below the viewport": gamma[1] > inner[1] > 0,
        "note is not focused before": (iso("note", "focus") or [None])[0] is False,
        "note is the active element after focus": bool(focus_after) and focus_after[0] is True,
        # only in a document that has focus does the focus style apply; a move without it would be a surprise
        # the live fixture's field no longer moves when focused (FP37); until then this check asked for
        # the 40 px its focus style gave it
        "note is where it was once focused": bool(note_before and note_after) and note_after == note_before,
        "the page's world reports the replaced rectangle": (lied["page_world"] or {}).get("rect") == [0, 0, 10, 10],
        "the isolated world reports the real rectangle": (lied["isolated_world"] or {}).get("rect") == [40, 60, 140, 44],
        "the isolated world reads the real isConnected": (found["is_connected"]["page_world"] == "forged"
                                                          and found["is_connected"]["isolated_world"] is True),
    }
    return {"checks": checks, "held": all(checks.values())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    if not out.is_absolute() or out.exists():
        raise SystemExit("--out must be an absolute path that does not exist yet")
    out.mkdir(parents=True)
    probe_page_effects.FIXTURE = probe_filmed_page_pointer.FIXTURE
    server, port = probe_page_effects._serve(out)
    profile = tempfile.mkdtemp(prefix="footwork-headless-")
    record: dict = {"front_pid_before": _front_pid(), "started": time.time()}
    chrome = subprocess.Popen(
        [CHROME, "--headless=new", "--remote-debugging-port=0", f"--user-data-dir={profile}", "--no-first-run",
         "--no-default-browser-check", "--window-size=1200,900", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    record["chrome_pid"] = chrome.pid
    try:
        endpoint = None
        deadline = time.time() + 30
        while time.time() < deadline and endpoint is None:
            line = chrome.stderr.readline()
            if not line and chrome.poll() is not None:
                break
            said = re.search(r"DevTools listening on (ws://127\.0\.0\.1:\d+/\S+)", line or "")
            endpoint = said.group(1) if said else None
        if endpoint is None:
            raise SystemExit("headless Chrome did not report a DevTools endpoint")
        record["front_pid_during"] = _front_pid()
        record["found"] = asyncio.run(examine(endpoint, f"http://127.0.0.1:{port}/"))
        record["verdict"] = verdict(record["found"])
        record["delivery_verdict"] = delivery_verdict(record["found"]["delivery"])
    finally:
        chrome.terminate()
        try:
            chrome.wait(timeout=10)
        except subprocess.TimeoutExpired:
            chrome.kill()
            chrome.wait(timeout=10)
        record["chrome_exit"] = chrome.returncode
        server.shutdown()
        shutil.rmtree(profile, ignore_errors=True)
        record["profile_removed"] = not Path(profile).exists()
        record["front_pid_after"] = _front_pid()
        (out / "headless.json").write_text(json.dumps(record, indent=1))
    print(json.dumps(record.get("verdict"), indent=1))
    print(json.dumps(record.get("delivery_verdict"), indent=1))
    print(json.dumps({key: record.get(key) for key in ("front_pid_before", "front_pid_during", "front_pid_after",
                                                         "chrome_exit", "profile_removed")}))


if __name__ == "__main__":
    main()
