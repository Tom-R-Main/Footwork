"""Persistent page identity for ordinary owned Chrome across CUA reconnects.

CUA tab handles are connection-local. A bounded read of the configured owned
Chrome's target catalogue pins its CDP page ID and process incarnation instead.
URL is used only to correlate the initial unique page, never to replace a lost ID.
"""
from __future__ import annotations

import asyncio
import json
from urllib.request import urlopen

from .coordination import CoordinationError


def _catalog(pid):
    from . import browser_driver as browser

    if browser.chrome_pid() != pid:
        raise CoordinationError("owned browser process unavailable")
    incarnation = browser._incarnation(pid)
    with urlopen(f"http://127.0.0.1:{browser.PORT}/json/list", timeout=2) as response:
        raw = response.read(1_048_577)
    if len(raw) > 1_048_576:
        raise CoordinationError("owned browser target catalogue exceeds its bound")
    rows = json.loads(raw)
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise CoordinationError("invalid owned browser target catalogue")
    if browser.chrome_pid() != pid or browser._incarnation(pid) != incarnation:
        raise CoordinationError("owned browser process changed while reading targets")
    return {"pid": pid, "incarnation": incarnation, "port": browser.PORT,
            "profile": str(browser.PROFILE_DIR.resolve())}, [row for row in rows if row.get("type") == "page"]


def _resolve(pid, url, expected):
    identity, pages = _catalog(pid)
    if expected:
        if any(expected.get(key) != value for key, value in identity.items()):
            raise CoordinationError("owned browser identity changed; start a fresh session")
        original = [page for page in pages if page.get("id") == expected.get("target")]
        if len(original) != 1:
            raise CoordinationError("the original browser page is no longer open; nothing dispatched")
        page = original[0]
        if url is not None and page.get("url") != url:
            raise CoordinationError("the original browser page changed after observation; observe again")
    else:
        same = [page for page in pages if page.get("url") == url]
        if len(same) != 1:
            raise CoordinationError("initial browser page requires one unique exact URL in the owned browser")
        page = same[0]
    # A URL peer could make CUA's connection-local handle correlation ambiguous.
    if sum(row.get("url") == page.get("url") for row in pages) != 1:
        raise CoordinationError("browser page URL is ambiguous; no replacement target is selected")
    if not isinstance(page.get("id"), str) or not page["id"] or not isinstance(page.get("url"), str):
        raise CoordinationError("browser page identity unavailable")
    return {**identity, "target": page["id"]}, page["url"]


async def resolve(pid, *, url=None, expected=None):
    return await asyncio.to_thread(_resolve, pid, url, expected)
