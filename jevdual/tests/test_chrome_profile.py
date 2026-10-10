"""The agent's Chrome must not drop input after a login with a breached password (package C).

Chrome's leak check raises a "Change your password" warning after a form submits a listed password;
in headless Chrome the warning is invisible and every dispatched click is dropped while it is up. The
browser test logs in to a local page with saucedemo's demo password and clicks a button that counts
trusted mousedowns. With a plain ``BrowserProfile`` it received 0 of 3 on 2026-09-26 (notebook U16);
the leak check calls Google's service, so without a network the old profile would pass too, and this
test guards the fix, not the network.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from jevdual.chrome_profile import QUIET_PREFS, TEMP_PREFIX, automation_profile, quiet_profile_dir

LOGIN = """<html><body><form method=post action=/login>
<input id=u name=u autocomplete=username><input id=p name=p type=password autocomplete=current-password>
<button id=go type=submit>Login</button></form></body></html>"""
SHOP = """<html><body><button id=add style='width:200px;height:60px'>Add</button>
<script>window.__md=0;addEventListener('mousedown',e=>{if(e.isTrusted)window.__md++},true)</script>
</body></html>"""


def test_quiet_profile_turns_off_the_password_manager_and_leak_check():
    d = quiet_profile_dir()
    try:
        assert d.name.startswith(TEMP_PREFIX)
        prefs = json.loads((d / "Default" / "Preferences").read_text())
        assert prefs == QUIET_PREFS
        assert prefs["profile"]["password_manager_leak_detection"] is False
    finally:
        import shutil

        shutil.rmtree(d, ignore_errors=True)


def test_automation_profile_uses_a_fresh_quiet_dir_each_time():
    a, b = automation_profile(headless=True), automation_profile(headless=True)
    assert a.user_data_dir != b.user_data_dir
    for p in (a, b):
        assert (Path(str(p.user_data_dir)) / "Default" / "Preferences").exists()


@pytest.mark.browser
@pytest.mark.timeout(120)
async def test_a_click_after_a_breached_password_login_reaches_the_page(httpserver):
    from browser_use import BrowserSession
    from browser_use.tools.service import Tools

    httpserver.expect_request("/", method="GET").respond_with_data(LOGIN, content_type="text/html")
    httpserver.expect_request("/login", method="POST").respond_with_data(SHOP, content_type="text/html")
    s = BrowserSession(browser_profile=automation_profile(headless=True))
    await s.start()
    try:
        tools = Tools()

        async def act(name, **params):
            am = tools.registry.create_action_model()
            return await tools.act(am(**{name: params}), s)

        def by_id(sm, id_):
            return next(i for i, n in sm.items() if (n.attributes or {}).get("id") == id_)

        await s.navigate_to(httpserver.url_for("/"))
        sm = (await s.get_browser_state_summary()).dom_state.selector_map
        await act("input", index=by_id(sm, "u"), text="standard_user", clear=True)
        await act("input", index=by_id(sm, "p"), text="secret_sauce", clear=True)
        await act("click", index=by_id(sm, "go"))
        await asyncio.sleep(3)  # long enough for the leak check to answer
        sm = (await s.get_browser_state_summary()).dom_state.selector_map
        await act("click", index=by_id(sm, "add"))
        await asyncio.sleep(0.5)
        cdp = await s.get_or_create_cdp_session()
        r = await cdp.cdp_client.send.Runtime.evaluate(
            params={"expression": "window.__md", "returnByValue": True}, session_id=cdp.session_id
        )
        assert r["result"]["value"] == 1
    finally:
        await s.kill()
