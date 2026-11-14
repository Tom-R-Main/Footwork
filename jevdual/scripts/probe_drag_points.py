"""Does ``footwork drag-points`` reach a real page as one trusted drag? The live part of PTD2.

One bare Chrome on a fresh temporary profile, with no debugging port, on a page that is one canvas
filling the viewport. The page counts its own pointer events and writes a short summary into its title,
which this script reads through accessibility: nothing connects to DevTools, as the command's caller
requires. Six runs of the command against that page:

1. one drag between two viewport points;
2. the same drag over three seconds (PTD10: a slow drag posts as often as a fast one);
3. one slow drag, interrupted by a key press this script posts while the button is down;
4. one slow drag, told to stop with SIGTERM while the button is down (PTD10);
5. one drag too short to be a drag;
6. the first drag again, naming an application the page is not in (PTD16): refused, nothing posted.

It moves the real pointer and presses its left button over its own Chrome window, and posts one F13
key press. It waits for an unlocked screen and 10 s of idle, brings the application that was in front
back at the end, closes its Chrome and removes the profile.

    PYTHONPATH=python .venv/bin/python scripts/probe_drag_points.py --out /abs/fresh/out/dir

``--rejudge RUN_JSON`` posts nothing: it judges a kept run's record again by the present rules.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import re
import shutil
import signal
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
#: an application that is running and that the probe's page is not in
WRONG_APP = "Finder"

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


def judge_drag(before: dict, after: dict, said: dict, exit_code: int, app: str | None = None) -> dict:
    """PTD2's first live prediction: one trusted press and release at the points, held all the way.
    ``app``: the browser the run named, which the command must report as what it claimed (None for a
    record kept from before the command reported it)."""
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
    if app is not None:
        checks["claimed_the_browser_named"] = said.get("app") == app
    return {"checks": checks, "held": all(checks.values())}


def judge_abort(before: dict, after: dict, said: dict, exit_code: int, exit_aborted: int,
                origin: tuple[float, float], cause: str = "aborted:pointer_contended:key_down",
                app: str | None = None) -> dict:
    """A drag stopped while the button was down: one press and one release reached the page, the
    release where the command says it posted it, with the button held on every move before it.

    PTD9: the first form of this took a release or a cancel, anywhere, after any moves, so a drag whose
    button had come up early, or whose release went somewhere the command did not say, held. ``origin``
    is the screen point of the page's 0,0, which takes the command's screen points to the page's."""
    released = said.get("released_at")
    where = (released[0] - origin[0], released[1] - origin[1]) if released else None
    checks = {
        "exit_says_pressed_then_stopped": exit_code == exit_aborted and str(said.get("outcome", "")).startswith(cause)
        and said.get("pressed") is True,
        "one_press": after["downs"] - before["downs"] == 1,
        "one_release_and_no_cancel": after["ups"] - before["ups"] == 1 and after["cancels"] == before["cancels"],
        "pressed_within_1px": _near(after["down_at"], FROM),
        "released_where_it_said": where is not None and _near(after["up_at"], where),
        "released_short_of_the_end": released is not None and released != said.get("end"),
        "button_held_through_every_move": after["held_moves"] > 0 and after["loose_moves"] == 0,
        "no_gap_over_the_limit": after["max_move_gap_ms"] <= GAP_LIMIT_MS,
        "escape_was_sent": said.get("escape_sent") is True,
        "no_second_release": "extra_release" not in said,
        "all_trusted": after["untrusted"] == 0,
        "all_on_the_canvas": after["off_canvas"] == 0,
        "button_reads_up": said.get("button_up") is True,
    }
    if app is not None:
        checks["claimed_the_browser_named"] = said.get("app") == app
    return {"checks": checks, "held": all(checks.values())}


def judge_stop(before: dict, after: dict, said: dict, exit_code: int, exit_aborted: int,
               origin: tuple[float, float], app: str | None = None) -> dict:
    """PTD10: told to stop by SIGTERM with the button down, the command ends as an interrupted drag
    does, says what stopped it, and leaves nothing claimed."""
    verdict = judge_abort(before, after, said, exit_code, exit_aborted, origin, cause="aborted:cancelled", app=app)
    verdict["checks"]["says_what_stopped_it"] = said.get("stopped_by") == "SIGTERM"
    verdict["checks"]["claim_given_up"] = said.get("claim_kept") is None
    verdict["held"] = all(verdict["checks"].values())
    return verdict


