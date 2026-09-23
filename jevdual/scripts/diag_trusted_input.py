"""Diagnostic: does trusted input (CDP Input.dispatchMouseEvent) still reach the page after a click that
navigated? Found 2026-09-23 while every practice-shop consent task paused on `evaluate`: browser-use 0.13.10
reports "Clicked" but no mousedown reaches the window after the login click, in most launches, on
the-internet.herokuapp.com and saucedemo.com; a page-script click works. Run:

    uv run python scripts/diag_trusted_input.py

Prints one PROBE line per launch: an empty list after a login means trusted input is dead for that page.
"""

import asyncio
import os

from browser_use import BrowserProfile, BrowserSession


async def ev(session, expr):
    cdp = await session.get_or_create_cdp_session()
    r = await cdp.cdp_client.send.Runtime.evaluate(
        params={"expression": expr, "returnByValue": True}, session_id=cdp.session_id
    )
    return r.get("result", {}).get("value")


async def trusted_alive(session):
    """Dispatch a raw mouse move+click at the page centre-ish (on body) and see whether trusted events reach window."""
    await ev(
        session,
        "window.__t=[]; ['mousemove','mousedown'].forEach(t=>window.addEventListener(t,e=>window.__t.push(t+':'+e.isTrusted),true))",
    )
    cdp = await session.get_or_create_cdp_session()
    await cdp.cdp_client.send.Input.dispatchMouseEvent(
        params={"type": "mouseMoved", "x": 400, "y": 300}, session_id=cdp.session_id
    )
    await cdp.cdp_client.send.Input.dispatchMouseEvent(
        params={"type": "mousePressed", "x": 400, "y": 300, "button": "left", "clickCount": 1},
        session_id=cdp.session_id,
    )
    await cdp.cdp_client.send.Input.dispatchMouseEvent(
        params={"type": "mouseReleased", "x": 400, "y": 300, "button": "left", "clickCount": 1},
        session_id=cdp.session_id,
    )
    await asyncio.sleep(0.4)
    return await ev(session, "JSON.stringify(window.__t)")


async def one(k):
    session = BrowserSession(browser_profile=BrowserProfile(headless=True))
    await session.start()
    try:
        from browser_use.tools.service import Tools

        tools = Tools()

        async def act(name, **params):
            am = tools.registry.create_action_model()
            return await tools.act(am(**{name: params}), session)

        out = []
        # A: herokuapp form login (real POST navigation)
        await session.navigate_to("https://the-internet.herokuapp.com/login")
        await asyncio.sleep(1.5)
        out.append(("heroku login page", await trusted_alive(session)))
        sm = (await session.get_browser_state_summary()).dom_state.selector_map
        f = lambda id_: next(i for i, n in sm.items() if (n.attributes or {}).get("id") == id_)
        await act("input", index=f("username"), text="tomsmith", clear=True)
        await act("input", index=f("password"), text="SuperSecretPassword!", clear=True)
        sm2 = (await session.get_browser_state_summary()).dom_state.selector_map
        btn = next(i for i, n in sm2.items() if (n.attributes or {}).get("type") == "submit")
        await act("click", index=btn)
        await asyncio.sleep(2)
        out.append(
            (
                "heroku after login " + str("secure" in (await ev(session, "location.href") or "")),
                await trusted_alive(session),
            )
        )
        # B: saucedemo login
        await session.navigate_to("https://www.saucedemo.com/")
        await asyncio.sleep(1.5)
        out.append(("sauce login page", await trusted_alive(session)))
        sm = (await session.get_browser_state_summary()).dom_state.selector_map
        f = lambda id_: next(i for i, n in sm.items() if (n.attributes or {}).get("id") == id_)
        await act("input", index=f("user-name"), text="standard_user", clear=True)
        await act("input", index=f("password"), text=os.environ.get("SAUCE", "secret_sauce"), clear=True)
        await act("click", index=f("login-button"))
        await asyncio.sleep(2)
        out.append(
            (
                "sauce after login " + str("inventory" in (await ev(session, "location.href") or "")),
                await trusted_alive(session),
            )
        )
        # C: plain navigate_to inventory directly (cookie persists)
        await session.navigate_to("https://www.saucedemo.com/inventory.html")
        await asyncio.sleep(1.5)
        out.append(("sauce inventory via navigate_to", await trusted_alive(session)))
        print(f"PROBE launch {k}: " + " | ".join(f"{a}: {b}" for a, b in out))
    finally:
        await session.kill()


async def main():
    for k in range(2):
        try:
            await one(k)
        except Exception as e:  # noqa: BLE001 - a diagnostic reports and moves on
            print("PROBE launch", k, "error", str(e)[:120])


asyncio.run(main())
