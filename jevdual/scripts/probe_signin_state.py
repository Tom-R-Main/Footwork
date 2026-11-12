"""Read-only sign-in check for AAD7 over a test browser's DevTools port: tab URLs, Suno's Clerk sign-in time being nonzero, and Notion's same-origin getSpaces status. Returns only status codes, booleans and counts.

Usage: .venv/bin/python -I scripts/probe_signin_state.py PORT
"""
import asyncio
import json
import sys
import urllib.request
from urllib.parse import urlsplit

import websockets

PORT = int(sys.argv[1])

async def evaluate(ws_url, expression):
    async with websockets.connect(ws_url, max_size=2**20) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                                  "params": {"expression": expression, "returnByValue": True, "awaitPromise": True}}))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                return msg.get("result", {}).get("result", {}).get("value")

def _tabs(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
        return json.load(response)


async def main():
    tabs = await asyncio.to_thread(_tabs, PORT)
    out = []
    for t in tabs:
        if t.get("type") != "page":
            continue
        u = urlsplit(t.get("url") or "")
        row = {"title": (t.get("title") or "")[:50], "url": f"{u.scheme}://{u.netloc}{u.path[:40]}"}
        if "suno.com" in u.netloc:
            # Clerk's readable __client_uat cookie is the time of the last sign-in, 0 when signed out
            row["suno_client_uat_positive"] = await evaluate(t["webSocketDebuggerUrl"], """(() => {
                const v = document.cookie.split('; ').filter(c => c.startsWith('__client_uat')).map(c => Number(c.split('=')[1]));
                return v.length ? v.some(n => n > 0) : 'absent';
            })()""")
        if u.netloc == "app.notion.com":
            row["notion_getSpaces"] = await evaluate(t["webSocketDebuggerUrl"], """(async () => {
                const r = await fetch('/api/v3/getSpaces', {method: 'POST', credentials: 'include',
                    headers: {'content-type': 'application/json'}, body: '{}'});
                const j = await r.json().catch(() => null);
                return {http: r.status, spaces: j && typeof j === 'object' && r.ok ? Object.keys(j).length : null};
            })()""")
        out.append(row)
    print(json.dumps(out, indent=1))

asyncio.run(main())
