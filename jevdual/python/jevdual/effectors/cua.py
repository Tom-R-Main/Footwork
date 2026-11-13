"""The sole runtime import boundary for the pinned CUA SDK.

Native callers still receive the original SDK driver and records. The browser
bridge instead calls :class:`CuaBrowserOperations`, which sends the same tool
requests as before and translates each reply into Footwork-owned records without
dropping fields. Nothing here retries operations, catches cancellation or
shortens shutdown.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Any

from .base import BrowserRefusal, BrowserReply, EffectorUnavailable

log = logging.getLogger("jevdual.browser")
_INSTALL_HINT = "Install the matching full Footwork bundle with its pinned cua-driver wheel."


def _sdk(kind: str = "desktop") -> Any:
    try:
        import cua_driver
    except ModuleNotFoundError as exc:
        if exc.name != "cua_driver":
            # A broken SDK/native library or transitive dependency is not a
            # missing optional effector. Preserve its actual diagnostic.
            raise
        raise EffectorUnavailable(kind, "cua-driver", _INSTALL_HINT) from exc
    return cua_driver


def cursor_planner() -> Any:
    """CUA's pure motion planner (``plan_cursor_move`` and its request types); no driver, no input."""
    return _sdk("desktop")


def require_available(kind: str) -> None:
    """Import-check the implementation without constructing a driver."""
    _sdk(kind)


def create_desktop_driver() -> Any:
    from jevdual.coordination import guard_driver

    return guard_driver(_sdk().CuaDriver.create(embedded=True))


def authorization_host(pid: int, *, executable: str, owned_pid: Callable[[], int | None]) -> Any:
    """Build the original authorization host against the caller's owned root."""
    import psutil

    cd = _sdk("browser")
    if owned_pid() != pid:
        raise RuntimeError("browser process does not match the owned profile")
    incarnation = psutil.Process(pid).create_time()

    class FootworkAuthorizationHost(cd.DriverAuthorizationHost):
        async def authorize(self, request: Any) -> Any:
            try:
                res = json.loads(request.resource_json or "{}")
            except json.JSONDecodeError:
                res = {}
            if not isinstance(res, dict):
                res = {}
            fp = res.get("process_fingerprint") or {}
            if not isinstance(fp, dict):
                fp = {}
            try:
                same_process = owned_pid() == pid and psutil.Process(pid).create_time() == incarnation
            except (psutil.Error, RuntimeError, OSError):
                same_process = False
            ok = (
                same_process
                and res.get("pid") == pid
                and res.get("endpoint_owner_pid") in (None, pid)
                and fp.get("executable") == executable
            )
            log.info(
                "driver authorization %s: %s", "allowed" if ok else "denied", request.human_summary[:160]
            )
            action = cd.DriverAuthorizationAction.ALLOW if ok else cd.DriverAuthorizationAction.DENY
            return cd.DriverAuthorizationDecision(action=action, request_digest=request.request_digest)

    return FootworkAuthorizationHost


def create_browser_driver(pid: int, *, host_factory: Callable[[int], Any]) -> Any:
    cd = _sdk("browser")
    from cua_driver import _native

    _native.uniffi_set_event_loop(asyncio.get_running_loop())
    opts = cd.ConfiguredDriverOptions(
        claude_code_compatibility=False,
        authorization=cd.RuntimeAuthorizationOptions(
            allowed_modes=[cd.SessionPermissionMode.STANDARD],
            compatibility_mode=cd.SessionPermissionMode.STANDARD,
            compatibility_capability_manifest_path=None,
            compatibility_bounded_manifest_path=None,
            unrestricted_acknowledged=False,
            max_session_ttl_seconds=8 * 3600,
            max_idle_ttl_seconds=1800,
        ),
    )
    from jevdual.coordination import guard_driver

    return guard_driver(cd.CuaDriver.create_configured_with_authorization_host(opts, host_factory(pid)()))


def _frozen(value: Any) -> Mapping[str, Any] | None:
    return MappingProxyType(value) if isinstance(value, dict) else None


_REFUSAL_SUMMARY = re.compile(r"refused \(([a-z0-9_]+)\):\s*(.*)", re.DOTALL)


