"""Footwork's own browser operations over CDP, for a Chrome launched by :mod:`.launch`.

This first slice (L3a-1) observes only. Click, type and navigate validate the ref's binding and then
refuse before any input method is sent, saying so (``dispatched=False``). Each ref binds the browser
incarnation, browser context, target, CDP session, main frame, its ``loaderId`` (document generation)
and the backend DOM node; any change refuses. A lost target is never recovered by URL.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from ..base import BrowserRefusal, BrowserReply
from .launch import OwnedChrome, verify_endpoint
from .snapshot import STYLES, compose
from .transport import CdpConnection, CdpError


@dataclass(frozen=True)
class RefBinding:
    incarnation: float
    context_id: str
    target_id: str
    session_id: str
    frame_id: str
    loader_id: str
    backend_node_id: int


def _ok(payload: dict[str, Any]) -> BrowserReply:
    return BrowserReply("ok", "", False, MappingProxyType(payload))


def _refused(code: str, message: str, *, dispatched: bool | None = False) -> BrowserReply:
    detail = {"delivery": "not_sent"} if dispatched is False else None
    refusal = BrowserRefusal(code, message, MappingProxyType(detail) if detail else None)
    payload = {"status": "refused", "refusal": {"code": code, "message": message, **({"detail": detail} if detail else {})}}
    return BrowserReply("refused", f"refused ({code}): {message}", False, MappingProxyType(payload), refusal,
                        dispatched=dispatched)


class CdpBrowserOperations:
    """One owned browser over one verified connection. Implements ``effectors.base.BrowserOperations``."""

    effector = "cdp"

    def __init__(self, chrome: OwnedChrome, conn: CdpConnection):
        self.chrome = chrome
        self.conn = conn
        self.browser_id = f"cdp:{chrome.pid}:{chrome.incarnation!r}"
        self._contexts: dict[str, str] = {}
        self._sessions: dict[str, str] = {}
        self._refs: dict[str, RefBinding] = {}

    @classmethod
    async def connect(cls, chrome: OwnedChrome) -> CdpBrowserOperations:
        conn = await CdpConnection.open(chrome.browser_url)
        try:
            await verify_endpoint(conn, chrome)
        except BaseException:
            await conn.close()
            raise
        return cls(chrome, conn)

    async def close(self) -> None:
        await self.conn.close()

    # ---- binding

    async def prepare(self, *, pid: int, window_id: int) -> BrowserReply:
        if pid != self.chrome.pid or not self.chrome.alive():
            return _refused("browser_identity_mismatch", "the requested browser is not the launched one")
        return _ok({"status": "ok"})

    async def _pages(self) -> list[dict[str, Any]]:
        infos = (await self.conn.send("Target.getTargets")).get("targetInfos") or []
        return [t for t in infos if t.get("type") == "page"]

    async def bind(self, *, pid: int, window_id: int) -> BrowserReply:
        """Bind the owned browser's one page. Several pages are ambiguous in this slice and refuse."""
        if pid != self.chrome.pid or not self.chrome.alive():
            return _refused("browser_identity_mismatch", "the requested browser is not the launched one")
        pages = await self._pages()
        if len(pages) != 1:
            return _refused("browser_binding_ambiguous" if pages else "browser_binding_unavailable",
                            f"the owned browser has {len(pages)} pages; exactly one is supported")
        page = pages[0]
        self._contexts[page["targetId"]] = str(page.get("browserContextId") or "")
        return _ok({
            "status": "ok",
            "target_id": self.browser_id,
            "tabs": [{"tab_id": page["targetId"], "active": True, "url": page.get("url", ""),
                      "title": page.get("title", "")}],
        })

    async def _session(self, target_id: str, tab_id: str | None) -> tuple[str, str] | BrowserReply:
        if target_id != self.browser_id or not self.chrome.alive():
            return _refused("target_changed", "the bound browser is not the one this session launched")
        page = next((p for p in await self._pages() if p.get("targetId") == tab_id), None)
        if page is None:
            return _refused("target_changed", "the bound page no longer exists; it is not rebound by URL")
        context = str(page.get("browserContextId") or "")
        if self._contexts.get(tab_id or "") != context:
            return _refused("target_changed", "the bound page changed browser context")
        if tab_id not in self._sessions:
            attached = await self.conn.send("Target.attachToTarget", {"targetId": tab_id, "flatten": True})
            self._sessions[tab_id] = attached["sessionId"]
        return self._sessions[tab_id], context

    async def _main_frame(self, session: str) -> tuple[dict[str, Any], int]:
        tree = (await self.conn.send("Page.getFrameTree", session_id=session)).get("frameTree") or {}

        def count(node: dict[str, Any]) -> int:
            return sum(1 + count(child) for child in node.get("childFrames") or [])

        return tree.get("frame") or {}, count(tree)

    # ---- observation

    async def snapshot(self, *, target_id: str, tab_id: str | None) -> BrowserReply:
        bound = await self._session(target_id, tab_id)
        if isinstance(bound, BrowserReply):
            return bound
        session, context = bound
        frame, child_frames = await self._main_frame(session)
        loader = frame.get("loaderId")
        if not loader:
            return _refused("document_unavailable", "the page reports no document generation")
        ax = await self.conn.send("Accessibility.getFullAXTree", session_id=session, timeout=20)
        document = await self.conn.send("DOM.getDocument", {"depth": -1, "pierce": True}, session_id=session,
                                        timeout=20)
        layout = await self.conn.send("DOMSnapshot.captureSnapshot", {"computedStyles": list(STYLES)},
                                      session_id=session, timeout=20)
        metrics = await self.conn.send("Page.getLayoutMetrics", session_id=session)
        after, _ = await self._main_frame(session)
        if after.get("loaderId") != loader or after.get("id") != frame.get("id"):
            return _refused("document_changed", "the page loaded a new document while it was being observed")
        snapshot_id = secrets.token_hex(6)
        composed = compose(snapshot_id=snapshot_id, url=str(frame.get("url") or ""), ax=ax, document=document,
                           dom_snapshot=layout, metrics=metrics, child_frames=child_frames)
        for ref, backend in composed.backend.items():
            self._refs[ref] = RefBinding(self.chrome.incarnation, context, str(tab_id), session,
                                         str(frame.get("id")), str(loader), backend)
        return _ok({**composed.semantic, "document": {"frame_id": frame.get("id"), "loader_id": loader}})

    # ---- actions: validated, then refused before dispatch in this slice

    async def validate(self, *, target_id: str, tab_id: str | None, ref: str) -> BrowserReply | RefBinding:
        """Re-establish the exact tuple a ref was observed under; any difference refuses."""
        binding = self._refs.get(ref)
        if binding is None:
            return _refused("stale_ref", "the ref is not from an observation of this connection")
        bound = await self._session(target_id, tab_id)
        if isinstance(bound, BrowserReply):
            return bound
        session, context = bound
        if (binding.target_id, binding.session_id, binding.context_id) != (tab_id, session, context):
            return _refused("target_changed", "the ref belongs to another page or session")
        frame, _ = await self._main_frame(session)
        if (frame.get("id"), frame.get("loaderId")) != (binding.frame_id, binding.loader_id):
            return _refused("document_changed", "the page loaded a new document since it was observed")
        try:
            await self.conn.send("DOM.describeNode", {"backendNodeId": binding.backend_node_id},
                                 session_id=session)
        except CdpError:
            return _refused("stale_ref", "the observed element no longer exists")
        return binding

    async def _unqualified(self, operation: str, **ref: Any) -> BrowserReply:
        if "ref" in ref:
            checked = await self.validate(**ref)
            if isinstance(checked, BrowserReply):
                return checked
        return _refused(
            "browser_mutation_unqualified",
            f"{operation} through Footwork's own browser effector is not qualified yet; nothing was sent",
        )

    async def click(self, *, target_id: str, tab_id: str | None, ref: str, input_route: str) -> BrowserReply:
        return await self._unqualified("click", target_id=target_id, tab_id=tab_id, ref=ref)

    async def type_text(
        self, *, target_id: str, tab_id: str | None, ref: str, text: str, replace: bool
    ) -> BrowserReply:
        return await self._unqualified("type", target_id=target_id, tab_id=tab_id, ref=ref)

    async def navigate(self, *, target_id: str, tab_id: str | None, url: str) -> BrowserReply:
        return await self._unqualified("navigate")
