"""AAD11 follow-up: read Suno's lyrics editor as paragraphs, then clear it with DevTools key input.

Reports digests and counts only. Usage: .venv/bin/python -I scripts/probe_lyrics_structure_and_clear.py PORT
"""
import asyncio
import json
import sys
import urllib.request

import websockets

READ = r"""(async () => {
  const sha = async (s) => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s))))
      .map(b => b.toString(16).padStart(2, '0')).join('');
  const vis = e => !!(e.offsetWidth || e.offsetHeight);
  const e = [...document.querySelectorAll('[contenteditable="true"]')].filter(vis)[0];
  if (!e) return null;
  const blocks = [...e.children];
  const joined = blocks.map(b => b.textContent).join('\n');
  const counter = [...document.querySelectorAll('*')].filter(x => x.children.length === 0 && /characters used/.test(x.textContent || '')).map(x => x.textContent.trim())[0];
  return {block_tags: [...new Set(blocks.map(b => b.tagName))], blocks: blocks.length,
          paragraph_join: {len: [...joined].length, lf: (joined.match(/\n/g) || []).length, sha: await sha(joined)}, counter};
})()"""

def _tabs(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
        return json.load(response)


async def main(port):
    tabs = await asyncio.to_thread(_tabs, port)
    tab = next(t for t in tabs if t.get("type") == "page" and "suno.com/create" in (t.get("url") or ""))
    out = {}
    async with websockets.connect(tab["webSocketDebuggerUrl"], max_size=2**22) as ws:
        n = 0
        async def call(method, params):
            nonlocal n
            n += 1
            await ws.send(json.dumps({"id": n, "method": method, "params": params}))
            while True:
                m = json.loads(await ws.recv())
                if m.get("id") == n:
                    return m
        async def ev(expr):
            m = await call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
            return m.get("result", {}).get("result", {}).get("value")
        out["before_clear"] = await ev(READ)
        await ev("(() => { const e = [...document.querySelectorAll('[contenteditable=\"true\"]')].filter(x => x.offsetWidth || x.offsetHeight)[0]; e.focus(); return true; })()")
        await call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "a", "code": "KeyA", "modifiers": 4,
                                               "windowsVirtualKeyCode": 65, "commands": ["selectAll"]})
        await call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "a", "code": "KeyA", "modifiers": 4, "windowsVirtualKeyCode": 65})
        for kind in ("keyDown", "keyUp"):
            await call("Input.dispatchKeyEvent", {"type": kind, "key": "Backspace", "code": "Backspace",
                                                   "windowsVirtualKeyCode": 8, "nativeVirtualKeyCode": 51})
        await asyncio.sleep(1.0)
        out["after_clear"] = await ev(READ)
    print(json.dumps(out, indent=1))

asyncio.run(main(int(sys.argv[1])))
