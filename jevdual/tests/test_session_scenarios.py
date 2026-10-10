"""The operator session end to end: real ``footwork`` commands against a simulated Mac.

On 2026-09-25 three bugs were found by driving and none by the suite (docs/plans/legible-harness.md,
"Driving it myself"): ``s1 --act`` crashed on a Decision attribute, an installed-but-not-running app
surfaced as a window-discovery error, and a click went to whatever held the chosen id after the window
changed. Each is a scenario here, run through ``jevdual.cli.main`` with only the Driver, the TypeSafe
client, System 1's policy and the verifier's models replaced. A bug found by driving becomes a
scenario first (the typesafe-computer-use rule: fix the loop, not the scenario).
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import ClassVar

import pytest

cd = pytest.importorskip("cua_driver")

from jevdual import cli
from jevdual.policy import Decision

from tests.fixtures.native_world import World


@pytest.fixture
def text_capability(tmp_path, monkeypatch):
    """Public MCP calls over the actual service/backend/native append route."""
    from jevdual.capability.backend import ScopedBackend
    from jevdual.capability.journal import Journal
    from jevdual.capability.mcp_server import ToolFacade
    from jevdual.capability.service import CapabilityService

    from tests.fixtures.native_world import TextWorld

    world = TextWorld(tmp_path / "invoice.txt")
    world.install(monkeypatch)
    backend = ScopedBackend(
        {
            "task": "text-repair-scenario",
            "source": {"pid": 1, "window_id": 2, "url": "http://127.0.0.1:8000/"},
            "destination": {
                "pid": world.pid,
                "window_id": world.window_id,
                "document": str(world.document),
            },
        }
    )
    journal = Journal(tmp_path / "operations.sqlite")
    yield world, ToolFacade(backend, CapabilityService(journal, backend))
    journal.close()


def _append_target(observation):
    return next(row for row in observation["elements"] if "append" in row["moves"])


async def test_capability_no_newline_explains_separator_then_appends_once(text_capability):
    world, tools = text_capability
    observation = await tools.call("bind", {"name": "destination"})
    row = _append_target(observation)
    assert row["value"] == "Invoice report"
    assert row["append_separator"] == "\n"
    result = await tools.call("act", {"target": row["target"], "text": "17.25 USD"})
    assert result["disposition"] == "applied"
    assert world.content == "Invoice report\n17.25 USD"
    assert [v for k, v in world.writes if k == "AXSelectedText"] == ["\n17.25 USD"]


@pytest.mark.parametrize(
    ("prefix", "separator"),
    [("Invoice report\n", ""), ("Invoice report\n\tkept  \n\n", ""), ("  \t", "\n")],
)
async def test_capability_keeps_prefix_and_literal_payload_whitespace(text_capability, prefix, separator):
    world, tools = text_capability
    world.content = prefix
    row = _append_target(await tools.call("bind", {"name": "destination"}))
    assert row["value"] == prefix and row["append_separator"] == separator
    payload = "\n  17.25 USD\t  \n"
    result = await tools.call("act", {"target": row["target"], "text": payload})
    assert result["disposition"] == "applied" and world.content == prefix + separator + payload
    assert [v for k, v in world.writes if k == "AXSelectedText"] == [separator + payload]


async def test_capability_proven_empty_is_applied_when_driver_label_changes(text_capability):
    world, tools = text_capability
    world.content = ""
    observation = await tools.call("bind", {"name": "destination"})
    row = _append_target(observation)
    assert row["label"] == "First Text View" and row["value"] == ""
    assert row["append_separator"] == ""
    result = await tools.call("act", {"target": row["target"], "text": "17.25 USD"})
    assert result["disposition"] == "applied" and world.content == "17.25 USD"
    fresh = await tools.call("observe", {"resource": observation["resource"]})
    assert _append_target(fresh)["label"] == "text area"
    status = await tools.call("status", {"operation": result["operation_id"]})
    assert status["disposition"] == "applied"
    assert len([v for k, v in world.writes if k == "AXSelectedText"]) == 1


@pytest.mark.parametrize("count", [None, 7])
async def test_capability_absent_unreadable_value_is_not_assumed_empty(text_capability, count):
    world, tools = text_capability
    world.content, world.readable, world.character_count = "", False, count
    observation = await tools.call("bind", {"name": "destination"})
    assert all("target" not in row and row["moves"] == [] for row in observation["elements"])
    assert world.writes == []


@pytest.mark.parametrize("guard", ["noninsertable", "secure", "ambiguous", "setter_error", "frameless"])
async def test_capability_unqualified_field_never_offers_append(text_capability, guard):
    world, tools = text_capability
    if guard == "noninsertable":
        world.insertable = False
    elif guard == "setter_error":
        world.setter_error = -25205
    elif guard == "frameless":
        world.frame = None
    else:
        setattr(world, guard, True)
    observation = await tools.call("bind", {"name": "destination"})
    assert all("target" not in row and row["moves"] == [] for row in observation["elements"])
    assert world.writes == []


@pytest.mark.parametrize("change", ["content", "document"])
async def test_capability_stale_field_or_document_refuses_before_input(text_capability, change):
    from jevdual.capability.contracts import CapabilityError

    world, tools = text_capability
    row = _append_target(await tools.call("bind", {"name": "destination"}))
    if change == "content":
        world.content += "\nExternal edit"
    else:
        world.document = world.document.with_name("different.txt")
    with pytest.raises(CapabilityError):
        await tools.call("act", {"target": row["target"], "text": "17.25 USD"})
    assert world.writes == []


async def test_capability_same_token_collects_receipt_after_target_expires(text_capability):
    world, tools = text_capability
    observed = await tools.call("bind", {"name": "destination"})
    row = _append_target(observed)
    arguments = {"target": row["target"], "text": "17.25 USD", "client_token": "one-append"}
    first = await tools.call("act", arguments)
    await tools.call("observe", {"resource": observed["resource"]})
    repeated = await tools.call("act", arguments)
    status = await tools.call("status", {"client_token": "one-append"})
    assert first["disposition"] == repeated["disposition"] == status["disposition"] == "applied"
    assert repeated["repeat"] and repeated["operation_id"] == first["operation_id"]
    assert world.content == "Invoice report\n17.25 USD"
    assert len([v for k, v in world.writes if k == "AXSelectedText"]) == 1


async def test_capability_lost_setter_permission_refuses_before_input(text_capability):
    from jevdual.capability.contracts import CapabilityError

    world, tools = text_capability
    row = _append_target(await tools.call("bind", {"name": "destination"}))
    world.insertable = False
    with pytest.raises(CapabilityError) as caught:
        await tools.call("act", {"target": row["target"], "text": "17.25 USD"})
    assert caught.value.code == "not_writable" and world.writes == []
    assert world.content == "Invoice report"


async def test_capability_restart_without_durable_execution_evidence_stays_unknown(text_capability, monkeypatch):
    """Baseline: a completed append whose final journal write dies loses its local evidence."""
    from jevdual.capability.backend import ScopedBackend
    from jevdual.capability.contracts import CapabilityError
    from jevdual.capability.journal import Journal
    from jevdual.capability.mcp_server import ToolFacade
    from jevdual.capability.service import CapabilityService

    world, tools = text_capability
    observed = await tools.call("bind", {"name": "destination"})
    row = _append_target(observed)
    journal = tools.service.journal
    original_finish = journal.finish

    def fail_final_write(*args, **kwargs):
        raise RuntimeError("simulated process loss at final journal write")

    monkeypatch.setattr(journal, "finish", fail_final_write)
    with pytest.raises(RuntimeError, match="simulated process loss"):
        await tools.call("act", {"target": row["target"], "text": "17.25 USD", "client_token": "lost-reply"})
    monkeypatch.setattr(journal, "finish", original_finish)
    assert world.content == "Invoice report\n17.25 USD"
    assert len([v for k, v in world.writes if k == "AXSelectedText"]) == 1
    journal.close()
    # This fixture normally owns close; the simulated restart already released it.
    monkeypatch.setattr(journal, "close", lambda: None)
    restarted_backend = ScopedBackend(tools.backend.scope)
    restarted_journal = Journal(journal.path)
    restarted = ToolFacade(restarted_backend, CapabilityService(restarted_journal, restarted_backend))
    try:
        current = await restarted.call("bind", {"name": "destination"})
        assert _append_target(current)["value"] == world.content
        status = await restarted.call("status", {"client_token": "lost-reply", "reconcile": True})
        assert status["disposition"] == "unknown"
        assert "No retained resource identity" in status["note"]
        with pytest.raises(CapabilityError) as caught:
            await restarted.call("act", {"target": _append_target(current)["target"], "text": "17.25 USD"})
        assert caught.value.code == "busy"
        assert len([v for k, v in world.writes if k == "AXSelectedText"]) == 1
    finally:
        await restarted_backend.close()
        restarted_journal.close()


@pytest.fixture
def durable_text_capability(text_capability, monkeypatch):
    """Only launch and OS identity are simulated; the fixed worker runs unchanged."""
    import asyncio

    from jevdual.capability import execution_worker, recovery

    world, tools = text_capability
    tools.backend.durable = True
    identity = {"boot": "test-boot", "pid": world.pid, "start": "0x1.0p0", "document": str(world.document),
                "device": 1, "inode": 2}
    monkeypatch.setattr(recovery, "native_identity", lambda scope: dict(identity))
    monkeypatch.setattr(execution_worker, "native_identity", lambda scope: dict(identity))
    launches = []

    class Process:
        def __init__(self, task):
            self.task = task

        def poll(self):
            return self.task.result() if self.task.done() else None

    def launch(op):
        launches.append(op.id)
        packet = tools.service.executor.directory(op.id) / "packet.json"
        return Process(asyncio.create_task(execution_worker.run(packet)))

    monkeypatch.setattr(tools.service.executor, "_launch", launch)
    return world, tools, identity, launches


async def _reopened_capability(tools, monkeypatch):
    from jevdual.capability.backend import ScopedBackend
    from jevdual.capability.journal import Journal
    from jevdual.capability.mcp_server import ToolFacade
    from jevdual.capability.service import CapabilityService

    journal = tools.service.journal
    journal.close()
    monkeypatch.setattr(journal, "close", lambda: None)
    fresh_journal = Journal(journal.path)
    backend = ScopedBackend(tools.backend.scope, durable=True)
    return ToolFacade(backend, CapabilityService(fresh_journal, backend))


@pytest.mark.parametrize("change", ["none", "content", "document", "process", "role", "frame", "ambiguous"])
async def test_capability_durable_receipt_recovers_historical_applied_after_restart(durable_text_capability, monkeypatch, change):
    world, tools, identity, launches = durable_text_capability
    row = _append_target(await tools.call("bind", {"name": "destination"}))
    arguments = {"target": row["target"], "text": "17.25 USD", "client_token": "durable-lost-reply"}
    journal = tools.service.journal
    original_finish = journal.finish

    def final_commit_loss(*args, **kwargs):
        raise RuntimeError("simulated loss after durable worker receipt")

    monkeypatch.setattr(journal, "finish", final_commit_loss)
    with pytest.raises(RuntimeError, match="after durable worker receipt"):
        await tools.call("act", arguments)
    monkeypatch.setattr(journal, "finish", original_finish)
    assert world.content == "Invoice report\n17.25 USD" and len(launches) == 1
    if change == "content":
        world.content += "\nLater user edit"
    elif change == "document":
        world.document = world.document.with_name("replacement.txt")
    elif change == "process":
        identity["start"] = "0x2.0p0"
    elif change == "role":
        world.secure = True
    elif change == "frame":
        world.frame = (110, 20, 400, 300)
    elif change == "ambiguous":
        world.ambiguous = True
    restarted = await _reopened_capability(tools, monkeypatch)
    try:
        status = await restarted.call("status", {"client_token": arguments["client_token"], "reconcile": True})
        assert status["disposition"] == "applied" and status["resolved_by"] == "execution"
        assert status["evidence"]["readback"]["passed"] is True
        assert status["evidence"]["readback"]["historical"] is True
        retained = restarted.service.journal.get(status["operation_id"])
        assert retained.evidence["readback"]["passed"] is True
        expected_agreement = "yes" if change == "none" else "no" if change == "content" else "unverifiable"
        assert status["current"]["agreement"] == expected_agreement
        repeated = await restarted.call("act", arguments)
        assert repeated["repeat"] and repeated["operation_id"] == status["operation_id"]
        assert len(launches) == 1 and len([v for k, v in world.writes if k == "AXSelectedText"]) == 1
    finally:
        await restarted.backend.close()
        restarted.service.journal.close()


async def test_capability_started_no_receipt_rejects_matching_external_text(durable_text_capability, monkeypatch):
    world, tools, _, launches = durable_text_capability
    row = _append_target(await tools.call("bind", {"name": "destination"}))

    class DeadProcess:
        def poll(self):
            return 1

    def launch_without_receipt(op):
        launches.append(op.id)
        return DeadProcess()

    monkeypatch.setattr(tools.service.executor, "_launch", launch_without_receipt)
    arguments = {"target": row["target"], "text": "17.25 USD", "client_token": "no-receipt"}
    first = await tools.call("act", arguments)
    assert first["disposition"] == "unknown" and world.writes == []
    world.content = "Invoice report\n17.25 USD"  # a different actor creates the exact expected value
    restarted = await _reopened_capability(tools, monkeypatch)
    try:
        status = await restarted.call("status", {"client_token": "no-receipt", "reconcile": True})
        assert status["disposition"] == "unknown" and status["current"]["agreement"] == "yes"
        assert (await restarted.call("act", arguments))["repeat"]
        current = await restarted.call("bind", {"name": "destination"})
        from jevdual.capability.contracts import CapabilityError

        with pytest.raises(CapabilityError) as caught:
            await restarted.call("act", {"target": _append_target(current)["target"], "text": "17.25 USD"})
        assert caught.value.code == "busy" and len(launches) == 1 and world.writes == []
    finally:
        await restarted.backend.close()
        restarted.service.journal.close()


@pytest.mark.parametrize("boundary", ["prepare", "start"])
async def test_capability_durable_storage_admission_failure_never_launches(durable_text_capability, monkeypatch, boundary):
    world, tools, _, launches = durable_text_capability
    row = _append_target(await tools.call("bind", {"name": "destination"}))

    def fail_admission(*args, **kwargs):
        raise OSError("simulated durable storage failure")

    owner = tools.service.executor if boundary == "prepare" else tools.service.journal
    monkeypatch.setattr(owner, boundary, fail_admission)
    result = await tools.call("act", {"target": row["target"], "text": "17.25 USD"})
    assert result["disposition"] == "not_sent" and result["phase"] == "not_sent"
    assert launches == [] and world.writes == [] and world.content == "Invoice report"


async def test_capability_second_worker_claim_cannot_replay_packet(durable_text_capability):
    from jevdual.capability.execution_worker import run

    world, tools, _, launches = durable_text_capability
    row = _append_target(await tools.call("bind", {"name": "destination"}))
    result = await tools.call("act", {"target": row["target"], "text": "17.25 USD"})
    assert result["disposition"] == "applied"
    assert result["evidence"]["readback"]["passed"] is True
    assert tools.service.journal.get(result["operation_id"]).evidence["readback"]["passed"] is True
    packet_path = tools.service.executor.directory(result["operation_id"]) / "packet.json"
    assert await run(packet_path) == 2
    assert len(launches) == 1 and len([v for k, v in world.writes if k == "AXSelectedText"]) == 1


async def test_capability_worker_readback_refusal_after_input_remains_unknown(durable_text_capability, monkeypatch):
    from jevdual.capability.backend import ScopedBackend
    from jevdual.capability.contracts import CapabilityError

    world, tools, _, launches = durable_text_capability
    original_readback = ScopedBackend.readback

    async def lose_readback(self, validated):
        await original_readback(self, validated)
        raise CapabilityError("lost_identity", "simulated post-input readback loss")

    monkeypatch.setattr(ScopedBackend, "readback", lose_readback)
    row = _append_target(await tools.call("bind", {"name": "destination"}))
    result = await tools.call("act", {"target": row["target"], "text": "17.25 USD"})
    assert result["disposition"] == "unknown" and result["phase"] == "ambiguous"
    assert world.content == "Invoice report\n17.25 USD"
    status = await tools.call("status", {"operation": result["operation_id"], "reconcile": True})
    assert status["disposition"] == "unknown" and status["current"]["agreement"] == "yes"
    assert len(launches) == 1 and len([v for k, v in world.writes if k == "AXSelectedText"]) == 1


async def test_capability_input_marker_storage_failure_proves_no_input(durable_text_capability, monkeypatch):
    from jevdual.capability.recovery import ExecutionStore

    world, tools, _, launches = durable_text_capability
    original_write = ExecutionStore.write_record

    def fail_input_marker(store, op_id, name, value):
        if name == "input_started":
            raise OSError("simulated input-marker persistence failure")
        return original_write(store, op_id, name, value)

    monkeypatch.setattr(ExecutionStore, "write_record", fail_input_marker)
    row = _append_target(await tools.call("bind", {"name": "destination"}))
    result = await tools.call("act", {"target": row["target"], "text": "17.25 USD"})
    assert result["disposition"] == "not_sent" and result["phase"] == "not_sent"
    assert world.content == "Invoice report" and world.writes == [] and len(launches) == 1


async def test_capability_cancelled_parent_does_not_cancel_effect_owner(durable_text_capability, monkeypatch):
    import asyncio

    from jevdual.capability.backend import ScopedBackend

    world, tools, _, launches = durable_text_capability
    original_dispatch = ScopedBackend.dispatch
    entered, release = asyncio.Event(), asyncio.Event()

    async def delayed_dispatch(self, validated):
        entered.set()
        await release.wait()
        return await original_dispatch(self, validated)

    monkeypatch.setattr(ScopedBackend, "dispatch", delayed_dispatch)
    row = _append_target(await tools.call("bind", {"name": "destination"}))
    arguments = {"target": row["target"], "text": "17.25 USD", "client_token": "delayed-owner"}
    pending = asyncio.create_task(tools.call("act", arguments))
    await asyncio.wait_for(entered.wait(), 3)
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    retained = tools.service.journal.by_token(tools.backend.task, "delayed-owner")
    assert tools.service.executor.custody(retained) == "active"
    before = await tools.call("status", {"client_token": "delayed-owner", "reconcile": True})
    assert before["disposition"] == "unknown" and before["current"]["agreement"] == "no"
    assert (await tools.call("act", arguments))["repeat"] and len(launches) == 1
    release.set()
    deadline = asyncio.get_running_loop().time() + 3
    while tools.service.executor.read_result(retained) is None:
        assert asyncio.get_running_loop().time() < deadline
        await asyncio.sleep(0.01)
    after = await tools.call("status", {"client_token": "delayed-owner", "reconcile": True})
    assert after["disposition"] == "applied" and after["current"]["agreement"] == "yes"
    assert len(launches) == 1 and len([v for k, v in world.writes if k == "AXSelectedText"]) == 1


@pytest.mark.parametrize("change", ["role", "frame", "ambiguous"])
async def test_capability_readback_identity_loss_stays_unknown_without_retry(text_capability, change):
    from jevdual.capability.contracts import CapabilityError

    world, tools = text_capability
    row = _append_target(await tools.call("bind", {"name": "destination"}))
    world.after_insert = change
    arguments = {"target": row["target"], "text": "17.25 USD", "client_token": "uncertain-append"}
    result = await tools.call("act", arguments)
    assert result["disposition"] == "unknown" and world.content == "Invoice report\n17.25 USD"
    status = await tools.call("status", {"operation": result["operation_id"], "reconcile": True})
    assert status["disposition"] == "unknown"
    repeated = await tools.call("act", arguments)
    assert repeated["repeat"] and repeated["operation_id"] == result["operation_id"]
    with pytest.raises(CapabilityError) as caught:
        await tools.call("act", {"target": row["target"], "text": "another append"})
    assert caught.value.code == "busy"
    assert len([v for k, v in world.writes if k == "AXSelectedText"]) == 1


class _Client:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None


class _Verifier:
    """Accepts when the last word of every requirement is on the window; the models are not under test."""

    def __init__(self, client):
        pass

    #: every judgment asked for, and the probability a scenario wants back (secondary audit 2026-09-27)
    judged: ClassVar[list[list[str]]] = []
    p: ClassVar[float] = 0.05

    async def judge_destructive(self, task, targets, *, url, title):
        _Verifier.judged.append([t["label"] for t in targets])
        return [_Verifier.p for _ in targets]

    async def verify(self, task, requirements, menu, answer, *, answer_expected, trajectory, **_):
        unmet = {r: (0.05 if r.split()[-1] in menu.page_text else 0.95) for r in requirements}
        ok = all(p < 0.5 for p in unmet.values())
        return SimpleNamespace(
            band="accept" if ok else "reject",
            complete=0.95 if ok else 0.1,
            reason="all requirements on the window" if ok else "a requirement is not on the window",
            unmet=unmet,
            unmet_effective=unmet,
            unsupported_claims=[],
        )


class _Policy:
    """System 1 proposes the next label from a script, by the id it holds on the menu it was shown."""

    script: ClassVar[list[str]] = []

    def __init__(self, client):
        pass

    async def decide(self, menu, ctx):
        label = _Policy.script.pop(0)
        target = next(c.id for c in menu.candidates if c.label == label)
        return Decision(
            operation="click",
            operation_confidence=0.97,
            operation_probabilities={"click": 0.97},
            target=target,
            target_confidence=0.96,
            target_probabilities={target: 0.96},
            alternates=(),
            nouls={},
            model="fake",
            request_tokens=None,
            latency_ms=1.0,
        )


@pytest.fixture
def world(monkeypatch):
    w = World()
    import jevdual.keys
    import jevdual.policy
    import jevdual.verify
    import typesafe_sdk

    monkeypatch.setattr(cd.CuaDriver, "create", staticmethod(w.create))
    monkeypatch.setattr(typesafe_sdk, "AsyncTypeSafeClient", _Client)
    monkeypatch.setattr(jevdual.keys, "load_keys", lambda *a, **k: {"TYPESAFE_API_KEY": "test"})
    monkeypatch.setattr(jevdual.verify, "Verifier", _Verifier)
    monkeypatch.setattr(jevdual.policy, "JevPolicy", _Policy)
    return w


@pytest.fixture
def fw(tmp_path, capsys):
    """Run one footwork command in the test session; returns (exit code, stdout, stderr)."""
    session = str(tmp_path / "session")

    def run(*argv: str):
        extra = ["--settle", "0"] if argv[0] in ("do", "s1") else []
        code = cli.main([*argv, "--session", session, *extra])
        out = capsys.readouterr()
        return code, out.out, out.err

    run.session = tmp_path / "session"  # type: ignore[attr-defined]
    return run


def _state(fw) -> dict:
    return json.loads((fw.session / "session.json").read_text())


def _id(out: str, label: str) -> int:
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("[") and f"'{label}'" in s:
            return int(s[1 : s.index("]")])
    raise AssertionError(f"{label!r} not in the observation")


def test_a_calculator_job_from_start_to_a_verified_done(world, fw):
    code, out, _ = fw(
        "start", "Compute 48 times 13", "--app", "Calculator", "--require", "The display shows 624"
    )
    assert code == 0 and "bound Calculator" in out
    for label in ("All Clear", "4", "8", "Multiply", "1", "3", "Equals"):
        # a number is an id, so digits are chosen by the id the last observation printed for them
        target = str(_id(out, label)) if label.isdigit() else label
        code, out, err = fw("do", "click", target, "--no-judge")
        assert code == 0, err
    assert world.display() == "624"
    code, out, _ = fw("done", "624")
    assert code == 0 and "accepted" in out
    st = _state(fw)
    assert st["status"] == "done"
    # every press after the first changed the window, so each earlier action has a confirmed receipt
    receipts = [m for m in st["memory"] if "->" in m and "click(" in m]
    assert len(receipts) == 7 and all(m.endswith("-> confirmed") for m in receipts[1:])


def test_s1_act_dispatches_the_proposal(world, fw):
    # 2026-09-25: `s1 --act` read decision.text, which Decision does not have, and crashed
    fw("start", "Compute 7", "--app", "Calculator")
    _Policy.script = ["7"]
    code, out, err = fw("s1", "--act")
    assert code == 0, err
    assert "System 1 proposes: click" in out and world.presses == ["7"]


def test_an_installed_app_that_is_not_running_is_named_not_a_window_error(world, fw):
    world.apps = [("Calculator", 0, False)]
    code, _, err = fw("start", "Compute 7", "--app", "Calculator")
    assert code == 2 and "installed but not running" in err


def test_a_changed_window_refuses_the_chosen_id_and_nothing_is_pressed(world, fw):
    # 2026-09-25: an overlay opened between look and do; the click went to what now held id 37
    _, out, _ = fw("start", "Compute 7", "--app", "Calculator")
    seven = _id(out, "7")
    world.relabels[seven] = "sin"  # the person switched the calculator's mode
    code, out, err = fw("do", "click", str(seven), "--no-judge")
    assert code == 4 and "it was '7'" in err and "Nothing dispatched" in err
    assert world.presses == []


def test_delete_pauses_until_authorized_and_a_press_that_changes_nothing_says_so(world, fw):
    fw("start", "Clear the last digit", "--app", "Calculator")
    code, out, _ = fw("do", "click", "Delete", "--no-judge")
    assert code == 3 and "paused before dispatch" in out and world.presses == []
    code, out, _ = fw("do", "click", "Delete", "--no-judge", "--authorize", "Delete")
    assert code == 0 and world.presses == ["Delete"]
    # the display was 0 and is still 0: the Driver confirmed delivery, the window did not change.
    # `do` reobserves and prints the receipt itself; a later `look` has no pending action left
    assert "suspected no-op" in out and "reported the press as delivered" in out
    assert _state(fw)["memory"][-1].endswith("click(Delete) -> suspected_noop")
    assert "receipt:" not in fw("look")[1]


def test_background_only_sends_no_hotkey(world, fw):
    fw("start", "Save", "--app", "Calculator")
    # a chord may press any button on screen, and Calculator's backspace is labelled "Delete"
    code, out, _ = fw("do", "hotkey", "cmd", "s")
    assert code == 3 and "on button 'Delete' reachable by" in out
    code, out, _ = fw("do", "hotkey", "cmd", "s", "--authorize", "Delete")
    assert code == 0 and "not sent" in out and "requires_foreground" in out
    assert world.tool_calls == [] and world.presses == []


def test_a_driver_refusal_is_reported_and_the_receipt_follows_the_window(world, fw):
    fw("start", "Compute 8", "--app", "Calculator")
    _, out, _ = fw("look")
    world.refuse.add("8")
    code, out, _ = fw("do", "click", str(_id(out, "8")), "--no-judge")
    assert code == 0 and "driver says refused" in out and world.presses == []
    assert "receipt: Receipt for click(8): refused" in out
    assert _state(fw)["memory"] == ["step 1: click(8) -> refused"]


# ---- package G: a carried value, its provenance and the exact saved-file oracle ----


def _compute_624(fw) -> None:
    code, out, _ = fw("start", "Compute 48 times 13", "--app", "Calculator")
    for label in ("All Clear", "4", "8", "Multiply", "1", "3", "Equals"):
        target = str(_id(out, label)) if label.isdigit() else label
        code, out, err = fw("do", "click", target, "--no-judge")
        assert code == 0, err


def test_a_read_value_carries_where_it_came_from_and_the_file_oracle_is_exact(world, fw, tmp_path):
    _compute_624(fw)
    code, out, err = fw("read", "--match", r"(?m)^\s*‎?(\d[\d,]*)\s*$", "--as", "result")
    assert code == 0, err
    assert "@result = '624'" in out and "native Calculator" in out and "step 7" in out
    saved = tmp_path / "note.txt"
    saved.write_text("Result\n624\n")
    code, out, _ = fw("check-file", str(saved), "@result")
    assert code == 0 and out.startswith("confirmed: line 2 of") and "@result = '624'" in out
    # a line that only contains the value is not the value: the oracle is exact
    saved.write_text("Result: 624\n")
    code, out, _ = fw("check-file", str(saved), "@result")
    assert code == 6 and "contains the text but is not equal to it" in out
    st = _state(fw)
    assert any("check-file" in m and m.endswith("-> failed") for m in st["memory"])


def test_an_unknown_carry_and_a_missing_match_dispatch_nothing(world, fw, tmp_path):
    _compute_624(fw)
    presses = len(world.presses)
    code, _, err = fw("read", "--match", "no such text", "--as", "x")
    assert code == 4 and "does not occur" in err
    code, _, err = fw("do", "append", "Equals", "@missing")
    assert code == 4 and "@missing was not read in session" in err
    assert len(world.presses) == presses
    code, _, err = fw("check-file", str(tmp_path / "absent.txt"), "@missing")
    assert code == 4


# ---- secondary audit (2026-09-27): real-command gaps ----


def test_a_key_and_a_return_go_to_the_judge_through_the_real_command(world, fw):
    """authorize.py judged key and Enter since package B, but the CLI built the judge only for click,
    menu, hotkey and navigate, so a Return reached no judgment through `footwork do`."""
    _Verifier.judged.clear()
    _Verifier.p = 0.95
    try:
        # "Delete" granted, so the keyword rule stands aside and the judgment itself is what pauses
        fw("start", "Compute", "--app", "Calculator", "--authorize", "Delete")
        code, out, err = fw("do", "key", "Return")
        assert _Verifier.judged, f"the judge was never asked: {code} {out[:300]} {err[:300]}"
        assert code == 3 and "paused before dispatch" in out and "judgment p=0.95" in out
        assert world.presses == []
    finally:
        _Verifier.p = 0.05


@pytest.mark.parametrize("words", [
    ("click", "All Clear"), ("key", "Tab"), ("hotkey", "cmd", "s"),
    ("menu", "File > Save"), ("enter", "All Clear"), ("navigate", "http://127.0.0.1/fixture"),
])
def test_missing_required_judge_pauses_operator_routes(world, fw, monkeypatch, words):
    import jevdual.keys
    from jevdual.native import NativeBridge

    dispatch_calls = []

    def spy(method):
        original = getattr(NativeBridge, method, None)

        async def recorded(*args, **kwargs):
            dispatch_calls.append(method)
            if original is None:
                raise RuntimeError(f"unexpected {method} dispatch on native fixture")
            return await original(*args, **kwargs)

        return recorded

    for method in ("act", "key", "hotkey", "menu", "navigate"):
        monkeypatch.setattr(NativeBridge, method, spy(method), raising=False)

    fw("start", "Compute", "--app", "Calculator")
    monkeypatch.setattr(jevdual.keys, "load_keys", lambda *a, **k: {})
    code, out, err = fw("do", *words)
    assert code == 3 and "judgment_unavailable" in out, (code, out, err)
    assert dispatch_calls == []
    assert world.presses == []
    assert _state(fw).get("pending") is None


def test_explicit_no_judge_preserves_keyword_only_mode(world, fw, monkeypatch):
    import jevdual.keys

    fw("start", "Compute", "--app", "Calculator")
    monkeypatch.setattr(jevdual.keys, "load_keys", lambda *a, **k: {})
    code, out, err = fw("do", "click", "All Clear", "--no-judge")
    assert code == 0, (out, err)
    assert world.presses == ["All Clear"]
    code, out, _ = fw("do", "click", "Delete", "--no-judge")
    assert code == 3 and "paused before dispatch" in out
    assert world.presses == ["All Clear"]


def test_missing_judge_is_not_cleared_by_an_exact_grant(world, fw, monkeypatch):
    import jevdual.keys

    fw("start", "Compute", "--app", "Calculator")
    fw("grant", "click", "All Clear")
    monkeypatch.setattr(jevdual.keys, "load_keys", lambda *a, **k: {})
    code, out, err = fw("do", "click", "All Clear")
    assert code == 3 and "judgment_unavailable" in out, (code, out, err)
    assert world.presses == []


def test_observations_remain_available_without_judgment_credentials(world, fw, monkeypatch):
    import jevdual.keys

    fw("start", "Compute", "--app", "Calculator")
    monkeypatch.setattr(jevdual.keys, "load_keys", lambda *a, **k: {})
    code, out, err = fw("look")
    assert code == 0 and "All Clear" in out, (out, err)
    assert world.presses == []


def test_a_raised_dispatch_error_ends_in_a_named_refusal_not_a_crash(world, fw, monkeypatch):
    """cmd_do caught a bridge exception, then read ``eff.readback`` with ``eff`` unassigned."""
    from jevdual.native import NativeBridge, NativeBridgeError

    async def boom(self, *a, **k):
        raise NativeBridgeError("element_missing", "the element went away")

    fw("start", "Compute", "--app", "Calculator")
    monkeypatch.setattr(NativeBridge, "act", boom)
    code, out, err = fw("do", "click", "All Clear", "--no-judge")
    assert code == 0, err
    assert "not dispatched" in out and "element_missing" in out
    assert "refused (not applied: element_missing" in out  # the receipt, printed with the fresh observation


def test_the_workflow_oracle_through_the_real_commands(world, fw, tmp_path):
    _compute_624(fw)
    code, _, err = fw("read", "--match", r"(?m)^\s*‎?(\d[\d,]*)\s*$", "--as", "result")
    assert code == 0, err
    doc = tmp_path / "doc.txt"
    doc.write_text("Result:\n")
    code, out, _ = fw("snapshot-file", str(doc))
    assert code == 0 and "8 characters" in out
    doc.write_text("Result:\n624\n624\n")
    code, out, _ = fw("check-file", str(doc), "@result", "--appended")
    assert code == 6 and "inserted 2 times" in out
    doc.write_text("Result:\n624")
    code, out, _ = fw("check-file", str(doc), "@result", "--appended")
    assert code == 0 and out.startswith("confirmed: line 2")


def test_a_new_session_does_not_inherit_an_old_sessions_carries(world, fw):
    _compute_624(fw)
    code, _, _ = fw("read", "--match", r"(?m)^\s*‎?(\d[\d,]*)\s*$", "--as", "result")
    assert code == 0
    fw("start", "Another job", "--app", "Calculator")
    code, _, err = fw("do", "append", "Equals", "@result")
    assert code == 4 and "@result was not read in session" in err


def test_a_driver_error_at_start_stops_with_its_reason_not_a_traceback(world, fw, monkeypatch):
    """G7 pilot: TextEdit's accessibility walk timed out in `footwork start`, which printed a DriverError
    traceback and left no session behind."""

    async def timeout(inp):
        raise RuntimeError("AX tree walk for pid=77 timed out after 20 s")

    monkeypatch.setattr(world, "get_window_state", timeout)
    code, _, err = fw("start", "Compute", "--app", "Calculator")
    assert code == 7 and "stopped: RuntimeError: AX tree walk for pid=77 timed out" in err
    assert "Traceback" not in err


# ---- package H: grants bound to a resource and an effect ----


def test_a_grant_clears_one_exact_click_once(world, fw):
    fw("start", "Clear the entry", "--app", "Calculator")
    code, out, _ = fw("do", "click", "Delete", "--no-judge")
    assert code == 3 and "footwork grant click Delete" in out  # the pause names the exact grant
    code, out, _ = fw("grant", "click", "Delete")
    assert code == 0 and "granted" in out and "click on button 'Delete'" in out
    code, out, _ = fw("do", "click", "Delete", "--no-judge")
    assert code == 0 and "cleared by grant" in out and world.presses == ["Delete"]
    # an unexpected retry: the one use is spent
    code, out, _ = fw("do", "click", "Delete", "--no-judge")
    assert code == 3 and "no uses left" in out and world.presses == ["Delete"]


def test_a_grant_does_not_follow_its_label_to_another_element(world, fw):
    fw("start", "Clear the entry", "--app", "Calculator")
    fw("grant", "click", "Delete")
    # the person relabels another button "Delete all": a different element, the grant must not apply
    code, _, _ = fw("look")
    world.relabels[_id_of_label(world, "All Clear")] = "Delete all"
    code, out, _ = fw("do", "click", "Delete all", "--no-judge")
    assert code == 3 and "and this is button 'Delete all'" in out


def _id_of_label(world, label):
    return next(e["element_index"] for e in world.base["elements"] if e.get("label") == label)


@pytest.mark.parametrize("change", ["trailing_space", "trailing_newline", "frame", "unwritable"])
@pytest.mark.parametrize("durable", [False, True])
async def test_capability_exact_preconditions_survive_native_dispatch(change, durable, request, monkeypatch):
    """An external edit after validation must refuse before either AX setter."""
    from jevdual.capability.backend import ScopedBackend

    fixture = request.getfixturevalue("durable_text_capability" if durable else "text_capability")
    world, tools = fixture[:2]
    row = _append_target(await tools.call("bind", {"name": "destination"}))
    original = ScopedBackend.dispatch

    async def changed_between_validation_and_input(backend, validated):
        if change == "trailing_space":
            world.content += " "
        elif change == "trailing_newline":
            world.content += "\n"
        elif change == "frame":
            world.frame = (110, 20, 400, 300)
        else:
            world.insertable = False
        return await original(backend, validated)

    monkeypatch.setattr(ScopedBackend, "dispatch", changed_between_validation_and_input)
    result = await tools.call("act", {"target": row["target"], "text": "17.25 USD"})
    assert result["phase"] == "not_sent"
    assert result["disposition"] in {"not_sent", "refused"}
    assert world.writes == []
    assert "17.25 USD" not in world.content


@pytest.mark.parametrize(
    "durable,change", [(False, "document"), (True, "document"), (True, "process"), (True, "inode")]
)
async def test_capability_resource_replacement_during_live_observation_sends_nothing(
    durable, change, request, monkeypatch
):
    from jevdual.native import NativeBridge

    fixture = request.getfixturevalue("durable_text_capability" if durable else "text_capability")
    world, tools = fixture[:2]
    identity = fixture[2] if durable else None
    row = _append_target(await tools.call("bind", {"name": "destination"}))
    original = NativeBridge._live

    async def replace_while_observing(bridge, snapshot, cid, operation):
        if change == "document":
            world.document = world.document.with_name("replacement.txt")
        elif change == "process":
            identity["start"] = "0x2.0p0"
        else:
            identity["inode"] += 1
        return await original(bridge, snapshot, cid, operation)

    monkeypatch.setattr(NativeBridge, "_live", replace_while_observing)
    result = await tools.call("act", {"target": row["target"], "text": "17.25 USD"})
    assert result["phase"] == "not_sent"
    assert world.writes == [] and world.content == "Invoice report"
