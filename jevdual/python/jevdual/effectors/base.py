"""Effector protocols and the Footwork-owned browser contract.

L1a isolates the optional SDK without changing its requests, returned records,
refusal payloads or lifecycle; the driver protocols below are still structural.
L1b adds owned browser records (:class:`BrowserReply`, :class:`BrowserRefusal`,
:class:`BrowserBinding`) and the bounded :class:`BrowserOperations` the bridge
calls. Native SDK records stay behind the CUA adapter until an owned desktop
effector needs another shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class BrowserRefusal:
    """A refusal as the effector reported it. A refusal is not proof that nothing was sent."""

    code: str | None
    message: str
    #: the effector's machine detail, unmodified (candidate lists, delivery, retryable, next_call)
    detail: Mapping[str, Any] | None = None

    @property
    def delivery(self) -> str | None:
        """The effector's own delivery word, e.g. ``"unknown"`` after an acknowledged input; else None."""
        value = (self.detail or {}).get("delivery")
        return value if isinstance(value, str) else None

    @property
    def retryable(self) -> bool | None:
        value = (self.detail or {}).get("retryable")
        return value if isinstance(value, bool) else None


@dataclass(frozen=True)
class BrowserReply:
    """One browser operation's reply. ``payload`` keeps every structured field the effector sent."""

    status: str | None
    text: str
    is_error: bool
    payload: Mapping[str, Any] = field(default_factory=dict)
    refusal: BrowserRefusal | None = None
    #: advisory recovery text from the effector; never an instruction to the host agent
    hint: str | None = None
    #: the effector's suggested follow-up call. It names an effector tool, so it is carried for
    #: diagnosis only and never offered to the host agent as a callable surface.
    next_call: Mapping[str, Any] | None = None
    #: False only when the effector knows nothing reached the page (it refused before sending);
    #: None when the reply cannot say, which is every CUA reply
    dispatched: bool | None = None
    #: qualified actual delivery route, when distinct from the caller's requested route
    route: str | None = None

    @property
    def refused(self) -> bool:
        return self.status == "refused" or self.is_error


@dataclass(frozen=True)
class BrowserBinding:
    """The browser target a bridge bound, with the identity this effector cannot supply made explicit.

    CUA's tab ids are handles for one connection, new on every command, so a session rebinds by page
    URL. That is compatibility behavior, not persistent identity: there is no browser context id, no
    document generation and no target identity that survives a reconnection.
    """

    target_id: str
    tabs: tuple[Mapping[str, Any], ...] = ()
    tab_scope: str = "connection"
    context_id: str | None = None
    document_generation: str | None = None
    persistent_target_identity: bool = False


class BrowserOperations(Protocol):
    """The bounded browser surface the bridge uses. No raw tool, CDP or script passthrough."""

    async def prepare(self, *, pid: int, window_id: int) -> BrowserReply: ...

    async def bind(self, *, pid: int, window_id: int) -> BrowserReply: ...

    async def snapshot(self, *, target_id: str, tab_id: str | None) -> BrowserReply: ...

    async def click(self, *, target_id: str, tab_id: str | None, ref: str, input_route: str) -> BrowserReply: ...

    async def type_text(
        self, *, target_id: str, tab_id: str | None, ref: str, text: str, replace: bool
    ) -> BrowserReply: ...

    async def navigate(self, *, target_id: str, tab_id: str | None, url: str) -> BrowserReply: ...


class BrowserEffector(Protocol):
    """Current browser driver lifecycle and wire; values remain the adapter's."""

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
