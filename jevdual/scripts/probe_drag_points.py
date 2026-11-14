"""Does ``footwork drag-points`` reach a real page as one trusted drag? The live part of PTD2.

One bare Chrome on a fresh temporary profile, with no debugging port, on a page that is one canvas
filling the viewport. The page counts its own pointer events and writes a short summary into its title,
which this script reads through accessibility: nothing connects to DevTools, as the command's caller
requires. Three runs of the command against that page:

1. one drag between two viewport points;
2. one slower drag, interrupted by a key press this script posts while the button is down;
3. one drag too short to be a drag.

It moves the real pointer and presses its left button over its own Chrome window, and posts one F13
key press. It waits for an unlocked screen and 10 s of idle, brings the application that was in front
back at the end, closes its Chrome and removes the profile.

    PYTHONPATH=python .venv/bin/python scripts/probe_drag_points.py --out /abs/fresh/out/dir
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

#: the two ends of the drag, in the page's viewport (CSS px); the canvas fills the viewport from 0,0
FROM, TO = (300.0, 300.0), (520.0, 440.0)
#: how far (CSS px) the page's pointerdown and pointerup may be from the points asked for
NEAR_PX = 1.0
#: the engine's own limit on the time between two posts, which the page's moves are held to as well
GAP_LIMIT_MS = 50.0
F13 = 105  # a key press no page and no default system shortcut acts on

PAGE = """<!doctype html><meta charset=utf-8><title>PD starting</title>
<style>html,body{margin:0;height:100%;overflow:hidden}canvas{display:block;width:100vw;height:100vh;background:#f4f1ea}</style>
<canvas id=c></canvas><script>
const c = document.getElementById('c');
let downs = 0, ups = 0, cancels = 0, keys = 0, off = 0, untrusted = 0;
let held = 0, loose = 0, gap = 0, last = null, inside = false, d = null, r = null;
function say() {
  const p = v => v ? Math.round(v[0] * 10) / 10 + ',' + Math.round(v[1] * 10) / 10 : '-';
  document.title = `PD n${downs} u${ups} x${cancels} h${held} l${loose} o${off} t${untrusted} g${Math.ceil(gap)} k${keys} d${p(d)} r${p(r)}`;
}
function seen(e) {
  if (!e.isTrusted) untrusted++;
  if (e.type !== 'keydown' && e.target !== c) off++;
}
addEventListener('pointerdown', e => { seen(e); downs++; inside = true; held = loose = gap = 0; last = null; d = [e.clientX, e.clientY]; r = null; say(); }, true);
addEventListener('pointermove', e => {
  if (!inside) return;
  seen(e);
  if (e.buttons === 1) held++; else loose++;
  if (last !== null) gap = Math.max(gap, e.timeStamp - last);
  last = e.timeStamp;
}, true);
addEventListener('pointerup', e => { seen(e); ups++; inside = false; r = [e.clientX, e.clientY]; say(); }, true);
addEventListener('pointercancel', e => { seen(e); cancels++; inside = false; say(); }, true);
addEventListener('keydown', e => { seen(e); keys++; say(); }, true);
say();
</script>"""

SUMMARY = re.compile(r"PD n(\d+) u(\d+) x(\d+) h(\d+) l(\d+) o(\d+) t(\d+) g(\d+) k(\d+) d(\S+) r(\S+)")


def page_url() -> str:
    return "data:text/html;base64," + base64.b64encode(PAGE.encode()).decode()


def parse(title: str) -> dict | None:
    """The page's own count of its pointer events, from the window's title; None when it shows none."""
    match = SUMMARY.search(title or "")
    if not match:
        return None

    def point(text: str) -> list[float] | None:
        return None if text == "-" else [float(v) for v in text.split(",")]

    downs, ups, cancels, held, loose, off, untrusted, gap, keys = (int(v) for v in match.groups()[:9])
    return {"downs": downs, "ups": ups, "cancels": cancels, "held_moves": held, "loose_moves": loose,
            "off_canvas": off, "untrusted": untrusted, "max_move_gap_ms": gap, "keydowns": keys,
            "down_at": point(match.group(10)), "up_at": point(match.group(11))}


def _near(got: list[float] | None, want: tuple[float, float]) -> bool:
    return got is not None and math.dist(got, want) <= NEAR_PX


def judge_drag(before: dict, after: dict, said: dict, exit_code: int) -> dict:
    """PTD2's first live prediction: one trusted press and release at the points, held all the way."""
    checks = {
        "exit_0_and_dropped": exit_code == 0 and said.get("outcome") == "dropped",
        "one_press_one_release": after["downs"] - before["downs"] == 1 and after["ups"] - before["ups"] == 1
        and after["cancels"] == before["cancels"],
        "all_trusted": after["untrusted"] == 0,
        "all_on_the_canvas": after["off_canvas"] == 0,
        "pressed_within_1px": _near(after["down_at"], FROM),
        "released_within_1px": _near(after["up_at"], TO),
        "button_held_through_every_move": after["held_moves"] >= 20 and after["loose_moves"] == 0,
        "no_gap_over_the_limit": after["max_move_gap_ms"] <= GAP_LIMIT_MS,
        "button_reads_up": said.get("button_up") is True,
    }
    return {"checks": checks, "held": all(checks.values())}


def judge_abort(before: dict, after: dict, said: dict, exit_code: int, exit_aborted: int) -> dict:
    """PTD2's second: an interrupted drag lets go once, says where, and leaves the button up."""
    checks = {
        "exit_says_pressed_then_aborted": exit_code == exit_aborted and str(said.get("outcome", "")).startswith(
            "aborted:pointer_contended:key_down") and said.get("pressed") is True,
        "one_press": after["downs"] - before["downs"] == 1,
        "one_release_or_cancel": (after["ups"] - before["ups"]) + (after["cancels"] - before["cancels"]) == 1,
        "escape_was_sent": said.get("escape_sent") is True,
        "released_short_of_the_end": said.get("released_at") is not None and said["released_at"] != said.get("end"),
        "all_trusted": after["untrusted"] == 0,
        "all_on_the_canvas": after["off_canvas"] == 0,
        "button_reads_up": said.get("button_up") is True,
    }
    return {"checks": checks, "held": all(checks.values())}


def judge_short(before: dict, after: dict, said: dict, exit_code: int, exit_refused: int) -> dict:
    """PTD2's third: a drag too short is refused and the page sees nothing."""
    checks = {
        "refused_too_short": exit_code == exit_refused and said.get("code") == "drag_too_short",
        "the_page_saw_nothing": all(after[k] == before[k] for k in ("downs", "ups", "cancels", "keydowns")),
    }
    return {"checks": checks, "held": all(checks.values())}


def _window(pid: int):
    from ApplicationServices import AXUIElementCreateApplication
    from jevdual import ax

    windows = list(ax._attr(AXUIElementCreateApplication(pid), "AXWindows") or ())
    return windows[0] if windows else None


def _title(pid: int) -> str:
    from jevdual import ax

    window = _window(pid)
    return str(ax._attr(window, "AXTitle") or "") if window is not None else ""


def _summary(pid: int, *, wait_s: float = 3.0, until=lambda s: True) -> dict | None:
    """The page's summary, read until ``until`` accepts it or ``wait_s`` passes (the last one read)."""
    deadline, last = time.time() + wait_s, None
    while True:
        last = parse(_title(pid)) or last
        if (last is not None and until(last)) or time.time() >= deadline:
            return last
        time.sleep(0.05)


def _content_origin(pid: int, wait_s: float = 8.0) -> tuple[list[float] | None, float | None]:
    """The web area's frame once two readings agree, and how long that took."""
    from jevdual import ax

    began, last = time.time(), None
    while time.time() - began < wait_s:
        window = _window(pid)
        frame = ax.web_area_frame(window) if window is not None else None
        found = [frame.x, frame.y, frame.w, frame.h] if frame is not None else None
        if found is not None and found == last:
            return found, round(time.time() - began, 2)
        last = found
        time.sleep(0.2)
    return None, None


def _press_f13() -> None:
    import Quartz

    for down in (True, False):
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, Quartz.CGEventCreateKeyboardEvent(None, F13, down))


