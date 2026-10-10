"""Local reproduction of the input loss after a navigating click (package C, prediction C1).

A stdlib HTTP server answers on one port under two hostnames, ``localhost`` and ``127.0.0.1``, which
Chromium treats as different sites. The start page's form posts and the server redirects (303) to a
target page, either on the same site or on the other one. browser-use 0.13.10 clicks the submit
button, then one raw CDP mouse click is dispatched at the centre of the target page, where a
full-page button counts trusted ``mousedown`` events. No third-party site is involved.

    uv run python scripts/diag_nav_input.py [--launches 10] [--late 3.0]

Prints one line per launch and variant, and a summary: ``count`` is the trusted mousedowns seen
0.4 s after the raw click (1 is correct, 0 is lost, 2 is duplicated); ``late`` repeats the raw click
after a further wait in the same launch.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import threading
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

START = """<!doctype html><title>start</title>
<form method="post" action="/login"><input name="to" type="hidden" value="{to}">
<button id="go" type="submit" style="font-size:24px">Sign in</button></form>"""

TARGET = """<!doctype html><title>target</title>
<style>html,body{{margin:0;height:100%}}#pad{{width:100%;height:100%;font-size:32px}}</style>
<button id="pad">target on {host}</button>
<script>window.__t=[];document.getElementById('pad').addEventListener('mousedown',
e=>window.__t.push(e.isTrusted),true);</script>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        return

    def _send(self, code: int, body: str = "", headers: dict[str, str] | None = None) -> None:
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        host = self.headers.get("Host", "")
        if self.path.startswith("/start"):
            to = self.path.split("to=", 1)[1] if "to=" in self.path else "/target"
            self._send(200, START.format(to=to))
        elif self.path.startswith("/target"):
            self._send(200, TARGET.format(host=host))
        else:
            self._send(404, "no")

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        form = dict(p.split("=", 1) for p in self.rfile.read(n).decode().split("&") if "=" in p)
        from urllib.parse import unquote

        self._send(303, "", {"Location": unquote(form.get("to", "/target"))})


def serve() -> tuple[ThreadingHTTPServer, int]:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


async def _eval(session, expr: str):
    cdp = await session.get_or_create_cdp_session()
    r = await cdp.cdp_client.send.Runtime.evaluate(
        params={"expression": expr, "returnByValue": True}, session_id=cdp.session_id
    )
    return r.get("result", {}).get("value")


async def raw_click(session, x: int = 400, y: int = 300) -> None:
    cdp = await session.get_or_create_cdp_session()
    for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
        params = {"type": kind, "x": x, "y": y}
        if kind != "mouseMoved":
            params |= {"button": "left", "clickCount": 1}
        await cdp.cdp_client.send.Input.dispatchMouseEvent(params=params, session_id=cdp.session_id)


async def count(session) -> int | None:
    v = await _eval(session, "JSON.stringify(window.__t || null)")
    t = json.loads(v) if v else None
    return None if t is None else sum(1 for x in t if x)


async def launch(port: int, variant: str, late: float) -> dict:
    from browser_use import BrowserProfile, BrowserSession
    from browser_use.tools.service import Tools

    start_host = "localhost"
    target_host = "localhost" if variant == "same-site" else "127.0.0.1"
    session = BrowserSession(browser_profile=BrowserProfile(headless=True))
    await session.start()
    try:
        tools = Tools()
        await session.navigate_to(f"http://{start_host}:{port}/start?to=http://{target_host}:{port}/target")
        await asyncio.sleep(1.0)
        sm = (await session.get_browser_state_summary()).dom_state.selector_map
        go = next(i for i, n in sm.items() if (n.attributes or {}).get("id") == "go")
        am = tools.registry.create_action_model()
        await tools.act(am(click={"index": go}), session)
        await asyncio.sleep(1.5)
        url = await _eval(session, "location.href") or ""
        await raw_click(session)
        await asyncio.sleep(0.4)
        first = await count(session)
        await _eval(session, "window.__t && (window.__t.length = 0)")
        await asyncio.sleep(late)
        await raw_click(session)
        await asyncio.sleep(0.4)
        second = await count(session)
        return {"variant": variant, "url": url, "count": first, "late": second}
    finally:
        await session.kill()


async def main(launches: int, late: float) -> None:
    srv, port = serve()
    rows = []
    try:
        for k in range(launches):
            for variant in ("same-site", "cross-site"):
                try:
                    row = await launch(port, variant, late)
                except Exception as exc:  # noqa: BLE001 - a diagnostic reports and moves on
                    row = {"variant": variant, "error": f"{type(exc).__name__}: {str(exc)[:100]}"}
                row["launch"] = k
                rows.append(row)
                print(json.dumps(row), flush=True)
    finally:
        srv.shutdown()
    for variant in ("same-site", "cross-site"):
        rs = [r for r in rows if r["variant"] == variant]
        first = Counter(r.get("count") for r in rs)
        second = Counter(r.get("late") for r in rs)
        errors = sum(1 for r in rs if "error" in r)
        print(f"SUMMARY {variant}: count {dict(first)}  late {dict(second)}  errors {errors}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--launches", type=int, default=10)
    ap.add_argument("--late", type=float, default=3.0)
    a = ap.parse_args()
    asyncio.run(main(a.launches, a.late))
