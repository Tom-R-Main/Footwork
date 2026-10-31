"""Compatibility protocols for the current driver boundary.

L1a isolates the optional SDK without changing its requests, returned records,
refusal payloads or lifecycle. These are structural driver protocols, not yet
SDK-independent snapshot or action contracts. Normalization is a separate step.
"""

from __future__ import annotations

from typing import Any, Protocol


class EffectorUnavailable(RuntimeError):
    """An optional implementation is absent before driver creation or dispatch."""

    code = "effector_unavailable"
    dispatched = False

    def __init__(self, kind: str, distribution: str, install_hint: str):
        self.kind = kind
        self.distribution = distribution
        self.install_hint = install_hint
        super().__init__(f"{kind} effector requires {distribution}. {install_hint}")


class BrowserEffector(Protocol):
    """Current browser driver operations; wire values remain the adapter's."""

    async def call_tool(self, name: str, arguments_json: str) -> Any: ...

    async def list_windows(self, input: Any) -> Any: ...

    async def shutdown(self) -> None: ...


class DesktopEffector(BrowserEffector, Protocol):
    """Current native bridge operations, with original input/output records."""

    async def list_apps(self, input: Any) -> Any: ...

    async def get_window_state(self, input: Any) -> Any: ...

    async def click(self, input: Any) -> Any: ...

    async def invoke_menu(self, input: Any) -> Any: ...

    async def verify_state(self, input: Any) -> Any: ...
