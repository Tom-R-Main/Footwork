"""The task-level symptom (package C, prediction C4): after the saucedemo login, does browser-use's
own click on "Add to cart" add the item?

Per launch: log in the way the agent does (browser-use input and click actions), read a fresh browser
state, click the backpack's "Add to cart" by its index, then read the cart badge and the element the
click's trusted mousedown actually landed on. Q11 and Q12 recorded these clicks reported as done and
changing nothing.

    uv run python scripts/diag_add_to_cart.py [--launches 10]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os

TRACK = (
    "(()=>{if(!window.__probe){window.__probe=1;window.__hits=[];"
    "window.addEventListener('mousedown',e=>window.__hits.push([e.isTrusted,"
    "(e.target.id||e.target.tagName||'').slice(0,60),e.clientX,e.clientY]),true);}return 1})()"
)


async def ev(s, expr):
    cdp = await s.get_or_create_cdp_session()
    r = await cdp.cdp_client.send.Runtime.evaluate(
        params={"expression": expr, "returnByValue": True}, session_id=cdp.session_id
    )
    return r.get("result", {}).get("value")


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

        def by_id(sm, id_):
            return next((i for i, n in sm.items() if (n.attributes or {}).get("id") == id_), None)

        await s.navigate_to("https://www.saucedemo.com/")
        await asyncio.sleep(1.5)
        sm = (await s.get_browser_state_summary()).dom_state.selector_map
        await act("input", index=by_id(sm, "user-name"), text="standard_user", clear=True)
        await act(
            "input", index=by_id(sm, "password"), text=os.environ.get("SAUCE", "secret_sauce"), clear=True
        )
        await act("click", index=by_id(sm, "login-button"))
        await asyncio.sleep(2)
        await ev(s, TRACK)
        sm = (await s.get_browser_state_summary()).dom_state.selector_map
        idx = by_id(sm, "add-to-cart-sauce-labs-backpack")
        if idx is None:
            return {"launch": k, "error": "no add-to-cart in the fresh selector map"}
        result = await act("click", index=idx)
        await asyncio.sleep(1.0)
        badge = await ev(s, "(document.querySelector('.shopping_cart_badge')||{}).textContent||''")
        hits = json.loads(await ev(s, "JSON.stringify(window.__hits||[])") or "[]")
        rect = await ev(
            s,
            "(()=>{const b=document.getElementById('add-to-cart-sauce-labs-backpack')||"
            "document.getElementById('remove-sauce-labs-backpack');if(!b)return null;"
            "const r=b.getBoundingClientRect();return [Math.round(r.x),Math.round(r.y),"
            "Math.round(r.width),Math.round(r.height)]})()",
        )
        return {
            "launch": k,
            "added": badge == "1",
            "badge": badge,
            "reported": (getattr(result, "extracted_content", "") or "")[:60],
            "error": getattr(result, "error", None),
            "mousedowns": hits,
            "button_rect": rect,
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
    ap.add_argument("--launches", type=int, default=10)
    asyncio.run(main(ap.parse_args().launches))
