"""Probe for notebook prediction FP46 (which revises FP37, FP29, FP28 and FP20): does a filmed browser take put
the real pointer on each page target, keep it there while every event of the action is delivered, and
refuse or stop where it cannot?

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
7. click Clipped, whose lower part a scrolling box hides though its centre shows: refused the same way;
8. click Turned, inside a rotated box: refused the same way (the driver reports no position for it);
9. click Hidden, whose style hides the pointer (``cursor: none``): refused the same way, because the
   film would show no pointer on it;
10. click Shy, which moves 300 px away when an untrusted ``pointerover`` reaches it (the click's own
    first hover event; the real pointer's arrival does not move it): the pointer goes to it, that
    event moves it, and nothing more is sent, no press and no click;
11. click Dodge, which moves 300 px away when it is pressed: the pointer goes to it, ``pointerdown`` and
    ``mousedown`` are sent, and no release or click is, because it is no longer under the pointer;
12. type into Note, a text field without focus: refused (``target_unfocused``), no input, no pointer move;
13. click Note: clicked; the press focuses it;
14. type into Note: the text is inserted with the pointer on the field;
15. type into Note again, which now holds text: refused (``replace_unfilmed``), no input, no pointer
    move, because replacing selects the text after the pointer was verified;
16. click Gamma, below the fold: refused, no click, no pointer move;
17. click Jump down, in view: clicked; its handler scrolls Gamma into view;
18. click Gamma again: clicked, with the pointer on it first, on the scrolled page.

Before the steps it parks the pointer on an empty part of the page, so no step starts on its target by
accident.

The fixture logs every trusted ``mouseover``; inside each click handler, each input and each move of Shy
or Dodge, the last trusted pointer event before it (move or over) with its client coordinates, the
control's client rectangle, the scroll offset and the device pixel ratio; and every ``pointerdown``,
``mousedown``, ``pointerup``, ``mouseup``, ``click``, ``beforeinput`` and ``input`` it sees anywhere,
trusted or not, numbered in the order it saw them, each with its client coordinates and the rectangle of
the control it was on at that moment. The session's pointer-gestures.jsonl records where each approach
ended in screen points, and the probe counts its lines after every step. The probe also reads the system
pointer itself about every 5 ms for the whole run (pointer-samples.jsonl, not the session's reading).

``analyze`` reads each step against its own evidence: events are matched to a step by time, and gestures
by their order. A clicked step needs the page to have seen exactly ``pointerdown``, ``mousedown``,
``pointerup``, ``mouseup``, ``click``, in that order, all on its control, each at a point inside the
control's rectangle as it was at that event; a typed step exactly one ``input``; Dodge exactly
``pointerdown`` and ``mousedown``; Shy and every refused step none at all. For every one of those
events, the probe's own samples from 250 ms before the earliest moment it can have happened to 250 ms
after the latest must all lie on that rectangle on screen, at least twenty of them, with no gap between
consecutive samples or to either end of that window longer than 50 ms. The verdict needs a device pixel ratio of 2, the case in which page and screen units
could differ, and the page's own record that its replaced hit test answers Forged.

Three things make that reading sound, and the run does not hold without them (FP46, FP54):

- the page's clock and the probe's are two clocks, so a page record has no exact time in the probe's.
  It has an interval. The probe received the record at a time of its own, R, so the record was made
  before R; and the page reports, by its own clock, how long after making the record it had the answer,
  d, so the record was made after R - d. The page's clock is coarsened by the browser: each reading
  is assumed to be within a grain (1 ms) of the true one, so d, the difference of two readings, is
  taken two grains longer than reported, and a tenth of a percent longer again for any difference in
  the two clocks' rates. The page measures the step of its clock when it loads and reports it. That
  is a diagnostic of its resolution: a step coarser than the grain shows the assumption false and
  the run does not hold; a fine one does not show it true. Records the page numbered earlier bound a record below too, and ones it
  numbered later above (``_timer``): by their numbers, which are an order with no ties, and never by
  comparing timestamps, since two records with one timestamp were not made at one moment. Nothing here
  assumes the two clocks keep a constant difference.
  A record of something done to the page must be placed within 20 ms this way, and everything read
  against it uses the whole interval: the samples must hold from 250 ms before its earliest moment to
  250 ms after its latest. As a check on the run, the difference between the clocks is also bounded
  from all the posts together (``_clock``); bounds that cross mean a clock was changed;
- every press, release, insertion, click handler, input and move the page recorded, at any time in the
  run, must lie, by its whole interval, inside the interval of exactly one tried step, where it is
  judged. A record between two steps is not ignored, and one whose interval reaches across the start or
  the end of a step is ambiguous and the run does not hold. Each step judges every record that could
  lie in it;
- the page numbers every record it makes, and the numbers received must run from one with none missing
  or repeated, from a single load, through a fence. When the last step's interval has closed, the
  probe's server answers the page's next post with a request for a fence; the page makes its fence
  record only on reading that answer, so the fence was made after the interval closed whatever the
  clocks say, and every record the page made before it has a lower number. The probe waits for the
  fence before it closes Chrome. The run is accounted for through the fence, and the fence is the
  cutoff for what must be whole: a number missing after it is reported and does not fail the run, and
  the verdict claims nothing about what the page did then. One thing is stricter than the cutoff
  requires: a record of something done to the page is judged by when it was made, wherever its number
  falls, so one made after the last step fails the run when it is in hand, before the fence or after
  it. Nothing should be acting on the page by then.

What the samples cannot show: where the pointer was between two of them. They are about 5 ms apart and
at most 50; an excursion off a control and back inside one gap is not excluded by this probe.

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
import bisect
import itertools
import json
import math
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
#: the trusted route) or "type"; the expectation is "clicked", "typed", "unpressed" (approached, and
#: stopped by the click's own hover events before any press), "pressed" (pressed, and stopped before the
#: release), or the code a refusal before anything moved must carry. Gamma is refused until Jump down has
#: scrolled it into view; Note until a click has focused it, and again once it holds text.
STEPS = (
    ("Alpha", "click", "clicked"),
    ("Beta", "trusted", "route_unfilmed"),
    ("Beta", "click", "clicked"),
    ("Covered", "click", "target_unlocated"),
    ("Forged", "click", "target_unlocated"),
    ("Edge", "click", "target_unlocated"),
    ("Clipped", "click", "target_unlocated"),
    ("Turned", "click", "target_unlocated"),
    ("Hidden", "click", "target_unlocated"),
    ("Shy", "click", "unpressed"),
    ("Dodge", "click", "pressed"),
    ("Note", "type", "target_unfocused"),
    ("Note", "click", "clicked"),
    ("Note", "type", "typed"),
    ("Note", "type", "replace_unfilmed"),
    ("Gamma", "click", "target_unlocated"),
    ("Jump down", "click", "clicked"),
    ("Gamma", "click", "clicked"),
)
DELIVERED = ("clicked", "typed")
#: what the page must see during each kind of step that reaches it: exactly these events, in this order,
#: all on the step's control (FP37). Any other expectation is a refusal, during which it must see none.
EXPECTED_EVENTS = {"clicked": ("pointerdown", "mousedown", "pointerup", "mouseup", "click"), "typed": ("input",),
                   "pressed": ("pointerdown", "mousedown"), "unpressed": ()}
#: what the command must say of a click that stopped part way
SAID = {"unpressed": ("no press or click was sent",), "pressed": ("after mousedown", "no click event was sent")}
#: the event that moves each control that moves, as the page records it
MOVED_BY = {"Shy": "pointerover", "Dodge": "mousedown"}
#: what a refused step's refusal must also say, where the prediction names the reason: by label, or by
#: label and code where a control is refused more than one way
REASONS = {"Covered": "another element is at its centre", "Forged": "another element is at its centre",
           "Clipped": "container hides part of it", "Turned": "(transformed)",
           "Hidden": "hides or replaces the pointer",
           ("Note", "replace_unfilmed"): "types only into an empty field"}


def reason(label: str, expect: str) -> str:
    return REASONS.get((label, expect)) or REASONS.get(label, "")
#: what the type steps send; one word, so the command line carries it as one argument
TYPED = "footwork"

#: viewport CSS px with no button, overlay or fixed element near it
EMPTY_SPOT = (520, 200)
#: the probe's own pointer samples from this long before each event the page saw to this long after
#: must all lie on the control, at least ``MIN_SAMPLES`` of them (FP28), and no two consecutive ones, nor
#: either end of that window and the sample nearest it, may be further apart than ``MAX_GAP_S`` (FP37):
#: a sampler that stalled across the event saw nothing of it
DELIVERY_WINDOW_S = 0.25
MIN_SAMPLES = 20
MAX_GAP_S = 0.05
SAMPLE_EVERY_S = 0.005
#: the two bounds on the difference between the probe's clock and the page's must agree this closely
#: for a page time to be read against the pointer samples (FP46)
MAX_CLOCK_WIDTH_S = 0.02
#: how far a time the page reports is assumed to be from the true reading of its clock. Chrome coarsens
#: performance.now() to 0.1 ms (0.005 ms in an isolated context). The page measures the step of its
#: own clock when it loads; one coarser than this shows the assumption false, and a finer one is only
#: a diagnostic of resolution.
PAGE_CLOCK_GRAIN_S = 0.001
#: by how much the page's clock and the probe's may differ in rate: an elapsed page time is taken to be
#: at most this fraction longer in the probe's clock. System clocks are slewed by far less.
CLOCK_RATE_SLACK = 0.001
#: how long the probe waits for the page's fence record once it has asked for it
FENCE_WAIT_S = 6.0
#: the page's records of something done to it; each must fall in one tried step's interval
ACTION_RECORDS = ("page_event", "click_handler", "input", "moved")

FIXTURE = """<!doctype html>
<meta charset="utf-8">
<title>Footwork filmed page pointer fixture</title>
<style>
  #note { position: absolute; left: 620px; top: 130px; width: 140px; height: 30px; box-sizing: border-box }
