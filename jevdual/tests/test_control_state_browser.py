"""Control state through a real Chromium (notebook CTL3): browser-use observes, the harness's own click
dispatches, and the effect diff names the transition although no text or URL changes."""

from __future__ import annotations

import asyncio

import pytest
from jevdual.chrome_profile import automation_profile
from jevdual.effects import diff
from jevdual.menu import build_menu

PAGE = """<!doctype html><html><head><title>Settings</title></head><body>
<h1>Settings</h1><p>Every control below changes state without changing any text on the page.</p>
<label><input type="checkbox" id="all"> Select all</label>
<button id="bold" aria-pressed="false">Bold</button>
<button id="more" aria-expanded="false" aria-controls="panel">More options</button>
<div id="panel" hidden></div>
<div role="switch" id="s1" tabindex="0" aria-checked="true" aria-label="Enabled">on/off</div>
<div role="switch" id="s2" tabindex="0" aria-checked="false" aria-label="Enabled">on/off</div>
<script>
document.getElementById('all').indeterminate = true;
const flip = (el, attr) => el.setAttribute(attr, el.getAttribute(attr) === 'true' ? 'false' : 'true');
document.getElementById('bold').onclick = e => flip(e.currentTarget, 'aria-pressed');
document.getElementById('more').onclick = e => flip(e.currentTarget, 'aria-expanded');
for (const id of ['s1', 's2']) document.getElementById(id).onclick = e => flip(e.currentTarget, 'aria-checked');
</script></body></html>"""


@pytest.mark.browser
@pytest.mark.timeout(120)
async def test_state_only_changes_are_named_transitions_in_a_real_browser(httpserver):
    from browser_use import BrowserSession
    from browser_use.tools.service import Tools

    httpserver.expect_request("/").respond_with_data(PAGE, content_type="text/html")
    s = BrowserSession(browser_profile=automation_profile(headless=True))
    await s.start()
    try:
        tools = Tools()
        await s.navigate_to(httpserver.url_for("/"))

        async def look():
            st = await s.get_browser_state_summary(include_screenshot=False)
            ids = {(n.attributes or {}).get("id"): i for i, n in st.dom_state.selector_map.items()}
            return build_menu(st), ids

        async def click(element_id: str):
            before, ids = await look()
            am = tools.registry.create_action_model()
            await tools.act(am(click={"index": ids[element_id]}), s)
            await asyncio.sleep(0.3)
            after, _ = await look()
            return before, after, diff(before, after)

        m, ids = await look()
        by = {c.id: c for c in m.candidates}
        assert by[ids["all"]].checked == "mixed"
        assert by[ids["bold"]].pressed is False and by[ids["more"]].expanded is False

        _, after, e = await click("all")  # an indeterminate checkbox clicked becomes checked
        assert e.status == "changed" and any("checked mixed -> True" in t for t in e.transitions)
        assert e.text_ratio == 1.0 and not e.url_changed

        for element_id, expected in (("bold", "pressed False -> True"), ("more", "expanded False -> True")):
            _, _, e = await click(element_id)
            assert e.status == "changed" and any(expected in t for t in e.transitions), (
                element_id,
                e.summary,
            )

        _, after, e = await click("s2")  # the second of two same-label switches
        assert e.status == "changed" and e.transitions == ("'Enabled' checked False -> True",)
        assert [c.checked for c in after.candidates if c.label == "Enabled"] == [True, True]

        first, _ = await look()  # two looks with nothing in between: no false progress
        second, _ = await look()
        assert diff(first, second).status == "unchanged"
    finally:
        await s.kill()
