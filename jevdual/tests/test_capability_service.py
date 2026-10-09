"""The capability service's dispatch sequence against a fake backend (capability slice; CS1).

The fake document is a file, so a child process killed mid-dispatch and the test share it.
"""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Any

import pytest
from jevdual.capability.contracts import CapabilityError, DispatchOutcome, Validated
from jevdual.capability.journal import Journal
from jevdual.capability.service import CapabilityService

TASK = "fixture"
RES = "native:1:2"
PREFIX = "Result:\n"


class FileDoc:
    """A TextEdit stand-in: append writes the file, readback classifies its content."""

    def __init__(self, path: Path, *, raise_after_send: bool = False, refuse: bool = False) -> None:
        self.path = path
        self.raise_after_send = raise_after_send
        self.refuse = refuse
        self.dispatches = 0
        self.gate: asyncio.Event | None = None
        if not path.exists():
            path.write_text(PREFIX)

    async def validate(self, resource, observation, target, move, args) -> Validated:
        if self.refuse:
            raise CapabilityError("stale_target", "target expired; observe again")
        return Validated(resource, observation, target, move, args, context=self.path.read_text())

    async def dispatch(self, v: Validated) -> DispatchOutcome:
        self.dispatches += 1
        if self.gate is not None:
            await self.gate.wait()
        self.path.write_text(self.path.read_text() + v.args["text"])
        if self.raise_after_send:
            raise RuntimeError("connection reset after send")
        return DispatchOutcome(phase="sent", effect_hint="sent")

    async def readback(self, v: Validated) -> dict[str, Any]:
        now, before, text = self.path.read_text(), v.context, v.args["text"]
        if now == before + text:
            return {"outcome": "applied", "text": now}
        if now == before:
            return {"outcome": "absent", "text": now}
        if now.startswith(before) and now[len(before) :] == text * (now[len(before) :].count(text) or 1):
            return {"outcome": "duplicate", "text": now}
        return {"outcome": "partial", "text": now}

    def same_incarnation(self, resource: str) -> bool:
        return True


def act(svc: CapabilityService, token: str | None = "tok-1", text: str = "624"):
    return svc.act(
        task=TASK,
        resource=RES,
        observation="obs_1",
        target="t_1",
        move="append",
        args={"text": text},
        client_token=token,
    )


@pytest.fixture
def doc(tmp_path):
    return FileDoc(tmp_path / "doc.txt")


@pytest.fixture
def svc(tmp_path, doc):
    return CapabilityService(Journal(tmp_path / "ops.db"), doc)


async def test_an_append_is_applied_once_and_a_repeated_token_does_not_dispatch_again(svc, doc):
    first = await act(svc)
    assert first["disposition"] == "applied" and not first["repeat"]
    again = await act(svc)
    assert again["repeat"] and again["operation_id"] == first["operation_id"]
    assert doc.dispatches == 1 and doc.path.read_text() == PREFIX + "624"


async def test_a_pre_send_refusal_sends_nothing_and_journals_nothing(tmp_path):
    doc = FileDoc(tmp_path / "doc.txt", refuse=True)
    svc = CapabilityService(Journal(tmp_path / "ops.db"), doc)
    with pytest.raises(CapabilityError) as exc:
        await act(svc)
    assert exc.value.code == "stale_target" and doc.dispatches == 0
    assert (await svc.status(task=TASK))["unresolved"] == []


async def test_a_raise_after_send_is_unknown_blocks_the_resource_and_reconciles_by_readback(tmp_path):
    doc = FileDoc(tmp_path / "doc.txt", raise_after_send=True)
    svc = CapabilityService(Journal(tmp_path / "ops.db"), doc)
    r = await act(svc)
    assert r["disposition"] == "unknown" and r["phase"] == "ambiguous"
    assert r["next"] == {"tool": "status", "operation": r["operation_id"], "reconcile": True}
    with pytest.raises(CapabilityError) as exc:
        await act(svc, token=None)
    assert exc.value.code == "busy" and exc.value.operation_id == r["operation_id"]
    s = await svc.status(task=TASK, operation=r["operation_id"], reconcile=True)
    assert s["disposition"] == "applied" and s["resolved_by"] == "readback"
    assert doc.path.read_text() == PREFIX + "624"


async def test_a_concurrent_append_on_the_same_resource_is_busy(svc, doc):
    doc.gate = asyncio.Event()
    first = asyncio.create_task(act(svc))
    await asyncio.sleep(0.05)
    with pytest.raises(CapabilityError) as exc:
        await act(svc, token="tok-2")
    assert exc.value.code == "busy"
    doc.gate.set()
    assert (await first)["disposition"] == "applied"
    assert doc.dispatches == 1


