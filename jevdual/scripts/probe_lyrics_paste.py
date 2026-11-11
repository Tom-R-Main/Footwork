"""AAD10: paste the verified lyrics into Suno Create's lyrics editor in the test profile, read them back.

Reports only lengths, line-feed counts, SHA-256 digests and Suno's own counter text; the lyrics are not
printed. Clears the editor afterwards. Creates nothing.

Usage: .venv/bin/python -I scripts/probe_lyrics_paste.py PORT LYRICS_FILE [paste|type]
"""
import asyncio, json, sys, urllib.request
import websockets

STATS = r"""
const sha = async (s) => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s))))
    .map(b => b.toString(16).padStart(2, '0')).join('');
const stat = async (s) => s == null ? null : ({len: [...s].length, lf: (s.match(/\n/g) || []).length,
    cr: (s.match(/\r/g) || []).length, sha: await sha(s), nonlf_sha: await sha(s.replace(/[\r\n]/g, ''))});
const vis = e => !!(e.offsetWidth || e.offsetHeight);
const lyricsEditor = () => {
  const eds = [...document.querySelectorAll('textarea, [contenteditable="true"]')].filter(vis);
  const named = eds.find(e => /lyric/i.test((e.getAttribute('placeholder') || e.getAttribute('data-placeholder') || e.getAttribute('aria-label') || '') + ' ' + (e.closest('[class]')?.className || '')));
  return named || eds.find(e => e.tagName !== 'TEXTAREA') || null;
};
const counters = () => [...document.querySelectorAll('*')].filter(e => e.children.length === 0 && /\b\d+\s*(\/|of)\s*\d{3,}\b/.test(e.textContent || '')).map(e => e.textContent.trim().slice(0, 30));
"""

def S(expr):
    """Each evaluation gets its own block so the helper constants are not redeclared globally."""
    return "{" + STATS + expr + "}"


async def call(ws, n, method, params):
    await ws.send(json.dumps({"id": n, "method": method, "params": params}))
    while True:
        m = json.loads(await ws.recv())
        if m.get("id") == n:
            return m

async def ev(ws, n, expr):
    m = await call(ws, n, "Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
    return m.get("result", {}).get("result", {}).get("value", m.get("result", {}).get("exceptionDetails"))

async def main(port, path):
    text = open(path, encoding="utf-8").read()
    tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5))
    tab = next(t for t in tabs if t.get("type") == "page" and "suno.com/create" in (t.get("url") or ""))
    report = {}
    async with websockets.connect(tab["webSocketDebuggerUrl"], max_size=2**22) as ws:
        report["advanced"] = await ev(ws, 1, r"""(() => { const b = [...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'Advanced');
            if (!b) return 'no Advanced button'; b.click(); return 'clicked'; })()""")
        await asyncio.sleep(2.0)
        report["editor_before"] = await ev(ws, 2, S(r"""(async () => { const e = lyricsEditor(); if (!e) return null;
            return {tag: e.tagName, ph: (e.getAttribute('placeholder') || e.getAttribute('data-placeholder') || '').slice(0, 40),
                    innerText: await stat(e.innerText), value: e.tagName === 'TEXTAREA' ? await stat(e.value) : null, counters: counters()}; })()"""))
        if not report["editor_before"]:
            print(json.dumps(report, indent=1)); return
        mode = sys.argv[3] if len(sys.argv) > 3 else "paste"
        if report["editor_before"]["tag"] == "TEXTAREA" or mode == "type":
            # AAD11: DevTools input on the focused editor, Enter once per line feed
            await ev(ws, 3, S("(() => { const e = lyricsEditor(); e.focus(); const r = document.createRange(); r.selectNodeContents(e); r.collapse(false); const s = getSelection(); s.removeAllRanges(); s.addRange(r); return true; })()"))
            report["entry"] = "Input.insertText per line, Enter key per line feed"
            n = 100
            for i, line in enumerate(text.split("\n")):
                if i:
                    for kind in ("keyDown", "keyUp"):
                        n += 1
                        await call(ws, n, "Input.dispatchKeyEvent", {"type": kind, "key": "Enter", "code": "Enter",
                                   "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 36,
                                   **({"text": "\r"} if kind == "keyDown" else {})})
                if line:
                    n += 1
                    await call(ws, n, "Input.insertText", {"text": line})
                await asyncio.sleep(0.02)
        else:
            report["entry"] = "synthetic paste event, text/plain"
            report["paste"] = await ev(ws, 4, S("(() => { const e = lyricsEditor(); e.focus(); const dt = new DataTransfer(); dt.setData('text/plain', "
                                        + json.dumps(text) + "); const ok = e.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true})); return {default_prevented: !ok}; })()"))
        await asyncio.sleep(1.5)
        report["editor_after"] = await ev(ws, 5, S(r"""(async () => { const e = lyricsEditor();
            return {tag: e.tagName, innerText: await stat(e.innerText), textContent: await stat(e.textContent),
                    value: e.tagName === 'TEXTAREA' ? await stat(e.value) : null,
                    paragraphs: e.tagName === 'TEXTAREA' ? null : e.querySelectorAll('p').length,
                    empty_paragraphs: e.tagName === 'TEXTAREA' ? null : [...e.querySelectorAll('p')].filter(p => !p.textContent).length,
                    counters: counters()}; })()"""))
        report["cleared"] = await ev(ws, 6, S(r"""(async () => { const e = lyricsEditor(); e.focus();
            if (e.tagName === 'TEXTAREA') { e.select(); document.execCommand('delete'); }
            else { document.execCommand('selectAll'); document.execCommand('delete'); }
            await new Promise(r => setTimeout(r, 800));
            return {innerText: await stat(e.innerText), counters: counters()}; })()"""))
    print(json.dumps(report, indent=1))

asyncio.run(main(int(sys.argv[1]), sys.argv[2]))
