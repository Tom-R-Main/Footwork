"""Probe for notebook predictions AAD1 (live half) and AAD4.

Drives an owned local fixture page in a Chrome that Footwork launches into an isolated profile and
port, kept in the background, and records three independent things with wall-clock timestamps:

* each driver reply, as Footwork's browser bridge reads it;
* the page's own event log (focus, blur, visibility, clicks, input; a key event is logged without
  its key);
* every change of the frontmost application.

Steps: a page-route click on a checkbox; a page-route click on a control whose state cannot change;
replacing the held text of a field; a trusted click at the viewport coordinates of a button. The
last two bypass the session's posture gate on purpose: the question is what the driver itself does.
Launching Chrome takes the foreground, so after binding the probe re-activates the application that
was frontmost when it started and waits before the first step. It sends no input to any other
application.

Run from ``jevdual/`` with the pinned driver overlay first on ``PYTHONPATH``::

    FOOTWORK_CHROME_PROFILE=/abs/fresh/profile FOOTWORK_CHROME_PORT=9444 \
    PYTHONPATH=output/foreground-helptag/overlay:python \
    .venv/bin/python scripts/probe_page_effects.py --out /abs/out/dir

Refuses to run against Footwork's default profile or port.
"""

from __future__ import annotations

import argparse
import asyncio
import http.server
import json
import os
import subprocess
import threading
import time
from pathlib import Path

FIXTURE = """<!doctype html>
<meta charset="utf-8">
<title>Footwork page-effects fixture</title>
<body style="font: 16px system-ui; margin: 40px">
<p><label><input type="checkbox" id="cb"> Enable option</label></p>
<p><button type="button" id="inert">Inert control</button></p>
<p><button type="button" id="count">Count clicks</button> <output id="n">0</output></p>
<p><label>Name <input id="name" value="held text" size="30"></label></p>
<script>
const post = (type, detail) => fetch('/log', {method: 'POST', keepalive: true,
  body: JSON.stringify({t: (performance.timeOrigin + performance.now()) / 1000, type, detail})});
let n = 0;
document.getElementById('count').addEventListener('click', () => { n += 1; document.getElementById('n').value = n; });
for (const type of ['focus', 'blur']) window.addEventListener(type, () => post('window_' + type, {}));
document.addEventListener('visibilitychange', () => post('visibility', {state: document.visibilityState}));
document.addEventListener('keydown', () => post('keydown', {}), true);  // never the key itself
document.addEventListener('click', (e) => post('click', {id: e.target.id || null, trusted: e.isTrusted,
  x: e.clientX, y: e.clientY, count: n}), true);
document.addEventListener('input', (e) => post('input', {id: e.target.id || null, value: e.target.value}), true);
document.addEventListener('change', (e) => post('change', {id: e.target.id || null,
  checked: e.target.checked === undefined ? null : e.target.checked}), true);
window.addEventListener('load', () => {
  const r = document.getElementById('count').getBoundingClientRect();
  post('loaded', {visibility: document.visibilityState, focused: document.hasFocus(),
    count_center: [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)]});
});
</script>
"""


def _serve(out: Path) -> tuple[http.server.ThreadingHTTPServer, int]:
    events = out / "page-events.jsonl"

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_: object) -> None:
            pass

        def do_GET(self) -> None:  # noqa: N802
            body = FIXTURE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            raw = self.rfile.read(min(int(self.headers.get("Content-Length") or 0), 4096))
            try:
                record = json.loads(raw)
            except ValueError:
                record = {"type": "unreadable"}
            record["received"] = time.time()
            with events.open("a") as stream:
                stream.write(json.dumps(record) + "\n")
            self.send_response(204)
            self.end_headers()

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def _front() -> str:
    try:
        asn = subprocess.run(["lsappinfo", "front"], capture_output=True, text=True, timeout=2).stdout.strip()
        name = subprocess.run(
            ["lsappinfo", "info", "-only", "name", asn], capture_output=True, text=True, timeout=2
        ).stdout.strip()
        return name.split("=", 1)[-1].strip('"') or asn
    except (OSError, subprocess.SubprocessError):
        return "unreadable"


def _front_asn() -> str:
    try:
        return subprocess.run(["lsappinfo", "front"], capture_output=True, text=True, timeout=2).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unreadable"


def _sample_front(out: Path, stop: threading.Event) -> None:
    """Record every change of the frontmost application, sampling as fast as one lookup allows.

    A change shorter than the gap between two samples is invisible, so the sample count and the
    largest gap are written at the end: they bound what this log can and cannot exclude.
    """
    last = None
    samples, largest_gap, previous = 0, 0.0, time.time()
    names: dict[str, str] = {}
    with (out / "front-app.jsonl").open("a") as stream:
        while not stop.is_set():
            asn = _front_asn()
            now = time.time()
            samples += 1
            largest_gap = max(largest_gap, now - previous)
            previous = now
            if asn != last:
                if asn not in names:
                    names[asn] = _front()
                stream.write(json.dumps({"t": now, "front": names[asn]}) + "\n")
                stream.flush()
                last = asn
        stream.write(json.dumps({"t": time.time(), "samples": samples, "largest_gap_s": round(largest_gap, 4)}) + "\n")


