"""Check for notebook BH2: are tab ids stable across get_browser_state calls on one driver? Isolated profile only."""
import asyncio
import json
import sys

sys.path.insert(0, "scripts")
from pathlib import Path

from probe_page_effects import _serve


async def main():
    from jevdual.browser_driver import PORT, bind_footwork_chrome, chrome_pid

    if str(PORT) in {"9333", "9555"}:
        raise SystemExit("refusing a protected port; set FOOTWORK_CHROME_PROFILE and FOOTWORK_CHROME_PORT")
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    server, port = _serve(out)
    driver, bridge = await bind_footwork_chrome(f"http://127.0.0.1:{port}/")
    rows = [{"attach_tab": bridge.tab_id, "tabs": [dict(t) for t in bridge.binding.tabs]}]
    try:
        for i in range(3):
            await asyncio.sleep(1.0)
            r = await bridge.operations.bind(pid=bridge.pid, window_id=bridge.window_id)
            rows.append({"bind": i, "tabs": [{k: t.get(k) for k in ("tab_id", "active", "url")} for t in r.payload.get("tabs", [])]})
    finally:
        await driver.shutdown(); server.shutdown()
        import os
        import signal
        pid = chrome_pid()
        if pid: os.kill(pid, signal.SIGTERM)
    print(json.dumps(rows, indent=1, default=str))
asyncio.run(main())
