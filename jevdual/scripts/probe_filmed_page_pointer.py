"""Probe for notebook prediction FP28 (which revises FP20): does a filmed browser take put the real
pointer on each page target, keep it there while the action is delivered, and refuse the ones it cannot
verify?

Starts a filmed ``start --browser`` session (``--mode exclusive_desktop --pointer-motion filmed``) on an
owned local fixture in a Chrome that Footwork launches on a fresh profile and its own port, then runs
``do``, in order (``STEPS``):

1. click Alpha, in view: clicked, with the pointer on it first;
2. click Beta by the trusted route: refused (``route_unfilmed``), no click, no pointer move;
3. click Beta: clicked;
4. click Covered, whose centre a fixed overlay covers: refused, no click, no pointer move;
5. click Forged, covered the same way, on a page that has replaced ``Document.prototype.elementFromPoint``
   to answer with Forged anywhere on it: refused the same way, because the driver reads in an isolated
   world;
6. click Edge, fixed half below the viewport: refused the same way;
7. click Clipped, whose lower part a scrolling box hides though its centre shows: refused the same way,
   because the page click would scroll the box after the pointer arrived;
8. click Turned, inside a rotated box: refused the same way (the driver reports no position for it);
9. type into Note, a text field without focus: refused (``target_unfocused``), no input, no pointer move;
10. click Note: clicked; the press focuses it, and in a document that has focus its style then moves
    it 40 px down;
11. type into Note: the pointer goes to where the field now is and the text is inserted;
12. type into Note again, which now holds text: refused (``replace_unfilmed``), no input, no pointer
    move, because replacing selects the text after the pointer was verified;
13. click Gamma, below the fold: refused, no click, no pointer move;
14. click Jump down, in view: clicked; its handler scrolls Gamma into view;
15. click Gamma again: clicked, with the pointer on it first, on the scrolled page.

Before the steps it parks the pointer on an empty part of the page, so no step starts on its target by
accident.

The fixture logs every trusted ``mouseover``, and inside each click handler and each input the last
trusted pointer event before it (move or over) with its client coordinates, the control's client
rectangle (for a click, where it was when the press began), the scroll offset and the device pixel
ratio. The session's pointer-gestures.jsonl records where each approach ended in screen points, and the
probe counts its lines after every step. ``analyze`` reads each step against its own evidence: events
are matched to a step by time, and gestures by their order. The verdict needs a device pixel ratio of 2,
the case in which page and screen units could differ, and the page's own record that its replaced hit
test answers Forged.

Two more records show the pointer at delivery and a press that reached nothing (FP28). The probe reads
the system pointer itself about every 5 ms for the whole run (pointer-samples.jsonl, not the session's
reading): a delivered step holds only if every sample from 250 ms before the page's event to 250 ms
after lies on the control's rectangle on screen, with at least twenty samples. And the page reports
every ``pointerdown``, ``mousedown``, ``mouseup``, ``click``, ``beforeinput`` and ``input`` it sees
anywhere, trusted or not: a refused step holds only if there was none during it, and a delivered step
only if all of them were on its own control.

Waits for an unlocked screen and 10 s of idle, then checks again, immediately before launching, that
the profile directory does not exist, the port is not Footwork's default or the sign-in test's and has
no listener, and no Chrome matches that profile and port. It signals only the Chrome the session says
its own start launched (process ID and start time both matching), restores the frontmost application,
and records whether Chrome closed; a Chrome it cannot prove is its own is left running and reported.

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
#: (label, operation, expectation) in order. The operation is "click", "trusted" (a click asked for by
#: the trusted route) or "type"; the expectation is "clicked", "typed", or the code a refusal must
#: carry. Gamma is refused until Jump down has scrolled it into view; Note until a click has focused it,
#: and again once it holds text.
STEPS = (
    ("Alpha", "click", "clicked"),
    ("Beta", "trusted", "route_unfilmed"),
    ("Beta", "click", "clicked"),
    ("Covered", "click", "target_unlocated"),
    ("Forged", "click", "target_unlocated"),
    ("Edge", "click", "target_unlocated"),
    ("Clipped", "click", "target_unlocated"),
    ("Turned", "click", "target_unlocated"),
    ("Note", "type", "target_unfocused"),
    ("Note", "click", "clicked"),
    ("Note", "type", "typed"),
    ("Note", "type", "replace_unfilmed"),
    ("Gamma", "click", "target_unlocated"),
    ("Jump down", "click", "clicked"),
    ("Gamma", "click", "clicked"),
)
DELIVERED = ("clicked", "typed")
#: what a refused step's refusal must also say, where the prediction names the reason: by label, or by
#: label and code where a control is refused more than one way
REASONS = {"Covered": "another element is at its centre", "Forged": "another element is at its centre",
           "Clipped": "container hides part of it", "Turned": "(transformed)",
           ("Note", "replace_unfilmed"): "types only into an empty field"}


def reason(label: str, expect: str) -> str:
    return REASONS.get((label, expect)) or REASONS.get(label, "")
#: what the type steps send; one word, so the command line carries it as one argument
TYPED = "footwork"

#: viewport CSS px with no button, overlay or fixed element near it
EMPTY_SPOT = (520, 200)
#: the probe's own pointer samples from this long before a delivery's page event to this long after
#: must all lie on the control, and there must be at least ``MIN_SAMPLES`` of them (FP28)
DELIVERY_WINDOW_S = 0.25
MIN_SAMPLES = 20
SAMPLE_EVERY_S = 0.005

FIXTURE = """<!doctype html>
<meta charset="utf-8">
<title>Footwork filmed page pointer fixture</title>
<style>
  #note { position: absolute; left: 620px; top: 130px; width: 140px; height: 30px; box-sizing: border-box }
  #note:focus { top: 170px }
