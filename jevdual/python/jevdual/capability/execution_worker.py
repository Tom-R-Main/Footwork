"""Execute one admitted native packet independently of MCP, then retain a receipt.

No retry, arbitrary route, browser binding, journal takeover or RPC input. The
parent and recovery caller both consume the same private result file.
"""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import os
import threading
import time
from pathlib import Path

from .backend import ScopedBackend
from .contracts import CapabilityError
from .recovery import (
    WORKER_DEADLINE_S,
    ExecutionStore,
    RecoveryError,
    _private_info,
    binding,
    fingerprint,
    native_identity,
    process_identity,
    read_private,
    same_native_identity,
    validate_packet,
    validate_result,
)
from .runtime import emit_runtime_audit


async def run(packet_path: Path) -> int:
    if packet_path.name != "packet.json" or packet_path.parent.parent.suffix != ".executions":
        raise RecoveryError("unsupported packet path")
    store = ExecutionStore(Path(str(packet_path.parent.parent)[: -len(".executions")]))
    op_id = packet_path.parent.name
    directory = store._check(op_id)
    lock = os.open(directory / "worker.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    backend = None
    watchdog = None
    try:
        _private_info(os.fstat(lock))
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 2  # another effect owner; do not queue/retry
        packet = validate_packet(read_private(packet_path))
        if packet["operation_id"] != op_id:
            raise RecoveryError("packet path does not match operation")
        proof = binding(packet)
        try:
            store.write_record(op_id, "claimed", proof)
        except FileExistsError:
            return 2  # even a dead/finished predecessor never grants replay authority
        store.write_record(
            op_id, "registration", {**proof, **process_identity(os.getpid()), "pgid": os.getpgrp()}
        )
        recovery = packet["recovery"]
        admission = threading.Lock()
        admitted = False

        def deadline() -> None:
            # Hold the admission fence until process exit. No thread can begin
            # input after a pre-input not_sent record has been published.
            with admission:
                expired = {
                    **proof,
                    "disposition": "unknown" if admitted else "not_sent",
                    "phase": "ambiguous" if admitted else "not_sent",
                    "evidence": {"worker_deadline": True, "input_admitted": admitted},
                    "error": "worker_deadline",
                }
                try:
                    store.write_record(op_id, "result", validate_result(packet, expired))
                except (OSError, ValueError):
                    pass  # absent/conflicting receipt never grants execution authority
                finally:
                    os._exit(2)  # owned worker only, kills blocked threads; sent effect may still land

        watchdog = threading.Timer(WORKER_DEADLINE_S, deadline)
        watchdog.daemon = True
        watchdog.start()
        invoked = False
        dispatch_returned = False
        result = {**proof, "disposition": "unknown", "phase": "ambiguous", "evidence": {}, "error": None}
        try:
            backend = ScopedBackend(recovery["scope"])
            if await asyncio.to_thread(native_identity, backend.scope) != recovery["identity"]:
                raise CapabilityError("identity_changed", "Original native identity changed")
            observed = await backend.bind("destination")  # no source/browser binding
            emit_runtime_audit("worker", op_id)
            candidates = []
            for row in observed["elements"]:
                if "append" in row["moves"]:
                    offered = backend.offered(row["target"])
                    snapshot = backend.bound[observed["resource"]].snapshot
                    if (
                        snapshot.ax_roles.get(offered.candidate_id) == recovery["field"]["role"]
                        and list(offered.frame or ()) == recovery["field"]["frame"]
                    ):
                        candidates.append(row)
            if len(candidates) != 1:
                raise CapabilityError("identity_changed", "Original field cannot be resolved uniquely")
            row = candidates[0]
            validated = await backend.validate(
                observed["resource"], observed["observation"], row["target"], "append", packet["args"]
            )
            context = validated.context
            if (
                fingerprint(context["before"]) != recovery["before"]
                or fingerprint(context["expected"]) != recovery["expected"]
            ):
                raise CapabilityError("precondition_changed", "Original exact content changed")
            if await asyncio.to_thread(native_identity, backend.scope) != recovery["identity"]:
                raise CapabilityError("identity_changed", "Original native identity changed before input")
            context["recovery_identity"] = dict(recovery["identity"])
            with admission:
                admitted = True  # no blocking I/O under the watchdog fence
            store.write_record(op_id, "input_started", {**proof, "t": time.time()})
            invoked = True
            outcome = await backend.dispatch(validated)
            dispatch_returned = True
            if outcome.phase == "not_sent":
                result.update(
                    disposition="refused" if outcome.effect_hint == "refused" else "not_sent",
                    phase="not_sent",
                    evidence=outcome.evidence,
                    error=outcome.error,
                )
            else:
                readback = await backend.readback(validated)
                identity = await asyncio.to_thread(native_identity, backend.scope)
                qualified = (
                    outcome.phase == "sent"
                    and outcome.effect_hint == "confirmed"
                    and readback.get("passed") is True
                    and same_native_identity(identity, recovery["identity"])
                    and fingerprint(readback["actual"]) == recovery["expected"]
                )
                result.update(
                    disposition="applied" if qualified else "unknown",
                    phase=outcome.phase,
                    evidence={
                        "driver_effect": outcome.effect_hint,
                        "identity": recovery["identity"],
                        "identity_after": identity,
                        "before": recovery["before"],
                        "after": fingerprint(readback["actual"]),
                        "readback": {
                            "passed": qualified,
                            "kind": "exact_field_readback",
                            "persistence": "not_checked",
                        },
                    },
                    error=outcome.error,
                )
        except CapabilityError as exc:
            # Only fixed native guards use CapabilityError as an affirmative no-send refusal.
            result.update(
                disposition="unknown" if dispatch_returned else "refused",
                phase="ambiguous" if dispatch_returned else "not_sent",
                error=exc.code,
                evidence={"refusal": exc.code},
            )
        except Exception as exc:  # noqa: BLE001 - unknown once input invocation began
            result.update(
                disposition="unknown" if invoked else "not_sent",
                phase="ambiguous" if invoked else "not_sent",
                error=type(exc).__name__,
            )
        store.write_record(op_id, "result", validate_result(packet, result))
        return 0
    finally:
        try:
            if backend is not None:
                await backend.close()
        finally:
            if watchdog is not None:
                watchdog.cancel()
            fcntl.flock(lock, fcntl.LOCK_UN)
            os.close(lock)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    args = parser.parse_args()
    try:
        return asyncio.run(run(args.packet.absolute()))
    except (OSError, ValueError, CapabilityError):
        return 2  # no terminal receipt: the caller must keep uncertainty


if __name__ == "__main__":
    raise SystemExit(main())
