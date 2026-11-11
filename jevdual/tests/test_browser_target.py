"""A surviving page's URL never substitutes for a closed session target."""
from __future__ import annotations

import pytest
from jevdual import browser_target
from jevdual.coordination import CoordinationError


@pytest.fixture
def catalogue(monkeypatch):
    identity = {"pid": 77, "incarnation": 1.0, "port": 9333, "profile": "/owned"}
    pages = [{"id": "original", "url": "http://127.0.0.1/form", "type": "page"}]
    monkeypatch.setattr(browser_target, "_catalog", lambda pid: (dict(identity), list(pages)))
    return identity, pages


async def test_missing_original_refuses_even_if_replacement_has_same_url(catalogue):
    _, pages = catalogue
    pin, _ = await browser_target.resolve(77, url=pages[0]["url"])
    pages[0] = {**pages[0], "id": "replacement"}
    with pytest.raises(CoordinationError, match="original.*no longer open"):
        await browser_target.resolve(77, expected=pin)


async def test_original_navigation_is_observable_and_stale_action_refuses(catalogue):
    _, pages = catalogue
    before = pages[0]["url"]
    pin, _ = await browser_target.resolve(77, url=before)
    pages[0]["url"] += "/next"
    assert (await browser_target.resolve(77, expected=pin))[1] == pages[0]["url"]
    with pytest.raises(CoordinationError, match="changed after observation"):
        await browser_target.resolve(77, url=before, expected=pin)


async def test_incarnation_profile_or_port_change_never_adopts_browser(catalogue):
    identity, pages = catalogue
    pin, _ = await browser_target.resolve(77, url=pages[0]["url"])
    for key, value in [("incarnation", 2.0), ("profile", "/other"), ("port", 9555)]:
        original = identity[key]
        identity[key] = value
        with pytest.raises(CoordinationError, match="identity changed"):
            await browser_target.resolve(77, expected=pin)
        identity[key] = original


async def test_duplicate_url_is_ambiguous_even_when_original_id_survives(catalogue):
    _, pages = catalogue
    pin, _ = await browser_target.resolve(77, url=pages[0]["url"])
    pages.append({**pages[0], "id": "peer"})
    with pytest.raises(CoordinationError, match="ambiguous"):
        await browser_target.resolve(77, expected=pin)


async def test_bounded_catalogue_reads_owned_loopback_browser(httpserver, monkeypatch, tmp_path):
    from jevdual import browser_driver

    httpserver.expect_request("/json/list").respond_with_json([
        {"type": "page", "id": "original", "url": "http://127.0.0.1/form"}])
    monkeypatch.setattr(browser_driver, "PORT", httpserver.port)
    monkeypatch.setattr(browser_driver, "PROFILE_DIR", tmp_path / "profile")
    monkeypatch.setattr(browser_driver, "chrome_pid", lambda: 77)
    monkeypatch.setattr(browser_driver, "_incarnation", lambda pid: 1.0)
    pin, url = await browser_target.resolve(77, url="http://127.0.0.1/form")
    assert pin["target"] == "original" and pin["port"] == httpserver.port
    assert url == "http://127.0.0.1/form"
