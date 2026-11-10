"""Select an effector without importing its optional implementation at startup.

The compatibility desktop/browser factories below use the optional CUA extra.
The owned CDP and read-only Lightpanda commands select their own implementations
explicitly; installing fewer dependencies never switches a live session's route.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .base import (
    BrowserBinding,
    BrowserEffector,
    BrowserOperations,
    BrowserRefusal,
    BrowserReply,
    DesktopEffector,
    EffectorUnavailable,
)

__all__ = [
    "BrowserBinding", "BrowserEffector", "BrowserOperations", "BrowserRefusal", "BrowserReply",
    "DesktopEffector", "EffectorUnavailable",
    "browser_effector", "browser_operations", "desktop_effector", "require_available",
]


def require_available(kind: str) -> None:
    from .cua import require_available as require_cua

    require_cua(kind)


def desktop_effector() -> DesktopEffector:
    from .cua import create_desktop_driver

    return create_desktop_driver()


def browser_effector(pid: int, *, host_factory: Callable[[int], Any]) -> BrowserEffector:
    from .cua import create_browser_driver

    return create_browser_driver(pid, host_factory=host_factory)


def browser_operations(driver: Any, *, session: str) -> BrowserOperations:
    """The bounded browser operations over ``driver``. Imports no SDK; the driver already exists."""
    from .cua import CuaBrowserOperations

    return CuaBrowserOperations(driver, session=session)