</style>
<body style="font: 16px system-ui; margin: 0">
<div style="position: relative; height: 2600px">
  <button type="button" id="alpha" style="position: absolute; left: 40px; top: 60px; width: 140px; height: 44px">Alpha</button>
  <button type="button" id="beta" style="position: absolute; left: 620px; top: 330px; width: 140px; height: 44px">Beta</button>
  <button type="button" id="covered" style="position: absolute; left: 40px; top: 200px; width: 140px; height: 44px">Covered</button>
  <button type="button" id="jump" style="position: absolute; left: 300px; top: 60px; width: 140px; height: 44px">Jump down</button>
  <button type="button" id="gamma" style="position: absolute; left: 240px; top: 1900px; width: 140px; height: 44px">Gamma</button>
  <button type="button" id="forged" style="position: absolute; left: 620px; top: 60px; width: 140px; height: 44px">Forged</button>
  <input type="text" id="note" aria-label="Note">
  <div id="scroller" style="position: absolute; left: 40px; top: 300px; width: 200px; height: 60px; overflow: auto">
    <div style="position: relative; height: 300px">
      <button type="button" id="clipped" style="position: absolute; left: 20px; top: 30px; width: 140px; height: 44px">Clipped</button>
    </div>
  </div>
  <div id="turner" style="position: absolute; left: 300px; top: 300px; width: 180px; height: 70px; transform: rotate(8deg)">
    <button type="button" id="turned" style="position: absolute; left: 20px; top: 13px; width: 140px; height: 44px">Turned</button>
  </div>
</div>
<div id="lid" style="position: absolute; left: 80px; top: 205px; width: 60px; height: 34px; background: #c33"></div>
<div id="lid2" style="position: absolute; left: 660px; top: 65px; width: 60px; height: 34px; background: #c33"></div>
<button type="button" id="edge" style="position: fixed; left: 480px; bottom: -22px; width: 140px; height: 44px">Edge</button>
<script>
const now = () => (performance.timeOrigin + performance.now()) / 1000;
const post = (type, detail) => fetch('/log', {method: 'POST', keepalive: true,
  body: JSON.stringify({t: now(), type, detail})});
