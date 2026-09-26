"""Where does trusted input go after the saucedemo login? (package C, exploratory E1)

For each launch: the login probe, browser-use's login click, then for the focused page target every
CDP session browser-use holds for it, and one raw mouse click sent through each session in turn,
counting the trusted mousedowns that reach the page. Listeners are installed once per document
(guarded by a flag), so a document that survives the login is not double-counted.

    uv run python scripts/diag_input_sessions.py [--launches 6]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os

LISTEN = (
    "(()=>{if(!window.__probe){window.__probe=1;window.__t=[];"
    "window.addEventListener('mousedown',e=>window.__t.push(e.isTrusted),true);}"
    "return performance.timeOrigin;})()"
)


async def ev(session, sid, expr):
    cdp = await session.get_or_create_cdp_session()
    r = await cdp.cdp_client.send.Runtime.evaluate(
        params={"expression": expr, "returnByValue": True}, session_id=sid or cdp.session_id
    )
    return r.get("result", {}).get("value")


async def click_via(session, sid, x=600, y=300) -> None:
    cdp = await session.get_or_create_cdp_session()
    for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
        p = {"type": kind, "x": x, "y": y}
        if kind != "mouseMoved":
            p |= {"button": "left", "clickCount": 1}
        await cdp.cdp_client.send.Input.dispatchMouseEvent(params=p, session_id=sid)


async def arrivals(session, sid) -> int:
    await ev(session, None, "window.__t && (window.__t.length=0)")
    try:
        await click_via(session, sid)
    except Exception as exc:  # noqa: BLE001 - a dead session is the finding
        return f"error {type(exc).__name__}: {str(exc)[:60]}"
    await asyncio.sleep(0.4)
    v = await ev(session, None, "JSON.stringify(window.__t||[])")
    return sum(1 for x in json.loads(v or "[]") if x)


async def one(k: int) -> dict:
    from browser_use import BrowserProfile, BrowserSession
    from browser_use.tools.service import Tools

    s = BrowserSession(browser_profile=BrowserProfile(headless=True))
    await s.start()
    try:
        tools = Tools()

        async def act(name, **params):
            am = tools.registry.create_action_model()
            return await tools.act(am(**{name: params}), s)

        await s.navigate_to("https://www.saucedemo.com/")
        await asyncio.sleep(1.5)
        origin_before = await ev(s, None, LISTEN)
        focus_before = s.agent_focus_target_id
        before = await arrivals(s, (await s.get_or_create_cdp_session()).session_id)
        sm = (await s.get_browser_state_summary()).dom_state.selector_map
        f = lambda id_: next(i for i, n in sm.items() if (n.attributes or {}).get("id") == id_)
        await act("input", index=f("user-name"), text="standard_user", clear=True)
        await act("input", index=f("password"), text=os.environ.get("SAUCE", "secret_sauce"), clear=True)
        await act("click", index=f("login-button"))
        await asyncio.sleep(2)
        origin_after = await ev(s, None, LISTEN)
        focus = s.agent_focus_target_id
        chosen = (await s.get_or_create_cdp_session()).session_id
        mapping = s.session_manager.get_target_sessions_mapping()
        targets = (await s._cdp_client_root.send.Target.getTargets())["targetInfos"]
        pages = [
            (t["targetId"][-6:], t["type"], t["url"][:50], t.get("attached"))
            for t in targets
            if t["type"] in ("page", "iframe")
        ]
        per_session = {}
        for sid in sorted(mapping.get(focus, set())):
            per_session[sid[-6:]] = await arrivals(s, sid)
        return {
            "launch": k,
            "before_login": before,
            "document_replaced": origin_before != origin_after,
            "focus_changed": focus_before != focus,
            "focus": (focus or "")[-6:],
            "sessions_for_focus": len(mapping.get(focus, set())),
            "chosen": chosen[-6:],
            "via_chosen": await arrivals(s, chosen),
            "via_each": per_session,
            "pages": pages,
            "url": (await ev(s, None, "location.href") or "")[-30:],
        }
    finally:
        await s.kill()


async def main(n: int) -> None:
    for k in range(n):
        try:
            print(json.dumps(await one(k)), flush=True)
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"launch": k, "error": f"{type(exc).__name__}: {str(exc)[:120]}"}), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--launches", type=int, default=6)
    asyncio.run(main(ap.parse_args().launches))
