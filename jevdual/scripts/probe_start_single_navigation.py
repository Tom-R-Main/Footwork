#!/usr/bin/env python3
"""SN2: how many times Chrome fetches a page when it is launched on the page's URL and then navigated
to it, and when it is launched on a blank page and then navigated.

No window: each Chrome is headless, on a temporary profile and a free local port of its own, and is
closed and its profile removed afterwards. This is the mechanism under a browser start, without
Footwork: the launch argument, then one Page.navigate on the same tab. It does not run a start.

    PYTHONPATH=python python scripts/probe_start_single_navigation.py
"""

from __future__ import annotations

import asyncio
import json
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

#: the arm's name, and what its launch opens (None: the page's own URL)
ARMS = (("launched on the URL", None), ("launched on a blank page", "about:blank"))
PAGE = b"<!doctype html><title>Single navigation</title><p>one page</p>"


def _serve() -> tuple[ThreadingHTTPServer, list[float]]:
    fetched: list[float] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/page":
                fetched.append(time.time())
                body, status = PAGE, 200
            else:
                body, status = b"", 404
            self.send_response(status)
            self.send_header("Content-Type", "text/html")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, fetched


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _page_target(port: int, deadline: float) -> dict:
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1) as reply:
                pages = [t for t in json.load(reply) if t.get("type") == "page"]
            if pages:
                return pages[0]
        except OSError:
            pass
        time.sleep(0.1)
    raise RuntimeError("the headless browser showed no page target")


async def _navigate(target: dict, url: str) -> dict:
    import websockets

    async with websockets.connect(target["webSocketDebuggerUrl"], max_size=None) as page:
        await page.send(json.dumps({"id": 1, "method": "Page.enable"}))
        await page.send(json.dumps({"id": 2, "method": "Page.navigate", "params": {"url": url}}))
        answer, loaded = None, False
        try:
            async with asyncio.timeout(10):
                while answer is None or not loaded:
                    message = json.loads(await page.recv())
                    if message.get("id") == 2:
                        answer = message.get("result") or message
                    loaded = loaded or message.get("method") == "Page.loadEventFired"
        except TimeoutError:
            pass
        return {"answer": answer, "load_event": loaded}


def arm(name: str, launch_page: str | None, url: str, fetched: list[float]) -> dict:
    from jevdual.browser_driver import chrome_executable

    profile, port, before = tempfile.mkdtemp(prefix="footwork-single-navigation-"), _free_port(), len(fetched)
    command = [chrome_executable(), "--headless=new", f"--user-data-dir={profile}", f"--remote-debugging-port={port}",
               "--remote-debugging-address=127.0.0.1", "--no-first-run", "--no-default-browser-check",
               "--disable-gpu", launch_page or url]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    found: dict = {"arm": name, "launch_opens": launch_page or "the URL"}
    try:
        target = _page_target(port, time.time() + 20)
        # as a start does: the tab is bound some time after the launch, and then navigated
        time.sleep(1.5)
        found["fetched_before_the_navigation"] = len(fetched) - before
        found["tab_showed"] = _page_target(port, time.time() + 5).get("url")
        found["navigation"] = asyncio.run(_navigate(target, url))
        time.sleep(1.0)
        found["fetched"] = len(fetched) - before
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        found["closed"] = process.poll() is not None
        shutil.rmtree(profile, ignore_errors=True)
    return found


def main() -> None:
    server, fetched = _serve()
    url = f"http://127.0.0.1:{server.server_address[1]}/page"
    try:
        arms = [arm(name, launch_page, url, fetched) for name, launch_page in ARMS]
    finally:
        server.shutdown()
    print(json.dumps({"arms": arms, "fetches": {a["arm"]: a.get("fetched") for a in arms},
                      "every_browser_closed": all(a.get("closed") for a in arms)}, indent=1))


if __name__ == "__main__":
    main()
