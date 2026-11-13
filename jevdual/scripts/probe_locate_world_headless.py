"""Headless check for notebook prediction FP22: what the driver's locate page function reports in a real
Chrome, read in the page's own script world and in an isolated world.

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
in a window, and the driver's own binding are the live probe's (FP20).

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


def function_text() -> str:
    """``DOM_NODE_LOCATE`` as JavaScript, from the pinned archive's tools.rs."""
    with tarfile.open(ROOT / "vendor/cua-driver/native-source.tar.gz") as archive:
        source = archive.extractfile(TOOLS).read().decode()
    literal = re.search(r'const DOM_NODE_LOCATE: &str = "(.*?)";\n', source, re.DOTALL)
    if literal is None:
        raise SystemExit("DOM_NODE_LOCATE is not in the pinned tools.rs")
    return re.sub(r"\\\n\s*", "", literal.group(1))


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


async def read(cdp: Cdp, source: str, object_id: str) -> dict:
    reply = await cdp.call("Runtime.callFunctionOn", {"objectId": object_id, "functionDeclaration": source,
                                                      "arguments": [], "returnByValue": True})
    if "exceptionDetails" in reply:
        return {"exception": reply["exceptionDetails"].get("text"),
                "description": (reply["exceptionDetails"].get("exception") or {}).get("description")}
    return reply["result"].get("value")


async def examine(endpoint: str, url: str) -> dict:
    import websockets

    source = function_text()
    out: dict = {"function_sha256": hashlib.sha256(source.encode()).hexdigest(), "controls": {}}
    async with websockets.connect(endpoint, max_size=None) as socket:
        cdp = Cdp(socket)
        out["browser"] = (await cdp.call("Browser.getVersion", browser=True)).get("product")
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
    print(json.dumps({key: record.get(key) for key in ("front_pid_before", "front_pid_during", "front_pid_after",
                                                         "chrome_exit", "profile_removed")}))


if __name__ == "__main__":
    main()
