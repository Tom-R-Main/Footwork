"""Select an effector without importing its optional implementation at startup.

Only CUA is selected today. The base install and runtime selection do not change
until an independent browser effector and its evidence contract are qualified.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .base import BrowserEffector, DesktopEffector, EffectorUnavailable

__all__ = [
    "BrowserEffector", "DesktopEffector", "EffectorUnavailable",
    "browser_effector", "desktop_effector", "require_available",
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
