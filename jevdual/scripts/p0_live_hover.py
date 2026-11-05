"""P0 live acceptance (pointer-motion plan §6): one real desktop hover lands within 1 pt of an element centre.

Moves the real pointer once. Run only with the owner's authorization and nobody at the machine. Refuses
unless HID idle time is at least 3 s (the idle guard). Writes a JSON result to the path given.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path


def calculator_pid() -> int:
    subprocess.run(["open", "-a", "Calculator"], check=True)
    time.sleep(1.5)
    found = subprocess.run(["pgrep", "-x", "Calculator"], capture_output=True, text=True, check=True)
    return int(found.stdout.split()[0])


async def main(out: Path, pid: int) -> int:
    import Quartz
    from jevdual.coexist import idle_seconds
    from jevdual.effectors.cua import create_desktop_driver, list_windows_input
    from jevdual.native import NativeBridge
    from jevdual.posture import ExecutionPolicy

    driver = create_desktop_driver()
    wins = (await driver.list_windows(list_windows_input(pid=pid, on_screen_only=True))).windows
    win = max(wins, key=lambda w: w.bounds.width * w.bounds.height)
    bridge = NativeBridge(driver, pid, win.window_id, policy=ExecutionPolicy("exclusive_desktop"))
    nm = await bridge.observe()
    target = next(c for c in nm.menu.candidates if c.label == "7")
    object.__setattr__(target, "operations", (*target.operations, "hover"))
    fx, fy, fw, fh = nm.frames[target.id]
    centre = (fx + fw / 2, fy + fh / 2)
    before = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
    idle = idle_seconds()
    result: dict = {
        "frame": [fx, fy, fw, fh],
        "centre_pt": centre,
        "before_pt": [before.x, before.y],
        "idle_s": idle,
    }
    if idle < 3.0:
        result["outcome"] = "refused:idle_guard"
    else:
        eff = await bridge.act(nm, "hover", target.id)
        await asyncio.sleep(0.2)
        after = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
        err = max(abs(after.x - centre[0]), abs(after.y - centre[1]))
        result.update(
            {
                "after_pt": [after.x, after.y],
                "max_axis_error_pt": err,
                "effect": {"dispatched": eff.dispatched, "error_code": eff.error_code, "effect": eff.effect},
                "outcome": "pass" if eff.dispatched and err <= 1.0 else "fail",
            }
        )
    result["t"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    await driver.shutdown()
    return 0 if result["outcome"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(Path(sys.argv[1]), calculator_pid())))
