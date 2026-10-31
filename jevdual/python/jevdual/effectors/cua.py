"""The sole runtime import boundary for the pinned CUA SDK.

This compatibility stage deliberately returns the original SDK driver and
records. It does not translate effects, retry operations, catch cancellation or
shorten shutdown. Footwork-owned normalized records follow in L1b.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

from .base import EffectorUnavailable

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


def require_available(kind: str) -> None:
    """Import-check the implementation without constructing a driver."""
    _sdk(kind)


def create_desktop_driver() -> Any:
    return _sdk().CuaDriver.create(embedded=True)


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
    return cd.CuaDriver.create_configured_with_authorization_host(opts, host_factory(pid)())


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