def rejudge(record: dict, exit_aborted: int, exit_refused: int) -> dict:
    """A kept run's record, judged by the present rules from what it stored. Runs it has none of are
    left out; nothing is posted or read from a screen."""
    runs, origin, first = record["runs"], record["content"][:2], record["page_at_start"]
    app = record.get("app")  # absent from a record kept before the command reported what it claimed
    order = [name for name in ("drag", "slow", "interrupted", "stopped", "short", "wrong_app") if name in runs]
    out, before = {}, first
    for name in order:
        run = runs[name]
        if name in ("drag", "slow"):
            verdict = judge_drag(before, run["page"], run["said"], run["exit"], app=app)
        elif name == "interrupted":
            verdict = judge_abort(before, run["page"], run["said"], run["exit"], exit_aborted, origin, app=app)
        elif name == "stopped":
            verdict = judge_stop(before, run["page"], run["said"], run["exit"], exit_aborted, origin, app=app)
        elif name == "wrong_app":
            verdict = judge_wrong_app(before, run.get("page_read"), run["said"], run["exit"], exit_refused,
                                      WRONG_APP, app or "")
        else:
            verdict = judge_short(before, run["page"], run["said"], run["exit"], exit_refused)
        out[name] = {"held": verdict["held"], "failed": [k for k, v in verdict["checks"].items() if not v],
                     "held_when_run": run["held"]}
        before = run["page"]
    return out


def judge_short(before: dict, after: dict, said: dict, exit_code: int, exit_refused: int) -> dict:
    """PTD2's third: a drag too short is refused and the page sees nothing."""
    checks = {
        "refused_too_short": exit_code == exit_refused and said.get("code") == "drag_too_short",
        "the_page_saw_nothing": all(after[k] == before[k] for k in ("downs", "ups", "cancels", "keydowns")),
    }
    return {"checks": checks, "held": all(checks.values())}