def _command(out: Path, name: str, points: tuple[float, float, float, float], *extra: str,
             during=None) -> tuple[int, dict]:
    argv = [sys.executable, "-m", "jevdual.cli", "drag-points", *(repr(float(v)) for v in points),
            "--mode", "exclusive_desktop", "--owner", str(out), *extra]
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    worker = None
    if during is not None:
        worker = threading.Thread(target=during, daemon=True)
        worker.start()
    stdout, stderr = process.communicate(timeout=60)
    if worker is not None:
        worker.join(timeout=5)
    (out / f"{name}.stdout").write_text(stdout)
    (out / f"{name}.stderr").write_text(stderr)
    try:
        said = json.loads(stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        said = {"unreadable": stdout[-300:]}
    return process.returncode, said


def main() -> None:
    from jevdual.browser_driver import ACCESSIBILITY_SWITCH, chrome_executable
    from jevdual.coordination import Coordinator
    from jevdual.point_drag import EXIT_ABORTED, EXIT_REFUSED
    from probe_browser_holder import _activate_pid, _front_pid, _wait_idle

    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--out", required=True)
    parser.add_argument("--gate-limit", type=float, default=60.0, help="seconds to wait for idle before giving up")
    args = parser.parse_args()
    out = Path(args.out)
    if not out.is_absolute() or out.exists():
        raise SystemExit("--out must be an absolute path that does not exist yet")
    record: dict = {"gate": _wait_idle(limit_s=args.gate_limit), "front_pid_at_start": _front_pid(), "runs": {}}
    out.mkdir(parents=True)
    profile = tempfile.mkdtemp(prefix="footwork-drag-points-")
    process = subprocess.Popen(
        [chrome_executable(), f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
         "--window-size=1200,900", ACCESSIBILITY_SWITCH, page_url()],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    record["chrome_pid"] = process.pid
    try:
        origin, shown_s = _content_origin(process.pid)
        record["content"], record["content_shown_s"] = origin, shown_s
        first = _summary(process.pid, wait_s=4.0)
        record["page_at_start"] = first
        if origin is None or first is None:
            record["stopped"] = "the window showed no web area, or the page no summary; nothing was posted"
            return

        def screen(point: tuple[float, float]) -> tuple[float, float]:
            return (origin[0] + point[0], origin[1] + point[1])

        ends = (*screen(FROM), *screen(TO))
        record["screen_points"] = list(ends)

        code, said = _command(out, "1-drag", ends, "--record", str(out / "gestures.jsonl"))
        after = _summary(process.pid, until=lambda s: s["ups"] > first["ups"]) or first
        record["runs"]["drag"] = {"exit": code, "said": said, "page": after, **judge_drag(first, after, said, code)}

        def interrupt() -> None:
            # once the page has seen the press and some held moves, one key press the command did not post
            seen = _summary(process.pid, wait_s=6.0, until=lambda s: s["downs"] > after["downs"])
            if seen is not None and seen["downs"] > after["downs"]:
                time.sleep(0.5)
                _press_f13()
                record["interrupted_at"] = time.time()

        code, said = _command(out, "2-interrupted", ends, "--duration", "2.5", during=interrupt)
        later = _summary(process.pid, until=lambda s: s["ups"] + s["cancels"] > after["ups"] + after["cancels"]) or after
        record["runs"]["interrupted"] = {"exit": code, "said": said, "page": later,
                                         **judge_abort(after, later, said, code, EXIT_ABORTED)}

        near = (ends[0], ends[1], ends[0] + 3.0, ends[1] + 2.0)
        code, said = _command(out, "3-short", near)
        time.sleep(0.5)
        last = _summary(process.pid) or later
        record["runs"]["short"] = {"exit": code, "said": said, "page": last,
                                   **judge_short(later, last, said, code, EXIT_REFUSED)}
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        record["chrome_closed"] = process.poll() is not None
        shutil.rmtree(profile, ignore_errors=True)
        record["profile_removed"] = not Path(profile).exists()
        before = record["front_pid_at_start"]
        if before and _front_pid() != before:
            _activate_pid(before)
            time.sleep(0.5)
        record["front_pid_at_end"] = _front_pid()
        try:
            import Quartz

            record["left_button_down_at_end"] = bool(Quartz.CGEventSourceButtonState(
                Quartz.kCGEventSourceStateCombinedSessionState, Quartz.kCGMouseButtonLeft))
            status = Coordinator().status()
            record["registry_at_end"] = {
                "requests": len(status["requests"]),
                "active_reservations": sum(1 for r in status["reservations"] if r["state"] == "active")}
        except Exception as exc:  # noqa: BLE001 - the closing readings are reported, never raised
            record["closing_readings_error"] = f"{type(exc).__name__}: {str(exc)[:120]}"
        runs = record["runs"]
        record["held"] = (len(runs) == 3 and all(run["held"] for run in runs.values())
                          and record["chrome_closed"] and record.get("left_button_down_at_end") is False)
        (out / "run.json").write_text(json.dumps(record, indent=1))
        print(json.dumps({"held": record["held"], "stopped": record.get("stopped"),
                          "runs": {name: {"exit": run["exit"], "held": run["held"],
                                          "failed": [k for k, v in run["checks"].items() if not v]}
                                   for name, run in runs.items()},
                          "chrome": [record["chrome_pid"], record["chrome_closed"]],
                          "front": [record["front_pid_at_start"], record["front_pid_at_end"]],
                          "button_down": record.get("left_button_down_at_end"),
                          "registry": record.get("registry_at_end")}, indent=1))


if __name__ == "__main__":
    main()
