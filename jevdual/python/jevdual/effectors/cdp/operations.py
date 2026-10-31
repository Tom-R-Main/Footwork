"""Footwork's own browser operations over CDP, for a Chrome launched by :mod:`.launch`.

The DOM route qualifies plain native button activation on one connection; it is not the pointer/mouse
event sequence used by CUA. Typing, trusted input and navigation remain unavailable. Each ref binds the browser
incarnation, browser context, target, CDP session, main frame, its ``loaderId`` (document generation)
and the backend DOM node; any change refuses. A lost target is never recovered by URL.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from ..base import BrowserRefusal, BrowserReply
from .click import ACTIVATE, MARK_DOCUMENT, ROUTE, ButtonTarget, button_targets
from .launch import OwnedChrome, verify_endpoint
from .snapshot import STYLES, compose
from .transport import CdpClosed, CdpConnection, CdpError, CdpUnknownOutcome

log = logging.getLogger("jevdual.browser")


@dataclass(frozen=True)
class RefBinding:
    incarnation: float
    context_id: str
    target_id: str
    session_id: str
    frame_id: str
    loader_id: str
    backend_node_id: int
    execution_context_id: int | None = None
    button: ButtonTarget | None = None
    document_token: str | None = None


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
        self._ownership = asyncio.Lock()
        self._world_name = f"footwork-{secrets.token_hex(12)}"
        self._document_key = f"__footwork_document_{secrets.token_hex(16)}"
        self._click_unknown = False

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
        self._refs.clear()
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
        async with self._ownership:
            self._refs.clear()
            return await self._snapshot(target_id=target_id, tab_id=tab_id)

    async def _snapshot(self, *, target_id: str, tab_id: str | None) -> BrowserReply:
        bound = await self._session(target_id, tab_id)
        if isinstance(bound, BrowserReply):
            return bound
        session, context = bound
        frame, child_frames = await self._main_frame(session)
        loader = frame.get("loaderId")
        if not loader:
            return _refused("document_unavailable", "the page reports no document generation")
        try:
            world = await self.conn.send("Page.createIsolatedWorld", {
                "frameId": frame.get("id"), "worldName": self._world_name,
            }, session_id=session)
        except CdpError:
            return _refused("document_unavailable", "the observation's isolated context is unavailable")
        execution_context = world.get("executionContextId")
        if type(execution_context) is not int or execution_context <= 0:
            return _refused("document_unavailable", "the observation reports no isolated context")
        document_token = secrets.token_hex(16)
        try:
            marked = await self.conn.send("Runtime.callFunctionOn", {
                "executionContextId": execution_context, "functionDeclaration": MARK_DOCUMENT,
                "arguments": [{"value": self._document_key}, {"value": document_token}],
                "returnByValue": True, "awaitPromise": False,
            }, session_id=session)
        except (CdpError, CdpClosed, CdpUnknownOutcome):
            return _refused("document_unavailable", "the observation's private document marker is unavailable")
        remote = marked.get("result") if isinstance(marked, dict) else None
        if (not isinstance(remote, dict) or marked.get("exceptionDetails")
                or remote.get("value") != {"status": "document_marked", "token": document_token}):
            return _refused("document_unavailable", "the observation's private document marker was not established")
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
        buttons = button_targets(document, composed.semantic.get("refs") or [], composed.backend)
        for ref, backend in composed.backend.items():
            self._refs[ref] = RefBinding(self.chrome.incarnation, context, str(tab_id), session,
                                         str(frame.get("id")), str(loader), backend, execution_context,
                                         buttons.get(backend), document_token)
        return _ok({**composed.semantic, "document": {"frame_id": frame.get("id"), "loader_id": loader}})

    # ---- bounded native button activation; all other mutations remain unavailable

    async def validate(self, *, target_id: str, tab_id: str | None, ref: str) -> BrowserReply | RefBinding:
        """Re-establish the exact tuple a ref was observed under; any difference refuses."""
        binding = self._refs.get(ref)
        if binding is None:
            return _refused("stale_ref", "the ref is not from an observation of this connection")
        if binding.incarnation != self.chrome.incarnation:
            return _refused("target_changed", "the ref belongs to another browser incarnation")
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
        async with self._ownership:
            if self._click_unknown:
                return _refused("browser_delivery_unknown", "an earlier activation is unresolved; no further click was sent")
            if input_route != "dom_event":
                return _refused("browser_route_unqualified", "only bounded native-button DOM activation is qualified")
            try:
                binding = await self.validate(target_id=target_id, tab_id=tab_id, ref=ref)
                if isinstance(binding, BrowserReply):
                    return binding
                if binding.button is None or binding.execution_context_id is None:
                    return _refused("browser_mutation_unqualified", "this control is outside the qualified native-button subset")
                if not binding.document_token:
                    return _refused("document_unavailable", "the observed document has no private marker; no activation was sent")
                resolved = await self.conn.send("DOM.resolveNode", {
                    "backendNodeId": binding.backend_node_id,
                    "executionContextId": binding.execution_context_id,
                }, session_id=binding.session_id)
                obj = (resolved.get("object") or {}).get("objectId")
                if not isinstance(obj, str) or not obj:
                    return _refused("stale_ref", "the exact observed node could not be resolved")
            except (CdpError, CdpClosed, CdpUnknownOutcome):
                return _refused("browser_validation_unavailable", "read-only target validation failed; no activation was sent")

            # Admission is connection-local. No fresh observation can reset ambiguity, and the
            # current observation is consumed before anything that might activate a control.
            self._refs.clear()
            self._click_unknown = True
            try:
                try:
                    result = await self.conn.send("Runtime.callFunctionOn", {
                        "objectId": obj, "functionDeclaration": ACTIVATE,
                        "arguments": [{"value": binding.button.argument()}, {"value": self._document_key},
                                      {"value": binding.document_token}],
                        "returnByValue": True, "awaitPromise": False,
                    }, session_id=binding.session_id)
                except CdpClosed:
                    self._click_unknown = False
                    return _refused("browser_connection_closed", "the connection closed before activation was sent")
                except asyncio.CancelledError:
                    raise  # the unknown latch survives cancellation
                except Exception:  # noqa: BLE001 - admission makes every unclassified loss unknown
                    return self._unknown_click()
                if not isinstance(result, dict):
                    return self._unknown_click()
                remote = result.get("result")
                value = remote.get("value") if isinstance(remote, dict) else None
                if result.get("exceptionDetails") or not isinstance(value, dict):
                    return self._unknown_click()
                if value.get("status") == "refused" and value.get("code") in {
                    "stale_ref", "button_changed", "button_disabled", "button_hidden", "button_validation_unavailable",
                    "document_changed",
                }:
                    self._click_unknown = False
                    return _refused(value["code"], "the native button changed or is ineligible; no activation was sent")
                if value == {"status": "invoked"}:
                    self._click_unknown = False
                    return BrowserReply("ok", "native button activation invoked; business effect unverified", False,
                                        MappingProxyType({"status": "ok", "route": ROUTE}),
                                        dispatched=True, route=ROUTE)
                return self._unknown_click()
            finally:
                try:
                    await self.conn.send("Runtime.releaseObject", {"objectId": obj},
                                         session_id=binding.session_id, timeout=0.2)
                except asyncio.CancelledError:
                    self._click_unknown = True
                    raise
                except Exception as exc:  # noqa: BLE001 - cleanup cannot settle or mask the activation
                    log.debug("CDP read-handle release unavailable (%s)", type(exc).__name__)

    def _unknown_click(self) -> BrowserReply:
        detail = {"delivery": "unknown", "retryable": False}
        refusal = BrowserRefusal("browser_delivery_unknown", "native button activation may have happened; do not retry",
                                 MappingProxyType(detail))
        return BrowserReply("refused", refusal.message, False, MappingProxyType({
            "status": "refused", "refusal": {"code": refusal.code, "message": refusal.message, "detail": detail},
        }), refusal, dispatched=None, route=ROUTE)

    async def type_text(
        self, *, target_id: str, tab_id: str | None, ref: str, text: str, replace: bool
    ) -> BrowserReply:
        return await self._unqualified("type", target_id=target_id, tab_id=tab_id, ref=ref)

    async def navigate(self, *, target_id: str, tab_id: str | None, url: str) -> BrowserReply:
        return await self._unqualified("navigate")