def judge_wrong_app(before: dict, after: dict | None, said: dict, exit_code: int, exit_refused: int,
                    named: str, browser: str) -> dict:
    """PTD16: a drag over the page that names another application is refused because the hit test found
    the browser there, the command says it posted nothing, and the page, read afresh, saw nothing.

    PTD18: the first form held for a refusal that named something else than the browser, for a report
    that contradicted the refusal, and with the earlier summary standing in for one that was not read."""
    reason = str(said.get("reason", ""))
    start = reason.partition("the start point ")[2]
    checks = {
        "refused_as_covered": exit_code == exit_refused and said.get("code") == "point_covered",
        "found_the_browser_at_the_start": f" is on {browser}, not {named}" in start,
        "says_nothing_was_posted": said.get("pressed") is False and said.get("approach_moves") == 0
        and said.get("drags") == 0 and said.get("releases_posted") == 0,
        "a_fresh_summary_was_read": after is not None,
        "the_page_saw_nothing": after is not None
        and all(after[k] == before[k] for k in ("downs", "ups", "cancels", "keydowns")),
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


def _command(out: Path, name: str, points: tuple[float, float, float, float], app: str, *extra: str,
             during=None) -> tuple[int, dict]:
    """One run of the command; ``during`` is called beside it with its process."""
    argv = [sys.executable, "-m", "jevdual.cli", "drag-points", *(repr(float(v)) for v in points),
            "--mode", "exclusive_desktop", "--app", app, "--owner", str(out), *extra]
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    worker = None
    if during is not None:
        worker = threading.Thread(target=during, args=(process,), daemon=True)
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
    parser.add_argument("--out")
    parser.add_argument("--gate-limit", type=float, default=60.0, help="seconds to wait for idle before giving up")
    parser.add_argument("--rejudge", metavar="RUN_JSON", help="judge a kept run again; posts nothing")
    args = parser.parse_args()
    if args.rejudge:
        print(json.dumps(rejudge(json.loads(Path(args.rejudge).read_text()), EXIT_ABORTED, EXIT_REFUSED), indent=1))
        return
    if not args.out:
        raise SystemExit("--out or --rejudge is required")
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
        # the name the system gives this Chrome, which is what the command's hit test will be held to
        import AppKit

        running = AppKit.NSRunningApplication.runningApplicationWithProcessIdentifier_(process.pid)
        app = str(running.localizedName() or "") if running is not None else ""
        record["app"] = app
        if not app or app == WRONG_APP:
            record["stopped"] = f"this Chrome's application name could not be read ({app!r}); nothing was posted"
            return

        code, said = _command(out, "1-drag", ends, app, "--record", str(out / "gestures.jsonl"))
        after = _summary(process.pid, until=lambda s: s["ups"] > first["ups"]) or first
        record["runs"]["drag"] = {"exit": code, "said": said, "page": after,
                                  **judge_drag(first, after, said, code, app=app)}

        code, said = _command(out, "2-slow", ends, app, "--duration", "3", "--record", str(out / "gestures.jsonl"))
        slow = _summary(process.pid, until=lambda s: s["ups"] > after["ups"]) or after
        record["runs"]["slow"] = {"exit": code, "said": said, "page": slow,
                                  **judge_drag(after, slow, said, code, app=app)}

        def once_pressed(since: dict, act) -> None:
            # once the page has seen the press and half a second of held moves
            seen = _summary(process.pid, wait_s=6.0, until=lambda s: s["downs"] > since["downs"])
            if seen is not None and seen["downs"] > since["downs"]:
                time.sleep(0.5)
                act()

        def interrupt(_command_process) -> None:
            once_pressed(slow, _press_f13)  # one key press the command did not post

        code, said = _command(out, "3-interrupted", ends, app, "--duration", "2.5", during=interrupt)
        later = _summary(process.pid, until=lambda s: s["ups"] + s["cancels"] > slow["ups"] + slow["cancels"]) or slow
        record["runs"]["interrupted"] = {"exit": code, "said": said, "page": later,
                                         **judge_abort(slow, later, said, code, EXIT_ABORTED, origin[:2], app=app)}

        def stop(command_process) -> None:
            once_pressed(later, lambda: command_process.send_signal(signal.SIGTERM))

        code, said = _command(out, "4-stopped", ends, app, "--duration", "2.5", during=stop)
        ended = _summary(process.pid, until=lambda s: s["ups"] + s["cancels"] > later["ups"] + later["cancels"]) or later
        record["runs"]["stopped"] = {"exit": code, "said": said, "page": ended,
                                     **judge_stop(later, ended, said, code, EXIT_ABORTED, origin[:2], app=app)}

        near = (ends[0], ends[1], ends[0] + 3.0, ends[1] + 2.0)
        code, said = _command(out, "5-short", near, app)
        time.sleep(0.5)
        last = _summary(process.pid) or ended
        record["runs"]["short"] = {"exit": code, "said": said, "page": last,
                                   **judge_short(ended, last, said, code, EXIT_REFUSED)}

        code, said = _command(out, "6-wrong-app", ends, WRONG_APP)
        time.sleep(0.5)
        read = _summary(process.pid)  # None when the page's summary could not be read: no stand-in for it
        record["runs"]["wrong_app"] = {"exit": code, "said": said, "page": read or last, "page_read": read,
                                       **judge_wrong_app(last, read, said, code, EXIT_REFUSED, WRONG_APP, app)}
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
                "orphaned": [r["token"] for r in status["requests"] if r["state"] == "orphaned"],
                "active_reservations": sum(1 for r in status["reservations"] if r["state"] == "active")}
        except Exception as exc:  # noqa: BLE001 - the closing readings are reported, never raised
            record["closing_readings_error"] = f"{type(exc).__name__}: {str(exc)[:120]}"
        runs = record["runs"]
        record["held"] = (len(runs) == 6 and all(run["held"] for run in runs.values())
                          and record["chrome_closed"] and record.get("left_button_down_at_end") is False
                          and record.get("registry_at_end", {}).get("requests") == 0)
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
