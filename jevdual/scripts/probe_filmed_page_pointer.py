"""Probe for notebook prediction FP1: does a filmed browser take move the real pointer onto each page target?

Starts a filmed ``start --browser`` session (``--mode exclusive_desktop --pointer-motion filmed``) on an
owned local fixture in a Chrome that Footwork launches on an isolated profile and port, then clicks,
through ``do click``, three buttons at different places: Alpha (top left), Beta (right, lower), and
Gamma, which is below the fold until the page is scrolled by clicking "Jump down" first.

The fixture logs every trusted ``mouseover`` (the element the real pointer entered) and, inside each
click handler, the last trusted ``mousemove`` before it, the button's client rectangle and the scroll
offset. The session's pointer-gestures.jsonl records where each approach ended in screen points.
``analyze`` decides each click: the last trusted move before the handler targets the button, and the
gesture for that click ends inside the button's screen rectangle (content origin plus client rect).

Waits for an unlocked screen and 10 s of idle before launching. Refuses Footwork's default port and the
sign-in test's. Restores the frontmost application and closes the owned Chrome at the end, recording
whether it closed.

Run from ``jevdual/`` with the pinned driver installed::

    FOOTWORK_CHROME_PROFILE=/abs/fresh/profile FOOTWORK_CHROME_PORT=9466 \\
    PYTHONPATH=python \\
    .venv/bin/python scripts/probe_filmed_page_pointer.py --out /abs/out/dir

``--analyze-only`` re-reads an existing ``--out`` directory and rewrites its verdicts.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import signal
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_page_effects
from probe_browser_holder import _activate_pid, _cli, _front_pid, _sample_front, _wait_idle

#: (label, how it is reached) in click order; Jump down scrolls Gamma into view
CLICKS = (("Alpha", "in view"), ("Beta", "in view"), ("Jump down", "in view"), ("Gamma", "after scrolling"))
TARGETS = ("Alpha", "Beta", "Gamma")

FIXTURE = """<!doctype html>
<meta charset="utf-8">
<title>Footwork filmed page pointer fixture</title>
<body style="font: 16px system-ui; margin: 0">
<div style="position: relative; height: 2600px">
  <button type="button" id="alpha" style="position: absolute; left: 40px; top: 60px; width: 140px; height: 44px">Alpha</button>
  <button type="button" id="beta" style="position: absolute; left: 420px; top: 300px; width: 140px; height: 44px">Beta</button>
  <button type="button" id="jump" style="position: absolute; left: 40px; top: 420px; width: 140px; height: 44px">Jump down</button>
  <button type="button" id="gamma" style="position: absolute; left: 240px; top: 1900px; width: 140px; height: 44px">Gamma</button>
</div>
<script>
const now = () => (performance.timeOrigin + performance.now()) / 1000;
const post = (type, detail) => fetch('/log', {method: 'POST', keepalive: true,
  body: JSON.stringify({t: now(), type, detail})});
const label = (el) => (el && el.closest && el.closest('button')) ? el.closest('button').textContent : (el && el.tagName) || null;
let lastMove = null;
document.addEventListener('mousemove', (e) => {
  if (e.isTrusted) lastMove = {t: now(), target: label(e.target), x: e.clientX, y: e.clientY};
}, true);
document.addEventListener('mouseover', (e) => {
  if (e.isTrusted) post('trusted_mouseover', {target: label(e.target), x: e.clientX, y: e.clientY});
}, true);
for (const b of document.querySelectorAll('button')) {
  b.addEventListener('click', (e) => {
    const r = b.getBoundingClientRect();
    post('click_handler', {button: b.textContent, trusted: e.isTrusted, last_trusted_move: lastMove,
      rect: [r.x, r.y, r.width, r.height], scroll: [window.scrollX, window.scrollY],
      dpr: window.devicePixelRatio, viewport: [window.innerWidth, window.innerHeight]});
    if (b.id === 'jump') window.scrollTo(0, 1500);
  });
}
window.addEventListener('scroll', () => post('scrolled', {y: window.scrollY}), {passive: true});
window.addEventListener('load', () => post('loaded', {dpr: window.devicePixelRatio}));
</script>
"""


def _ref(text: str, label: str) -> int | None:
    match = re.search(rf"\[\s*(\d+)\]\s+button\s+'{re.escape(label)}'", text)
    return int(match.group(1)) if match else None


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _inside(point, rect) -> bool:
    x, y = point
    rx, ry, rw, rh = rect
    return rx <= x <= rx + rw and ry <= y <= ry + rh


def analyze(out: Path) -> dict:
    """Per-target verdicts from the page log, the gesture trace and the session's filmed content origin."""
    events = _jsonl(out / "page-events.jsonl")
    gestures = [g for g in _jsonl(out / "session/pointer-gestures.jsonl") if g.get("kind") == "approach"]
    try:
        content = json.loads((out / "session/session.json").read_text())["filmed"]["content"]
    except (OSError, ValueError, KeyError, TypeError):
        content = None
    handlers = [e for e in events if e.get("type") == "click_handler"]
    verdicts = {}
    for label in TARGETS:
        handler = next((e["detail"] for e in handlers if e["detail"].get("button") == label), None)
        gesture = next((g for g in reversed(gestures) if g.get("label") == label), None)
        v: dict = {"handler_ran": handler is not None, "gesture": gesture is not None}
        if handler is not None:
            move = handler.get("last_trusted_move") or {}
            v["last_trusted_move_target"] = move.get("target")
            v["move_on_button"] = move.get("target") == label
            v["click_trusted"] = handler.get("trusted")
            v["scroll"] = handler.get("scroll")
        if handler is not None and gesture is not None and content is not None and gesture.get("final_location"):
            x, y, w, h = handler["rect"]
            screen = (content[0] + x, content[1] + y, w, h)
            v["button_screen_rect"] = screen
            v["gesture_end"] = gesture["final_location"]
            v["end_inside"] = _inside(gesture["final_location"], screen)
        v["held"] = bool(v.get("move_on_button") and v.get("end_inside"))
        verdicts[label] = v
    scrolled = verdicts.get("Gamma", {}).get("scroll") or [0, 0]
    return {"targets": verdicts, "gamma_scrolled": scrolled[1] > 0,
            "held": all(v["held"] for v in verdicts.values()) and scrolled[1] > 0}


