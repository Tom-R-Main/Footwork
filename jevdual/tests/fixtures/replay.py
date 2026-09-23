"""Offline replay: run browser-use's real DOM pipeline on a recorded fixture, no browser.

``DomService.get_dom_tree`` fetches CDP trees through ``_get_all_trees`` and then
does pure computation (AX lookup, snapshot lookup, enhanced tree construction,
serialization). The replay swaps only ``_get_all_trees`` for the fixture's
recorded ``TargetAllTrees`` and supplies a stub browser session exposing the
handful of attributes the pure path reads. Everything downstream is upstream code,
so equality tests and the menu builder see exactly what production sees.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from functools import cache
from typing import Any

from browser_use.browser.views import BrowserStateSummary, PageInfo
from browser_use.dom.service import DomService
from browser_use.dom.views import EnhancedDOMTreeNode, SerializedDOMState

from tests.fixtures.loader import Fixture, load_fixture

REPLAY_TARGET_ID = "replay-target"
REPLAY_SESSION_ID = "replay-session"


@dataclass
class _StubCdpSession:
    session_id: str = REPLAY_SESSION_ID
    target_id: str = REPLAY_TARGET_ID


class _StubBrowserSession:
    """Only what DomService reads on the pure computation path."""

    def __init__(self) -> None:
        self.id = "replay-browser-session"
        self.agent_focus_target_id = REPLAY_TARGET_ID
        self.logger = logging.getLogger("jevdual.replay")
        self._cdp = _StubCdpSession()

    async def get_or_create_cdp_session(
        self, target_id: str | None = None, focus: bool = False
    ) -> _StubCdpSession:
        return self._cdp

    async def get_all_frames(self) -> tuple[dict, dict]:  # only reached with cross_origin_iframes=True
        return {}, {}


class _ReplayDomService(DomService):
    def __init__(self, fixture: Fixture, **kwargs: Any) -> None:
        super().__init__(_StubBrowserSession(), logger=logging.getLogger("jevdual.replay"), **kwargs)
        self._fixture = fixture

    async def _get_all_trees(self, target_id: str):  # type: ignore[override]
        return self._fixture.to_target_all_trees()


def _run(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Inside a running loop (pytest-asyncio): run on a private loop in a thread.
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(asyncio.run, coro).result()


@cache
def replay_serialized(slug: str) -> tuple[SerializedDOMState, EnhancedDOMTreeNode, dict[str, float]]:
    """Serialized DOM state, enhanced root and timing for a fixture, via the real pipeline."""

    fixture = load_fixture(slug)
    svc = _ReplayDomService(fixture)
    return _run(svc.get_serialized_dom_tree(None))


def page_info(fixture: Fixture) -> PageInfo:
    """PageInfo from the recorded Page.getLayoutMetrics."""

    vp = fixture.viewport
    layout = vp.get("cssLayoutViewport") or vp.get("layoutViewport") or {}
    content = vp.get("cssContentSize") or vp.get("contentSize") or {}
    visual = vp.get("cssVisualViewport") or vp.get("visualViewport") or {}
    vw = int(layout.get("clientWidth", 0))
    vh = int(layout.get("clientHeight", 0))
    pw = int(content.get("width", vw))
    ph = int(content.get("height", vh))
    sx = int(visual.get("pageX", layout.get("pageX", 0)))
    sy = int(visual.get("pageY", layout.get("pageY", 0)))
    return PageInfo(
        viewport_width=vw,
        viewport_height=vh,
        page_width=pw,
        page_height=ph,
        scroll_x=sx,
        scroll_y=sy,
        pixels_above=max(0, sy),
        pixels_below=max(0, ph - vh - sy),
        pixels_left=max(0, sx),
        pixels_right=max(0, pw - vw - sx),
    )


def _title(root: EnhancedDOMTreeNode) -> str:
    """First <title> of the main document, in document order; iframe documents are not entered."""
    queue = [root]
    while queue:
        n = queue.pop(0)
        if n.node_name.upper() == "TITLE":
            return n.get_all_children_text()
        queue.extend(n.children_and_shadow_roots)
    return ""


@cache
def replay_state(slug: str) -> BrowserStateSummary:
    """A BrowserStateSummary as the agent would receive it, built from the fixture."""

    fixture = load_fixture(slug)
    dom_state, root, _timing = replay_serialized(slug)
    info = page_info(fixture)
    return BrowserStateSummary(
        dom_state=dom_state,
        url=fixture.url,
        title=_title(root),
        tabs=[],
        screenshot=None,
        page_info=info,
        pixels_above=info.pixels_above,
        pixels_below=info.pixels_below,
    )
