"""The operation service behind the capability tools: the dispatch sequence for ``act`` and ``status``.

``act`` runs one governed append. Steps, in order:

1. A known client token returns its stored record, even after its observation has expired.
2. Busy check: the resource is mid-dispatch here, or has an unresolved operation in the journal.
3. ``backend.validate`` (pre-send; a refusal here sends nothing and is not journaled).
4. ``journal.begin`` commits the intent as ``dispatching``.
5. ``backend.dispatch``.
6. ``backend.readback``.
7. ``journal.finish``.

The reply is rendered from the journal row, never from the backend's prose.

Only affirmative evidence makes an outcome known. A dispatch that raised, or reported an ambiguous phase,
is ``unknown`` unless the readback shows the intended effect. A sent append that the readback does not
show is also ``unknown``: it may still land. ``status`` never redispatches. It reconciles an unknown by
readback only while this process still holds the original validated request and the backend says the
resource is the same incarnation. After a restart that context is gone, so the operation stays unknown
until someone inspects the document.

``backend.readback`` reports ``{"outcome": ...}`` with one of ``applied``, ``absent``, ``partial``,
``duplicate`` or ``indeterminate``, plus its evidence fields.
"""

from __future__ import annotations

import asyncio
from typing import Any

from jevdual.capability.contracts import Backend, CapabilityError, Disposition, Phase, Validated
from jevdual.capability.journal import Busy, Journal, JournalError, Operation, TokenConflict, request_digest

SCHEMA_VERSION = "1"
PHASES = ("not_sent", "sent", "ambiguous")
READBACK_OUTCOMES = ("applied", "absent", "partial", "duplicate", "indeterminate")


def _from_readback(phase: Phase, readback: dict[str, Any]) -> Disposition:
    outcome = readback.get("outcome")
    if outcome == "applied":
        return "applied"
    if outcome in ("partial", "duplicate"):
        return "partial"
    return "unknown"  # absent after a send may still land; indeterminate is unknown by definition