async def test_after_a_restart_an_unknown_cannot_be_reconciled_without_retained_identity(tmp_path):
    doc = FileDoc(tmp_path / "doc.txt", raise_after_send=True)
    j = Journal(tmp_path / "ops.db")
    r = await act(CapabilityService(j, doc))
    j.close()
    svc2 = CapabilityService(Journal(tmp_path / "ops.db"), FileDoc(tmp_path / "doc.txt"))
    s = await svc2.status(task=TASK, operation=r["operation_id"], reconcile=True)
    assert s["disposition"] == "unknown" and "No retained resource identity" in s["note"]


_CHILD = textwrap.dedent(
    """
    import asyncio, sys
    from pathlib import Path
    sys.path.insert(0, {tests!r})
    from test_capability_service import FileDoc, act
    from jevdual.capability.journal import Journal
    from jevdual.capability.service import CapabilityService

    class Hang(FileDoc):
        async def dispatch(self, v):
            self.path.write_text(self.path.read_text() + v.args["text"])
            await asyncio.sleep(3600)  # delivered; the reply never comes

    async def main():
        svc = CapabilityService(Journal(Path({db!r})), Hang(Path({doc!r})))
        await act(svc)

    asyncio.run(main())
    """
)


def test_cs1_sigkill_mid_dispatch_leaves_unknown_and_no_second_append(tmp_path):
    db, docpath = tmp_path / "ops.db", tmp_path / "doc.txt"
    docpath.write_text(PREFIX)
    code = _CHILD.format(tests=str(Path(__file__).parent), db=str(db), doc=str(docpath))
    child = subprocess.Popen([sys.executable, "-c", code])
    deadline = time.monotonic() + 30
    while docpath.read_text() == PREFIX:
        assert child.poll() is None, "child exited before delivering"
        assert time.monotonic() < deadline, "append never delivered"
        time.sleep(0.02)
    os.kill(child.pid, signal.SIGKILL)
    child.wait()

    doc = FileDoc(docpath)
    svc = CapabilityService(Journal(db), doc)
    pending = asyncio.run(svc.status(task=TASK))["unresolved"]
    assert len(pending) == 1 and pending[0]["disposition"] == "unknown"
    op_id = pending[0]["operation_id"]

    repeat = asyncio.run(act(svc))
    assert repeat["repeat"] and repeat["operation_id"] == op_id and doc.dispatches == 0
    with pytest.raises(CapabilityError) as exc:
        asyncio.run(act(svc, token=None))
    assert exc.value.code == "busy" and exc.value.operation_id == op_id
    assert docpath.read_text() == PREFIX + "624"


async def test_a_tokenless_caller_recovers_a_finished_result_whose_reply_was_lost(svc, doc):
    first = await act(svc, token=None)
    listing = await svc.status(task=TASK)
    assert listing["unresolved"] == []
    assert [r["operation_id"] for r in listing["recent"]] == [first["operation_id"]]
    assert listing["recent"][0]["disposition"] == "applied" and doc.dispatches == 1


async def test_a_cancellation_after_a_send_is_unknown_with_its_phase_and_reconciles_without_redispatch(
    svc, doc
):
    gate = asyncio.Event()
    real_readback = doc.readback

    async def slow_readback(v):
        await gate.wait()
        return await real_readback(v)

    doc.readback = slow_readback
    task = asyncio.create_task(act(svc))
    while doc.dispatches == 0:
        await asyncio.sleep(0.01)
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    pending = (await svc.status(task=TASK))["unresolved"]
    assert len(pending) == 1
    op = pending[0]
    assert op["disposition"] == "unknown" and op["phase"] == "sent", op
    with pytest.raises(CapabilityError) as exc:
        await act(svc, token=None)
    assert exc.value.code == "busy"
    doc.readback = real_readback
    s = await svc.status(task=TASK, operation=op["operation_id"], reconcile=True)
    assert s["disposition"] == "applied" and doc.dispatches == 1
    assert doc.path.read_text() == PREFIX + "624"


async def test_backend_schema_drift_is_recorded_as_unknown_not_trusted(svc, doc):
    async def odd_readback(v):
        return {"outcome": "looks_fine"}

    doc.readback = odd_readback
    r = await act(svc)
    assert r["disposition"] == "unknown"
    assert "unsupported readback outcome" in r["evidence"]["readback"]["schema_error"]
