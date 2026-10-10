"""Explicitly scoped browser reads and TextEdit appends using existing bridges.

The startup scope is trusted configuration. Tool arguments cannot name a new
app, document, profile or execution route. No task planner or raw driver tool
is exposed by this adapter.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from .contracts import CapabilityError, DispatchOutcome, Validated
from .observations import Observations


@dataclass
class BoundResource:
    name: str
    driver: Any
    bridge: Any
    snapshot: Any


class ScopedBackend:
    def __init__(self, scope: dict[str, Any], *, durable: bool = False) -> None:
        self._check_scope(scope)
        self.durable = durable
        self.scope = scope
        self.task = scope["task"]
        self.observations = Observations()
        self.bound: dict[str, BoundResource] = {}
        self.session = "footwork-slice-" + uuid4().hex

    @staticmethod
    def _check_scope(scope: Any) -> None:
        if not isinstance(scope, dict) or set(scope) != {"task", "source", "destination"}:
            raise CapabilityError("invalid_scope", "Scope requires task, source and destination")
        if not isinstance(scope["task"], str) or not scope["task"].strip():
            raise CapabilityError("invalid_scope", "Scope task must be a nonempty string")
        for name in ("source", "destination"):
            spec = scope[name]
            required = {"pid", "window_id", "url" if name == "source" else "document"}
            if not isinstance(spec, dict) or set(spec) != required:
                raise CapabilityError("invalid_scope", f"Invalid {name} scope fields")
            for field in ("pid", "window_id"):
                if type(spec[field]) is not int or spec[field] <= 0:
                    raise CapabilityError("invalid_scope", f"{name}.{field} must be a positive integer")
        url = scope["source"]["url"]
        if not isinstance(url, str):
            raise CapabilityError("invalid_scope", "Source URL must be a string")
        parts = urlsplit(url)
        if parts.scheme != "http" or parts.hostname not in ("127.0.0.1", "localhost", "::1"):
            raise CapabilityError("invalid_scope", "The thin slice reads a loopback HTTP fixture only")
        if parts.username or parts.password or parts.fragment:
            raise CapabilityError("invalid_scope", "Source URL cannot contain credentials or a fragment")
        document = scope["destination"]["document"]
        if not isinstance(document, str) or not Path(document).is_absolute():
            raise CapabilityError("invalid_scope", "Destination document must have an absolute path")

    def resource_id(self, name: str) -> str:
        spec = self.scope[name]
        # Same native window always has the same key, including after restart.
        # Unknown operations block new binds/aliases from bypassing recovery.
        prefix = "browser" if name == "source" else "native"
        return f"{prefix}:{spec['pid']}:{spec['window_id']}"

    async def bind(self, name: str) -> dict[str, Any]:
        if name not in ("source", "destination"):
            raise CapabilityError("outside_scope", "Choose source or destination")
        resource = self.resource_id(name)
        if resource not in self.bound:
            if name == "source":
                from jevdual.browser_driver import BrowserBridge, configured_driver

                spec = self.scope[name]
                driver = configured_driver(spec["pid"])
                bridge = BrowserBridge(driver, spec["pid"], spec["window_id"], session=self.session)
                try:
                    await bridge.attach(expect_url=spec["url"])
                    snapshot = await bridge.observe()
                except BaseException:
                    await driver.shutdown()
                    raise
            else:
                from cua_driver import CuaDriver

                from jevdual.native import NativeBridge

                spec = self.scope[name]
                driver = CuaDriver.create()
                bridge = NativeBridge(
                    driver, spec["pid"], spec["window_id"], session=self.session, live_check=True
                )
                try:
                    snapshot = await bridge.observe()
                    await self._document_identity(bridge, snapshot)
                except BaseException:
                    await driver.shutdown()
                    raise
            self.bound[resource] = BoundResource(name, driver, bridge, snapshot)
        return await self.observe(resource)

    async def _document_identity(self, bridge: Any, snapshot: Any) -> None:
        if snapshot.app_name != "TextEdit":
            raise CapabilityError("outside_scope", "Destination must be the selected TextEdit document")
        got = await asyncio.to_thread(bridge.ax.document_path, bridge.pid, bridge.window_id)
        expected = self.scope["destination"]["document"]
        if not got or Path(got).resolve() != Path(expected).resolve():
            raise CapabilityError("lost_identity", "The selected window no longer names the scoped document")

    async def observe(self, resource: str) -> dict[str, Any]:
        from jevdual.ax import AXError

        bound = self.bound.get(resource)
        if bound is None:
            raise CapabilityError("resource_unbound", "Bind this resource in the current process first")
        snapshot = await bound.bridge.observe()
        unavailable: dict[int, str] = {}
        if bound.name == "source":
            if snapshot.menu.url != self.scope["source"]["url"]:
                raise CapabilityError("outside_scope", "The source navigated away from the scoped fixture")
        else:
            await self._document_identity(bound.bridge, snapshot)
            # The driver's preview can omit empty/whitespace-only values. Resolve
            # independently, then qualify the actual insertion route. Absence is
            # never converted to empty, and previews never confer write authority.
            for candidate in snapshot.menu.candidates:
                if "append" in candidate.operations:
                    snapshot.values.pop(candidate.id, None)
                    try:
                        snapshot.values[candidate.id] = await self._value(
                            bound.bridge, snapshot, candidate.id, require_insertable=True
                        )
                    except AXError as exc:
                        unavailable[candidate.id] = exc.reason
        bound.snapshot = snapshot
        return self.observations.project(
            resource, snapshot, writable=bound.name == "destination", unavailable=unavailable
        )

    @staticmethod
    async def _value(
        bridge: Any, snapshot: Any, candidate_id: int, *, require_insertable: bool = False
    ) -> str:
        ax = bridge.ax
        frame = snapshot.frames.get(candidate_id)
        role = snapshot.ax_roles.get(candidate_id, "AXTextArea")

        def read() -> str:
            if require_insertable and frame is None:
                raise ax.AXError("target_geometry_unavailable", "Append requires the observed field frame")
            element = ax.resolve(bridge.pid, bridge.window_id, role, ax.Frame(*frame) if frame else None)
            if require_insertable and not ax.can_insert(element):
                raise ax.AXError("not_writable", "The field does not support exact caret-and-insert input")
            return ax.value(element)

        return await asyncio.to_thread(read)

    def offered(self, target: str) -> Any:
        return self.observations.resolve(target)

    async def validate(
        self, resource: str, observation: str, target: str | None, move: str, args: dict[str, Any]
    ) -> Validated:
        from jevdual.ax import AXError

        if not target or move != "append" or set(args) != {"text"}:
            raise CapabilityError("unsupported_move", "The thin slice only appends to an offered destination")
        text = args["text"]
        if not isinstance(text, str) or not text.strip() or len(text) > 4096:
            raise CapabilityError("invalid_arguments", "Append text must contain 1 to 4096 characters")
        offered = self.offered(target)
        if (offered.resource, offered.observation, offered.move) != (resource, observation, move):
            raise CapabilityError("stale_target", "Target does not match the bound observation and operation")
        bound = self.bound.get(resource)
        if bound is None or bound.name != "destination":
            raise CapabilityError("outside_scope", "Only the scoped native destination is writable")
        fresh = await bound.bridge.observe()
        await self._document_identity(bound.bridge, fresh)
        candidate = fresh.menu.candidate(offered.candidate_id)
        if (
            candidate is None
            or candidate.label != offered.label
            or candidate.role != offered.role
            or "append" not in candidate.operations
            or fresh.frames.get(candidate.id) != offered.frame
        ):
            raise CapabilityError("stale_target", "Destination target changed; observe again. Nothing sent.")
        try:
            before = await self._value(bound.bridge, fresh, candidate.id, require_insertable=True)
        except AXError as exc:
            raise CapabilityError(
                exc.reason, "Destination cannot be qualified for append; observe again. Nothing sent."
            ) from exc
        if before != offered.value:
            raise CapabilityError(
                "precondition_changed", "Destination content changed; observe again. Nothing sent."
            )
        fresh.values[candidate.id] = before
        separator = "" if not before or before.endswith("\n") else "\n"
        return Validated(
            resource,
            observation,
            target,
            move,
            dict(args),
            {
                "bridge": bound.bridge,
                "snapshot": fresh,
                "candidate_id": candidate.id,
                "before": before,
                "expected": before + separator + text,
            },
        )

    async def dispatch(self, validated: Validated) -> DispatchOutcome:
        from jevdual.native import NativeBridgeError

        context = validated.context
        try:
            # Recheck the declared document immediately before invoking input.
            await self._document_identity(context["bridge"], context["snapshot"])
            effect = await context["bridge"].act(
                context["snapshot"], "append", context["candidate_id"], validated.args["text"]
            )
        except NativeBridgeError as exc:
            # These append-route guards are before NativeBridge's send boundary.
            # Do not generalize this allowlist to key/menu routes with preparation effects.
            if exc.reason in {
                "stale",
                "target_missing",
                "unknown_operation",
                "text_required",
                "target_changed",
                "precondition_changed",
                "screen_locked",
            }:
                raise CapabilityError(exc.reason, "Append refused before input; observe again") from exc
            raise
        if not effect.dispatched:
            return DispatchOutcome("not_sent", "not_sent", effect.error_code, {"reason": effect.summary})
        if effect.effect not in ("confirmed", "partial"):
            return DispatchOutcome("ambiguous", "unknown", effect.error_code or effect.summary)
        return DispatchOutcome("sent", effect.effect, evidence={"driver_effect": effect.effect})

    async def readback(self, validated: Validated) -> dict[str, Any]:
        if not self.same_incarnation(validated.resource):
            raise CapabilityError("lost_identity", "Original resource binding is unavailable")
        context = validated.context
        bridge = context["bridge"]
        snapshot = await bridge.observe()
        await self._document_identity(bridge, snapshot)
        original = context["snapshot"].menu.candidate(context["candidate_id"])
        matches = [
            c
            for c in snapshot.menu.candidates
            if original is not None
            # Cua derives the presentation label from the current value. An
            # empty/whitespace field becomes "text area" after insertion. Bind
            # readback to the scoped document, AX role and unique original frame.
            and c.role == original.role
            and snapshot.ax_roles.get(c.id) == context["snapshot"].ax_roles.get(original.id)
            and snapshot.frames.get(c.id) == context["snapshot"].frames.get(original.id)
        ]
        if len(matches) != 1:
            raise CapabilityError("lost_identity", "Readback target changed; the operation remains unknown")
        got = await self._value(bridge, snapshot, matches[0].id)
        expected = context["expected"]
        return {
            "outcome": "applied" if got == expected else "absent" if got == context["before"] else "partial",
            "kind": "exact_field_readback",
            "passed": got == expected,
            "actual": got,
            "expected": expected,
            "persistence": "not_checked",
        }

    async def prepare_recovery(self, validated: Validated) -> dict[str, Any]:
        from .recovery import make_recovery, native_identity

        context = validated.context
        snapshot, cid = context["snapshot"], context["candidate_id"]
        try:
            identity = await asyncio.to_thread(native_identity, self.scope)
            await self._document_identity(context["bridge"], snapshot)
            return make_recovery(
                self.scope,
                identity,
                snapshot.ax_roles[cid],
                snapshot.frames[cid],
                context["before"],
                context["expected"],
            )
        except Exception as exc:  # unsupported durable identity is a pre-send refusal
            raise CapabilityError(
                "recovery_unavailable", "Native restart identity cannot be qualified; nothing sent"
            ) from exc

    async def current_recovery(self, recovery: dict[str, Any]) -> dict[str, Any]:
        """Read current agreement only; this never confers historical execution authority."""
        from .recovery import digest, fingerprint, native_identity, same_native_identity, validate_recovery

        try:
            validate_recovery(recovery)
            if digest(self.scope) != recovery["scope_digest"]:
                return {"agreement": "unverifiable", "reason": "scope_changed"}
            identity = await asyncio.to_thread(native_identity, self.scope)
            if not same_native_identity(identity, recovery["identity"]):
                return {"agreement": "unverifiable", "reason": "identity_changed"}
            from jevdual import ax

            def read() -> str:
                spec = self.scope["destination"]
                if ax.document_path(spec["pid"], spec["window_id"]) != identity["document"]:
                    raise ValueError("document changed")
                field = recovery["field"]
                expected_frame = ax.Frame(*field["frame"])
                element = ax.resolve(spec["pid"], spec["window_id"], field["role"], expected_frame)
                if ax.frame_of(element) != expected_frame:
                    raise ValueError("field frame changed")
                return ax.value(element)

            got = fingerprint(await asyncio.to_thread(read))
            if not same_native_identity(await asyncio.to_thread(native_identity, self.scope), identity):
                return {"agreement": "unverifiable", "reason": "identity_changed"}
            return {
                "agreement": "yes" if got == recovery["expected"] else "no",
                "value": got,
                "disk_identity_changed": identity != recovery["identity"],
                "persistence": "not_checked",
            }
        except Exception as exc:  # noqa: BLE001 - current readback cannot invalidate historical completion
            return {"agreement": "unverifiable", "reason": type(exc).__name__}

    def same_incarnation(self, resource: str) -> bool:
        return resource in self.bound

    async def close(self) -> None:
        resources, self.bound = self.bound, {}
        for bound in resources.values():
            await bound.driver.shutdown()
