"""Probe for notebook prediction FP6: does a filmed browser take put the real pointer on each page target?

Starts a filmed ``start --browser`` session (``--mode exclusive_desktop --pointer-motion filmed``) on an
owned local fixture in a Chrome that Footwork launches on a fresh profile and its own port, then runs
``do click`` on, in order:

1. Alpha and Beta, in view: clicked, with the pointer on them first;
2. Covered, whose centre a fixed overlay covers: refused, no click, no pointer move;
3. Edge, fixed half below the viewport: refused the same way;
4. Gamma, below the fold: refused the same way;
5. Jump down, in view: clicked; its handler scrolls Gamma into view;
6. Gamma again: clicked, with the pointer on it first, on the scrolled page.

The fixture logs every trusted ``mouseover``, and inside each click handler the last trusted pointer
event before it (move or over), the button's client rectangle, the scroll offset and the device pixel
ratio. The session's pointer-gestures.jsonl records where each approach ended in screen points, and the
probe counts its lines after every step. ``analyze`` reads each step against its own evidence: events
are matched to a step by time, and gestures by their order.

Waits for an unlocked screen and 10 s of idle before launching. Needs a profile directory that does not
exist yet, a port that is not Footwork's default or the sign-in test's and has no listener, an output
directory that does not exist yet, and no Chrome already matching that profile and port. It closes only
the Chrome its own start launched, restores the frontmost application, and records whether Chrome closed.

Run from ``jevdual/`` with the pinned driver installed::

    FOOTWORK_CHROME_PROFILE=/abs/fresh/profile FOOTWORK_CHROME_PORT=9466 \\
    PYTHONPATH=python \\
    .venv/bin/python scripts/probe_filmed_page_pointer.py --out /abs/fresh/out/dir

``--analyze-only`` re-reads an existing ``--out`` directory and rewrites its verdict.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import signal
import socket
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_page_effects
from probe_browser_holder import _activate_pid, _cli, _front_pid, _sample_front, _wait_idle

PROTECTED_PORTS = frozenset({9333, 9555})
#: (label, "clicked" | "refused") in order; Gamma is refused until Jump down has scrolled it into view
STEPS = (("Alpha", "clicked"), ("Beta", "clicked"), ("Covered", "refused"), ("Edge", "refused"),
         ("Gamma", "refused"), ("Jump down", "clicked"), ("Gamma", "clicked"))

FIXTURE = """<!doctype html>
<meta charset="utf-8">
<title>Footwork filmed page pointer fixture</title>
<body style="font: 16px system-ui; margin: 0">
<div style="position: relative; height: 2600px">
  <button type="button" id="alpha" style="position: absolute; left: 40px; top: 60px; width: 140px; height: 44px">Alpha</button>
  <button type="button" id="beta" style="position: absolute; left: 620px; top: 330px; width: 140px; height: 44px">Beta</button>
  <button type="button" id="covered" style="position: absolute; left: 40px; top: 200px; width: 140px; height: 44px">Covered</button>
  <button type="button" id="jump" style="position: absolute; left: 300px; top: 60px; width: 140px; height: 44px">Jump down</button>
  <button type="button" id="gamma" style="position: absolute; left: 240px; top: 1900px; width: 140px; height: 44px">Gamma</button>
</div>
<div id="lid" style="position: absolute; left: 80px; top: 205px; width: 60px; height: 34px; background: #c33"></div>
<button type="button" id="edge" style="position: fixed; left: 480px; bottom: -22px; width: 140px; height: 44px">Edge</button>
<script>
const now = () => (performance.timeOrigin + performance.now()) / 1000;
const post = (type, detail) => fetch('/log', {method: 'POST', keepalive: true,
  body: JSON.stringify({t: now(), type, detail})});