</style>
<body style="font: 16px system-ui; margin: 0">
<div style="position: relative; height: 2600px">
  <button type="button" id="alpha" style="position: absolute; left: 40px; top: 60px; width: 140px; height: 44px">Alpha</button>
  <button type="button" id="beta" style="position: absolute; left: 620px; top: 330px; width: 140px; height: 44px">Beta</button>
  <button type="button" id="covered" style="position: absolute; left: 40px; top: 200px; width: 140px; height: 44px">Covered</button>
  <button type="button" id="jump" style="position: absolute; left: 300px; top: 60px; width: 140px; height: 44px">Jump down</button>
  <button type="button" id="gamma" style="position: absolute; left: 240px; top: 1900px; width: 140px; height: 44px">Gamma</button>
  <button type="button" id="forged" style="position: absolute; left: 620px; top: 60px; width: 140px; height: 44px">Forged</button>
  <button type="button" id="hidden" style="position: absolute; left: 300px; top: 130px; width: 140px; height: 44px; cursor: none">Hidden</button>
  <button type="button" id="shy" style="position: absolute; left: 40px; top: 130px; width: 140px; height: 44px">Shy</button>
  <button type="button" id="dodge" style="position: absolute; left: 300px; top: 200px; width: 140px; height: 44px">Dodge</button>
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
// n numbers the records in the order the page made them: several events of one click can carry the
// same time, and the posts need not arrive in order
let seq = 0;
// when each post was answered, by this page's clock: with the time it was made and the probe's time of
// receiving it, that bounds the difference between the two clocks on both sides
const acks = [];
// the fence: the probe's server asks for it in an answer once the last step's interval has closed, and
// the record is made here, on reading that answer, so it is later than the asking whatever the clocks
// say, and every record made before it has a lower number
let fenced = false;
const post = (type, detail) => {
  const n = ++seq;
  fetch('/log', {method: 'POST', keepalive: true, body: JSON.stringify({t: now(), n, type, detail})})
    .then((answer) => { acks.push([n, now()]); return answer.status === 200 ? answer.text() : ''; })
    .then((body) => { if (body === 'fence' && !fenced) { fenced = true; post('fence', {asked_in_answer_to: n}); } },
          () => {});
};
// a record twice a second whatever else happens: it carries the answers, and one made after the last
// step shows that everything numbered before it has arrived
setInterval(() => post('beat', {acks: acks.splice(0, 60)}), 500);
const box = (el) => { const r = el.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; };
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
for (const type of ['mousemove', 'mouseover']) document.addEventListener(type, (e) => {
  if (!e.isTrusted) return;
  lastPointer = {t: now(), type, target: label(e.target), x: e.clientX, y: e.clientY};
  if (type === 'mouseover') post('trusted_mouseover', lastPointer);
}, true);
for (const b of document.querySelectorAll('button, input')) {
  b.addEventListener('click', (e) => {
    post('click_handler', {button: named(b), trusted: e.isTrusted, last_trusted_pointer: lastPointer,
      rect: box(b), ...state()});
    if (b.id === 'jump') window.scrollTo(0, 1500);
  });
}
// every press, release and insertion the page sees, anywhere, trusted or not, with where the control it
// is on was at that moment (read before any listener of the control's own can move it): a refused step
// must show none, and a delivered one exactly its own control's, in order
for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click', 'beforeinput', 'input'])
  window.addEventListener(type, (e) => post('page_event', {event: type, trusted: e.isTrusted,
    target: label(e.target), x: 'clientX' in e ? e.clientX : null, y: 'clientY' in e ? e.clientY : null,
    rect: control(e.target) ? box(control(e.target)) : null}), true);