def browser_reply(result: Any) -> BrowserReply:
    """Translate one browser ``ToolResult``. Every structured field is kept in ``payload``.

    Browser tools reply ``{"status": "ok" | "refused", ...}``; a refusal is ``{"refusal": {code,
    message, detail?}}`` and the recovery layer adds top-level ``hint`` and ``next_call``
    (cua-driver-core browser/refusal.rs and recovery_hint.rs at d5373879). An unreadable reply has no
    status; it is not evidence of an effect.
    """
    try:
        payload = json.loads(getattr(result, "structured_json", None) or "{}")
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    text = str(getattr(result, "text", "") or "")
    status = payload.get("status")
    raw_refusal = payload.get("refusal")
    refusal = None
    if isinstance(raw_refusal, dict) or status == "refused":
        raw_refusal = raw_refusal if isinstance(raw_refusal, dict) else {}
        code = raw_refusal.get("code")
        refusal = BrowserRefusal(
            code=code if isinstance(code, str) else None,
            message=str(raw_refusal.get("message") or ""),
            detail=_frozen(raw_refusal.get("detail")),
        )
    if refusal is None and payload.get("effect") == "refused" and status is None:
        # cua-driver 0.46 projects an action tool's refusal as an ActionResult: effect "refused",
        # the code only in its summary ("refused (<code>): <message>"), no status, no refusal object
        # and so no delivery word (tool.rs publish_action_result; BH14). Whether input was sent is
        # therefore unknown here: the refusal carries no detail and dispatched stays None.
        summary = str(payload.get("summary") or text)
        match = _REFUSAL_SUMMARY.match(summary.strip())
        status = "refused"
        refusal = BrowserRefusal(code=match.group(1) if match else None,
                                 message=(match.group(2) if match else summary)[:2000])
    hint = payload.get("hint")
    next_call = payload.get("next_call")
    if next_call is None and refusal is not None and refusal.detail is not None:
        next_call = refusal.detail.get("next_call")
    # cua-driver 0.46 replaces a successful action tool's structured content with its typed result
    # (cua-driver-core tool.rs publish_action_result; cua-driver-contract outputs.rs ActionResult):
    # effect, route, delivery, evidence, escalation, summary, hint, and no status.
    effect = payload.get("effect")
    raw_evidence = payload.get("evidence")
    evidence = tuple(
        f"{item.get('kind')}: {item.get('detail')}" if item.get("detail") else str(item.get("kind"))
        for item in (raw_evidence if isinstance(raw_evidence, list) else [])
        if isinstance(item, dict) and isinstance(item.get("kind"), str)
    )
    return BrowserReply(
        status=status if isinstance(status, str) else None,
        text=text,
        is_error=bool(getattr(result, "is_error", False)),
        payload=MappingProxyType(payload),
        refusal=refusal,
        hint=hint if isinstance(hint, str) else None,
        next_call=_frozen(next_call),
        effect=effect if isinstance(effect, str) else None,
        evidence=evidence,
        escalation=_frozen(payload.get("escalation")),
    )


class CuaBrowserOperations:
    """The bridge's bounded browser surface over CUA's browser tools on one driver connection."""

    def __init__(self, driver: Any, *, session: str):
        self.driver = driver
        self.session = session

    async def _call(self, name: str, args: dict[str, Any]) -> BrowserReply:
        return browser_reply(await self.driver.call_tool(name, json.dumps({"session": self.session, **args})))

    async def prepare(self, *, pid: int, window_id: int) -> BrowserReply:
        return await self._call(
            "browser_prepare", {"pid": pid, "window_id": window_id, "strategy": {"kind": "existing_profile"}}
        )

    async def bind(self, *, pid: int, window_id: int) -> BrowserReply:
        return await self._call("get_browser_state", {"pid": pid, "window_id": window_id})

    async def snapshot(self, *, target_id: str, tab_id: str | None) -> BrowserReply:
        return await self._call(
            "get_browser_state", {"target_id": target_id, "tab_id": tab_id, "snapshot_format": "semantic_v2"}
        )

    async def click(self, *, target_id: str, tab_id: str | None, ref: str, input_route: str) -> BrowserReply:
        return await self._call(
            "browser_click", {"target_id": target_id, "tab_id": tab_id, "ref": ref, "input_route": input_route}
        )

    async def locate(
        self, *, target_id: str, tab_id: str | None, ref: str, point: Any = None
    ) -> BrowserReply:
        """Where one current ref's element is in the viewport (get_browser_state's locate mode,
        cua-driver locate2). Read-only: nothing is scrolled, focused or dispatched. ``point`` (x, y in
        viewport CSS px) also asks what is at that point."""
        args: dict[str, Any] = {"target_id": target_id, "tab_id": tab_id, "locate_ref": ref}
        if point is not None:
            args["locate_point"] = {"x": float(point[0]), "y": float(point[1])}
        return await self._call("get_browser_state", args)

    async def type_text(
        self, *, target_id: str, tab_id: str | None, ref: str, text: str, replace: bool
    ) -> BrowserReply:
        # insert_text only: keystroke mode is never used (browser_driver.BrowserBridge.act)
        return await self._call(
            "browser_type",
            {"target_id": target_id, "tab_id": tab_id, "ref": ref, "text": text, "mode": "insert_text",
             "replace": replace},
        )

    async def navigate(self, *, target_id: str, tab_id: str | None, url: str) -> BrowserReply:
        return await self._call("browser_navigate", {"target_id": target_id, "tab_id": tab_id, "url": url})


# Explicit compatibility constructors: no coercion or defaults are introduced.
# SDK contract tests continue to pin these records; callers can retain driver
# doubles without constructing a runtime or replacing their output objects.
def list_apps_input(**fields: Any) -> Any:
    return _sdk().ListAppsInput(**fields)


def list_windows_input(**fields: Any) -> Any:
    return _sdk().ListWindowsInput(**fields)


def window_state_input(**fields: Any) -> Any:
    return _sdk().GetWindowStateInput(**fields)


def click_input(**fields: Any) -> Any:
    return _sdk().ClickInput(**fields)


def invoke_menu_input(**fields: Any) -> Any:
    return _sdk().InvokeMenuInput(**fields)


def verify_state_input(**fields: Any) -> Any:
    return _sdk().VerifyStateInput(**fields)


def window_target(*, pid: int, window_id: int) -> Any:
    return _sdk().ActionTarget.WINDOW(pid=pid, window_id=window_id)


def element_position(*, element_token: str) -> Any:
    return _sdk().ClickPosition.ELEMENT(element_token=element_token)


def background_delivery() -> Any:
    return _sdk().InputDeliveryMode.BACKGROUND


def foreground_delivery() -> Any:
    return _sdk().InputDeliveryMode.FOREGROUND