const control = (el) => (el && el.closest) ? el.closest('button, input') : null;
const named = (c) => c.getAttribute('aria-label') || c.textContent;
const label = (el) => control(el) ? named(control(el)) : (el && (el.id || el.tagName)) || null;
// This page answers its own hit test: asked about any point of Forged, it names Forged, though the lid
// covers its centre. A reader in the page's script world is told the button is on top.
const forged = document.getElementById('forged');
const nativeHit = Document.prototype.elementFromPoint;
Document.prototype.elementFromPoint = function (x, y) {
  const r = forged.getBoundingClientRect();
  return (x >= r.left && x <= r.right && y >= r.top && y <= r.bottom) ? forged : nativeHit.call(this, x, y);
};
const state = () => ({scroll: [window.scrollX, window.scrollY], dpr: window.devicePixelRatio,
  viewport: [window.innerWidth, window.innerHeight], page_focused: document.hasFocus(),
  pinch: window.visualViewport ? window.visualViewport.scale : null});
let lastPointer = null;
// where a control was when the press on it began: a field can move when the press focuses it
let press = null;
document.addEventListener('pointerdown', (e) => {
  const c = control(e.target);
  press = c ? {control: c, rect: c.getBoundingClientRect()} : null;
}, true);
for (const type of ['mousemove', 'mouseover']) document.addEventListener(type, (e) => {
  if (!e.isTrusted) return;
  lastPointer = {t: now(), type, target: label(e.target), x: e.clientX, y: e.clientY};
  if (type === 'mouseover') post('trusted_mouseover', lastPointer);
}, true);
for (const b of document.querySelectorAll('button, input')) {
  b.addEventListener('click', (e) => {
    const r = (press && press.control === b) ? press.rect : b.getBoundingClientRect();
    post('click_handler', {button: named(b), trusted: e.isTrusted, last_trusted_pointer: lastPointer,
      rect: [r.x, r.y, r.width, r.height], ...state()});
    if (b.id === 'jump') window.scrollTo(0, 1500);
  });
}
// every press and insertion the page sees, anywhere, trusted or not: a refused step must show none,
// and a delivered one only its own control's
for (const type of ['pointerdown', 'mousedown', 'mouseup', 'click', 'beforeinput', 'input'])
  window.addEventListener(type, (e) => post('page_event', {event: type, trusted: e.isTrusted,
    target: label(e.target), x: 'clientX' in e ? e.clientX : null, y: 'clientY' in e ? e.clientY : null}), true);