def _reply(reply: object) -> dict[str, object]:
    return {
        "status": getattr(reply, "status", None),
        "is_error": getattr(reply, "is_error", None),
        "effect": getattr(reply, "effect", None),
        "evidence": list(getattr(reply, "evidence", ()) or ()),
        "escalation": dict(getattr(reply, "escalation", None) or {}) or None,
        "refusal_code": getattr(getattr(reply, "refusal", None), "code", None),
        "text": (getattr(reply, "text", "") or "")[:300],
        "payload_keys": sorted(getattr(reply, "payload", {}) or {}),
    }


async def _run(out: Path) -> None:
    from jevdual.browser_driver import PORT, PROFILE_DIR, bind_footwork_chrome

    if PORT == 9333 or PROFILE_DIR == Path.home() / ".config/jevdual/chrome-profile":
        raise SystemExit("refusing to run against Footwork's default profile or port; set both overrides")

    server, port = _serve(out)
    stop = threading.Event()
    sampler = threading.Thread(target=_sample_front, args=(out, stop), daemon=True)
    sampler.start()
    steps = (out / "steps.jsonl").open("a")

    def record(name: str, started: float, **fields: object) -> None:
        steps.write(json.dumps({"step": name, "t_start": started, "t_end": time.time(), **fields}) + "\n")
        steps.flush()

    front_at_start = _front()
    driver, bridge = await bind_footwork_chrome(f"http://127.0.0.1:{port}/")
    try:
        await asyncio.sleep(1.0)
        t = time.time()
        if _front() != front_at_start and front_at_start != "unreadable":
            subprocess.run(["osascript", "-e", f'tell application "{front_at_start}" to activate'],
                           capture_output=True, timeout=10, check=False)
        await asyncio.sleep(2.0)
        record("background_restored", t, front_at_start=front_at_start, front_before_steps=_front())

        def find(nm: object, label: str) -> int:
            for c in nm.menu.candidates:  # type: ignore[attr-defined]
                if label.lower() in (c.label or "").lower():
                    return c.id
            raise SystemExit(f"fixture control {label!r} not on the observation")

        nm = await bridge.observe()
        t = time.time()
        eff = await bridge.act(nm, "click", find(nm, "Enable option"))
        record("dom_click_checkbox", t, effect=eff.effect, route=eff.route, evidence=list(eff.evidence),
               escalation=eff.escalation, summary=eff.summary)
        await asyncio.sleep(1.0)

        nm = await bridge.observe()
        t = time.time()
        eff = await bridge.act(nm, "click", find(nm, "Inert control"))
        record("dom_click_inert", t, effect=eff.effect, route=eff.route, evidence=list(eff.evidence),
               escalation=eff.escalation, summary=eff.summary)
        await asyncio.sleep(1.0)

        nm = await bridge.observe()
        name_id = find(nm, "Name")
        t = time.time()
        out_reply = await bridge.operations.type_text(
            target_id=bridge.target_id, tab_id=bridge.tab_id, ref=nm.refs[name_id], text="replacement", replace=True
        )
        record("replace_held_text", t, held_before=nm.values.get(name_id), **_reply(out_reply))
        await asyncio.sleep(1.0)

        centre = None
        for line in (out / "page-events.jsonl").read_text().splitlines():
            event = json.loads(line)
            if event.get("type") == "loaded":
                centre = event["detail"]["count_center"]
        if centre is None:
            raise SystemExit("the fixture never reported its layout")
        t = time.time()
        out_reply = await bridge.operations._call(  # noqa: SLF001 - the bounded surface has no coordinate click
            "browser_click",
            {"target_id": bridge.target_id, "tab_id": bridge.tab_id, "x": centre[0], "y": centre[1],
             "input_route": "trusted"},
        )
        record("trusted_click_at_coordinates", t, x=centre[0], y=centre[1], **_reply(out_reply))
        await asyncio.sleep(1.5)

        nm = await bridge.observe()
        t = time.time()
        record("final_observation", t, name_value=nm.values.get(find(nm, "Name")),
               controls=[{"label": c.label, "role": c.role, "value": c.value, "checked": c.checked}
                         for c in nm.menu.candidates])
    finally:
        await driver.shutdown()
        stop.set()
        sampler.join(timeout=5)
        steps.close()
        server.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--out", required=True, help="absolute directory for the three logs")
    args = parser.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        raise SystemExit("--out must be absolute")
    out.mkdir(parents=True, exist_ok=True)
    (out / "environment.json").write_text(json.dumps({
        "started": time.time(), "profile": os.environ.get("FOOTWORK_CHROME_PROFILE"),
        "port": os.environ.get("FOOTWORK_CHROME_PORT"), "front_at_start": _front(),
    }))
    asyncio.run(_run(out))


if __name__ == "__main__":
    main()