const label = (el) => (el && el.closest && el.closest('button')) ? el.closest('button').textContent : (el && (el.id || el.tagName)) || null;
let lastPointer = null;
for (const type of ['mousemove', 'mouseover']) document.addEventListener(type, (e) => {
  if (!e.isTrusted) return;
  lastPointer = {t: now(), type, target: label(e.target), x: e.clientX, y: e.clientY};
  if (type === 'mouseover') post('trusted_mouseover', lastPointer);
}, true);
for (const b of document.querySelectorAll('button')) {
  b.addEventListener('click', (e) => {
    const r = b.getBoundingClientRect();
    post('click_handler', {button: b.textContent, trusted: e.isTrusted, last_trusted_pointer: lastPointer,
      rect: [r.x, r.y, r.width, r.height], scroll: [window.scrollX, window.scrollY],
      dpr: window.devicePixelRatio, viewport: [window.innerWidth, window.innerHeight],
      pinch: window.visualViewport ? window.visualViewport.scale : null});
    if (b.id === 'jump') window.scrollTo(0, 1500);
  });
}
window.addEventListener('scroll', () => post('scrolled', {y: window.scrollY}), {passive: true});
window.addEventListener('load', () => post('loaded', {dpr: window.devicePixelRatio,
  viewport: [window.innerWidth, window.innerHeight]}));
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
    """Each step's verdict from its own evidence. A clicked step holds when its command succeeded, the
    page ran that button's click handler during the step, the last trusted pointer event before the
    handler was on that button and happened during the step, and the step's one new gesture is an
    approach to that button that arrived inside the button's rectangle as the page reported it at click
    time. A refused step holds when the command reported ``target_unlocated``, no handler for that
    button ran during the step, and the step added no gesture."""
    try:
        run = json.loads((out / "run.json").read_text())
        content = json.loads((out / "session/session.json").read_text())["filmed"]["content"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {"held": False, "unreadable": f"{type(exc).__name__}: {exc}"}
    handlers = [e for e in _jsonl(out / "page-events.jsonl") if e.get("type") == "click_handler"]
    gestures = _jsonl(out / "session/pointer-gestures.jsonl")
    clicks = [s for s in run.get("steps", []) if s.get("expect")]
    verdicts, seen = [], run.get("gestures_at_start", 0)
    for step in clicks:
        label, expect = step["label"], step["expect"]
        window = (step["t_start"], step["t_end"] + 1.0)
        mine = [e["detail"] | {"t": e["t"]} for e in handlers
                if e["detail"].get("button") == label and window[0] <= e["t"] <= window[1]]
        new = gestures[seen:step.get("gestures_after", seen)]
        seen = step.get("gestures_after", seen)
        v: dict = {"label": label, "expect": expect, "exit": step.get("exit"), "handlers": len(mine),
                   "new_gestures": [(g.get("kind"), g.get("label"), g.get("outcome")) for g in new]}
        if expect == "refused":
            v["said_unlocated"] = "target_unlocated" in (step.get("stdout", "") + step.get("stderr", ""))
            v["held"] = bool(v["said_unlocated"] and not mine and not new)
        else:
            handler = mine[0] if len(mine) == 1 else None
            arrived = (len(new) == 1 and new[0].get("kind") == "approach" and new[0].get("label") == label
                       and new[0].get("outcome") == "arrived" and new[0].get("final_location"))
            if handler is not None:
                pointer = handler.get("last_trusted_pointer") or {}
                v["pointer_target"] = pointer.get("target")
                v["pointer_during_step"] = bool(pointer.get("t") and window[0] <= pointer["t"] <= handler["t"])
                v["click_trusted"], v["scroll"], v["dpr"] = handler.get("trusted"), handler.get("scroll"), handler.get("dpr")
                v["pinch"] = handler.get("pinch")
            if handler is not None and arrived:
                x, y, w, h = handler["rect"]
                v["button_screen_rect"] = (content[0] + x, content[1] + y, w, h)
                v["gesture_end"] = new[0]["final_location"]
                v["end_inside"] = _inside(new[0]["final_location"], v["button_screen_rect"])
            v["held"] = bool(step.get("exit") == 0 and handler is not None and arrived
                             and v.get("pointer_target") == label and v.get("pointer_during_step")
                             and v.get("end_inside"))
        verdicts.append(v)
    last = verdicts[-1] if verdicts else {}
    scrolled = bool(last.get("label") == "Gamma" and (last.get("scroll") or [0, 0])[1] > 0)
    complete = [(v["label"], v["expect"]) for v in verdicts] == list(STEPS)
    return {"steps": verdicts, "complete": complete, "gamma_clicked_after_scrolling": scrolled,
            "device_pixel_ratio": next((v.get("dpr") for v in verdicts if v.get("dpr")), None),
            "held": complete and scrolled and all(v["held"] for v in verdicts)}


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def preflight(out: Path, profile: str | None, port: str | None) -> str | None:
    """Why this run may not start, or None. Nothing here launches or signals anything."""
    from jevdual.browser_driver import chrome_pid

    if not out.is_absolute() or out.exists():
        return "--out must be an absolute path that does not exist yet"
    if not profile or not Path(profile).is_absolute() or Path(profile).exists():
        return "FOOTWORK_CHROME_PROFILE must be an absolute path that does not exist yet"
    if not port or not port.isdigit() or int(port) in PROTECTED_PORTS or not 1024 < int(port) < 65536:
        return "FOOTWORK_CHROME_PORT must be a number above 1024 that is not Footwork's default or the sign-in test's"
    if _port_open(int(port)):
        return f"something is already listening on port {port}"
    if chrome_pid() is not None:
        return "a Chrome already matches this profile and port; this probe only closes one it launched"
    return None


def _close_owned_chrome(record: dict) -> None:
    """SIGTERM the Chrome this run's start launched (none matched before it) and record whether it went."""
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


def _gestures(session: Path) -> int:
    return len(_jsonl(session / "pointer-gestures.jsonl"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--out", required=True)
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    out = Path(args.out)
    if args.analyze_only:
        verdict = analyze(out)
        (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
        print(json.dumps(verdict, indent=1))
        return
    refusal = preflight(out, os.environ.get("FOOTWORK_CHROME_PROFILE"), os.environ.get("FOOTWORK_CHROME_PORT"))
    if refusal:
        raise SystemExit(f"not starting: {refusal}")
    out.mkdir(parents=True)
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
    launched = False
    try:
        launched = True  # from here a Chrome matching this fresh profile and port is this run's own
        steps.append(_cli(env, out, "00-start", "start", "probe the filmed page pointer", "--browser", "--url", url,
                          "--mode", "exclusive_desktop", "--pointer-motion", "filmed", "--session", str(session)))
        if steps[-1]["exit"] == 0:
            time.sleep(2.0)
            record["gestures_at_start"] = _gestures(session)
            for i, (label, expect) in enumerate(STEPS, start=1):
                look = _cli(env, out, f"{i:02d}-look", "look", "--session", str(session))
                ref = _ref(look["stdout"], label)
                steps.append(look)
                if ref is None:
                    steps.append({"name": f"{i:02d}-click", "label": label, "skipped": "not on the observation"})
                    break
                click = _cli(env, out, f"{i:02d}-click", "do", "click", str(ref), "--no-judge", "--session", str(session))
                time.sleep(1.0)  # let the page's log of this step arrive before the next one starts
                click.update(label=label, expect=expect, gestures_after=_gestures(session))
                steps.append(click)
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
        if launched:
            _close_owned_chrome(record)
        if record["front_pid_at_start"] and _front_pid() != record["front_pid_at_start"]:
            _activate_pid(record["front_pid_at_start"])
        record["front_pid_at_end"] = _front_pid()
        stop.set()
        sampler.join(timeout=5)
        server.shutdown()
        for step in steps:
            step["stdout"] = (step.get("stdout") or "")[-600:] if step.get("expect") else ""
            step["stderr"] = (step.get("stderr") or "")[-600:]
        (out / "run.json").write_text(json.dumps(record, indent=1, default=str))
        verdict = analyze(out)
        (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
        print(json.dumps({"chrome_closed": record.get("chrome_closed"), **verdict}, indent=1))


if __name__ == "__main__":
    main()