document.getElementById('note').addEventListener('input', (e) => {
  const b = e.target, r = b.getBoundingClientRect();
  post('input', {field: named(b), value: b.value, trusted: e.isTrusted, last_trusted_pointer: lastPointer,
    rect: [r.x, r.y, r.width, r.height], ...state()});
});
window.addEventListener('scroll', () => post('scrolled', {y: window.scrollY}), {passive: true});
window.addEventListener('load', () => {
  const r = forged.getBoundingClientRect();
  post('loaded', {dpr: window.devicePixelRatio, viewport: [window.innerWidth, window.innerHeight],
    page_says_at_forged: label(document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2)),
    browser_says_at_forged: label(nativeHit.call(document, r.left + r.width / 2, r.top + r.height / 2))});
});
</script>
"""


def _ref(text: str, label: str) -> int | None:
    match = re.search(rf"\[\s*(\d+)\]\s+\S+\s+'{re.escape(label)}'", text)
    return int(match.group(1)) if match else None


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _inside(point, rect) -> bool:
    x, y = point
    rx, ry, rw, rh = rect
    return rx <= x <= rx + rw and ry <= y <= ry + rh


def _samples(path: Path) -> list[tuple[float, float, float]] | None:
    """The probe's pointer samples as (time, x, y) in screen points, or None when there is no readable
    record of them."""
    try:
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        return [(float(t), float(x), float(y)) for t, x, y in rows]
    except (OSError, ValueError, TypeError):
        return None


def _sample_pointer(out: Path, stop: threading.Event, stats: dict) -> None:
    """The system pointer's position about every 5 ms as ``[t, x, y]`` rows, read by this process from
    the window server and not through the session, with the count and the largest gap in ``stats``."""
    import Quartz

    count, largest_gap, previous = 0, 0.0, time.time()
    with (out / "pointer-samples.jsonl").open("a") as stream:
        while not stop.is_set():
            at = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
            now = time.time()
            stream.write(f"[{now:.4f}, {at.x:.2f}, {at.y:.2f}]\n")
            count, largest_gap, previous = count + 1, max(largest_gap, now - previous), now
            stop.wait(SAMPLE_EVERY_S)
    stats.update(samples=count, largest_gap_s=round(largest_gap, 4))


class _Joined:
    """Several threads joined as one."""

    def __init__(self, *threads: threading.Thread) -> None:
        self.threads = threads

    def join(self, timeout: float | None = None) -> None:
        for thread in self.threads:
            thread.join(timeout=timeout)


def analyze(out: Path) -> dict:
    """Each step's verdict from its own evidence.

    A clicked step holds when its command succeeded; the only click handler the page ran during the
    step was that control's, once, and nothing was typed; the last trusted pointer event before the
    handler was on that control, at client coordinates inside its rectangle as it was when the press
    began; and the step's one new gesture is an approach to that control that arrived inside that
    rectangle. That pointer event must have happened during the step, unless the approach posted
    nothing because the pointer was already there. A typed step holds the same way about the page's one
    input event during the step, with no click handler run, the field's rectangle read at the input, and
    the field then holding exactly the text sent. A delivered step also needs the probe's own pointer
    samples from ``DELIVERY_WINDOW_S`` before that page event to as long after it to lie, every one, on
    the control's rectangle on screen, at least ``MIN_SAMPLES`` of them, and every press or insertion
    the page saw during the step to be on that control. A refused step holds when the command reported
    the step's refusal code (and reason, where one is named), the page ran no click handler and saw no
    input, press or insertion of any kind anywhere during the step, and the step added no gesture. The
    whole run holds only when the start and the
    park succeeded, every delivered step reported a device pixel ratio of 2 and a pinch scale of 1, the
    page recorded that its own hit test answers Forged where the browser's does not, the run recorded
    the Chrome its start launched and that it closed, and no cleanup step failed."""
    try:
        run = json.loads((out / "run.json").read_text())
        content = json.loads((out / "session/session.json").read_text())["filmed"]["content"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {"held": False, "unreadable": f"{type(exc).__name__}: {exc}"}
    events = _jsonl(out / "page-events.jsonl")
    handlers = [e for e in events if e.get("type") == "click_handler"]
    inputs = [e for e in events if e.get("type") == "input"]
    seen_by_page = [e for e in events if e.get("type") == "page_event"]
    samples = _samples(out / "pointer-samples.jsonl")
    gestures = _jsonl(out / "session/pointer-gestures.jsonl")
    tried = [s for s in run.get("steps", []) if s.get("expect")]
    verdicts, seen = [], run.get("gestures_at_start", 0)
    for step in tried:
        label, op, expect = step["label"], step.get("op"), step["expect"]
        window = (step["t_start"], step["t_end"] + 1.0)

        def during(logged, key, window=window, label=label):
            mine = [e["detail"] | {"t": e["t"]} for e in logged if window[0] <= e["t"] <= window[1]]
            return mine, [e for e in mine if e.get(key) == label]

        clicks, my_clicks = during(handlers, "button")
        typed, my_typed = during(inputs, "field")
        reached, on_control = during(seen_by_page, "target")
        new = gestures[seen:step.get("gestures_after", seen)]
        seen = step.get("gestures_after", seen)
        v: dict = {"label": label, "op": op, "expect": expect, "exit": step.get("exit"),
                   "handlers": len(my_clicks), "inputs": len(my_typed),
                   "other_handlers": sorted({str(h.get("button")) for h in clicks if h.get("button") != label}),
                   "page_events": len(reached),
                   "page_events_elsewhere": sorted({f"{e.get('event')} on {e.get('target')}" for e in reached
                                                    if e.get("target") != label}),
                   "new_gestures": [(g.get("kind"), g.get("label"), g.get("outcome")) for g in new]}
        if expect not in DELIVERED:
            said = step.get("stdout", "") + step.get("stderr", "")
            v["said_code"] = expect in said
            v["said_reason"] = reason(label, expect) in said
            v["held"] = bool(v["said_code"] and v["said_reason"] and not clicks and not typed and not new
                             and not reached)
        else:
            if expect == "clicked":
                event = my_clicks[0] if len(clicks) == 1 and len(my_clicks) == 1 and not typed else None
            else:
                event = my_typed[0] if len(typed) == 1 and len(my_typed) == 1 and not clicks else None
            arrived = (len(new) == 1 and new[0].get("kind") == "approach" and new[0].get("label") == label
                       and new[0].get("outcome") == "arrived" and new[0].get("final_location"))
            if event is not None:
                pointer = event.get("last_trusted_pointer") or {}
                v["pointer_target"] = pointer.get("target")
                v["pointer_during_step"] = bool(pointer.get("t") and window[0] <= pointer["t"] <= event["t"])
                try:
                    v["pointer_inside"] = _inside((float(pointer["x"]), float(pointer["y"])), event["rect"])
                except (KeyError, TypeError, ValueError):
                    v["pointer_inside"] = False
                v["event_trusted"], v["scroll"], v["dpr"] = event.get("trusted"), event.get("scroll"), event.get("dpr")
                v["pinch"], v["page_focused"], v["rect"] = event.get("pinch"), event.get("page_focused"), event.get("rect")
                if expect == "typed":
                    v["value"] = event.get("value")
            if event is not None and arrived:
                x, y, w, h = event["rect"]
                v["control_screen_rect"] = (content[0] + x, content[1] + y, w, h)
                v["gesture_end"] = new[0]["final_location"]
                v["end_inside"] = _inside(new[0]["final_location"], v["control_screen_rect"])
                # an approach that posted nothing started on its target: the page saw no new pointer event
                v["already_there"] = new[0].get("posted_samples") == []
                # the pointer at delivery, by the probe's own reading around the page's event
                around = [s for s in samples or []
                          if event["t"] - DELIVERY_WINDOW_S <= s[0] <= event["t"] + DELIVERY_WINDOW_S]
                v["samples_around_delivery"] = len(around)
                v["samples_off_control"] = sum(1 for s in around if not _inside(s[1:], v["control_screen_rect"]))
                v["pointer_on_control_at_delivery"] = (len(around) >= MIN_SAMPLES and v["samples_off_control"] == 0)
            v["held"] = bool(step.get("exit") == 0 and event is not None and arrived
                             and v.get("pointer_on_control_at_delivery") and len(reached) == len(on_control) > 0
                             and v.get("pointer_target") == label and v.get("pointer_inside")
                             and (v.get("pointer_during_step") or v.get("already_there"))
                             and v.get("end_inside")
                             and (expect != "typed" or v.get("value") == TYPED))
        verdicts.append(v)
    last = verdicts[-1] if verdicts else {}
    scrolled = bool(last.get("label") == "Gamma" and (last.get("scroll") or [0, 0])[1] > 0)
    complete = [(v["label"], v["op"], v["expect"]) for v in verdicts] == list(STEPS)
    delivered = [v for v in verdicts if v["expect"] in DELIVERED]
    ratios = [v.get("dpr") for v in delivered]
    scale = bool(ratios) and all(ratio == 2 for ratio in ratios)
    pinches = [v.get("pinch") for v in delivered]
    unpinched = bool(pinches) and all(pinch == 1 for pinch in pinches)
    setup = {name: next((s.get("exit") for s in run.get("steps", []) if s.get("name") == name), None)
             for name in ("00-start", "00-park")}
    owned = bool(run.get("chrome_launch")) and run.get("chrome_closed") is True and not run.get("cleanup_errors")
    loaded = next((e.get("detail") or {} for e in events if e.get("type") == "loaded"), {})
    # the Forged step tests something only if the page's replaced hit test does answer Forged there
    forgery = loaded.get("page_says_at_forged") == "Forged" and loaded.get("browser_says_at_forged") != "Forged"
    # for the record, not the verdict: the field moves on focus only in a document that has focus
    note = {v["expect"]: v.get("rect") for v in verdicts if v["label"] == "Note" and v["expect"] in DELIVERED}
    moved = bool(note.get("clicked") and note.get("typed") and note["clicked"] != note["typed"])
    return {"steps": verdicts, "complete": complete, "gamma_clicked_after_scrolling": scrolled,
            "note_moved_when_focused": moved, "pointer_samples": None if samples is None else len(samples),
            "pointer_sampler": run.get("pointer_sampler"),
            "device_pixel_ratios": ratios, "scale_factor_tested": scale, "pinch_scales": pinches,
            "setup_exits": setup, "own_chrome_closed": owned, "page_forges_its_hit_test": forgery,
            "held": (complete and scrolled and scale and unpinched and owned and forgery
                     and all(code == 0 for code in setup.values())
                     and all(v["held"] for v in verdicts))}


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def preflight(out: Path, profile: str | None, port: str | None, *, again: bool = False) -> str | None:
    """Why this run may not start, or None. Nothing here launches or signals anything. ``again`` is the
    second reading, immediately before the launch, when ``out`` is this run's own directory."""
    from jevdual.browser_driver import chrome_pid

    if not out.is_absolute() or (out.exists() and not again):
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


