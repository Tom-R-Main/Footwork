"""Check for notebook BH4: does a fresh Footwork launch with a URL leave exactly one page on that URL?

Launches through bind_footwork_chrome into fresh profiles under --root on an isolated port, records
whether the window-recovery helper ran, counts page targets on the fixture URL, then terminates the
launched browser. Refuses Footwork's default port and the sign-in test's.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_page_effects import _front, _serve


def _pages(port: int) -> list[dict]:
    with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as response:
        return json.load(response)


async def _launch(url: str) -> dict:
    from jevdual import browser_driver as b

    helpers: list[list[str]] = []
    real = subprocess.Popen

    def watched(args, **kw):
        if list(args[:2]) == ["open", "-na"] or "--new-window" in args:
            helpers.append(list(args))
        return real(args, **kw)

    b.subprocess.Popen = watched
    started = time.time()
    try:
        driver, _bridge = await b.bind_footwork_chrome(url)
    finally:
        b.subprocess.Popen = real
    try:
        await asyncio.sleep(1.0)
        pages = [p for p in await asyncio.to_thread(_pages, b.PORT) if p.get("type") == "page"]
        return {"bind_s": round(time.time() - started, 2), "helper_runs": len(helpers),
                "pages_on_url": sum(p.get("url") == url for p in pages), "pages": len(pages)}
    finally:
        await driver.shutdown()
        pid = b.chrome_pid()
        if pid:
            os.kill(pid, signal.SIGTERM)
            for _ in range(50):
                if b.chrome_pid() is None:
                    break
                time.sleep(0.1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--root", required=True, help="absolute directory for the fresh profiles")
    parser.add_argument("--out", required=True)
    parser.add_argument("--launches", type=int, default=3)
    args = parser.parse_args()
    port = os.environ.get("FOOTWORK_CHROME_PORT", "9333")
    if port in {"9333", "9555"}:
        raise SystemExit("refusing a protected port; set FOOTWORK_CHROME_PORT")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    front = _front()
    rows = []
    for i in range(1, args.launches + 1):
        os.environ["FOOTWORK_CHROME_PROFILE"] = str(Path(args.root) / f"fresh-{i}-{int(time.time())}")
        import importlib

        from jevdual import browser_driver

        importlib.reload(browser_driver)  # PROFILE_DIR is read at import
        server, fixture = _serve(out)
        try:
            rows.append({"launch": i, **asyncio.run(_launch(f"http://127.0.0.1:{fixture}/"))})
        finally:
            server.shutdown()
            subprocess.run(["osascript", "-e", f'tell application "{front}" to activate'],
                           capture_output=True, timeout=10, check=False)
        time.sleep(2.0)
    (out / "launches.json").write_text(json.dumps(rows, indent=1))
    print(json.dumps(rows))


if __name__ == "__main__":
    main()