// Shy leaves when the click's own hover events reach it. The real pointer's arrival is a trusted event
// and does not move it, so the pointer can be put on it first.
const shy = document.getElementById('shy');
shy.addEventListener('pointerover', (e) => {
  if (e.isTrusted) return;
  const rect = box(shy);
  shy.style.top = '430px';
  post('moved', {control: 'Shy', by: 'pointerover', trusted: e.isTrusted, last_trusted_pointer: lastPointer,
    rect, ...state()});
});
// Dodge leaves when it is pressed
const dodge = document.getElementById('dodge');
dodge.addEventListener('mousedown', (e) => {
  const rect = box(dodge);
  dodge.style.top = '500px';
  post('moved', {control: 'Dodge', by: 'mousedown', trusted: e.isTrusted, last_trusted_pointer: lastPointer,
    rect, ...state()});
});
document.getElementById('note').addEventListener('input', (e) => {
  const b = e.target;
  post('input', {field: named(b), value: b.value, trusted: e.isTrusted, last_trusted_pointer: lastPointer,
    rect: box(b), ...state()});
});
window.addEventListener('scroll', () => post('scrolled', {y: window.scrollY}), {passive: true});
// the smallest step this page's clock takes, in seconds: the times above are no finer than this
const clockStep = () => {
  let least = Infinity;
  for (let i = 0; i < 50; i++) {
    const from = performance.now();
    let to = from;
    while (to === from) to = performance.now();
    least = Math.min(least, to - from);
  }
  return least / 1000;
};
window.addEventListener('load', () => {
  const r = forged.getBoundingClientRect();
  post('loaded', {dpr: window.devicePixelRatio, viewport: [window.innerWidth, window.innerHeight],
    clock_step_s: clockStep(),
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


def _bracket(samples, earliest: float, latest: float, rect) -> dict:
    """The probe's own pointer samples around a page record made between ``earliest`` and ``latest``
    (probe time), against screen rectangle ``rect``: how many there are in the window, how many lie off
    the rectangle, and the longest stretch of the window without one (between consecutive samples, or
    between an end of the window and the sample nearest it). The window runs from ``DELIVERY_WINDOW_S``
    before the earliest moment to as long after the latest. ``held`` needs enough samples, none off,
    and no such stretch longer than ``MAX_GAP_S``; a record with no bounded time does not hold."""
    if not (math.isfinite(earliest) and math.isfinite(latest)) or earliest > latest:
        return {"samples": 0, "off_control": 0, "untimed": True, "held": False}
    low, high = earliest - DELIVERY_WINDOW_S, latest + DELIVERY_WINDOW_S
    around = sorted(sample for sample in samples or [] if low <= sample[0] <= high)
    edges = [low, *(sample[0] for sample in around), high]
    gap = max(later - earlier for earlier, later in itertools.pairwise(edges))
    off = sum(1 for sample in around if not _inside(sample[1:], rect))
    return {"samples": len(around), "off_control": off, "largest_gap_s": round(gap, 4),
            "held": len(around) >= MIN_SAMPLES and off == 0 and gap <= MAX_GAP_S}


def _clock(received: list[dict]) -> dict:
    """How the page's clock and the probe's correspond, from the page's own posts.

    A record made at page time ``t`` and answered at page time ``r`` was received by the probe's server
    at probe time ``received``, between the two. With ``offset`` the probe's clock less the page's:
    ``t + offset <= received <= r + offset``, so every record bounds the offset above by
    ``received - t`` and every answered one bounds it below by ``received - r``. The page reports its
    answers in its ``beat`` records. ``held`` needs both bounds, not crossed (crossed bounds mean one of
    the clocks was changed during the run), and within ``MAX_CLOCK_WIDTH_S`` of each other. Each
    bound is loosened by ``PAGE_CLOCK_GRAIN_S``, since the page's times are that imprecise, so bounds
    do not cross for that reason alone. This is a check on the run and assumes one constant
    difference; no record's time is taken from it (``_timer``). ``offset_s`` is the midpoint, for the
    reader."""
    made = {e["n"]: e for e in received if isinstance(e.get("n"), int)}
    highs, lows = [], []
    for e in received:
        try:
            highs.append(float(e["received"]) - float(e["t"]))
        except (KeyError, TypeError, ValueError):
            pass
        answers = (e.get("detail") or {}).get("acks") if e.get("type") == "beat" else None
        for answer in answers if isinstance(answers, list) else []:
            try:
                n, answered = answer
                lows.append(float(made[n]["received"]) - float(answered))
            except (KeyError, TypeError, ValueError):
                pass
    if not highs or not lows:
        return {"held": False, "why": "the page's posts do not bound the clocks on both sides",
                "posts": len(highs), "answers": len(lows)}
    low, high = max(lows) - PAGE_CLOCK_GRAIN_S, min(highs) + PAGE_CLOCK_GRAIN_S
    width = high - low
    why = ("the bounds cross: a clock changed during the run" if width < -1e-6
           else f"the bounds are {width * 1000:.1f} ms apart" if width > MAX_CLOCK_WIDTH_S else None)
    return {"low_s": round(low, 4), "high_s": round(high, 4), "width_s": round(width, 4),
            "offset_s": (low + high) / 2, "posts": len(highs), "answers": len(lows),
            "held": why is None, **({"why": why} if why else {})}


def _elapsed(reported: float) -> float:
    """The most probe time that can have passed between two readings of the page's clock that differ by
    ``reported``: each reading may be a grain off, in opposite directions, and the clocks' rates may
    differ by the slack."""
    return (max(reported, 0.0) + 2 * PAGE_CLOCK_GRAIN_S) * (1 + CLOCK_RATE_SLACK)


def _timer(received: list[dict]):
    """``placed(record)`` and ``after(page_t)``: when, in the probe's clock, a page record was made, and
    the earliest that something at a page time can have happened, from the page's posts alone.

    A record made at page time ``t`` was received at probe time ``R``, so it was made before ``R``. If
    the page had its answer at page time ``r``, then at most ``r - t`` of page time passed between
    making it and a moment after the probe received it, so it was made after ``R - (r - t)``. The
    page's times are coarse, each assumed within ``PAGE_CLOCK_GRAIN_S`` of the true reading, and
    ``r - t`` is the difference of two of them, so the elapsed time is taken two grains longer than
    reported (``_elapsed``), and ``CLOCK_RATE_SLACK`` longer again in the probe's clock.

    The page numbers its records in the order it makes them, and that order has no ties. So a record
    is no earlier than any record numbered before it, and no later than any numbered after it:
    ``placed`` takes the latest lower bound among the records up to its number and the earliest
    receipt among those from its number on. Timestamps are not compared for this: two records with
    one timestamp were made at two moments, and which was first is their numbers. A record without a
    number has only the receipt of its own post above it and nothing below.

    A page event that was not posted (the last trusted pointer event) has a timestamp and no number.
    ``after`` bounds it below by the records whose timestamps are earlier than its own by two grains
    or more, which were therefore made before it.

    No difference between the two clocks is assumed constant: only that their rates differ by no more
    than ``CLOCK_RATE_SLACK``. A bound is infinite when no record gives it."""
    answered: dict[int, float] = {}
    for e in received:
        answers = (e.get("detail") or {}).get("acks") if e.get("type") == "beat" else None
        for answer in answers if isinstance(answers, list) else []:
            try:
                n, at = answer
                answered.setdefault(int(n), float(at))
            except (TypeError, ValueError):
                pass

    def own(e) -> tuple[float, float, float] | None:
        """(page time, earliest, latest) by the record's own post."""
        try:
            t, got = float(e["t"]), float(e["received"])
        except (KeyError, TypeError, ValueError):
            return None
        n = e.get("n")
        took = answered[n] - t if isinstance(n, int) and not isinstance(n, bool) and n in answered else None
        if took is None or took < -2 * PAGE_CLOCK_GRAIN_S:
            return t, -math.inf, got
        return t, got - _elapsed(took), got

    rows = [(e, bound) for e in received if (bound := own(e)) is not None]
    numbered = sorted(((e["n"], bound) for e, bound in rows
                       if isinstance(e.get("n"), int) and not isinstance(e.get("n"), bool)), key=lambda row: row[0])
    numbers = [n for n, _ in numbered]
    earliest = list(itertools.accumulate((bound[1] for _, bound in numbered), max))
    latest = list(itertools.accumulate((bound[2] for _, bound in reversed(numbered)), min))[::-1]
    by_time = sorted((bound[0], bound[1]) for _, bound in rows)
    times = [t for t, _ in by_time]
    earliest_by_time = list(itertools.accumulate((low for _, low in by_time), max))

    def placed(e) -> tuple[float, float]:
        bound = own(e)
        if bound is None:
            return -math.inf, math.inf
        n = e.get("n")
        if not isinstance(n, int) or isinstance(n, bool):
            return bound[1], bound[2]
        upto, since = bisect.bisect_right(numbers, n), bisect.bisect_left(numbers, n)
        return earliest[upto - 1], latest[since]

    def after(page_t: float) -> float:
        before = bisect.bisect_right(times, page_t - 2 * PAGE_CLOCK_GRAIN_S)
        return earliest_by_time[before - 1] if before else -math.inf

    return placed, after


def _rect(value) -> list[float] | None:
    try:
        x, y, w, h = (float(part) for part in value)
    except (TypeError, ValueError):
        return None
    return [x, y, w, h]


def analyze(out: Path) -> dict:
    """Each step's verdict from its own evidence.

    A step that reaches the page (``EXPECTED_EVENTS``) holds when:

    - the page saw, during the step, exactly the events its kind names, in that order, all on the step's
      control: five for a click, one ``input`` for a type, ``pointerdown`` and ``mousedown`` for the
      control that moves when pressed, none for the one that moves when hovered;
    - each of those events that has a position was at a point inside the control's rectangle as it was
      at that event, and the probe's own pointer samples around each of them hold (``_bracket``) on that
      rectangle on screen;
    - the page's one record of the step is the right one and nothing else ran: a click handler of that
      control for a click, the field's input for a type (the field then holding exactly the text sent),
      the control's own record that the named untrusted event moved it for the two that move (around
      which the samples must hold too);
    - the last trusted pointer event before that record was on the control, inside its rectangle, during
      the step (unless the approach posted nothing because the pointer was already there);
    - the step's one new gesture is an approach to that control that arrived inside that rectangle;
    - a clicked or typed step's command succeeded, and a stopped one's says what ``SAID`` names (its exit
      code is recorded and not judged).

    A refused step holds when the command reported the step's refusal code (and reason, where one is
    named), the page ran no click handler, saw no input, press, release or insertion of any kind
    anywhere, moved no control, and the step added no gesture.

    The whole run holds only when the start and the park succeeded, every step that reached the page
    reported a device pixel ratio of 2 and a pinch scale of 1, the page recorded that its own hit test
    answers Forged where the browser's does not, the run recorded the Chrome its start launched and that
    it closed, and no cleanup step failed."""
    try:
        run = json.loads((out / "run.json").read_text())
        content = json.loads((out / "session/session.json").read_text())["filmed"]["content"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {"held": False, "unreadable": f"{type(exc).__name__}: {exc}"}
    received = _jsonl(out / "page-events.jsonl")
    clock = _clock(received)
    numbers = [e.get("n") for e in received]
    whole = [n for n in numbers if isinstance(n, int) and not isinstance(n, bool)]
    # the fence is the cutoff for what must be whole: every number from one through the fence's (through
    # the last, when there is no fence), each once, and no record without a number anywhere
    fence = next((e for e in received if e.get("type") == "fence"), None)
    through = fence["n"] if fence is not None and isinstance(fence.get("n"), int) else max(whole, default=0)
    numbered = (bool(numbers) and len(whole) == len(numbers) and len(set(whole)) == len(whole)
                and set(range(1, through + 1)) <= set(whole))
    missing_after = sorted(set(range(through + 1, max(whole, default=0) + 1)) - set(whole))
    # each record with the interval of the probe's clock it was made in; "t" is the latest moment
    placed, after = _timer(received)
    events = []
    for e in received:
        if isinstance(e.get("t"), (int, float)):
            earliest, latest = placed(e)
            events.append(e | {"page_t": e["t"], "t_lo": earliest, "t": latest})
    # in the order the page made them
    events.sort(key=lambda e: (not isinstance(e.get("n"), int), e.get("n") if isinstance(e.get("n"), int) else 0))
    handlers = [e for e in events if e.get("type") == "click_handler"]
    inputs = [e for e in events if e.get("type") == "input"]
    moved = [e for e in events if e.get("type") == "moved"]
    seen_by_page = [e for e in events if e.get("type") == "page_event"]
    samples = _samples(out / "pointer-samples.jsonl")
    gestures = _jsonl(out / "session/pointer-gestures.jsonl")
    tried = [s for s in run.get("steps", []) if s.get("expect")]
    verdicts, seen = [], run.get("gestures_at_start", 0)

    def on_screen(rect):
        return (content[0] + rect[0], content[1] + rect[1], rect[2], rect[3])

    for step in tried:
        label, op, expect = step["label"], step.get("op"), step["expect"]
        window = (step["t_start"], step["t_end"] + 1.0)

        def during(logged, key, window=window, label=label):
            # every record that could lie in the step: its interval reaches into the step's
            mine = [(e.get("detail") or {}) | {"t": e["t"], "t_lo": e["t_lo"], "page_t": e["page_t"]}
                    for e in logged if e["t_lo"] <= window[1] and e["t"] >= window[0]]
            return mine, [e for e in mine if e.get(key) == label]

        clicks, my_clicks = during(handlers, "button")
        typed, my_typed = during(inputs, "field")
        moves, my_moves = during(moved, "control")
        reached, on_control = during(seen_by_page, "target")
        new = gestures[seen:step.get("gestures_after", seen)]
        seen = step.get("gestures_after", seen)
        said = step.get("stdout", "") + step.get("stderr", "")
        v: dict = {"label": label, "op": op, "expect": expect, "exit": step.get("exit"),
                   "handlers": len(my_clicks), "inputs": len(my_typed), "moves": len(my_moves),
                   "other_handlers": sorted({str(h.get("button")) for h in clicks if h.get("button") != label}),
                   "page_events": len(reached), "sequence": [str(e.get("event")) for e in reached],
                   "page_events_elsewhere": sorted({f"{e.get('event')} on {e.get('target')}" for e in reached
                                                    if e.get("target") != label}),
                   "new_gestures": [(g.get("kind"), g.get("label"), g.get("outcome")) for g in new]}
        if expect not in EXPECTED_EVENTS:
            v["said_code"] = expect in said
            v["said_reason"] = reason(label, expect) in said
            v["held"] = bool(v["said_code"] and v["said_reason"] and not clicks and not typed and not moves
                             and not new and not reached)
            verdicts.append(v)
            continue
        # the page's one record of this step, and nothing else
        if expect == "clicked":
            record = my_clicks[0] if len(clicks) == 1 and len(my_clicks) == 1 and not typed and not moves else None
        elif expect == "typed":
            record = my_typed[0] if len(typed) == 1 and len(my_typed) == 1 and not clicks and not moves else None
        else:
            record = (my_moves[0] if len(moves) == 1 and len(my_moves) == 1 and not clicks and not typed
                      and my_moves[0].get("by") == MOVED_BY.get(label) and my_moves[0].get("trusted") is False
                      else None)
        v["in_order"] = v["sequence"] == list(EXPECTED_EVENTS[expect]) and len(on_control) == len(reached)
        v["said"] = all(text in said for text in SAID.get(expect, ()))
        judged = []
        for event in reached:
            rect = _rect(event.get("rect"))
            positioned = event.get("event") != "input"
            try:
                inside = rect is not None and (
                    not positioned or _inside((float(event["x"]), float(event["y"])), rect))
            except (KeyError, TypeError, ValueError):
                inside = False
            around = (_bracket(samples, event["t_lo"], event["t"], on_screen(rect)) if rect is not None
                      else {"held": False})
            judged.append({"event": event.get("event"), "rect": rect, "inside": inside, **around})
        v["events"] = judged
        arrived = (len(new) == 1 and new[0].get("kind") == "approach" and new[0].get("label") == label
                   and new[0].get("outcome") == "arrived" and new[0].get("final_location"))
        rect = _rect(record.get("rect")) if record is not None else None
        if record is not None:
            pointer = record.get("last_trusted_pointer") or {}
            v["pointer_target"] = pointer.get("target")
            # the pointer event is not a post. It is bounded below by the records made clearly before
            # it, and by the record that carries it: that record was made after it, by no more than
            # the time between the two readings, and the record's own earliest moment is known. A
            # pointer reading later than the record that carries it is not one this can place.
            try:
                at = float(pointer["t"])
                since = record["page_t"] - at
                earliest = max(after(at), record["t_lo"] - _elapsed(since)) if since >= -2 * PAGE_CLOCK_GRAIN_S \
                    else -math.inf
                v["pointer_during_step"] = bool(window[0] <= earliest)
            except (KeyError, TypeError, ValueError):
                v["pointer_during_step"] = False
            try:
                v["pointer_inside"] = rect is not None and _inside((float(pointer["x"]), float(pointer["y"])), rect)
            except (KeyError, TypeError, ValueError):
                v["pointer_inside"] = False
            v["event_trusted"], v["scroll"], v["dpr"] = record.get("trusted"), record.get("scroll"), record.get("dpr")
            v["pinch"], v["page_focused"], v["rect"] = record.get("pinch"), record.get("page_focused"), rect
            if expect == "typed":
                v["value"] = record.get("value")
            if expect not in DELIVERED and rect is not None:
                # the pointer when the control's own listener moved it
                v["moved"] = _bracket(samples, record["t_lo"], record["t"], on_screen(rect))
        if rect is not None and arrived:
            v["control_screen_rect"] = on_screen(rect)
            v["gesture_end"] = new[0]["final_location"]
            v["end_inside"] = _inside(new[0]["final_location"], v["control_screen_rect"])
            # an approach that posted nothing started on its target: the page saw no new pointer event
            v["already_there"] = new[0].get("posted_samples") == []
        brackets = [*judged, *([v["moved"]] if "moved" in v else [])]
        v["samples_around_delivery"] = min((b.get("samples", 0) for b in brackets), default=0)
        v["samples_off_control"] = sum(b.get("off_control", 0) for b in brackets)
        v["largest_sample_gap_s"] = max((b.get("largest_gap_s", DELIVERY_WINDOW_S * 2) for b in brackets), default=None)
        v["pointer_on_control_at_delivery"] = bool(brackets) and all(b["held"] for b in brackets)
        v["held"] = bool(record is not None and arrived and v["in_order"] and v["said"]
                         and all(j["inside"] for j in judged) and v["pointer_on_control_at_delivery"]
                         and (expect in DELIVERED or "moved" in v)
                         and v.get("pointer_target") == label and v.get("pointer_inside")
                         and (v.get("pointer_during_step") or v.get("already_there"))
                         and v.get("end_inside")
                         and (expect not in DELIVERED or step.get("exit") == 0)
                         and (expect != "typed" or v.get("value") == TYPED))
        verdicts.append(v)
    last = verdicts[-1] if verdicts else {}
    scrolled = bool(last.get("label") == "Gamma" and (last.get("scroll") or [0, 0])[1] > 0)
    complete = [(v["label"], v["op"], v["expect"]) for v in verdicts] == list(STEPS)
    reaching = [v for v in verdicts if v["expect"] in EXPECTED_EVENTS]
    ratios = [v.get("dpr") for v in reaching]
    scale = bool(ratios) and all(ratio == 2 for ratio in ratios)
    pinches = [v.get("pinch") for v in reaching]
    unpinched = bool(pinches) and all(pinch == 1 for pinch in pinches)
    setup = {name: next((s.get("exit") for s in run.get("steps", []) if s.get("name") == name), None)
             for name in ("00-start", "00-park")}
    owned = bool(run.get("chrome_launch")) and run.get("chrome_closed") is True and not run.get("cleanup_errors")
    loaded = next((e.get("detail") or {} for e in events if e.get("type") == "loaded"), {})
    # the Forged step tests something only if the page's replaced hit test does answer Forged there
    forgery = loaded.get("page_says_at_forged") == "Forged" and loaded.get("browser_says_at_forged") != "Forged"
    # every record of something done to the page belongs, by the whole interval it can have been made
    # in, to one tried step, whose verdict judged it
    windows = [(step["t_start"], step["t_end"] + 1.0) for step in tried]
    apart = all(earlier[1] <= later[0] for earlier, later in itertools.pairwise(windows))

    def named(e, **more):
        when = [round(t, 3) if math.isfinite(t) else None for t in (e["t_lo"], e["t"])]
        return {"type": e.get("type"), "event": (e.get("detail") or {}).get("event"), "n": e.get("n"),
                "on": next((e["detail"][key] for key in ("target", "button", "field", "control")
                            if key in (e.get("detail") or {})), None), "between": when, **more}

    actions = [e for e in events if e.get("type") in ACTION_RECORDS]
    unaccounted, ambiguous, untimed = [], [], []
    for e in actions:
        width = e["t"] - e["t_lo"]
        if not 0 <= width <= MAX_CLOCK_WIDTH_S:
            untimed.append(named(e, width_s=round(width, 4) if math.isfinite(width) else None))
        if any(low <= e["t_lo"] and e["t"] <= high for low, high in windows):
            continue
        # not wholly inside a step: it reaches into one across its start or its end, or lies in none
        (ambiguous if any(e["t_lo"] <= high and e["t"] >= low for low, high in windows) else unaccounted).append(named(e))
    if untimed:
        clock = clock | {"held": False, "untimed": untimed}
        clock.setdefault("why", f"{len(untimed)} records of something done to the page are not placed within "
                                f"{MAX_CLOCK_WIDTH_S * 1000:.0f} ms by their own posts")
    widths = [e["t"] - e["t_lo"] for e in actions if math.isfinite(e["t"] - e["t_lo"])]
    clock["widest_action_record_s"] = round(max(widths), 4) if widths else None
    # the grain the bounds allow for is an assumption about the page's clock. The page's measured step
    # is a diagnostic of its resolution: a coarser one shows the assumption false; a finer one, or one
    # that was fine at load, does not show it true
    step = loaded.get("clock_step_s")
    clock["page_clock_step_s"] = step
    if not (isinstance(step, (int, float)) and not isinstance(step, bool) and 0 < step <= PAGE_CLOCK_GRAIN_S):
        clock["held"] = False
        clock.setdefault("why", f"the page did not report a step of its clock within the "
                                f"{PAGE_CLOCK_GRAIN_S * 1000:.0f} ms its times are allowed")
    # nothing the page made is missing: its numbers are whole, from one load, through a fence the page
    # made because the probe asked for it after the last step's interval had closed
    one_load = sum(1 for e in received if e.get("type") == "loaded") == 1
    asked = run.get("fence_asked")
    fenced = bool(windows and fence is not None and isinstance(fence.get("n"), int)
                  and isinstance(asked, (int, float)) and asked >= windows[-1][1]
                  and isinstance(fence.get("received"), (int, float)) and fence["received"] >= asked
                  and set(range(1, fence["n"] + 1)) <= set(whole))
    log = {"records": len(received), "numbered_without_gaps": numbered, "one_load": one_load,
           "fenced_after_the_last_step": fenced,
           "accounted_through": {"record": fence.get("n"), "asked_at": asked} if fenced else None,
           "missing_after_the_fence": missing_after if fenced else None,
           "step_intervals_apart": apart, "unaccounted": unaccounted, "ambiguous": ambiguous,
           "held": numbered and one_load and fenced and apart and not unaccounted and not ambiguous}
    return {"steps": verdicts, "complete": complete, "gamma_clicked_after_scrolling": scrolled,
            "clock": clock, "page_log": log,
            "pointer_samples": None if samples is None else len(samples),
            "pointer_sampler": run.get("pointer_sampler"),
            "device_pixel_ratios": ratios, "scale_factor_tested": scale, "pinch_scales": pinches,
            "setup_exits": setup, "own_chrome_closed": owned, "page_forges_its_hit_test": forgery,
            "held": (complete and scrolled and scale and unpinched and owned and forgery
                     and clock["held"] and log["held"]
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
    fence = threading.Event()
    server, fixture_port = probe_page_effects._serve(out, answer=lambda _record: b"fence" if fence.is_set() else None)
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
            # the last step's interval closes a second after its command returned; then ask the page
            # for its fence and wait for it, so that every record made up to here is in hand
            closes = max((step["t_end"] for step in steps if step.get("expect")), default=time.time()) + 1.0
            time.sleep(max(0.0, closes - time.time()) + 0.05)
            record["fence_asked"] = time.time()
            fence.set()
            record["fence_received"] = _await_fence(out / "page-events.jsonl", FENCE_WAIT_S)
    finally:
        _finish(record, out, session, start_stdout, stop, sampler, server)


def _await_fence(events: Path, wait_s: float) -> bool:
    """Whether the page's fence record arrived within ``wait_s``."""
    deadline = time.time() + wait_s
    while time.time() < deadline:
        try:
            if any(e.get("type") == "fence" for e in _jsonl(events)):
                return True
        except OSError:
            pass
        time.sleep(0.1)
    return False


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
        # a tried step's first words say what the driver did, and its last what was refused; the whole
        # output is in the step's own file
        said = (step.get("stdout") or "") if step.get("expect") else ""
        step["stdout"] = said if len(said) <= 2100 else said[:1500] + "\n[...]\n" + said[-600:]
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
