"""AAD8: read Suno Create's lyrics editor without input; return lengths, LF counts and hashes only."""
import asyncio
import json
import sys
import urllib.request

import websockets

EXPR = r"""(async () => {
  const sha = async (s) => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s))))
      .map(b => b.toString(16).padStart(2, '0')).join('');
  const stat = async (s) => s == null ? null : ({len: [...s].length, lf: (s.match(/\n/g) || []).length,
      cr: (s.match(/\r/g) || []).length, sha: await sha(s), nonlf_sha: await sha(s.replace(/[\r\n]/g, ''))});
  const cands = [...document.querySelectorAll('textarea, [contenteditable="true"], [contenteditable=""]')];
  const out = [];
  for (const e of cands) {
    const label = (e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.getAttribute('data-placeholder') || '').slice(0, 40);
    out.push({tag: e.tagName.toLowerCase(), label, visible: !!(e.offsetWidth || e.offsetHeight),
      value: e.tagName === 'TEXTAREA' ? await stat(e.value) : null,
      innerText: await stat(e.innerText), textContent: await stat(e.textContent),
      blocks: e.tagName === 'TEXTAREA' ? null : e.querySelectorAll('p, div, br').length});
  }
  return {url: location.pathname, candidates: out};
})()"""

def _tabs(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
        return json.load(response)


async def main(port):
    tabs = await asyncio.to_thread(_tabs, port)
    tab = next(t for t in tabs if t.get("type") == "page" and "suno.com/create" in (t.get("url") or ""))
    async with websockets.connect(tab["webSocketDebuggerUrl"], max_size=2**22) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                                  "params": {"expression": EXPR, "returnByValue": True, "awaitPromise": True}}))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                print(json.dumps(msg.get("result", {}).get("result", {}).get("value"), indent=1))
                return

asyncio.run(main(int(sys.argv[1])))
