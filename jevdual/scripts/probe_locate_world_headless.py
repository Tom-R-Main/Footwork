"""Headless check for notebook predictions FP22, FP27 and FP30: what the driver's locate page function reports
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
a pointer comes over it (FP30); the filmed insert into a focused field with the point off it, into a
field without focus, and into the focused field at its centre; and last, as controls that the two
counterexamples are real, the click sequence without a point on the page's own object, which is what
the driver did before locate6, on each button.

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
for (const type of ['pointerover', 'pointerdown', 'mousedown', 'mouseup', 'click', 'beforeinput', 'input'])
  document.addEventListener(type, (e) => log.events.push({type, target: e.target.id, trusted: e.isTrusted,
    x: 'clientX' in e ? e.clientX : null, y: 'clientY' in e ? e.clientY : null,
    top: e.target.style.top, data: 'data' in e ? e.data : null}), true);
</script>
"""
MOVER_CENTRE = (110.0, 82.0)  # of (40, 60, 140, 44)
SHY_CENTRE = (110.0, 182.0)  # of (40, 160, 140, 44)
PRESS = ("pointerdown", "mousedown", "mouseup", "click")
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

    async def objects(control: str) -> tuple[str, str]:
        mine = (await cdp.call("Runtime.evaluate", {"expression": f"document.getElementById('{control}')"}))["result"]["objectId"]
        backend = (await cdp.call("DOM.describeNode", {"objectId": mine}))["node"]["backendNodeId"]
        isolated = (await cdp.call("DOM.resolveNode", {"backendNodeId": backend, "executionContextId": world}))["object"]["objectId"]
        return mine, isolated

    async def state() -> dict:
        return await page("({...window.__log, events: window.__log.events.slice(), mover_top: mover.style.top, "
                          "shy_top: shy.style.top, "
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
    # 3: the filmed insert. The field is focused by the page; first with the point off it, ...
    await page("mover.style.top = '60px'; shy.style.top = '160px'; document.getElementById('field').focus()")
    _, field = await objects("field")
    _, other = await objects("other")
    out["insert_off_point"] = {"receipt": await read(cdp, insert, field, 10.0, 10.0, INSERTED), "after": await state()}
    # ... then into the field that does not have focus, at its own centre, ...
    out["insert_unfocused"] = {"receipt": await read(cdp, insert, other, *OTHER_CENTRE, INSERTED), "after": await state()}
    # ... then into the focused field at its centre
    out["insert"] = {"receipt": await read(cdp, insert, field, *FIELD_CENTRE, INSERTED), "after": await state()}
    # 4: the control. Without a point, on the page's own object, as the driver clicked before locate6:
    # the page's wrapper answers the sequence's rectangle read and moves the button under it.
    out["page_world_click"] = {"before": await state(), "receipt": await read(cdp, click, mover_page),
                               "after": await state()}
    # and on the button that moves when hovered: without the check before the press it is pressed anyway
    out["page_world_shy_click"] = {"before": await state(), "receipt": await read(cdp, click, shy_page),
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
    nothing = {"complete": False, "stopped": "not_under_pointer", "count": 0, "last": "", "retargeted": False}
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
            found["shy_click"]["receipt"] == {"complete": False, "stopped": "left_pointer", "count": 6,
                                              "last": "mousemove", "retargeted": False}),
        "it reached the page as hover events only, and the button had moved": (
            [(e["type"], e["target"]) for e in hovered] == [("pointerover", "shy")]
            and found["shy_click"]["after"]["shy_top"] == "460px" and untouched("shy_click")),
        "the field had focus for the inserts": found["insert_off_point"]["after"]["active"] == "field",
        "the insert with the point off the field left it empty": (
            found["insert_off_point"]["receipt"] == {"inserted": False, "why": "not_under_pointer"}
            and found["insert_off_point"]["after"]["field"] == "" and not events("insert_off_point", "shy_click")),
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
            [e["type"] for e in shy_control_events if e["target"] == "shy"] == ["pointerover", *PRESS]
            and shy_control["after"]["shy_top"] == "460px"),
    }
    return {"checks": checks, "held": all(checks.values()),
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
        "note moved 40 px exactly when its document has focus": bool(note_before and note_after and focus_after) and (
            (note_after[1] - note_before[1] == 40) is (focus_after[1] is True)),
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