class CapabilityService:
    def __init__(self, journal: Journal, backend: Backend) -> None:
        self.journal = journal
        self.backend = backend
        self._in_flight: set[str] = set()
        #: validated requests of this process's unknown operations, the only basis for a readback reconcile
        self._validated: dict[str, Validated] = {}

    async def act(
        self,
        *,
        task: str,
        resource: str,
        observation: str,
        target: str | None,
        move: str,
        args: dict[str, Any],
        client_token: str | None = None,
    ) -> dict[str, Any]:
        if client_token is not None:
            prior = self.journal.by_token(task, client_token)
            if prior is not None:
                digest = request_digest(
                    task=task, resource=resource, observation=observation, target=target, move=move, args=args
                )
                if prior.request_digest != digest:
                    raise CapabilityError("token_conflict", str(TokenConflict(prior.id)), prior.id)
                return self._receipt(prior, repeat=True)
        if resource in self._in_flight:
            raise CapabilityError("busy", "an append on this resource is in progress", None)
        blocking = next((op for op in self.journal.unresolved(task) if op.resource == resource), None)
        if blocking is not None:
            raise CapabilityError("busy", str(Busy(blocking.id)), blocking.id)
        self._in_flight.add(resource)
        try:
            validated = await self.backend.validate(resource, observation, target, move, args)
            try:
                op, created = self.journal.begin(
                    task=task,
                    resource=resource,
                    observation=observation,
                    target=target,
                    move=move,
                    args=args,
                    client_token=client_token,
                )
            except (Busy, TokenConflict) as exc:
                raise CapabilityError(exc.code, str(exc), exc.op_id) from None
            if not created:
                return self._receipt(op, repeat=True)
            return self._receipt(await self._dispatch(op, validated), repeat=False)
        finally:
            self._in_flight.discard(resource)

    async def _dispatch(self, op: Operation, validated: Validated) -> Operation:
        try:
            outcome = await self.backend.dispatch(validated)
        except CapabilityError as exc:
            # the backend's affirmation that nothing was sent (contracts.CapabilityError)
            return self.journal.finish(
                op.id, disposition="refused", phase="not_sent", evidence={}, error=f"{exc.code}: {exc}"
            )
        except asyncio.CancelledError:
            self._validated[op.id] = validated
            self.journal.finish(
                op.id,
                disposition="unknown",
                phase="ambiguous",
                evidence={},
                error="cancelled during dispatch",
            )
            raise
        except Exception as exc:  # noqa: BLE001 - an unexpected raise past the intent commit is an unknown outcome
            self._validated[op.id] = validated
            return self.journal.finish(
                op.id,
                disposition="unknown",
                phase="ambiguous",
                evidence={},
                error=f"{type(exc).__name__}: {exc}"[:300],
            )
        if outcome.phase not in PHASES:
            # schema drift from the backend is not evidence of anything; past the intent commit it is unknown
            self._validated[op.id] = validated
            return self.journal.finish(
                op.id,
                disposition="unknown",
                phase="ambiguous",
                evidence={"backend_phase": str(outcome.phase)},
                error=f"unsupported dispatch phase {outcome.phase!r}",
            )
        if outcome.phase == "not_sent":
            disposition: Disposition = "refused" if outcome.effect_hint == "refused" else "not_sent"
            return self.journal.finish(
                op.id,
                disposition=disposition,
                phase="not_sent",
                evidence=outcome.evidence,
                error=outcome.error,
            )
        try:
            readback = await self.backend.readback(validated)
        except asyncio.CancelledError:
            # cancelled after a send: the effect may have landed; keep the attempt reconcilable here
            self._validated[op.id] = validated
            self.journal.finish(
                op.id,
                disposition="unknown",
                phase=outcome.phase,
                evidence={**outcome.evidence, "effect_hint": outcome.effect_hint},
                error="cancelled during readback",
            )
            raise
        except Exception as exc:  # noqa: BLE001 - no readback leaves the sent effect unconfirmed
            readback = {"outcome": "indeterminate", "readback_error": f"{type(exc).__name__}: {exc}"[:300]}
        if not isinstance(readback, dict) or readback.get("outcome") not in READBACK_OUTCOMES:
            got = readback.get("outcome") if isinstance(readback, dict) else type(readback).__name__
            readback = {"outcome": "indeterminate", "schema_error": f"unsupported readback outcome {got!r}"}
        disposition = _from_readback(outcome.phase, readback)
        if disposition == "unknown":
            self._validated[op.id] = validated
        return self.journal.finish(
            op.id,
            disposition=disposition,
            phase=outcome.phase,
            evidence={**outcome.evidence, "readback": readback, "effect_hint": outcome.effect_hint},
            error=outcome.error,
        )

    async def status(
        self,
        *,
        task: str,
        operation: str | None = None,
        client_token: str | None = None,
        reconcile: bool = False,
    ) -> dict[str, Any]:
        if operation is None and client_token is None:
            pending = self.journal.unresolved(task)
            return {
                "schema_version": SCHEMA_VERSION,
                "unresolved": [self._receipt(op, repeat=False) for op in pending],
                "recent": [self._receipt(op, repeat=False) for op in self.journal.recent(task)],
                "summary": f"{len(pending)} unresolved operation(s) in this task"
                if pending
                else "No unresolved operations; recent shows the latest results.",
            }
        op = (
            self.journal.get(operation)
            if operation is not None
            else self.journal.by_token(task, client_token or "")
        )
        if op is None or op.task != task:
            raise CapabilityError("not_found", "no such operation in this task")
        note = None
        if reconcile and op.state == "unknown":
            op, note = await self._reconcile(op)
        return self._receipt(op, repeat=False, note=note)

    async def _reconcile(self, op: Operation) -> tuple[Operation, str]:
        validated = self._validated.get(op.id)
        if validated is None or not self.backend.same_incarnation(op.resource):
            return (
                op,
                "No retained resource identity for this attempt; it stays unknown. Inspect the document.",
            )
        try:
            readback = await self.backend.readback(validated)
        except Exception as exc:  # noqa: BLE001
            return op, f"Readback failed ({type(exc).__name__}); the operation stays unknown."
        if not isinstance(readback, dict) or readback.get("outcome") not in READBACK_OUTCOMES:
            return op, "Readback returned an unsupported outcome; the operation stays unknown."
        disposition = _from_readback(op.phase or "ambiguous", readback)
        if disposition == "unknown":
            return op, f"Readback shows {readback.get('outcome')!r}; the operation stays unknown."
        try:
            resolved = self.journal.resolve(op.id, disposition=disposition, evidence=readback, by="readback")
        except JournalError as exc:
            return op, str(exc)
        self._validated.pop(op.id, None)
        return resolved, f"Resolved by readback as {disposition}."

    # ---- rendering -----------------------------------------------------------------------------

    @staticmethod
    def _receipt(op: Operation, *, repeat: bool, note: str | None = None) -> dict[str, Any]:
        if op.state == "final" and op.disposition == "applied":
            summary = "Appended once; readback confirms the text."
            next_step: dict[str, Any] | None = None
        elif op.state == "final":
            summary = f"Finished as {op.disposition}" + (f": {op.error}" if op.error else ".")
            next_step = None
        else:
            summary = (
                f"Outcome unknown for {op.id}. Do not append again; call status with this operation "
                "(reconcile=true) or have the operator inspect the document."
            )
            next_step = {"tool": "status", "operation": op.id, "reconcile": True}
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "operation_id": op.id,
            "disposition": op.disposition or "unknown",
            "state": op.state,
            "phase": op.phase,
            "summary": summary,
            "repeat": repeat,
            "evidence": op.evidence,
        }
        if op.client_token is not None:
            result["client_token"] = op.client_token
        if op.error:
            result["error"] = op.error
        if op.resolved_by:
            result["resolved_by"] = op.resolved_by
        if next_step is not None:
            result["next"] = next_step
        if note:
            result["note"] = note
        return result
