"""Does a freshly launched Chrome show a web area in its window? A diagnostic for FP88.

Three launches of a bare Chrome, one after another, each on a fresh temporary profile with no debugging
port and a page that is one button: as Footwork launched its browser before FP88 and only read; the
same with the request to show web content made each second, each attribute's answer recorded; and with
``--force-renderer-accessibility``. Each window is read for six seconds through the functions a filmed
start reads with (``jevdual.ax``), then that Chrome is closed and its profile removed.

It reads and, in the second launch, sets two accessibility attributes on its own Chrome. It performs no
page action and moves no pointer. Each launch brings a Chrome window to the front; the application in
front at the beginning is brought back at the end. It waits for an unlocked screen and 10 s of idle.

    PYTHONPATH=python .venv/bin/python scripts/diag_chrome_web_area.py --out /abs/fresh/out/dir
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from probe_browser_holder import _activate_pid, _front_pid, _wait_idle

READ_S, EVERY_S, ASK_EVERY_S = 6.0, 0.2, 1.0
PAGE = "data:text/html,<title>Footwork web area diagnostic</title><button>Only</button>"
ATTRIBUTES = ("AXManualAccessibility", "AXEnhancedUserInterface")


def arms() -> tuple[tuple[str, tuple[str, ...], bool], ...]:
    """The launches: a name, the switches added to the bare launch, and whether the browser is asked."""
    from jevdual.browser_driver import ACCESSIBILITY_SWITCH

    return (("bare", (), False), ("bare_asked", (), True), ("forced", (ACCESSIBILITY_SWITCH,), False))


def first_seen(readings: list[dict]) -> float | None:
    """When a launch's window first showed a web area with a frame, in seconds from the launch."""
    return next((r["t"] for r in readings if r.get("web_area")), None)


def summary(found: dict) -> dict:
    """What the three launches say about FP88, from their readings alone."""
    seen = {name: first_seen(arm.get("readings", [])) for name, arm in found.items()}
    return {"first_seen_s": seen,
            "forced_shows_a_web_area": seen.get("forced") is not None,
            "bare_shows_none": seen.get("bare") is None and seen.get("bare_asked") is None,
            "every_browser_closed": all(arm.get("closed") is True for arm in found.values())}


def _read(pid: int) -> dict:
    from ApplicationServices import AXUIElementCreateApplication
    from jevdual import ax

    windows = list(ax._attr(AXUIElementCreateApplication(pid), "AXWindows") or ())
    reading: dict = {"windows": len(windows)}
    if windows:
        found = ax.web_area(windows[0])
        frame = found[0] if found else None
        reading["web_area"] = [frame.x, frame.y, frame.w, frame.h] if frame is not None else None
        reading["address"] = (found[1] or "")[:80] if found else None
        reading["title"] = str(ax._attr(windows[0], "AXTitle") or "")[:80]
    return reading


def _ask(pid: int) -> list[dict]:
    """Set each attribute on the application and record its answer, and whether it says it can be set."""
    from ApplicationServices import (
        AXUIElementCreateApplication,
        AXUIElementIsAttributeSettable,
        AXUIElementSetAttributeValue,
    )

    app = AXUIElementCreateApplication(pid)
    asked = []
    for attribute in ATTRIBUTES:
        error, settable = AXUIElementIsAttributeSettable(app, attribute, None)
        asked.append({"attribute": attribute, "settable_error": int(error), "settable": bool(settable),
                      "set_error": int(AXUIElementSetAttributeValue(app, attribute, True))})
    return asked


def launch(name: str, switches: tuple[str, ...], ask: bool) -> dict:
    from jevdual import ax
    from jevdual.browser_driver import chrome_executable

    profile = tempfile.mkdtemp(prefix="footwork-diag-")
    command = [chrome_executable(), f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
               "--window-size=1200,900", *switches, PAGE]
    found: dict = {"switches": list(switches), "asked": ask, "readings": [], "asks": []}
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    began, last_ask = time.time(), -ASK_EVERY_S
    found["pid"] = process.pid
    try:
        while (t := time.time() - began) < READ_S:
            reading: dict = {"t": round(t, 2)}
            try:
                reading |= _read(process.pid)
            except Exception as exc:  # noqa: BLE001 - a reading that fails is recorded as one that failed
                reading["error"] = f"{type(exc).__name__}: {str(exc)[:120]}"
            found["readings"].append(reading)
            if ask and t - last_ask >= ASK_EVERY_S:
                last_ask = t
                try:
                    found["asks"].append({"t": round(t, 2), "answers": _ask(process.pid)})
                except Exception as exc:  # noqa: BLE001
                    found["asks"].append({"t": round(t, 2), "error": f"{type(exc).__name__}: {str(exc)[:120]}"})
            time.sleep(EVERY_S)
        try:
            from ApplicationServices import AXUIElementCreateApplication

            windows = list(ax._attr(AXUIElementCreateApplication(process.pid), "AXWindows") or ())
            found["window_at_the_end"] = ax.outline(windows[0], depth=8) if windows else "no window"
        except Exception as exc:  # noqa: BLE001
            found["window_at_the_end"] = f"unreadable ({type(exc).__name__})"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        found["closed"] = process.poll() is not None
        shutil.rmtree(profile, ignore_errors=True)
        found["profile_removed"] = not Path(profile).exists()
    found["first_seen_s"] = first_seen(found["readings"])
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--out", required=True)
    parser.add_argument("--gate-limit", type=float, default=60.0, help="seconds to wait for idle before giving up")
    args = parser.parse_args()
    out = Path(args.out)
    if not out.is_absolute() or out.exists():
        raise SystemExit("--out must be an absolute path that does not exist yet")
    record: dict = {"gate": _wait_idle(limit_s=args.gate_limit), "front_pid_at_start": _front_pid(), "launches": {}}
    out.mkdir(parents=True)
    try:
        for name, switches, ask in arms():
            record["launches"][name] = launch(name, switches, ask)
            time.sleep(0.5)
    finally:
        before = record["front_pid_at_start"]
        if before and _front_pid() != before:
            _activate_pid(before)
            time.sleep(0.5)
        record["front_pid_at_end"] = _front_pid()
        record["summary"] = summary(record["launches"])
        (out / "diag.json").write_text(json.dumps(record, indent=1))
        print(json.dumps({"summary": record["summary"], "front": [record["front_pid_at_start"], record["front_pid_at_end"]],
                          "asks": {name: arm.get("asks", [])[:2] for name, arm in record["launches"].items() if arm.get("asked")},
                          "windows": {name: arm.get("window_at_the_end") for name, arm in record["launches"].items()}},
                         indent=1))


if __name__ == "__main__":
    main()
