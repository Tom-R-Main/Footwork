"""Probe for notebook prediction BH13: is input bound to the document and node it was observed on?

Through a session holder on a Footwork-launched Chrome in an isolated profile and port, with the
browser in the background, it observes a fixture page, lets the page change, then clicks with the
observation taken before the change:

* reload: the page reloads itself (a new document, same URL);
* rerender: the page replaces its counter button with an identical new one (same document).

The counter button's own handler logs every activation, so a click on a detached button is visible
even though it no longer bubbles to the document. A fresh observation and click follow each case as
a control. Then a third button removes itself on pointerdown (DC4), so a click that keeps sending
to it after the press shows as vanish_click. Waits for an unlocked screen and 10 s of idle before
launching. Refuses Footwork's default port and the sign-in test's.

Run from ``jevdual/`` with the pinned driver installed::

    FOOTWORK_CHROME_PROFILE=/abs/fresh/profile FOOTWORK_CHROME_PORT=9466 \\
    PYTHONPATH=python \\
    .venv/bin/python scripts/probe_document_binding.py --out /abs/out/dir
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_page_effects
from probe_browser_holder import _activate_pid, _front_pid, _sample_front, _wait_idle

FIXTURE = """<!doctype html>
<meta charset="utf-8">
<title>Footwork document-binding fixture</title>
<body style="font: 16px system-ui; margin: 40px">
<p id="slot"><button type="button" id="count">Count clicks</button></p>
<p><button type="button" id="reload">Reload soon</button>
<button type="button" id="rerender">Rerender soon</button></p>
<p id="vanish-slot"><button type="button" id="vanish">Vanish on press</button></p>
<script>
const post = (type, detail) => fetch('/log', {method: 'POST', keepalive: true,
  body: JSON.stringify({t: (performance.timeOrigin + performance.now()) / 1000, type, detail})});
let generation = 0;
function counter() {
  const b = document.createElement('button');
  b.type = 'button'; b.id = 'count'; b.textContent = 'Count clicks';
  const mine = generation;
  b.addEventListener('click', () => post('count_handler', {button_generation: mine, attached: b.isConnected}));
  return b;
}
document.getElementById('slot').replaceChildren(counter());
const vanish = document.getElementById('vanish');
vanish.addEventListener('pointerdown', () => { vanish.remove(); post('vanish_pointerdown', {attached: vanish.isConnected}); });
vanish.addEventListener('click', () => post('vanish_click', {attached: vanish.isConnected}));
document.getElementById('reload').addEventListener('click', () => setTimeout(() => location.reload(), 1500));
document.getElementById('rerender').addEventListener('click', () => setTimeout(() => {
  generation += 1; document.getElementById('slot').replaceChildren(counter()); post('rerendered', {generation});
}, 1500));
for (const type of ['focus', 'blur']) window.addEventListener(type, () => post('window_' + type, {}));
document.addEventListener('visibilitychange', () => post('visibility', {state: document.visibilityState}));
window.addEventListener('load', () => post('loaded', {}));
</script>
"""


def _id(nm, label: str) -> int:
    for c in nm.menu.candidates:
        if c.label == label:
            return c.id
    raise SystemExit(f"{label!r} not on the observation")


async def _case(bridge, name: str, trigger: str, steps: list[dict]) -> None:
    nm = await bridge.observe()
    t = time.time()
    eff = await bridge.act(nm, "click", _id(nm, trigger))
    steps.append({"step": f"{name}-trigger", "t": t, "effect": eff.effect})
    stale = await bridge.observe()  # the observation the late click uses
    steps.append({"step": f"{name}-observed", "t": time.time(), "snapshot": stale.snapshot_id})
    await asyncio.sleep(3.5)  # the page changes 1.5 s after the trigger
    t = time.time()
    eff = await bridge.act(stale, "click", _id(stale, "Count clicks"))
    steps.append({"step": f"{name}-late-click", "t": t, "effect": eff.effect, "error_code": eff.error_code,
                  "dispatched": eff.dispatched, "summary": eff.summary[:200]})
    await asyncio.sleep(1.0)
    fresh = await bridge.observe()
    t = time.time()
    eff = await bridge.act(fresh, "click", _id(fresh, "Count clicks"))
    steps.append({"step": f"{name}-fresh-click", "t": t, "effect": eff.effect, "error_code": eff.error_code})
    await asyncio.sleep(1.0)


async def _press_removal(bridge, steps: list[dict]) -> None:
    """DC4: a button whose own pointerdown handler removes it. A click sequence that stops when its
    node leaves the document sends no click; the page logs vanish_click if one arrives."""
    nm = await bridge.observe()
    t = time.time()
    eff = await bridge.act(nm, "click", _id(nm, "Vanish on press"))
    steps.append({"step": "vanish-click", "t": t, "effect": eff.effect, "error_code": eff.error_code,
                  "dispatched": eff.dispatched, "summary": eff.summary[:300]})
    await asyncio.sleep(1.0)


async def _run(out: Path, session: Path, url: str, record: dict) -> None:
    from jevdual import browser_session_holder as bsh
    from jevdual.browser_driver import BrowserBridge

    identity = await bsh.spawn_owned(url=url)
    runtime = Path(identity["runtime"])
    record["holder_pid"] = identity["pid"]
    record["owned_chrome_pid"] = identity["chrome_pid"]
    await asyncio.sleep(1.0)
    if record["front_pid_at_start"] and _front_pid() != record["front_pid_at_start"]:
        _activate_pid(record["front_pid_at_start"])
    await asyncio.sleep(5.0)
    record["restored"] = {"t": time.time(), "front_pid": _front_pid()}
    try:
        bridge = BrowserBridge(bsh.HeldDriver(), identity["chrome_pid"], identity["window_id"],
                               operations=bsh.RemoteBrowserOperations(runtime))
        await bridge.attach()
        steps: list[dict] = record["steps"]
        await _case(bridge, "reload", "Reload soon", steps)
        await _case(bridge, "rerender", "Rerender soon", steps)
        await _press_removal(bridge, steps)
    finally:
        record["holder_stop"] = await bsh.retire(runtime, expected=identity)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        raise SystemExit("--out must be absolute")
    if os.environ.get("FOOTWORK_CHROME_PORT", "9333") in {"9333", "9555"} or not os.environ.get("FOOTWORK_CHROME_PROFILE"):
        raise SystemExit("refusing a protected port or the default profile; set both overrides")
    out.mkdir(parents=True, exist_ok=True)
    probe_page_effects.FIXTURE = FIXTURE
    server, port = probe_page_effects._serve(out)
    record: dict = {"gate": _wait_idle(), "front_pid_at_start": _front_pid(), "steps": []}
    stop = threading.Event()
    sampler = threading.Thread(target=_sample_front, args=(out, stop), daemon=True)
    sampler.start()
    try:
        asyncio.run(_run(out, out / "session", f"http://127.0.0.1:{port}/", record))
    finally:
        from jevdual.browser_driver import chrome_pid

        pid = chrome_pid()
        if pid:
            os.kill(pid, signal.SIGTERM)
        stop.set()
        sampler.join(timeout=5)
        server.shutdown()
        (out / "run.json").write_text(json.dumps(record, indent=1, default=str))


if __name__ == "__main__":
    main()