def _close_chrome(record: dict) -> None:
    """SIGTERM the owned Chrome and record whether its process is gone within ten seconds."""
    from jevdual.browser_driver import chrome_pid

    pid = chrome_pid()
    record["chrome_pid"] = pid
    closed = True
    if pid:
        os.kill(pid, signal.SIGTERM)
        closed = False
        for _ in range(50):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                closed = True
                break
            time.sleep(0.2)
    record["chrome_closed"] = closed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--out", required=True)
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        raise SystemExit("--out must be absolute")
    if args.analyze_only:
        verdict = analyze(out)
        (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
        print(json.dumps(verdict, indent=1))
        return
    if os.environ.get("FOOTWORK_CHROME_PORT", "9333") in {"9333", "9555"} or not os.environ.get("FOOTWORK_CHROME_PROFILE"):
        raise SystemExit("refusing a protected port or the default profile; set both overrides")
    out.mkdir(parents=True, exist_ok=True)
    session = out / "session"
    env = dict(os.environ)
    probe_page_effects.FIXTURE = FIXTURE
    server, fixture_port = probe_page_effects._serve(out)
    url = f"http://127.0.0.1:{fixture_port}/"
    record: dict = {"gate": _wait_idle(), "front_pid_at_start": _front_pid(), "fixture": url, "steps": []}
    steps: list[dict] = record["steps"]
    stop = threading.Event()
    sampler = threading.Thread(target=_sample_front, args=(out, stop), daemon=True)
    sampler.start()
    try:
        steps.append(_cli(env, out, "00-start", "start", "probe the filmed page pointer", "--browser", "--url", url,
                          "--mode", "exclusive_desktop", "--pointer-motion", "filmed", "--session", str(session)))
        if steps[-1]["exit"] == 0:
            time.sleep(2.0)
            for i, (label, _) in enumerate(CLICKS, start=1):
                look = _cli(env, out, f"{i:02d}-look", "look", "--session", str(session))
                steps.append(look)
                ref = _ref(look["stdout"], label)
                if ref is None:
                    steps.append({"name": f"{i:02d}-click", "label": label, "skipped": "not on the observation"})
                    break
                click = _cli(env, out, f"{i:02d}-click", "do", "click", str(ref), "--no-judge", "--session", str(session))
                click["label"] = label
                steps.append(click)
                if click["exit"] != 0:
                    break
                time.sleep(1.0)
    finally:
        record["finished"] = time.time()
        from jevdual import browser_session_holder as bsh

        holder = {}
        try:
            holder = json.loads((session / "session.json").read_text()).get("browser_holder") or {}
        except (OSError, ValueError):
            pass
        if holder:
            record["holder_stop"] = asyncio.run(bsh.retire(bsh.recorded_runtime(holder, session), expected=holder))
        _close_chrome(record)
        if record["front_pid_at_start"] and _front_pid() != record["front_pid_at_start"]:
            _activate_pid(record["front_pid_at_start"])
        record["front_pid_at_end"] = _front_pid()
        stop.set()
        sampler.join(timeout=5)
        server.shutdown()
        for step in steps:
            step.pop("stdout", None)
            step["stderr"] = (step.get("stderr") or "")[-400:]
        (out / "run.json").write_text(json.dumps(record, indent=1, default=str))
        verdict = analyze(out)
        (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
        print(json.dumps({"chrome_closed": record.get("chrome_closed"), **verdict}, indent=1))


if __name__ == "__main__":
    main()