def _launched_chrome(session: Path, start_stdout: str) -> dict | None:
    """The Chrome this run's start says it launched, as ``{pid, incarnation}``, or None.

    From the session's record when the start finished; from the line the start prints as soon as it has
    bound the browser when it did not. A browser the start found already running is not this run's."""
    try:
        launch = json.loads((session / "session.json").read_text()).get("browser_launch") or {}
    except (OSError, ValueError):
        launch = {}
    if not launch:
        said = re.search(r"footwork's Chrome pid (\d+) started ([0-9.]+): (launched by this start|already running)",
                         start_stdout)
        if said:
            launch = {"pid": int(said.group(1)), "incarnation": float(said.group(2)),
                      "new_process": said.group(3) == "launched by this start"}
    if launch.get("new_process") is not True:
        return None
    try:
        return {"pid": int(launch["pid"]), "incarnation": float(launch["incarnation"])}
    except (KeyError, TypeError, ValueError):
        return None


def _close_owned_chrome(record: dict, launch: dict | None) -> None:
    """SIGTERM the Chrome this run's start launched, and only that process: the one matching the fresh
    profile and port must have the recorded process ID and start time. Records whether it went, or why
    nothing was signalled."""
    import psutil
    from jevdual.browser_driver import chrome_pid

    record["chrome_launch"] = launch
    try:
        pid = chrome_pid()
    except RuntimeError as exc:  # more than one Chrome matches: none of them is provably this run's
        record["chrome_closed"], record["chrome_not_signalled"] = False, str(exc)
        return
    record["chrome_pid"] = pid
    if pid is None:
        record["chrome_closed"] = True
        return
    try:
        started = psutil.Process(pid).create_time()
    except psutil.Error:
        started = None
    if launch is None or pid != launch["pid"] or started != launch["incarnation"]:
        record["chrome_closed"] = False
        record["chrome_not_signalled"] = ("the session did not record launching it" if launch is None
                                          else "it is not the process the session launched")
        return
    os.kill(pid, signal.SIGTERM)
    closed = False
    for _ in range(50):
        try:
            if psutil.Process(pid).create_time() != started:
                closed = True
                break
        except psutil.Error:
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
    record["pointer_sampler"] = {}
    front = threading.Thread(target=_sample_front, args=(out, stop), daemon=True)
    pointer = threading.Thread(target=_sample_pointer, args=(out, stop, record["pointer_sampler"]), daemon=True)
    front.start()
    pointer.start()
    sampler = _Joined(front, pointer)
    start_stdout = ""
    try:
        # the idle gate can wait a long time: read the launch conditions again, right before the launch
        refusal = preflight(out, os.environ.get("FOOTWORK_CHROME_PROFILE"), os.environ.get("FOOTWORK_CHROME_PORT"),
                            again=True)
        if refusal:
            record["not_started"] = refusal
            raise SystemExit(f"not starting: {refusal}")
        steps.append(_cli(env, out, "00-start", "start", "probe the filmed page pointer", "--browser", "--url", url,
                          "--mode", "exclusive_desktop", "--pointer-motion", "filmed", "--session", str(session)))
        start_stdout = steps[-1]["stdout"]
        if steps[-1]["exit"] == 0:
            time.sleep(2.0)
            # a filmed page action needs the browser in front (scene_changed otherwise); arranging the
            # scene is the operator's part, so the probe does it and records whether it had to
            chrome = json.loads((session / "session.json").read_text()).get("pid")
            record["chrome_front_after_start"] = _front_pid() == chrome
            if chrome and not record["chrome_front_after_start"]:
                _activate_pid(chrome)
                time.sleep(1.0)
                record["chrome_front_after_activation"] = _front_pid() == chrome
            # off every button, so no step starts with the pointer already on its target
            steps.append(_cli(env, out, "00-park", "park", str(EMPTY_SPOT[0]), str(EMPTY_SPOT[1]),
                              "--session", str(session)))
            time.sleep(0.5)
            record["gestures_at_start"] = _gestures(session)
            for i, (label, op, expect) in enumerate(STEPS, start=1):
                look = _cli(env, out, f"{i:02d}-look", "look", "--session", str(session))
                ref = _ref(look["stdout"], label)
                steps.append(look)
                if ref is None:
                    # the verdict is then incomplete; the remaining steps still give their evidence
                    steps.append({"name": f"{i:02d}-{op}", "label": label, "skipped": "not on the observation"})
                    continue
                words = {"click": ("click", str(ref)), "trusted": ("click", str(ref), "--route", "trusted"),
                         "type": ("type", str(ref), TYPED)}[op]
                done = _cli(env, out, f"{i:02d}-{op}", "do", *words, "--no-judge", "--session", str(session))
                time.sleep(1.0)  # let the page's log of this step arrive before the next one starts
                done.update(label=label, op=op, expect=expect, gestures_after=_gestures(session))
                steps.append(done)
    finally:
        _finish(record, out, session, start_stdout, stop, sampler, server)


def _retire_holder(record: dict, session: Path) -> None:
    from jevdual import browser_session_holder as bsh

    try:
        holder = json.loads((session / "session.json").read_text()).get("browser_holder") or {}
    except (OSError, ValueError):
        holder = {}
    if holder:
        record["holder_stop"] = asyncio.run(bsh.retire(bsh.recorded_runtime(holder, session), expected=holder))


def _restore_front(record: dict) -> None:
    """Bring back the application that was frontmost when the run began, and raise when it did not come
    back: the caller records that as a cleanup error, and a run with one does not hold."""
    before = record.get("front_pid_at_start")
    if before and _front_pid() != before:
        _activate_pid(before)
        for _ in range(10):
            if _front_pid() == before:
                break
            time.sleep(0.2)
    record["front_pid_at_end"] = _front_pid()
    if not before:
        raise RuntimeError("the run did not record which application was frontmost when it began")
    if record["front_pid_at_end"] != before:
        raise RuntimeError(f"pid {before} was frontmost at the start and pid {record['front_pid_at_end']} is at the end")


def _finish(record: dict, out: Path, session: Path, start_stdout: str, stop, sampler, server) -> dict:
    """Clean up and write the run's records. Each step runs whatever the others raise; what raised is
    kept in ``cleanup_errors``, and a run with any does not hold."""
    record["finished"] = time.time()
    errors: list[str] = record.setdefault("cleanup_errors", [])

    def attempt(name: str, step, *args) -> None:
        try:
            step(*args)
        except Exception as exc:  # noqa: BLE001 - one failed cleanup step must not skip the others
            errors.append(f"{name}: {type(exc).__name__}: {str(exc)[:200]}")

    def stop_helpers() -> None:
        stop.set()
        sampler.join(timeout=5)
        server.shutdown()

    attempt("holder", _retire_holder, record, session)
    attempt("chrome", lambda: _close_owned_chrome(record, _launched_chrome(session, start_stdout)))
    attempt("front", _restore_front, record)
    attempt("helpers", stop_helpers)
    for step in record.get("steps", []):
        step["stdout"] = (step.get("stdout") or "")[-600:] if step.get("expect") else ""
        step["stderr"] = (step.get("stderr") or "")[-600:]
    (out / "run.json").write_text(json.dumps(record, indent=1, default=str))
    verdict = analyze(out)
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    print(json.dumps({"chrome_closed": record.get("chrome_closed"),
                      "chrome_not_signalled": record.get("chrome_not_signalled"),
                      "cleanup_errors": errors, **verdict}, indent=1))
    return verdict


if __name__ == "__main__":
    main()
