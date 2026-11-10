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


def _mac_selectors(monkeypatch):
    """Select the simulated Mac routes without changing the interpreter's platform."""
    import sys

    from jevdual import native
    from jevdual.capability import backend, recovery

    monkeypatch.setattr(native, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(backend, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(recovery, "sys", SimpleNamespace(platform="darwin", executable=sys.executable))


@pytest.fixture
def text_capability(tmp_path, monkeypatch):
    """Public MCP calls over the actual service/backend/native append route."""
    from jevdual.capability.backend import ScopedBackend
    from jevdual.capability.journal import Journal
    from jevdual.capability.mcp_server import ToolFacade
    from jevdual.capability.service import CapabilityService

    from tests.fixtures.native_world import TextWorld

    _mac_selectors(monkeypatch)
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


async def test_capability_restart_without_durable_execution_evidence_stays_unknown(
    text_capability, monkeypatch
):
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
    identity = {
        "boot": "test-boot",
        "pid": world.pid,
        "start": "0x1.0p0",
        "document": str(world.document),
        "device": 1,
        "inode": 2,
    }
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
async def test_capability_durable_receipt_recovers_historical_applied_after_restart(
    durable_text_capability, monkeypatch, change
):
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
        status = await restarted.call(
            "status", {"client_token": arguments["client_token"], "reconcile": True}
        )
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


async def test_capability_started_no_receipt_rejects_matching_external_text(
    durable_text_capability, monkeypatch
):
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
async def test_capability_durable_storage_admission_failure_never_launches(
    durable_text_capability, monkeypatch, boundary
):
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


async def test_capability_worker_readback_refusal_after_input_remains_unknown(
    durable_text_capability, monkeypatch
):
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
    _mac_selectors(monkeypatch)
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


def test_linux_browser_start_recovers_window_in_exact_owned_profile(world, fw, monkeypatch):
    from jevdual import browser_driver as browser

    opened, running = [], [False]
    monkeypatch.setattr(browser, 'sys', SimpleNamespace(platform='linux'))
    monkeypatch.setattr(browser, 'launch_chrome', lambda *_: 42)
    monkeypatch.setattr(browser, '_begin_chrome', lambda *_: (42, None))
    monkeypatch.setattr(browser, 'chrome_pid', lambda: 42)
    monkeypatch.setattr(browser, 'chrome_executable', lambda: '/qualified/chromium')
    monkeypatch.setattr(browser, '_incarnation', lambda pid: 1.0, raising=False)
    monkeypatch.setattr(browser, '_recovery_flags', lambda pid, incarnation: [])

    class Driver:
        async def list_windows(self, _):
            window = SimpleNamespace(pid=42, window_id=7, bounds=SimpleNamespace(width=100, height=100))
            return SimpleNamespace(windows=[window] if running[0] else [])

        async def shutdown(self):
            pass

    def spawn(args, **_):
        opened.append(args)
        running[0] = True
        return SimpleNamespace(pid=99, poll=lambda: 0, wait=lambda **_: 0)

    async def attach(self):
        self.target_id, self.tab_id = 'target', 'tab'
        return {}

    async def observe(self, **_):
        return browser.menu_from_semantic({'snapshot': {'id': 'fixture', 'complete': True},
                                           'content_refs': [{'role': 'paragraph', 'name': 'Recovered page'}]})

    monkeypatch.setattr(browser, 'configured_driver', lambda pid: Driver())
    monkeypatch.setattr(browser.subprocess, 'run', spawn)
    monkeypatch.setattr(browser.subprocess, 'Popen', spawn)
    monkeypatch.setattr(browser.BrowserBridge, 'attach', attach)
    monkeypatch.setattr(browser.BrowserBridge, 'observe', observe)
    code, out, err = fw('start', 'Recover the owned browser', '--browser')
    assert code == 0, err
    assert 'Recovered page' in out
    assert opened and opened[0][0] == '/qualified/chromium'
    assert '--new-window' in opened[0]
    assert f'--user-data-dir={browser.PROFILE_DIR}' in opened[0]


def _state(fw) -> dict:
    return json.loads((fw.session / "session.json").read_text())


def _id(out: str, label: str) -> int:
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("[") and f"'{label}'" in s:
            return int(s[1 : s.index("]")])
    raise AssertionError(f"{label!r} not in the observation")


@pytest.mark.parametrize("observed_pid,observed_name,expected", [
    (77, "Org.xfce.mousepad", 0),
    (78, "Org.xfce.mousepad", 2),
    (77, "UnrelatedApplication", 2),
])
def test_linux_start_matches_observed_alias_only_to_requested_process(
    world, fw, monkeypatch, observed_pid, observed_name, expected
):
    from jevdual import native

    monkeypatch.setattr(native, "sys", SimpleNamespace(platform="linux"))
    world.base.update(app_name=observed_name, pid=observed_pid, elements=[], tree_markdown="")

    async def apps(inp):
        return SimpleNamespace(apps=[SimpleNamespace(
            name="Mousepad", bundle_id="org.xfce.mousepad", pid=77, running=True
        )])

    monkeypatch.setattr(world, "list_apps", apps)
    code, out, err = fw("start", "Inspect the owned editor", "--app", "Mousepad", "--pid", "77")
    assert code == expected, (out, err)
    if expected == 0:
        assert "Mousepad:" in out
        assert _state(fw)["app"] == "Mousepad"
    else:
        assert "does not match the requested app and PID" in err


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


@pytest.mark.parametrize("captured", [False, True])
def test_linux_refused_save_records_no_dispatch(world, fw, monkeypatch, captured):
    from jevdual import native

    monkeypatch.setattr(native, "sys", SimpleNamespace(platform="linux"))
    attempts = []

    async def refused(name, args_json):
        attempts.append((name, json.loads(args_json)))
        if captured:
            from pathlib import Path

            path = Path(__file__).parents[1] / "results/linux-vm-save-receipt-20261030/045fc5d-refused-profile-sdk.json"
            record = json.loads(path.read_text())
            return cd.ToolResult(
                text=record["text"], images=[], structured_json=record["structured_json"],
                is_error=record["is_error"], error_code=record["error_code"], action=None,
                verification=None, degraded=record["degraded"], raw_json=record["raw_json"],
            )
        return SimpleNamespace(
            action=None, is_error=True, error_code="foreground_unavailable",
            text="window did not become active; no input was sent",
            structured_json=json.dumps({
                "code": "foreground_unavailable", "effect": "none",
                "detail": "window did not become active; no input was sent",
                "suggestion": "Confirm the exact window before retrying",
            }),
        )

    monkeypatch.setattr(world, "call_tool", refused)
    assert fw("start", "Save", "--app", "Calculator", "--mode", "exclusive_desktop")[0] == 0
    code, out, err = fw("do", "hotkey", "ctrl", "s", "--no-judge", "--authorize", "Delete")
    assert code == 0, err
    assert len(attempts) == 1 and attempts[0][0] == "hotkey"
    assert world.tool_calls == world.presses == []
    assert "not sent" in out and "foreground_unavailable" in out
    assert _state(fw)["memory"][-1].endswith("hotkey(ctrl+s) -> refused")


def test_an_opaque_driver_error_does_not_claim_no_delivery(world, fw):
    fw("start", "Compute 8", "--app", "Calculator")
    _, out, _ = fw("look")
    world.refuse.add("8")
    code, out, _ = fw("do", "click", str(_id(out, "8")), "--no-judge")
    assert code == 0 and "driver says unverifiable" in out and world.presses == []
    assert "receipt: Receipt for click(8): unverifiable" in out
    assert _state(fw)["memory"] == ["step 1: click(8) -> unverifiable"]


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


@pytest.mark.parametrize(
    "words",
    [
        ("click", "All Clear"),
        ("key", "Tab"),
        ("hotkey", "cmd", "s"),
        ("menu", "File > Save"),
        ("enter", "All Clear"),
        ("navigate", "http://127.0.0.1/fixture"),
    ],
)
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


def test_post_press_driver_error_is_not_reported_as_refusal(world, fw, monkeypatch):
    original = world.click

    async def press_then_fail(inp):
        await original(inp)
        raise RuntimeError("post-press acknowledgement lost")

    fw("start", "Compute", "--app", "Calculator")
    monkeypatch.setattr(world, "click", press_then_fail)
    code, out, err = fw("do", "click", "All Clear", "--no-judge")
    assert code == 0, err
    assert world.presses == ["All Clear"]
    records = [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines()]
    action = next(r for r in records if r["kind"] == "do")
    assert action["driver_effect"] == "unverifiable", action
    assert "not applied" not in out
    assert "unverifiable" in out


def test_post_press_outer_runtime_error_remains_uncertain(world, fw, monkeypatch):
    from jevdual.native import NativeBridge

    original = NativeBridge.act

    async def press_then_fail(self, *args, **kwargs):
        await original(self, *args, **kwargs)
        raise RuntimeError("bridge reply lost after input")

    fw("start", "Compute", "--app", "Calculator")
    monkeypatch.setattr(NativeBridge, "act", press_then_fail)
    code, out, err = fw("do", "click", "All Clear", "--no-judge")
    assert code == 0, err
    assert world.presses == ["All Clear"]
    assert "not dispatched" not in out and "not applied" not in out
    assert "unverifiable" in out


def test_cancelled_granted_press_characterizes_missing_durable_intent(world, fw, monkeypatch):
    """OD2 diagnosis; durable admission must replace this characterization with safety assertions."""
    import asyncio

    from jevdual.native import NativeBridge

    original = NativeBridge.act

    async def press_then_cancel(self, *args, **kwargs):
        await original(self, *args, **kwargs)
        raise asyncio.CancelledError()

    fw("start", "Compute", "--app", "Calculator")
    fw("grant", "click", "Delete")
    monkeypatch.setattr(NativeBridge, "act", press_then_cancel)
    with pytest.raises(asyncio.CancelledError):
        fw("do", "click", "Delete", "--no-judge")
    assert world.presses == ["Delete"]
    records = [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines()]
    assert any(r["kind"] == "grant_used" for r in records)
    assert not any(r["kind"] == "do" for r in records)
    assert json.loads((fw.session / "grants.json").read_text())[0]["uses_left"] == 0
    monkeypatch.setattr(NativeBridge, "act", original)
    fw("grant", "click", "Delete")
    code, _, err = fw("do", "click", "Delete", "--no-judge")
    assert code == 0, err
    assert world.presses == ["Delete", "Delete"]


def _durable_start(fw, monkeypatch, tmp_path, app="Calculator"):
    import jevdual.session_operations as operations

    monkeypatch.setattr(
        operations,
        "native_identity",
        lambda pid, window_id: {"boot": "test-boot", "pid": pid, "start": "1.0", "window_id": window_id},
    )
    authority = tmp_path / "authority.sqlite"
    code, out, err = fw("start", "Compute", "--app", app, "--authority", str(authority))
    assert code == 0, (out, err)
    return authority


def test_durable_cancelled_granted_press_blocks_retry_without_extra_input(world, fw, monkeypatch, tmp_path):
    import asyncio

    from jevdual.native import NativeBridge

    authority = _durable_start(fw, monkeypatch, tmp_path)
    fw("grant", "click", "Delete")
    original = NativeBridge.act

    async def cancel_after_press(self, *args, **kwargs):
        await original(self, *args, **kwargs)
        raise asyncio.CancelledError()

    monkeypatch.setattr(NativeBridge, "act", cancel_after_press)
    with pytest.raises(asyncio.CancelledError):
        fw("do", "click", "Delete", "--no-judge", "--token", "delete-once")
    assert world.presses == ["Delete"]
    monkeypatch.setattr(NativeBridge, "act", original)
    code, out, err = fw("do", "click", "Delete", "--no-judge", "--token", "delete-once")
    assert code == 0 and "unknown" in out, (out, err)
    code, out, err = fw("do", "click", "Delete", "--no-judge", "--token", "another-delete")
    assert code != 0 and "busy" in (out + err).lower(), (out, err)
    assert world.presses == ["Delete"]
    from jevdual.session_operations import SessionOperations

    with SessionOperations(authority) as ops:
        assert len(ops.status()) == 1
        assert ops.status()[0].state == "unknown"


def test_durable_replay_needs_no_current_app_and_changed_request_conflicts(world, fw, monkeypatch, tmp_path):
    from jevdual import session

    _durable_start(fw, monkeypatch, tmp_path)
    assert fw("do", "click", "All Clear", "--no-judge", "--token", "clear-once")[0] == 0

    def unavailable(*args, **kwargs):
        raise AssertionError("replay must not bind the app")

    monkeypatch.setattr(session, "bind", unavailable)
    code, out, err = fw("do", "click", "All Clear", "--no-judge", "--token", "clear-once")
    assert code == 0 and "operation" in out, (out, err)
    assert world.presses == ["All Clear"]
    code, out, err = fw("do", "click", "Delete", "--no-judge", "--token", "clear-once")
    assert code != 0 and "token_conflict" in (out + err), (out, err)


def test_durable_lost_projection_replays_finished_operation(world, fw, monkeypatch, tmp_path):
    from jevdual.session import SessionState

    _durable_start(fw, monkeypatch, tmp_path)
    original = SessionState.log
    failed = False

    def lose_do(self, record):
        nonlocal failed
        if record.get("kind") == "do" and not failed:
            failed = True
            raise OSError("projection write lost after journal finish")
        return original(self, record)

    monkeypatch.setattr(SessionState, "log", lose_do)
    assert fw("do", "click", "All Clear", "--no-judge", "--token", "lost-response")[0] != 0
    code, out, err = fw("do", "click", "All Clear", "--no-judge", "--token", "lost-response")
    assert code == 0, (out, err)
    assert world.presses == ["All Clear"]
    records = [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines()]
    assert len([r for r in records if r["kind"] == "do"]) == 1


def test_durable_partial_projection_is_quarantined_before_replay_click_and_done(
    world, fw, monkeypatch, tmp_path
):
    from jevdual.session import SessionState
    from jevdual.session_operations import SessionOperations

    authority = _durable_start(fw, monkeypatch, tmp_path)
    original = SessionState.log
    fragment = b'{"kind":"do","operation_id":'
    failed = False

    def partial_do(self, record):
        nonlocal failed
        if record.get("kind") == "do" and not failed:
            failed = True
            with (self.path / "session.jsonl").open("ab") as stream:
                stream.write(fragment)
            raise OSError("projection interrupted after partial bytes")
        return original(self, record)

    monkeypatch.setattr(SessionState, "log", partial_do)
    assert fw("do", "click", "All Clear", "--no-judge", "--token", "partial-response")[0] != 0
    with SessionOperations(authority) as operations:
        (operation,) = operations.status()
        assert operation.state == "final"
    damaged = (fw.session / "session.jsonl").read_bytes()
    assert fragment in damaged
    code, out, err = fw("do", "click", "All Clear", "--no-judge", "--token", "partial-response")
    assert code == 0 and '"replay": true' in out, (out, err)
    code, out, err = fw("do", "click", "label:7", "--no-judge", "--token", "after-partial")
    assert code == 0, (out, err)
    code, out, err = fw("done", "7")
    assert code == 0 and "accepted" in out, (out, err)
    assert world.presses == ["All Clear", "7"]
    records = [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines()]
    repairs = [record for record in records if record.get("kind") == "projection_repair"]
    assert len(repairs) == 1
    assert (fw.session / repairs[0]["quarantine"]).read_bytes() == damaged
    assert sum(record.get("operation_id") == operation.id for record in records) == 1


def _legacy_unknown(authority):
    from jevdual.capability.journal import Journal

    with_journal = Journal(authority)
    try:
        operation, _ = with_journal.begin(
            task="legacy-task",
            resource="legacy-resource",
            observation="legacy-observation",
            target="legacy-target",
            move="append",
            args={"text": "unacknowledged"},
            client_token="legacy-token",
        )
        return operation.id
    finally:
        with_journal.close()


@pytest.mark.parametrize("later_count", [0, 101])
def test_durable_status_reports_legacy_unknown_without_operator_proof(
    world, fw, monkeypatch, tmp_path, later_count
):
    from jevdual.capability.journal import Journal

    authority = _durable_start(fw, monkeypatch, tmp_path)
    operation_id = _legacy_unknown(authority)
    journal = Journal(authority)
    try:
        for index in range(later_count):
            recent, _ = journal.begin(
                task="legacy-other",
                resource=f"resource-{index}",
                observation="legacy-observation",
                target="legacy-target",
                move="append",
                args={},
                client_token=f"recent-{index}",
            )
            journal.finish(recent.id, disposition="not_sent", phase="not_sent", evidence={})
    finally:
        journal.close()
    code, out, err = fw("status", "--reconcile")
    assert code == 0, (out, err)
    (blocker,) = json.loads(out)["domain_unresolved"]
    assert blocker["operation_id"] == operation_id and blocker["state"] == "unknown"
    assert blocker["disposition"] == "unknown" and blocker["reservation"] is None
    assert blocker["projection"] is None and blocker["protocol"] == "legacy"
    code, out, err = fw("do", "click", "All Clear", "--no-judge")
    assert code != 0 and "busy" in (out + err).lower()
    assert world.presses == []


@pytest.mark.parametrize(
    "scope",
    [
        "own",
        "domain",
        "legacy_domain",
        "context",
        "legacy_context",
        "legacy_own",
        "authority_pending",
        "authority_context_pending",
    ],
)
def test_done_refuses_unresolved_custody_before_keys_app_or_accepting_verifier(
    world, fw, monkeypatch, tmp_path, scope
):
    import jevdual.keys
    from jevdual import session
    from jevdual.session_operations import SessionOperations

    authority = _durable_start(fw, monkeypatch, tmp_path)
    context = tmp_path / "context"
    extra = []
    if scope in ("legacy_context", "legacy_own", "authority_pending", "authority_context_pending"):
        state = session.SessionState.load(fw.session)
        if scope in ("legacy_context", "authority_context_pending"):
            context.mkdir()
            state.dir = str(context)
            extra = ["--context-from", str(context)]
        if scope.startswith("legacy"):
            state.authority = ""
        state.pending = {"op": "click", "driver_effect": "unverifiable", "dispatched": None}
        state.save()  # Deliberately no do/receipt projection for the pending unknown.
    elif scope == "context":
        context.mkdir()
        state = session.SessionState.load(fw.session)
        state.dir, state.authority = str(context), str(tmp_path / "context.sqlite")
        state.save()
        _legacy_unknown(tmp_path / "context.sqlite")
        extra = ["--context-from", str(context)]
    elif scope == "legacy_domain":
        _legacy_unknown(authority)
    else:
        state = session.SessionState.load(fw.session)
        with SessionOperations(authority) as operations:
            operation = operations.admit(
                session_id=state.session_id if scope == "own" else "another-session",
                token="unfinished",
                request={"words": ["click", "Delete"]},
                resource="native:fixture",
                observation="old",
                target="1",
                move="click",
                authorization_basis="existing_policy",
                projection={"step": 1, "op": "click"},
            )
            operations.start(operation.id)

    calls = []
    monkeypatch.setattr(
        jevdual.keys, "load_keys", lambda: calls.append("keys") or {"TYPESAFE_API_KEY": "test"}
    )
    original_bind = session.bind

    async def counted_bind(state):
        calls.append("app")
        return await original_bind(state)

    monkeypatch.setattr(session, "bind", counted_bind)
    original_verify = _Verifier.verify

    async def accepting_verify(self, *args, **kwargs):
        calls.append("verifier")
        return await original_verify(self, *args, **kwargs)

    monkeypatch.setattr(_Verifier, "verify", accepting_verify)
    code, out, err = fw("done", "looks complete", *extra)
    assert code == 5 and "unresolved" in out + err, (out, err)
    assert calls == []
    assert _state(fw)["status"] == "open" and world.presses == []


@pytest.mark.parametrize("same_domain", [False, True])
def test_done_retains_context_ownership_through_verifier_without_relocking_shared_domain(
    world, fw, monkeypatch, tmp_path, same_domain
):
    from jevdual.capability.journal import JournalLocked
    from jevdual.session import SessionState
    from jevdual.session_operations import SessionOperations

    authority = _durable_start(fw, monkeypatch, tmp_path)
    context = tmp_path / "context"
    context.mkdir()
    state = SessionState.load(fw.session)
    context_authority = authority if same_domain else tmp_path / "context.sqlite"
    state.dir, state.authority = str(context), str(context_authority)
    state.save()
    if not same_domain:
        SessionOperations(context_authority).close()
    seen = []
    original_verify = _Verifier.verify

    async def accept_with_owned_context(self, *args, **kwargs):
        with pytest.raises(JournalLocked):
            SessionOperations(context_authority)
        seen.append("context held")
        return await original_verify(self, *args, **kwargs)

    monkeypatch.setattr(_Verifier, "verify", accept_with_owned_context)
    code, out, err = fw("done", "complete", "--context-from", str(context))
    assert code == 0 and "accepted" in out, (out, err)
    assert seen == ["context held"]
    SessionOperations(context_authority).close()  # The bounded command releases both domains.


def test_done_repairs_settled_durable_context_projection_without_repeating_effect(
    world, fw, monkeypatch, tmp_path
):
    from jevdual.session_operations import SessionOperations

    authority = _durable_start(fw, monkeypatch, tmp_path)
    context = tmp_path / "settled-context"
    assert (
        cli.main(
            [
                "start",
                "Compute",
                "--app",
                "Calculator",
                "--session",
                str(context),
                "--authority",
                str(authority),
            ]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "do",
                "click",
                "All Clear",
                "--no-judge",
                "--session",
                str(context),
                "--token",
                "context-once",
                "--settle",
                "0",
            ]
        )
        == 0
    )
    with SessionOperations(authority) as operations:
        (operation,) = operations.status()
        assert operation.state == "final"
    log = context / "session.jsonl"
    with log.open("ab") as stream:
        stream.write(b'{"kind":"interrupted-context"')
    damaged = log.read_bytes()
    code, out, err = fw("done", "complete", "--context-from", str(context))
    assert code == 0 and "accepted" in out, (out, err)
    assert world.presses == ["All Clear"]
    records = [json.loads(line) for line in log.read_bytes().splitlines()]
    repair = next(record for record in records if record.get("kind") == "projection_repair")
    assert (context / repair["quarantine"]).read_bytes() == damaged
    assert (
        sum(record.get("kind") == "do" and record.get("operation_id") == operation.id for record in records)
        == 1
    )
    assert any(record.get("kind") == "receipt" for record in records)


def test_done_refuses_corrupt_legacy_context_before_keys_app_or_provider(world, fw, monkeypatch, tmp_path):
    import jevdual.keys
    from jevdual import session

    _durable_start(fw, monkeypatch, tmp_path)
    context = tmp_path / "legacy-context"
    context.mkdir()
    state = session.SessionState.load(fw.session)
    state.dir, state.authority = str(context), ""
    state.save()
    log = context / "session.jsonl"
    original = b'{"kind":"receipt","effect":"confirmed"}\n{"interrupted":'
    log.write_bytes(original)
    calls = []
    monkeypatch.setattr(jevdual.keys, "load_keys", lambda: calls.append("keys") or {})

    async def forbidden_bind(state):
        calls.append("app")
        raise AssertionError("corrupt legacy evidence must refuse before app binding")

    monkeypatch.setattr(session, "bind", forbidden_bind)
    code, out, err = fw("done", "complete", "--context-from", str(context))
    assert code == 5 and "context_evidence_unreadable" in out + err, (out, err)
    assert calls == [] and _state(fw)["status"] == "open"
    assert log.read_bytes() == original and not list(context.glob("session.interrupted-*"))


def test_durable_process_change_refuses_new_input_but_status_stays_available(
    world, fw, monkeypatch, tmp_path
):
    import jevdual.session_operations as operations

    _durable_start(fw, monkeypatch, tmp_path)
    monkeypatch.setattr(
        operations,
        "native_identity",
        lambda pid, window_id: {"boot": "test-boot", "pid": pid, "start": "2.0", "window_id": window_id},
    )
    code, out, err = fw("do", "click", "All Clear", "--no-judge", "--token", "new-process")
    assert code != 0, (out, err)
    assert world.presses == []
    assert fw("status")[0] == 0


def test_durable_start_preserves_existing_history(world, fw, monkeypatch, tmp_path):
    authority = _durable_start(fw, monkeypatch, tmp_path)
    assert fw("do", "click", "All Clear", "--no-judge", "--token", "retained")[0] == 0
    before = (fw.session / "session.jsonl").read_text()
    code, _, _ = fw("start", "Replacement", "--app", "Calculator", "--authority", str(authority))
    assert code != 0
    assert (fw.session / "session.jsonl").read_text().startswith(before)


def test_durable_domain_blocks_another_session_before_missing_secret_resolution(
    world, fw, monkeypatch, tmp_path, capsys
):
    from jevdual.native import NativeBridge

    authority = _durable_start(fw, monkeypatch, tmp_path)

    async def uncertain(self, *args, **kwargs):
        raise RuntimeError("delivery cannot be determined")

    monkeypatch.setattr(NativeBridge, "act", uncertain)
    assert fw("do", "click", "All Clear", "--no-judge", "--token", "uncertain")[0] == 0
    other = tmp_path / "another-session"
    assert (
        cli.main(
            [
                "start",
                "Another",
                "--app",
                "Calculator",
                "--session",
                str(other),
                "--authority",
                str(authority),
            ]
        )
        == 0
    )
    capsys.readouterr()
    monkeypatch.delenv("FOOTWORK_SECRET_MISSING", raising=False)
    code = cli.main(
        [
            "do",
            "type",
            "anything",
            "{MISSING}",
            "--session",
            str(other),
            "--token",
            "blocked",
            "--settle",
            "0",
        ]
    )
    output = capsys.readouterr()
    assert code != 0 and "busy" in (output.out + output.err).lower()
    assert "export FOOTWORK_SECRET" not in output.err
    assert world.presses == []


def test_durable_lock_contention_does_not_write_another_owners_log(world, fw, monkeypatch, tmp_path):
    from jevdual.session_operations import SessionOperations

    authority = _durable_start(fw, monkeypatch, tmp_path)
    before = (fw.session / "session.jsonl").read_bytes()
    with SessionOperations(authority):
        code, _, _ = fw("look")
        assert code != 0
        assert (fw.session / "session.jsonl").read_bytes() == before


def test_durable_secret_request_replays_without_secret_and_never_persists_value(
    world, fw, monkeypatch, tmp_path
):
    import asyncio

    world.base["elements"].append(
        {
            "element_index": 999999,
            "role": "AXTextField",
            "label": "Fixture input",
            "value": "",
            "parent_index": 0,
        }
    )
    authority = _durable_start(fw, monkeypatch, tmp_path)
    value = "fixture-private-value"
    monkeypatch.setenv("FOOTWORK_SECRET_DEMO", value)
    attempts = []

    async def set_then_cancel(name, args_json):
        assert name == "set_value"
        attempts.append(json.loads(args_json)["value"])
        raise asyncio.CancelledError()

    monkeypatch.setattr(world, "call_tool", set_then_cancel)
    words = ("do", "type", "Fixture input", "{DEMO}", "--no-judge", "--token", "secret-input")
    try:
        result = fw(*words)
    except asyncio.CancelledError:
        pass
    else:
        pytest.fail(f"driver boundary was not reached: {result!r}")
    assert attempts == [value]
    monkeypatch.delenv("FOOTWORK_SECRET_DEMO")
    code, out, err = fw(*words)
    assert code == 0 and "unknown" in out, (out, err)
    assert len(attempts) == 1
    assert value not in out + err
    assert value.encode() not in authority.read_bytes()
    for name in ("session.json", "session.jsonl"):
        assert value not in (fw.session / name).read_text()
    code, out, err = fw("look")
    assert code != 0 and "secret_unavailable" in out + err
    assert fw("status")[0] == 0


def test_durable_short_secret_refuses_before_binding(world, fw, monkeypatch, tmp_path):
    from jevdual import session

    _durable_start(fw, monkeypatch, tmp_path)
    monkeypatch.setenv("FOOTWORK_SECRET_SHORT", "xy")

    def unexpected_bind(*args, **kwargs):
        raise AssertionError("short secret must be refused before binding")

    monkeypatch.setattr(session, "bind", unexpected_bind)
    code, out, err = fw("do", "type", "Anything", "{SHORT}", "--token", "short")
    assert code != 0 and "short_secret_unsupported" in out + err
    assert "xy" not in out + err
    assert world.presses == []


def test_retained_execution_reconciles_lost_finish_without_new_input(world, fw, monkeypatch, tmp_path):
    from jevdual import session
    from jevdual.session_operations import SessionOperations

    authority = _durable_start(fw, monkeypatch, tmp_path)
    fw("grant", "click", "Delete")
    original = SessionOperations.finish_from_execution

    def lost_finish(self, operation_id):
        raise OSError("lost journal finalization after retained runtime receipt")

    monkeypatch.setattr(SessionOperations, "finish_from_execution", lost_finish)
    code, out, err = fw("do", "click", "Delete", "--no-judge", "--token", "retained-return")
    assert code != 0, (out, err)
    assert world.presses == ["Delete"]
    monkeypatch.setattr(SessionOperations, "finish_from_execution", original)

    def no_live_app(*args, **kwargs):
        raise AssertionError("qualified reconciliation must not bind or dispatch")

    monkeypatch.setattr(session, "bind", no_live_app)
    code, out, err = fw("status", "--reconcile")
    assert code == 0 and "applied" in out, (out, err)
    assert fw("status", "--reconcile")[0] == 0
    assert fw("do", "click", "Delete", "--no-judge", "--token", "retained-return")[0] == 0
    assert world.presses == ["Delete"]
    with SessionOperations(authority) as operations:
        op = operations.status()[0]
        assert op.state == "final" and op.disposition == "applied"
        assert operations.receipt(op)["reservation"] == "spent"
        kinds = [event["kind"] for event in operations.events(op.id)]
        assert "recovered_unknown" in kinds and kinds.count("execution_reconciled") == 1


def test_reconciliation_without_retained_return_keeps_cancelled_input_unknown(
    world, fw, monkeypatch, tmp_path
):
    import asyncio

    from jevdual import session
    from jevdual.native import NativeBridge

    _durable_start(fw, monkeypatch, tmp_path)
    original = NativeBridge.act

    async def cancelled(self, *args, **kwargs):
        await original(self, *args, **kwargs)
        raise asyncio.CancelledError()

    monkeypatch.setattr(NativeBridge, "act", cancelled)
    with pytest.raises(asyncio.CancelledError):
        fw("do", "click", "All Clear", "--no-judge", "--token", "no-return")

    def no_live_app(*args, **kwargs):
        raise AssertionError("current state must not be used as execution proof")

    monkeypatch.setattr(session, "bind", no_live_app)
    code, out, err = fw("status", "--reconcile")
    assert code == 0 and "unknown" in out, (out, err)
    code, out, err = fw("do", "click", "All Clear", "--no-judge", "--token", "new-input")
    assert code != 0 and "busy" in out + err
    assert world.presses == ["All Clear"]


def test_retained_sent_unknown_does_not_become_success_on_reconciliation(world, fw, monkeypatch, tmp_path):
    from jevdual.session_operations import SessionOperations

    authority = _durable_start(fw, monkeypatch, tmp_path)
    fw("grant", "click", "Delete")
    original = world.click

    async def delivered_unknown(inp):
        await original(inp)
        return SimpleNamespace(
            effect="unverifiable",
            delivery=SimpleNamespace(mode="background", delivered_count=1),
            evidence=[],
            summary="input delivered; app effect unconfirmed",
        )

    monkeypatch.setattr(world, "click", delivered_unknown)
    code, out, err = fw("do", "click", "Delete", "--no-judge", "--token", "sent-unknown")
    assert code == 0, (out, err)
    code, out, err = fw("status", "--reconcile")
    assert code == 0 and "unknown" in out, (out, err)
    assert world.presses == ["Delete"]
    with SessionOperations(authority) as operations:
        op = operations.status()[0]
        assert op.state == "unknown" and op.phase == "sent"
        assert operations.receipt(op)["reservation"] == "spent"


def test_real_cli_live_append_retains_full_typed_value(world, fw, monkeypatch, tmp_path):
    from jevdual.completion import session_effects

    from tests.fixtures.native_world import TextWorld

    text_world = TextWorld(tmp_path / "note.txt", content="Prefix\n")
    text_world.install(monkeypatch)

    async def apps(inp):
        return SimpleNamespace(apps=[SimpleNamespace(name="TextEdit", pid=77, running=True)])

    async def windows(inp):
        return SimpleNamespace(
            windows=[
                SimpleNamespace(
                    window_id=40335, title="note.txt", bounds=SimpleNamespace(width=400, height=300)
                )
            ]
        )

    monkeypatch.setattr(text_world, "list_apps", apps, raising=False)
    monkeypatch.setattr(text_world, "list_windows", windows, raising=False)
    _durable_start(fw, monkeypatch, tmp_path, app="TextEdit")
    payload = "long-value-" + "x" * 240
    code, out, err = fw("do", "append", "1", payload, "--no-judge", "--token", "long-append")
    assert code == 0, (out, err)
    assert text_world.content == "Prefix\n" + payload
    assert len([item for item in text_world.writes if item[0] == "AXSelectedText"]) == 1
    facts = session_effects(fw.session)
    exact = [fact for fact in facts if fact.effect == "field_holds" and fact.usable]
    assert len(exact) == 1, [(fact.effect, fact.limits) for fact in facts]
    assert exact[0].values == (text_world.content,)


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


def test_native_start_and_look_use_a_cua_capture_session(world, fw, monkeypatch):
    """CUA publishes screenshots only inside a named driver session."""
    original = world.get_window_state
    original_click = world.click
    sessions = []

    async def capture(inp):
        if inp.include_screenshot and inp.screenshot_out_file and not inp.session:
            raise RuntimeError(
                "tool='get_window_state', message='capture binding failed: capture binding is invalid. "
                "Not dispatching click.', error_code='capture_binding_failed'"
            )
        sessions.append(inp.session)
        return await original(inp)

    async def click(inp):
        assert inp.session == sessions[-1]
        return await original_click(inp)

    monkeypatch.setattr(world, "get_window_state", capture)
    monkeypatch.setattr(world, "click", click)
    code, out, err = fw("start", "Observe Calculator", "--app", "Calculator")
    assert code == 0, err
    assert "elements:" in out and (fw.session / "session.json").exists()
    code, out, err = fw("look")
    assert code == 0, err
    assert "elements:" in out
    code, _, err = fw("do", "click", str(_id(out, "7")), "--no-judge")
    assert code == 0, err
    assert world.presses == ["7"]


def test_look_until_observes_delayed_exact_control_without_input(world, fw, monkeypatch):
    assert fw("start", "Observe delayed form", "--app", "Calculator")[0] == 0
    original = world.get_window_state
    calls = []
    captures = []

    async def delayed(inp):
        snap = await original(inp)
        calls.append(snap["snapshot_id"])
        captures.append(inp.screenshot_out_file)
        if len(calls) >= 2:
            snap["elements"] = [
                {**row, "label": "Song description"} if row.get("label") == "7" else row
                for row in snap["elements"]
            ]
        return snap

    monkeypatch.setattr(world, "get_window_state", delayed)
    code, out, err = fw("look", "--until", "Song description", "--timeout", "1")
    assert code == 0, err
    assert len(calls) == 2 and len(set(calls)) == 2
    assert len(set(captures)) == 2
    assert "observed exact candidate label 'Song description' (1 match)" in out
    assert "not action authorization or task completion" in out
    assert world.presses == [] and world.tool_calls == []


def test_look_until_timeout_preserves_partial_menu_and_ignores_title_text(world, fw, monkeypatch):
    world.toggles = {910: ["Song description helper", "0"]}
    assert fw("start", "Observe delayed form", "--app", "Calculator")[0] == 0
    original = world.get_window_state

    async def only_text(inp):
        snap = await original(inp)
        snap["window_title"] = "Song description"
        snap["tree_markdown"] += '\nAXStaticText = "Song description"'
        snap["elements_complete"] = False
        return snap

    monkeypatch.setattr(world, "get_window_state", only_text)
    code, out, err = fw("look", "--until", "Song description", "--timeout", "0.1")
    assert code == 6
    assert "exact candidate label 'Song description' not observed" in err
    assert "elements:" in out and "this observation is incomplete" in out
    assert world.presses == [] and world.tool_calls == []


def test_look_until_duplicate_appearance_does_not_authorize_click(world, fw):
    world.toggles = {910: ["Ready", "0"], 911: ["Ready", "0"]}
    assert fw("start", "Observe duplicate controls", "--app", "Calculator")[0] == 0
    code, out, err = fw("look", "--until", "Ready", "--timeout", "1")
    assert code == 0, err
    assert "(2 matches)" in out
    code, out, err = fw("do", "click", "Ready", "--no-judge")
    assert code == 4 and "matches 2 elements" in out + err
    assert world.presses == []


@pytest.mark.parametrize(
    "options",
    [
        ["--until", ""], ["--until", "x" * 81], ["--until", " x"],
        ["--until", "Ready\n"], ["--timeout", "1"],
        *[["--until", "Ready", "--timeout", value] for value in ("0", "-1", "61", "nan", "inf")],
    ],
)
def test_look_until_invalid_bounds_do_not_bind(world, fw, monkeypatch, options):
    def forbidden(**kwargs):
        pytest.fail("invalid wait options must not create a driver")

    monkeypatch.setattr(cd.CuaDriver, "create", forbidden)
    code, _, err = fw("look", *options)
    assert code == 2 and "look:" in err
    assert world.n == 0


def test_look_until_deadline_cancels_slow_observation_and_shuts_down(world, fw, monkeypatch):
    import asyncio
    import time

    assert fw("start", "Observe delayed form", "--app", "Calculator")[0] == 0
    events = []

    async def slow(inp):
        try:
            await asyncio.sleep(2)
        finally:
            events.append("observation cancelled")

    async def shutdown():
        events.append("shutdown")

    monkeypatch.setattr(world, "get_window_state", slow)
    monkeypatch.setattr(world, "shutdown", shutdown)
    started = time.monotonic()
    code, out, err = fw("look", "--until", "Ready", "--timeout", "0.1")
    assert code == 6 and time.monotonic() - started < 1
    assert "no observation completed before the deadline" in err
    assert "elements:" not in out
    assert events == ["observation cancelled", "shutdown"]
    assert world.presses == [] and world.tool_calls == []


def test_look_until_driver_timeout_keeps_its_actual_failure(world, fw, monkeypatch):
    assert fw("start", "Observe delayed form", "--app", "Calculator")[0] == 0

    async def broken(inp):
        raise TimeoutError("driver AX RPC expired")

    monkeypatch.setattr(world, "get_window_state", broken)
    code, _, err = fw("look", "--until", "Ready", "--timeout", "1")
    assert code == 7 and "driver AX RPC expired" in err
    assert "not observed" not in err


def test_look_until_refuses_browser_before_driver_binding(world, fw, monkeypatch):
    assert fw("start", "Observe form", "--app", "Calculator")[0] == 0
    path = fw.session / "session.json"
    raw = json.loads(path.read_text())
    raw["mode"] = "browser"
    path.write_text(json.dumps(raw))

    def forbidden(**kwargs):
        pytest.fail("unsupported browser wait must not create a driver")

    monkeypatch.setattr(cd.CuaDriver, "create", forbidden)
    code, _, err = fw("look", "--until", "Ready")
    assert code == 2 and "native sessions only" in err


def _add_native_enter_field(world):
    world.base["elements"].append({
        "element_index": 910, "element_token": "initial:910", "role": "AXTextField",
        "label": "Address and search bar", "value": "chrome://newtab", "enabled": True,
        "actions": [], "frame": {"x": 10, "y": 20, "w": 300, "h": 20},
    })


@pytest.mark.parametrize("tail", ["https://suno.com/create", "", "{UNRESOLVED_SECRET}"])
def test_native_enter_rejects_any_text_before_driver_binding(world, fw, monkeypatch, tail):
    _add_native_enter_field(world)
    assert fw("start", "Navigate own draft", "--app", "Calculator")[0] == 0
    previous = (fw.session / "session.jsonl").read_bytes()
    bindings = []
    original_create = world.create

    def counted_create(**kwargs):
        bindings.append(True)
        return original_create(**kwargs)

    monkeypatch.setattr(cd.CuaDriver, "create", counted_create)
    code, out, err = fw(
        "do", "enter", "Address and search bar", tail, "--no-judge",
        "--authorize", "enter:confirm the default button",
    )
    assert code == 2
    assert "native enter sends Return only and does not accept text" in err
    assert "do type TARGET TEXT" in err and "reobserve and verify the field" in err
    assert "do enter TARGET" in err
    assert bindings == [] and world.tool_calls == [] and world.presses == []
    assert "text=" not in out and "dispatched" not in out
    assert (fw.session / "session.jsonl").read_bytes() == previous


def test_native_enter_without_text_still_sends_one_return(world, fw):
    _add_native_enter_field(world)
    assert fw("start", "Navigate own draft", "--app", "Calculator")[0] == 0
    code, out, err = fw(
        "do", "enter", "Address and search bar", "--no-judge",
        "--authorize", "enter:confirm the default button",
    )
    assert code == 0, err
    assert "dispatched enter(Address and search bar)" in out
    assert len(world.tool_calls) == 1
    name, arguments = world.tool_calls[0]
    assert name == "press_key" and arguments["key"] == "return"
    assert "text" not in arguments


def test_native_enter_arity_guard_does_not_change_browser_route(world, fw, monkeypatch):
    from jevdual import session

    assert fw("start", "Browser operation scope", "--app", "Calculator")[0] == 0
    path = fw.session / "session.json"
    raw = json.loads(path.read_text())
    raw["mode"] = "browser"
    path.write_text(json.dumps(raw))

    async def browser_bind(state):
        raise RuntimeError("browser route reached unchanged")

    monkeypatch.setattr(session, "bind", browser_bind)
    code, _, err = fw("do", "enter", "Field", "retained text")
    assert code == 7 and "browser route reached unchanged" in err
    assert "native enter sends Return only" not in err


def _native_styles_field(world, monkeypatch, *, actual_after=None, initial=""):
    row = {
        "element_index": 910, "element_token": "initial:910", "role": "AXTextArea",
        "label": "Styles", "value": initial, "enabled": True, "actions": [],
        "frame": {"x": 10, "y": 20, "w": 300, "h": 100},
    }
    world.base["elements"].append(row)
    original = world.call_tool

    async def write(name, args_json):
        arguments = json.loads(args_json)
        if name == "set_value":
            row["value"] = arguments["value"] if actual_after is None else actual_after
        return await original(name, args_json)

    monkeypatch.setattr(world, "call_tool", write)
    return row


def _native_song_links(world, monkeypatch, urls=("https://example.test/song/a", "https://example.test/song/b")):
    from jevdual import ax

    rows, resources, clicked = [], {}, []
    for position, url in enumerate(urls):
        y = 20 + position * 30
        row = {"element_index": 920 + position, "element_token": f"initial:{920 + position}",
               "role": "AXLink", "label": "Generated song", "enabled": True,
               "actions": ["AXPress"], "in_web_content": True,
               "frame": {"x": 10, "y": y, "w": 300, "h": 20}}
        rows.append(row)
        resources[y] = url
        world.base["elements"].append(row)

    def resolve(pid, window_id, role, frame):
        assert (pid, window_id, role) == (77, 40335, "AXLink")
        hits = [row for row in rows if row["frame"]["y"] == frame.y]
        assert len(hits) == 1
        return hits[0]

    monkeypatch.setattr(ax, "resolve", resolve)
    monkeypatch.setattr(ax, "link_url", lambda element, **kwargs: resources[element["frame"]["y"]], raising=False)
    monkeypatch.setattr(ax, "semantic_section", lambda element: None)
    original = world.click

    async def click(inp):
        index = int(inp.position.element_token.split(":")[-1])
        row, = [row for row in rows if row["element_index"] == index]
        clicked.append(resources[row["frame"]["y"]])
        return await original(inp)

    monkeypatch.setattr(world, "click", click)
    return rows, resources, clicked


@pytest.mark.parametrize("selected", [920, 921])
def test_native_same_title_links_use_complete_qualified_resource_identity(world, fw, monkeypatch, selected):
    _, _, clicked = _native_song_links(world, monkeypatch)
    assert fw("start", "Open owned generated song", "--app", "Calculator")[0] == 0
    saved = [row for row in _state(fw)["last_candidates"] if row["label"] == "Generated song"]
    assert [row["id"] for row in saved] == [920, 921]
    assert all(row["href_qualified"] is True for row in saved)
    code, out, err = fw("do", "click", str(selected), "--no-judge")
    assert code == 0 and clicked == [f"https://example.test/song/{'a' if selected == 920 else 'b'}"], (out, err)


@pytest.mark.parametrize("variant", ["unreadable_peer", "same_url", "hidden_unreadable_peer"])
def test_native_link_resource_ambiguity_survives_pruning(world, fw, monkeypatch, variant):
    urls = {"unreadable_peer": ("https://example.test/song/a", None),
            "same_url": ("https://example.test/song/a",) * 2,
            "hidden_unreadable_peer": ("https://example.test/song/a", "https://example.test/song/b", None)}[variant]
    _, _, clicked = _native_song_links(world, monkeypatch, urls)
    assert fw("start", "Open owned generated song", "--app", "Calculator")[0] == 0
    code, out, err = fw("do", "click", "920", "--no-judge")
    assert code == 4 and "target_ambiguous" in out + err, (out, err)
    assert clicked == []


@pytest.mark.parametrize("change", ["url", "qualification_lost", "reordered_ids"])
def test_native_link_resource_changes_since_numeric_selection_refuse(world, fw, monkeypatch, change):
    rows, resources, clicked = _native_song_links(world, monkeypatch)
    assert fw("start", "Open owned generated song", "--app", "Calculator")[0] == 0
    if change == "reordered_ids":
        rows[0]["element_index"], rows[1]["element_index"] = 921, 920
    else:
        resources[20] = "https://example.test/song/replaced" if change == "url" else None
    code, out, err = fw("do", "click", "920", "--no-judge")
    assert code == 4 and ("target_changed" in out + err or "target_ambiguous" in out + err), (out, err)
    assert clicked == []


@pytest.mark.parametrize("change", ["url", "unreadable_peer", "same_url", "reordered_ids"])
def test_native_link_resource_changes_during_final_revalidation_send_nothing(world, fw, monkeypatch, change):
    from jevdual.native import NativeBridge

    rows, resources, clicked = _native_song_links(world, monkeypatch)
    assert fw("start", "Open owned generated song", "--app", "Calculator")[0] == 0
    observes = [0]
    observe = NativeBridge.observe

    async def change_after_preflight(bridge, **kwargs):
        result = await observe(bridge, **kwargs)
        observes[0] += 1
        if observes[0] == 1:
            if change == "reordered_ids":
                rows[0]["element_index"], rows[1]["element_index"] = 921, 920
            elif change == "unreadable_peer":
                resources[50] = None
            elif change == "same_url":
                resources[50] = resources[20]
            else:
                resources[20] = "https://example.test/song/replaced"
        return result

    monkeypatch.setattr(NativeBridge, "observe", change_after_preflight)
    code, out, err = fw("do", "click", "920", "--no-judge")
    assert clicked == [] and any(word in out + err for word in ("refused", "target_changed", "target_ambiguous")), (code, out, err)


def test_native_link_resource_read_budget_keeps_unread_peers_ambiguous(world, fw, monkeypatch):
    urls = tuple(f"https://example.test/song/{index}" for index in range(65))
    _, _, clicked = _native_song_links(world, monkeypatch, urls)
    assert fw("start", "Open owned generated song", "--app", "Calculator")[0] == 0
    code, out, err = fw("do", "click", "920", "--no-judge")
    assert code == 4 and "target_ambiguous" in out + err, (out, err)
    assert clicked == []


def test_native_same_title_links_still_require_unique_label_or_numeric_selection(world, fw, monkeypatch):
    _, _, clicked = _native_song_links(world, monkeypatch)
    assert fw("start", "Open owned generated song", "--app", "Calculator")[0] == 0
    code, out, err = fw("do", "click", "Generated song", "--no-judge")
    assert code == 4 and "matches 2 elements" in out + err, (out, err)
    assert clicked == []


@pytest.mark.parametrize("false_equality", [False, True])
def test_native_type_bounded_preview_is_not_full_readback(world, fw, monkeypatch, false_equality):
    intended = "a" * 479 + "…" if false_equality else "a" * 600
    actual = "a" * 479 + "different unseen suffix" if false_equality else intended
    row = _native_styles_field(world, monkeypatch, actual_after=actual)
    assert fw("start", "Fill own song styles", "--app", "Calculator")[0] == 0
    code, out, err = fw("do", "type", "Styles", intended, "--no-judge")
    assert code == 0, err
    assert row["value"] == actual
    assert (row["value"] != intended) is false_equality
    receipt = _state(fw)["memory"][-1]
    assert "unverifiable" in receipt
    assert "value preview is truncated" in out
    assert "not the text typed" not in out
    saved = next(c for c in _state(fw)["last_candidates"] if c["label"] == "Styles")
    assert saved["value_truncated"] is True
    assert len(saved["value"]) == 480


def test_native_literal_ellipsis_is_not_projection_truncation(world, fw, monkeypatch):
    payload = "a" * 479 + "…"
    row = _native_styles_field(world, monkeypatch)
    assert fw("start", "Fill own song styles", "--app", "Calculator")[0] == 0
    code, _, err = fw("do", "type", "Styles", payload, "--no-judge")
    assert code == 0 and row["value"] == payload, err
    assert "confirmed" in _state(fw)["memory"][-1]
    saved = next(c for c in _state(fw)["last_candidates"] if c["label"] == "Styles")
    assert saved["value_truncated"] is False


@pytest.mark.parametrize("legacy", [False, True])
def test_native_append_receipt_does_not_compare_a_truncated_persisted_baseline(
    world, fw, monkeypatch, legacy
):
    from jevdual.session import SessionState

    row = _native_styles_field(world, monkeypatch, initial="a" * 600)
    assert fw("start", "Append own song note", "--app", "Calculator")[0] == 0
    state = SessionState.load(fw.session)
    state.pending = {
        "line": "append(Styles)", "op": "append", "mode": "native", "target_id": 910,
        "target_label": "Styles", "intended": "new ending", "dispatched": True,
        "driver_effect": "unverifiable", "secret": False,
    }
    if legacy:
        for saved in state.last_candidates:
            saved.pop("value_truncated", None)
    state.save()
    # The action's eventual fresh state is short: only the old baseline is bounded.
    row["value"] = "new ending"
    code, out, err = fw("look")
    assert code == 0, err
    assert "unverifiable" in _state(fw)["memory"][-1]
    assert "earlier value preview is truncated" in out
    assert world.tool_calls == []


def _foreground_styles_fixture(
    world, monkeypatch, *, idle=60, initial="", selection_change=False, focus_change=False, outcome=None
):
    from jevdual import ax, native, posture

    from tests.test_posture import Activity

    row = _native_styles_field(world, monkeypatch, initial=initial)
    row["in_web_content"] = True
    selection = [(0, 0)]
    monkeypatch.setattr(native, "_foreground_web_text_version", lambda: "0.46.0+footwork.5486b624.cleanup2.focus1",
                        raising=False)
    monkeypatch.setattr(posture, "MacActivity", lambda: Activity(idle=idle, fronts=(77,)))
    monkeypatch.setattr(ax, "raise_window", lambda *a: None)
    monkeypatch.setattr(ax, "focused_window_id", lambda pid: 40335)
    monkeypatch.setattr(ax, "resolve", lambda *a: "styles")
    monkeypatch.setattr(ax, "value", lambda el: row["value"])
    monkeypatch.setattr(ax, "selected_range", lambda el: selection[0], raising=False)

    async def call(name, encoded):
        args = json.loads(encoded)
        world.tool_calls.append((name, args))
        if name == "bring_to_front" and focus_change:
            row["label"] = "Replaced field"
        if name == "press_key":
            assert args["delivery_mode"] == "foreground" and args["modifiers"] == ["cmd"]
            selection[0] = (0, len(row["value"].encode("utf-16-le")) // 2)
            if selection_change:
                row["label"] = "Replaced field"
        if name == "type_text":
            assert args["delivery_mode"] == "foreground"
            assert args["window_id"] == 40335 and args["element_token"].endswith(":910")
            if isinstance(outcome, Exception):
                raise outcome
            if outcome is not None:
                return outcome
            row["value"] = args["text"]
        return SimpleNamespace(
            action=cd.ActionResult(
                effect=cd.ActionEffect.UNVERIFIABLE, route=cd.ActionRoute.SYNTHETIC_EVENTS,
                delivery=cd.ActionDelivery(mode=cd.ActionDeliveryMode.FOREGROUND, delivered_count=None),
                evidence=[], escalation=None, summary="foreground event post attempted", error=None,
                hint=None, next_call=None, fast_path=None,
            ), text="", is_error=False, error_code=None,
            structured_json=json.dumps({"path": "key_events_fg", "effect": "unverifiable"}),
        )

    monkeypatch.setattr(world, "call_tool", call)
    return row


def _foreground_popup_fixture(world, monkeypatch, *, idle=60, outcome=None, changed=False):
    row = _foreground_styles_fixture(world, monkeypatch, idle=idle, focus_change=changed)
    row.update(role="AXPopUpButton", label="More actions")
    attempts = []

    async def click(inp):
        attempts.append(inp)
        if inp.delivery_mode.name == "BACKGROUND":
            raise RuntimeError("Not opened: select_menu_would_raise_window; nothing was sent")
        if isinstance(outcome, Exception):
            raise outcome
        if outcome is not None:
            return outcome
        world.presses.append("More actions")
        return cd.ActionResult(
            effect=cd.ActionEffect.UNVERIFIABLE, route=cd.ActionRoute.ACCESSIBILITY,
            delivery=cd.ActionDelivery(mode=cd.ActionDeliveryMode.FOREGROUND, delivered_count=1),
            evidence=[], escalation=None, summary="menu press acknowledged", error=None,
            hint=None, next_call=None, fast_path=None,
        )

    monkeypatch.setattr(world, "click", click)
    return row, attempts


def test_explicit_foreground_native_click_uses_fresh_token_and_sdk_delivery(world, fw, monkeypatch):
    _, attempts = _foreground_popup_fixture(world, monkeypatch)
    assert fw("start", "Open owned song menu", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "click", "More actions", "--click-delivery", "foreground", "--authorize", "More actions")
    assert code == 0 and world.presses == ["More actions"], (out, err)
    click, = attempts
    assert click.delivery_mode.name == "FOREGROUND"
    assert click.position.element_token == f"s{world.n - 1:08x}:910"
    assert click.target.pid == 77 and click.target.window_id == 40335
    records = [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines()]
    receipt = next(record for record in records if record["kind"] == "receipt")
    assert receipt["action"]["click_delivery"] == "foreground"
    assert receipt["action"]["native_delivery"]["driver_delivery"] == "foreground"


def test_native_dropdown_background_refusal_has_no_automatic_foreground_retry(world, fw, monkeypatch):
    _, attempts = _foreground_popup_fixture(world, monkeypatch)
    assert fw("start", "Open owned song menu", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "click", "More actions", "--authorize", "More actions")
    assert code == 0 and "unverifiable" in out + err, (out, err)
    assert len(attempts) == 1 and attempts[0].delivery_mode.name == "BACKGROUND"
    assert not world.presses and world.tool_calls == []


@pytest.mark.parametrize("failure", ["human_active", "target_changed", "window_changed", "uncertain"])
def test_explicit_foreground_native_click_refuses_drift_and_never_retries(world, fw, monkeypatch, failure):
    from jevdual import ax

    _, attempts = _foreground_popup_fixture(world, monkeypatch, idle=0 if failure == "human_active" else 60,
                                           changed=failure == "target_changed",
                                           outcome=RuntimeError("click reply lost") if failure == "uncertain" else None)
    if failure == "window_changed":
        monkeypatch.setattr(ax, "focused_window_id", lambda pid: 999)
        monkeypatch.setattr(ax, "title_bar_point", lambda *args: None)
    assert fw("start", "Open owned song menu", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "click", "More actions", "--click-delivery", "foreground", "--authorize", "More actions")
    assert code == 0, (out, err)
    assert len(attempts) == (1 if failure == "uncertain" else 0)
    assert ("unverifiable" in out + err if failure == "uncertain"
            else any(word in out + err for word in ("refused", "not sent")))


@pytest.mark.parametrize("variant", ["background_only", "browser", "type", "no_judge", "web_text", "route", "file_selector", "nonmac"])
def test_explicit_foreground_native_click_unsupported_refuses_before_binding(world, fw, monkeypatch, variant):
    _foreground_popup_fixture(world, monkeypatch)
    assert fw("start", "Open owned song menu", "--app", "Calculator", "--mode",
              "background_only" if variant == "background_only" else "foreground_permitted")[0] == 0
    if variant == "browser":
        path = fw.session / "session.json"
        state = json.loads(path.read_text()); state["mode"] = "browser"; path.write_text(json.dumps(state))
    if variant == "nonmac":
        from jevdual import native
        monkeypatch.setattr(native, "sys", SimpleNamespace(platform="linux"))

    def forbidden(**kwargs):
        pytest.fail("unsupported foreground click must refuse before binding")

    monkeypatch.setattr(cd.CuaDriver, "create", forbidden)
    args = ["do", "type" if variant == "type" else "click",
            "file:/owned/song" if variant == "file_selector" else "More actions"]
    if variant == "type":
        args.append("signal")
    args.extend(["--click-delivery", "foreground"])
    if variant == "no_judge":
        args.append("--no-judge")
    if variant == "web_text":
        args.extend(["--web-text-delivery", "foreground"])
    if variant == "route":
        args.extend(["--route", "dom"])
    code, _, err = fw(*args)
    assert code == 2 and "foreground click" in err


def test_explicit_foreground_native_click_does_not_retry_sdk_refusal(world, fw, monkeypatch):
    refusal = cd.ActionResult(
        effect=cd.ActionEffect.REFUSED, route=cd.ActionRoute.ACCESSIBILITY,
        delivery=cd.ActionDelivery(mode=cd.ActionDeliveryMode.FOREGROUND, delivered_count=0),
        evidence=[], escalation=None, summary="fresh target refused", error=None,
        hint=None, next_call=None, fast_path=None,
    )
    _, attempts = _foreground_popup_fixture(world, monkeypatch, outcome=refusal)
    assert fw("start", "Open owned song menu", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "click", "More actions", "--click-delivery", "foreground", "--authorize", "More actions")
    assert code == 0 and len(attempts) == 1 and world.presses == [], (out, err)
    records = [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines()]
    receipt = next(record for record in records if record["kind"] == "receipt")
    assert receipt["dispatched"] is False


def test_explicit_foreground_native_click_retains_hidden_peer_ambiguity_after_activation(world, fw, monkeypatch):
    row, attempts = _foreground_popup_fixture(world, monkeypatch)
    original = world.call_tool

    async def add_peer(name, encoded):
        result = await original(name, encoded)
        if name == "bring_to_front":
            world.base["elements"].append({**row, "element_index": 911, "element_token": "initial:911"})
        return result

    monkeypatch.setattr(world, "call_tool", add_peer)
    assert fw("start", "Open owned song menu", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "click", "More actions", "--click-delivery", "foreground", "--authorize", "More actions")
    assert code == 0 and "target_ambiguous" in out + err, (out, err)
    assert not attempts


@pytest.mark.parametrize("initial", ["", "prior text"])
def test_explicit_foreground_web_type_preserves_target_and_readback(world, fw, monkeypatch, initial):
    row = _foreground_styles_fixture(world, monkeypatch, initial=initial)
    assert fw("start", "Edit owned styles", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground", "--authorize", "replace")
    assert code == 0 and row["value"] == "signal", (out, err)
    assert len([v for k, v in world.tool_calls if k == "type_text"]) == 1
    assert "confirmed" in _state(fw)["memory"][-1]
    assert all(v.get("delivery_mode") == "foreground" for k, v in world.tool_calls if k in ("type_text", "press_key"))
    records = [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines()]
    receipt = next(record for record in records if record["kind"] == "receipt")
    assert receipt["action"]["web_text_delivery"] == "foreground"
    assert receipt["action"]["native_delivery"]["driver_delivery"] == "foreground"


@pytest.mark.parametrize("idle", [0, 2.9])
def test_explicit_foreground_web_type_yields_to_human_input(world, fw, monkeypatch, idle):
    _foreground_styles_fixture(world, monkeypatch, idle=idle)
    assert fw("start", "Edit owned styles", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    _, out, err = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground")
    assert "human_active" in out + err
    assert world.tool_calls == []


@pytest.mark.parametrize("failure", ["focus_changed", "selection_changed", "uncertain"])
def test_explicit_foreground_web_type_never_retries_after_selection_or_delivery(
    world, fw, monkeypatch, failure
):
    _foreground_styles_fixture(world, monkeypatch, initial="prior text",
                               selection_change=failure == "selection_changed",
                               focus_change=failure == "focus_changed",
                               outcome=RuntimeError("post reply lost") if failure == "uncertain" else None)
    assert fw("start", "Edit owned styles", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground", "--authorize", "replace")
    types = [v for k, v in world.tool_calls if k == "type_text"]
    assert len(types) == (1 if failure == "uncertain" else 0), (code, out, err)
    assert ("refused" if failure == "focus_changed" else "unverifiable") in out + err


def test_explicit_foreground_web_type_requires_independent_complete_selection(world, fw, monkeypatch):
    from jevdual import ax

    _foreground_styles_fixture(world, monkeypatch, initial="prior text")
    monkeypatch.setattr(ax, "selected_range", lambda el: (1, 1))
    assert fw("start", "Edit owned styles", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground", "--authorize", "replace")
    assert code == 0 and "selection_unqualified" in out + err
    assert not [value for name, value in world.tool_calls if name == "type_text"]


def _foreground_selection_fixture(world, monkeypatch, *, initial="\n", selection=(0, 0),
                                  selected_text="", actual_after=None, outcome=None):
    from jevdual import ax

    row = _foreground_styles_fixture(world, monkeypatch, initial=initial, outcome=outcome)
    monkeypatch.setattr(ax, "selected_range", lambda element: selection)
    monkeypatch.setattr(ax, "selected_text", lambda element: selected_text, raising=False)
    monkeypatch.setattr(ax, "focus_text_field_ack", lambda element: None, raising=False)
    monkeypatch.setattr(ax, "focused_element_matches", lambda pid, window_id, element: True, raising=False)
    original_call = world.call_tool

    async def call(name, encoded):
        if name == "press_key":
            pytest.fail("explicit range edits must not change the selection")
        before = row["value"]
        result = await original_call(name, encoded)
        if name == "type_text" and outcome is None:
            args = json.loads(encoded)
            raw = before.encode("utf-16-le")
            start, length = selection
            expected = (raw[:start * 2].decode("utf-16-le") + args["text"]
                        + raw[(start + length) * 2:].decode("utf-16-le"))
            row["value"] = expected if actual_after is None else actual_after
        return result

    monkeypatch.setattr(world, "call_tool", call)
    return row


@pytest.mark.parametrize("failure", [None, "setter_refused", "focus_unproven", "wrong_window",
                                     "value_changed", "identity_changed", "selection_changed", "focus_stolen"])
def test_foreground_range_prepares_focus_and_independently_requalifies(world, fw, monkeypatch, failure):
    from jevdual import ax

    row = _foreground_selection_fixture(world, monkeypatch)
    focused = [False]
    writes, checks = [], []

    def focus(element):
        writes.append(element)
        if failure == "setter_refused":
            raise ax.AXError("focus_refused", "AXFocused setter refused")
        focused[0] = True
        if failure == "value_changed":
            row["value"] += " "
        if failure == "identity_changed":
            row["label"] = "Different field"

    def matches(pid, window_id, element):
        checks.append((pid, window_id, element))
        if failure in ("focus_unproven", "wrong_window"):
            return False
        return focused[0] and not (failure == "focus_stolen" and len(checks) > 1)

    def selected_text(element):
        if not focused[0]:
            raise ax.AXError("selection_unreadable", "unfocused field exposes no selected text")
        return ""

    monkeypatch.setattr(ax, "focus_text_field_ack", focus, raising=False)
    monkeypatch.setattr(ax, "focused_element_matches", matches, raising=False)
    monkeypatch.setattr(ax, "selected_text", selected_text)
    monkeypatch.setattr(ax, "selected_range", lambda element: (1, 0) if focused[0] and failure == "selection_changed" else (0, 0))
    assert fw("start", "Edit owned styles selection", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground",
                        "--web-text-range", "0:0", "--authorize", "replace")
    assert code == 0 and writes == ["styles"], (out, err)
    types = [args for name, args in world.tool_calls if name == "type_text"]
    assert len(types) == (0 if failure else 1)
    assert not [args for name, args in world.tool_calls if name == "press_key"]
    records = [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines()]
    receipt = next(record for record in records if record["kind"] == "receipt")
    proof = receipt["action"]["native_readback"]
    assert proof["focus_preparation"]["attempted"] is True
    if failure:
        assert receipt["dispatched"] is True  # preparation attempt is not proven no input
        assert receipt["effect"] == "unverifiable"
        assert proof["text_dispatch"]["delivered_chars"] == 0
        assert proof["text_dispatch"]["dispatched"] is False
    else:
        assert row["value"] == "signal\n" and proof["focus_preparation"]["confirmed"] is True


@pytest.mark.parametrize(("initial", "selection", "selected_text", "expected"), [
    ("\n", (0, 0), "", "signal\n"),
    ("ab😀cd\n", (2, 2), "😀", "absignalcd\n"),
    ("a" * 600 + "\n", (600, 0), "", "a" * 600 + "signal\n"),
])
def test_foreground_web_range_preserves_exact_prefix_suffix(
    world, fw, monkeypatch, initial, selection, selected_text, expected
):
    row = _foreground_selection_fixture(world, monkeypatch, initial=initial, selection=selection,
                                        selected_text=selected_text)
    assert fw("start", "Edit owned styles selection", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground",
                        "--web-text-range", f"{selection[0]}:{selection[1]}", "--authorize", "replace")
    assert code == 0 and row["value"] == expected, (out, err)
    types = [args for name, args in world.tool_calls if name == "type_text"]
    assert len(types) == 1 and types[0]["delay_ms"] > 0
    assert "confirmed" in _state(fw)["memory"][-1]
    records = [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines()]
    receipt = next(record for record in records if record["kind"] == "receipt")
    assert receipt["action"]["web_text_range"] == list(selection)
    assert receipt["action"]["field_readback"]["expected_value"] == expected


@pytest.mark.parametrize("failure", ["wrong_range", "wrong_text", "unreadable_text", "read_error", "split_surrogate",
                                     "outside_value", "changed_value", "changed_identity"])
def test_foreground_web_range_requires_independent_exact_selection(world, fw, monkeypatch, failure):
    from jevdual import ax

    initial = "ab😀cd\n" if failure == "split_surrogate" else "prior\n"
    selection = (3, 0) if failure == "split_surrogate" else (0, 0)
    row = _foreground_selection_fixture(world, monkeypatch, initial=initial, selection=selection)
    if failure == "wrong_range":
        monkeypatch.setattr(ax, "selected_range", lambda element: (1, 0))
    if failure in ("wrong_text", "unreadable_text"):
        monkeypatch.setattr(ax, "selected_text", lambda element: "unselected" if failure == "wrong_text" else None)
    if failure == "read_error":
        def unreadable(element):
            raise ax.AXError("selection_unreadable", "selection unavailable")
        monkeypatch.setattr(ax, "selected_text", unreadable)
    if failure in ("changed_identity", "changed_value"):
        original = world.call_tool

        async def change(name, encoded):
            result = await original(name, encoded)
            if name == "bring_to_front":
                if failure == "changed_identity":
                    row["label"] = "Different field"
                else:
                    monkeypatch.setattr(ax, "value", lambda element: "different exact value")
            return result

        monkeypatch.setattr(world, "call_tool", change)
    assert fw("start", "Edit owned styles selection", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    requested = "90:0" if failure == "outside_value" else f"{selection[0]}:{selection[1]}"
    code, out, err = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground",
                        "--web-text-range", requested, "--authorize", "replace")
    prepared = failure in ("wrong_range", "wrong_text", "unreadable_text", "read_error")
    assert code == 0 and ("unverifiable" if prepared else "refused") in out + err, (out, err)
    if prepared:
        records = [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines()]
        receipt = next(record for record in records if record["kind"] == "receipt")
        assert receipt["action"]["native_readback"]["text_dispatch"]["delivered_chars"] == 0
    assert not [args for name, args in world.tool_calls if name in ("press_key", "type_text")]


@pytest.mark.parametrize("actual", ["signal", "signal\n\n", "other\n"])
def test_foreground_web_range_receipt_compares_exact_full_value(world, fw, monkeypatch, actual):
    _foreground_selection_fixture(world, monkeypatch, actual_after=actual)
    assert fw("start", "Edit owned styles selection", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground",
                        "--web-text-range", "0:0", "--authorize", "replace")
    assert code == 0, (out, err)
    assert "confirmed" not in _state(fw)["memory"][-1]
    assert len([args for name, args in world.tool_calls if name == "type_text"]) == 1


def test_foreground_web_range_never_retries_uncertain_input(world, fw, monkeypatch):
    _foreground_selection_fixture(world, monkeypatch, outcome=RuntimeError("reply lost"))
    assert fw("start", "Edit owned styles selection", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground",
                        "--web-text-range", "0:0", "--authorize", "replace")
    assert code == 0 and "unverifiable" in out + err, (out, err)
    assert len([args for name, args in world.tool_calls if name == "type_text"]) == 1
    records = [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines()]
    receipt = next(record for record in records if record["kind"] == "receipt")
    assert receipt["action"]["native_readback"]["focus_preparation"]["confirmed"] is True
    assert "text_dispatch" not in receipt["action"]["native_readback"]  # never invent zero after uncertain text


def test_foreground_web_range_durable_provenance_and_replay(world, fw, monkeypatch, tmp_path):
    from jevdual.session import SessionState

    _foreground_selection_fixture(world, monkeypatch)
    _durable_start(fw, monkeypatch, tmp_path)
    state = SessionState.load(fw.session)
    state.posture = "foreground_permitted"
    state.save()
    words = ["do", "type", "Styles", "signal", "--web-text-delivery", "foreground",
             "--web-text-range", "0:0", "--authorize", "replace", "--token", "selection-once"]
    code, out, err = fw(*words)
    assert code == 0, (out, err)
    records = [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines()]
    receipt = next(record for record in records if record["kind"] == "receipt")
    fact, = receipt["structured_evidence"]["facts"]
    assert fact["parameters"]["source"] == "native.foreground_web_selection_readback"
    assert fact["values"] == ["signal\n"] and fact["limits"] == []
    assert fw(*words)[0] == 0
    different = words.copy()
    different[different.index("0:0")] = "1:0"
    code, out, err = fw(*different)
    assert code != 0 and "conflict" in out + err, (out, err)
    assert len([args for name, args in world.tool_calls if name == "type_text"]) == 1


def test_foreground_web_range_secret_readback_is_redacted(world, fw, monkeypatch):
    _foreground_selection_fixture(world, monkeypatch)
    secret = "synthetic-private-selection-value"
    monkeypatch.setenv("FOOTWORK_SECRET_SELECTION", secret)
    assert fw("start", "Edit owned styles selection", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "type", "Styles", "{SELECTION}", "--web-text-delivery", "foreground",
                        "--web-text-range", "0:0", "--authorize", "replace")
    assert code == 0 and secret not in out + err, (out, err)
    for name in ("session.json", "session.jsonl"):
        assert secret not in (fw.session / name).read_text()
    assert "confirmed" not in _state(fw)["memory"][-1]


@pytest.mark.parametrize("failure", ["unreadable", "changed_identity", "stale_confirmation", "sdk_fallback"])
def test_foreground_web_range_requires_post_input_and_receipt_time_readback(world, fw, monkeypatch, failure):
    from jevdual import ax

    row = _foreground_selection_fixture(world, monkeypatch)
    original_call = world.call_tool

    async def call(name, encoded):
        result = await original_call(name, encoded)
        if name == "type_text":
            if failure == "unreadable":
                def unavailable(element):
                    raise ax.AXError("no_value", "field readback unavailable")
                monkeypatch.setattr(ax, "value", unavailable)
            elif failure == "changed_identity":
                row["label"] = "Different field"
            else:
                reads = [0]

                def delayed_change(element):
                    reads[0] += 1
                    # Immediate postcondition: supplement + independent direct read.
                    # Receipt-time observation then sees an external later edit.
                    if reads[0] <= 2:
                        return row["value"]
                    if failure == "sdk_fallback":
                        raise ax.AXError("no_value", "only SDK projection remains readable")
                    return "later edit\n"

                monkeypatch.setattr(ax, "value", delayed_change)
        return result

    monkeypatch.setattr(world, "call_tool", call)
    assert fw("start", "Edit owned styles selection", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground",
                        "--web-text-range", "0:0", "--authorize", "replace")
    assert code == 0 and "unverifiable" in _state(fw)["memory"][-1], (out, err)
    assert len([args for name, args in world.tool_calls if name == "type_text"]) == 1


def test_foreground_web_range_does_not_relax_whole_field_lf_guard(world, fw, monkeypatch):
    _foreground_selection_fixture(world, monkeypatch)
    # The whole-field path still tries Select All, then rejects the LF not being selected.
    original = world.call_tool

    async def call(name, encoded):
        if name == "press_key":
            world.tool_calls.append((name, json.loads(encoded)))
            return SimpleNamespace(text="selection attempted", is_error=False, error_code=None,
                                   action=None, structured_json=None)
        return await original(name, encoded)

    monkeypatch.setattr(world, "call_tool", call)
    assert fw("start", "Edit owned styles selection", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground", "--authorize", "replace")
    assert code == 0 and "selection_unqualified" in out + err, (out, err)
    assert not [args for name, args in world.tool_calls if name == "type_text"]


@pytest.mark.parametrize("range_text", ["-1:0", "0:-1", "0", "0:1:2", "65537:0", "65536:1", "a:0", ""])
def test_foreground_web_range_invalid_bounds_refuse_before_binding(world, fw, monkeypatch, range_text):
    _foreground_selection_fixture(world, monkeypatch)
    assert fw("start", "Edit owned styles selection", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0

    def forbidden(**kwargs):
        pytest.fail("invalid selected range must refuse before binding")

    monkeypatch.setattr(cd.CuaDriver, "create", forbidden)
    code, _, _ = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground",
                    "--web-text-range", range_text)
    assert code == 2


@pytest.mark.parametrize("variant", ["missing_foreground", "background_only", "append", "browser", "no_judge"])
def test_foreground_web_range_unsupported_refuses_before_binding(world, fw, monkeypatch, variant):
    _foreground_selection_fixture(world, monkeypatch)
    assert fw("start", "Edit owned styles selection", "--app", "Calculator", "--mode",
              "background_only" if variant == "background_only" else "foreground_permitted")[0] == 0
    if variant == "browser":
        path = fw.session / "session.json"
        state = json.loads(path.read_text()); state["mode"] = "browser"; path.write_text(json.dumps(state))

    def forbidden(**kwargs):
        pytest.fail("unsupported selected range must refuse before binding")

    monkeypatch.setattr(cd.CuaDriver, "create", forbidden)
    args = ["do", "append" if variant == "append" else "type", "Styles", "signal", "--web-text-range", "0:0"]
    if variant != "missing_foreground":
        args.extend(["--web-text-delivery", "foreground"])
    if variant == "no_judge":
        args.append("--no-judge")
    assert fw(*args)[0] == 2


@pytest.mark.parametrize("variant", [
    "background_only", "append", "click", "browser", "old_runtime", "no_judge", "file_selector", "browser_route",
])
def test_explicit_foreground_web_type_rejects_unsupported_before_binding(world, fw, monkeypatch, variant):
    from jevdual import native

    _foreground_styles_fixture(world, monkeypatch)
    posture = "background_only" if variant == "background_only" else "foreground_permitted"
    assert fw("start", "Edit owned styles", "--app", "Calculator", "--mode", posture)[0] == 0
    if variant == "browser":
        path = fw.session / "session.json"
        raw = json.loads(path.read_text()); raw["mode"] = "browser"; path.write_text(json.dumps(raw))
    if variant == "old_runtime":
        monkeypatch.setattr(native, "_foreground_web_text_version", lambda: "0.46.0+footwork.5486b624.cleanup2")

    def forbidden(**kwargs):
        pytest.fail("unsupported foreground option must refuse before driver binding")

    monkeypatch.setattr(cd.CuaDriver, "create", forbidden)
    operation = variant if variant in ("append", "click") else "type"
    target = "file:/owned/name.txt" if variant == "file_selector" else "Styles"
    args = ["do", operation, target, "signal", "--web-text-delivery", "foreground"]
    if variant == "no_judge":
        args.append("--no-judge")
    if variant == "browser_route":
        args.extend(["--route", "dom"])
    code, _, err = fw(*args)
    assert code == 2 and "foreground web text" in err


@pytest.mark.parametrize("initial", ["", "prior text"])
def test_explicit_foreground_focus_refusal_retains_no_text_evidence(world, fw, monkeypatch, initial):
    refused = SimpleNamespace(
        action=cd.ActionResult(
            effect=cd.ActionEffect.REFUSED, route=cd.ActionRoute.SYNTHETIC_EVENTS, delivery=None,
            evidence=[], escalation=None, summary="no text dispatched", error=None,
            hint=None, next_call=None, fast_path=None,
        ), text="no text dispatched", is_error=True, error_code="target_focus_unconfirmed",
        structured_json=json.dumps({
            "code": "target_focus_unconfirmed", "effect": "refused", "dispatched": False, "delivered_chars": 0,
        }),
    )
    _foreground_styles_fixture(world, monkeypatch, initial=initial, outcome=refused)
    assert fw("start", "Edit owned styles", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground", "--authorize", "replace")
    assert code == 0, (out, err)
    assert len([v for k, v in world.tool_calls if k == "type_text"]) == 1
    records = [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines()]
    receipt = next(record for record in records if record["kind"] == "receipt")
    proof = receipt["action"]["native_readback"]["text_dispatch"]
    assert proof["dispatched"] is False and proof["delivered_chars"] == 0
    assert receipt["dispatched"] is bool(initial)  # replacement selection is earlier input


def test_explicit_foreground_web_type_refuses_unreadable_nonempty_field(world, fw, monkeypatch):
    from jevdual import ax

    row = _foreground_styles_fixture(world, monkeypatch, initial="unreadable existing text")
    row["value"] = None

    def unreadable(element):
        raise ax.AXError("no_value", "the nonempty field does not expose its value")

    monkeypatch.setattr(ax, "value", unreadable)
    assert fw("start", "Edit owned styles", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground")
    assert code == 0 and "field_value_unreadable" in out + err
    assert not [value for name, value in world.tool_calls if name in ("type_text", "press_key")]


def test_explicit_foreground_web_type_partial_reply_uses_no_batched_tail_retry(world, fw, monkeypatch):
    # The pinned SDK's incomplete-ancestry case can enter its native-tail branch
    # only when delay_ms==0; explicit positive pacing must disable that branch.
    partial = SimpleNamespace(
        action=cd.ActionResult(
            effect=cd.ActionEffect.PARTIAL, route=cd.ActionRoute.SYNTHETIC_EVENTS,
            delivery=cd.ActionDelivery(mode=cd.ActionDeliveryMode.FOREGROUND, delivered_count=1),
            evidence=[], escalation=None, summary="one character observed, ancestry incomplete", error=None,
            hint=None, next_call=None, fast_path=None,
        ), text="type_text incomplete", is_error=True, error_code="type_text_incomplete",
        structured_json=json.dumps({"code": "type_text_incomplete", "effect": "partial", "delivered_chars": 1}),
    )
    _foreground_styles_fixture(world, monkeypatch, outcome=partial)
    assert fw("start", "Edit owned styles", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground")
    types = [value for name, value in world.tool_calls if name == "type_text"]
    assert code == 0 and "unverifiable" in out + err
    assert len(types) == 1 and types[0].get("delay_ms", 0) > 0


@pytest.mark.parametrize("representation", ["tuple", "cfrange"])
def test_foreground_web_replacement_decodes_real_range_representations(world, fw, monkeypatch, representation):
    import sys

    from jevdual import ax

    decode = ax.selected_range
    prior = "prior text"
    _foreground_styles_fixture(world, monkeypatch, initial=prior)
    monkeypatch.setattr(ax, "selected_range", decode)
    value = (0, len(prior)) if representation == "tuple" else SimpleNamespace(location=0, length=len(prior))
    monkeypatch.setattr(ax, "_attr", lambda element, attribute: "encoded-range" if attribute == "AXSelectedTextRange" else None)
    monkeypatch.setitem(sys.modules, "ApplicationServices", SimpleNamespace(
        AXValueGetValue=lambda raw, kind, out: (True, value), kAXValueCFRangeType=4,
    ))
    assert fw("start", "Edit owned styles", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground", "--authorize", "replace")
    assert code == 0 and "confirmed" in _state(fw)["memory"][-1], (out, err)
    assert len([value for name, value in world.tool_calls if name == "press_key"]) == 1
    assert len([value for name, value in world.tool_calls if name == "type_text"]) == 1


@pytest.mark.parametrize("value", [
    (0,), (0, 10, 2), (-1, 10), (0, -1), (False, 10), (0, 10.0), ("0", 10),
    SimpleNamespace(location=0), SimpleNamespace(location=0, length=-1), None,
])
def test_foreground_web_replacement_rejects_malformed_range_before_text(world, fw, monkeypatch, value):
    import sys

    from jevdual import ax

    decode = ax.selected_range
    _foreground_styles_fixture(world, monkeypatch, initial="prior text")
    monkeypatch.setattr(ax, "selected_range", decode)
    monkeypatch.setattr(ax, "_attr", lambda element, attribute: "encoded-range" if attribute == "AXSelectedTextRange" else None)
    monkeypatch.setitem(sys.modules, "ApplicationServices", SimpleNamespace(
        AXValueGetValue=lambda raw, kind, out: (True, value), kAXValueCFRangeType=4,
    ))
    assert fw("start", "Edit owned styles", "--app", "Calculator", "--mode", "foreground_permitted")[0] == 0
    code, out, err = fw("do", "type", "Styles", "signal", "--web-text-delivery", "foreground", "--authorize", "replace")
    assert code == 0 and "selection_unreadable" in out + err
    assert len([value for name, value in world.tool_calls if name == "press_key"]) == 1
    assert not [value for name, value in world.tool_calls if name == "type_text"]
    assert "unverifiable" in out + err  # selection was attempted; no retroactive no-input claim


@pytest.mark.parametrize("command", ["start", "look"])
@pytest.mark.parametrize("permission", ["not_granted", "unavailable"])
def test_denied_accessibility_is_an_explicit_observation_failure(world, fw, monkeypatch, command, permission):
    from jevdual import native

    if command == "look":
        assert fw("start", "Observe Calculator", "--app", "Calculator")[0] == 0
    monkeypatch.setattr(native, "accessibility_status", lambda: permission)
    before = world.n
    args = ("start", "Observe Calculator", "--app", "Calculator") if command == "start" else ("look",)
    code, out, err = fw(*args)
    reason = "accessibility_not_granted" if permission == "not_granted" else "accessibility_unavailable"
    assert code == 7 and reason in err
    assert "Privacy & Security" in err and "0 elements" not in out
    assert world.n == before and world.presses == []


def test_denied_native_start_preserves_existing_session(world, fw, monkeypatch):
    assert fw("start", "Observe Calculator", "--app", "Calculator")[0] == 0
    saved = (fw.session / "session.json").read_bytes()
    monkeypatch.setattr("jevdual.native.accessibility_status", lambda: "not_granted")
    code, _, err = fw("start", "Another task", "--app", "Calculator")
    assert code == 7 and "accessibility_not_granted" in err
    assert (fw.session / "session.json").read_bytes() == saved


def test_look_after_failed_start_reports_missing_initialized_session(world, fw, monkeypatch):
    async def capture_failure(inp):
        raise RuntimeError("capture_binding_failed")

    monkeypatch.setattr(world, "get_window_state", capture_failure)
    assert fw("start", "Observe Calculator", "--app", "Calculator")[0] == 7
    code, _, err = fw("look")
    assert code == 7 and "session_not_found" in err
    assert "start must complete successfully" in err
    assert "FileNotFoundError" not in err and "Traceback" not in err


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


def test_the_second_of_two_same_label_switches_is_observed_and_its_change_is_named(world, fw):
    from jevdual.effects import diff
    from jevdual.session import SessionState

    # 2026-10-28 (notebook CTL3): native pruning kept only the first of two "Enabled" switches, so
    # the second could not be chosen and a change to it was invisible to the effect diff
    world.toggles = {200: ["Enabled", "1"], 201: ["Enabled", "0"]}
    _, out, _ = fw("start", "Turn on the second switch", "--app", "Calculator")
    rows = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("[") and "'Enabled'" in ln]
    assert [int(r[1 : r.index("]")]) for r in rows] == [200, 201]
    assert "checked=True" in rows[0] and "checked=False" in rows[1]
    before = SessionState.load(fw.session).last_menu()
    # Both remain evidence, but native actions now refuse their unresolved backing identity.
    # An external change must still be visible to the observation diff.
    world.toggles[201][1] = "1"
    code, out, err = fw("look")
    assert code == 0, err
    assert world.toggles[201][1] == "1" and world.toggles[200][1] == "1"
    after = SessionState.load(fw.session).last_menu()
    assert "'Enabled' checked False -> True" in diff(before, after).summary
    assert world.presses == []


def test_a_reload_with_unchanged_switches_is_not_progress(world, fw):
    # the saved baseline must carry every state the fresh observation reports, or an untouched
    # control reads as changed after the session is reloaded by the next command
    world.toggles = {200: ["Enabled", "1"], 201: ["Mixed", "2"]}
    fw("start", "Look twice", "--app", "Calculator")
    st = _state(fw)
    saved = {c["label"]: c for c in st["last_candidates"] if c["label"] in ("Enabled", "Mixed")}
    assert saved["Enabled"]["checked"] is True and saved["Mixed"]["checked"] == "mixed"
    _, out, _ = fw("look")
    assert "the window changed since" not in out


def test_a_shifted_window_refuses_the_wrong_one_of_two_same_label_switches(world, fw):
    # review of 65bb991: with both "Enabled" switches offered, an id that still says "Enabled" can name
    # the other one after a switch is inserted above them; the label check alone dispatched it
    world.toggles = {200: ["Enabled", "0"], 201: ["Enabled", "0"]}
    fw("start", "Turn on the second switch", "--app", "Calculator")
    world.toggles = {200: ["Wi-Fi", "1"], 201: ["Enabled", "0"], 202: ["Enabled", "0"]}
    code, _, err = fw("do", "click", "201", "--no-judge")
    assert code == 4 and "1 of 2 now; it was 2 of 2" in err and "Nothing dispatched" in err
    assert world.presses == [] and [v for _, v in world.toggles.values()] == ["1", "0", "0"]


@pytest.mark.parametrize("change", ["reorder", "replace", "unchanged"])
def test_indistinguishable_native_switches_never_authorize_a_backing_setting_by_position(world, fw, change):
    from tests.fixtures.native_world import ToggleControl

    first, selected = ToggleControl("setting-A"), ToggleControl("setting-B")
    world.backed_toggles = {200: first, 201: selected}
    code, out, err = fw("start", "Enable setting B", "--app", "Calculator")
    assert code == 0, err
    assert {200, 201} <= {row["id"] for row in _state(fw)["last_candidates"]}
    if change == "reorder":
        world.backed_toggles = {200: selected, 201: first}
    elif change == "replace":
        world.backed_toggles[201] = ToggleControl("replacement-C")

    code, out, err = fw("do", "click", "201", "--no-judge")
    # The effect oracle names the backing setting, independent of its label, index and token.
    # No field in the public snapshot distinguishes these controls, even without a reorder.
    assert world.toggle_writes == [], (change, code, out, err, world.toggle_writes)
    assert first.value == selected.value == "0"
    assert code == 4 and "target_ambiguous" in err, (out, err)
    records = [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines()]
    assert not [record for record in records if record["kind"] == "do"]


def test_a_distinct_native_switch_still_changes_the_selected_backing_setting(world, fw):
    from tests.fixtures.native_world import ToggleControl

    first = ToggleControl("setting-A", label="Enable A")
    selected = ToggleControl("setting-B", label="Enable B")
    world.backed_toggles = {200: first, 201: selected}
    fw("start", "Enable B", "--app", "Calculator")
    code, out, err = fw("do", "click", "201", "--no-judge")
    assert code == 0, (out, err)
    assert world.toggle_writes == ["setting-B"]
    assert first.value == "0" and selected.value == "1"


def test_pruning_duplicate_native_switches_does_not_make_the_retained_one_unique(world, fw):
    from tests.fixtures.native_world import ToggleControl

    world.backed_toggles = {200 + i: ToggleControl(f"setting-{i}") for i in range(5)}
    fw("start", "Enable the first setting", "--app", "Calculator")
    offered = {row["id"] for row in _state(fw)["last_candidates"]}
    assert 200 in offered and not offered.intersection({201, 202, 203, 204})
    code, out, err = fw("do", "click", "200", "--no-judge")
    assert world.toggle_writes == [], (code, out, err, world.toggle_writes)
    assert code == 4 and "target_ambiguous" in err, (out, err)
    records = [json.loads(line) for line in (fw.session / "session.jsonl").read_text().splitlines()]
    assert not [record for record in records if record["kind"] == "do"]


def test_a_native_switch_becoming_ambiguous_during_revalidation_sends_nothing(world, fw, monkeypatch):
    from tests.fixtures.native_world import ToggleControl

    selected = ToggleControl("setting-B")
    world.backed_toggles = {201: selected}
    fw("start", "Enable setting B", "--app", "Calculator")
    next_observation = world.n + 1
    observe = world.get_window_state

    async def add_sibling_after_the_command_observes(inp):
        snapshot = await observe(inp)
        if world.n == next_observation:
            world.backed_toggles[200] = ToggleControl("new-setting-A")
        return snapshot

    monkeypatch.setattr(world, "get_window_state", add_sibling_after_the_command_observes)
    code, out, err = fw("do", "click", "201", "--no-judge")
    assert world.toggle_writes == [] and selected.value == "0", (code, out, err)
    assert "target_ambiguous" in out + err


def test_a_native_switch_peer_disappearing_does_not_rebind_the_selected_setting(world, fw):
    from tests.fixtures.native_world import ToggleControl

    first, selected = ToggleControl("setting-A"), ToggleControl("setting-B")
    world.backed_toggles = {200: first, 201: selected}
    fw("start", "Enable setting B", "--app", "Calculator")
    world.backed_toggles = {201: first}
    code, out, err = fw("do", "click", "201", "--no-judge")
    assert code == 4 and "Nothing dispatched" in err, (out, err)
    assert world.toggle_writes == [] and first.value == selected.value == "0"


def test_a_previously_pruned_native_lookalike_cannot_replace_the_selected_backing_button(world, fw):
    from tests.fixtures.native_world import ToggleControl

    selected = ToggleControl("setting-A", label="Enable", role="AXButton")
    lookalike = ToggleControl("setting-B", label="Enable", role="AXButton")
    world.backed_toggles = {200: selected, 201: lookalike}
    fw("start", "Enable setting A", "--app", "Calculator")
    offered = {row["id"] for row in _state(fw)["last_candidates"]}
    assert 200 in offered and 201 not in offered
    # The next command sees a singleton with the same public fields and index. Only the previous
    # observation knew that a pruned lookalike existed, so that uncertainty must survive save/load.
    world.backed_toggles = {200: lookalike}
    code, out, err = fw("do", "click", "200", "--no-judge")
    assert world.toggle_writes == [], (code, out, err, world.toggle_writes)
    assert selected.value == lookalike.value == "0"
    assert "target_ambiguous" in out + err


def test_a_legacy_native_baseline_requires_fresh_selection_before_numeric_input(world, fw):
    from tests.fixtures.native_world import ToggleControl

    selected = ToggleControl("setting-B", label="Enable B")
    world.backed_toggles = {201: selected}
    fw("start", "Enable B", "--app", "Calculator")
    old_state = _state(fw)
    old_state.pop("last_native_ambiguous", None)
    (fw.session / "session.json").write_text(json.dumps(old_state))
    code, out, err = fw("do", "click", "201", "--no-judge")
    assert code == 4 and "target_ambiguous" in err, (out, err)
    assert world.toggle_writes == [] and selected.value == "0"
    assert fw("look")[0] == 0
    code, out, err = fw("do", "click", "201", "--no-judge")
    assert code == 0 and world.toggle_writes == ["setting-B"], (out, err)


def _native_form_element(index, role, label=None, parent=0, **kwargs):
    return {
        "element_index": index, "role": role, "label": label,
        "parent_index": parent, "enabled": True, "actions": ["AXPress"],
        "frame": {"x": float(index), "y": 400.0, "w": 100.0, "h": 20.0},
        **kwargs,
    }


def _install_domain_rows(world, monkeypatch):
    rows = [
        _native_form_element(300, "AXRow", "example.test"),
        _native_form_element(301, "AXLink", "MANAGE", parent=300),
        _native_form_element(302, "AXRow", "other.test"),
        _native_form_element(303, "AXLink", "MANAGE", parent=302),
    ]
    world.base["elements"] += rows
    backing = {301: "domain-A", 303: "domain-B"}
    writes = []
    click = world.click

    async def click_domain(inp):
        index = int(inp.position.element_token.split(":")[1])
        writes.append(backing[index])
        return await click(inp)

    monkeypatch.setattr(world, "click", click_domain)

    def reorder():
        rows[0]["label"], rows[2]["label"] = rows[2]["label"], rows[0]["label"]
        backing[301], backing[303] = backing[303], backing[301]

    return rows, writes, reorder


def test_native_form_repeated_row_links_keep_distinct_domain_sections(world, fw, monkeypatch):
    _, writes, _ = _install_domain_rows(world, monkeypatch)
    code, out, err = fw("start", "Manage example.test", "--app", "Calculator")
    assert code == 0, (out, err)
    rows = {c["id"]: c for c in _state(fw)["last_candidates"]}
    assert rows[301]["section"] == "example.test"
    assert rows[303]["section"] == "other.test"
    code, out, err = fw("do", "click", "301", "--no-judge")
    assert code == 0 and writes == ["domain-A"], (out, err)


@pytest.mark.parametrize("when", ["before_command", "final_live"])
def test_native_form_reordered_rows_never_dispatch_to_another_domain(world, fw, monkeypatch, when):
    _, writes, reorder = _install_domain_rows(world, monkeypatch)
    assert fw("start", "Manage example.test", "--app", "Calculator")[0] == 0
    if when == "before_command":
        reorder()
    else:
        first = world.n + 1
        observe = world.get_window_state

        async def reorder_after_command_snapshot(inp):
            snapshot = await observe(inp)
            if world.n == first:
                reorder()
            return snapshot

        monkeypatch.setattr(world, "get_window_state", reorder_after_command_snapshot)
    code, out, err = fw("do", "click", "301", "--no-judge")
    if when == "before_command":
        assert code == 4 and writes == [], (out, err, writes)
    else:
        assert code == 0 and writes == ["domain-A"], (out, err, writes)


@pytest.mark.parametrize("unreadable_peer", [False, True])
def test_native_form_collapsed_groups_require_context_for_every_peer(world, fw, monkeypatch, unreadable_peer):
    from jevdual import native

    rows, writes, _ = _install_domain_rows(world, monkeypatch)
    # The pinned Driver drops AXGroup containers. Only the actual AX parent chain can supply
    # these explicitly named group scopes; no domain identity is invented from adjacent text.
    world.base["elements"] = [row for row in world.base["elements"] if row not in (rows[0], rows[2])]
    for row in (rows[1], rows[3]):
        row.update(parent_index=0, in_web_content=True)

    def section(element):
        if element == 303 and unreadable_peer:
            raise RuntimeError("unreadable AX parent")
        return {301: "example.test", 303: "other.test"}[element]

    ax = SimpleNamespace(
        Frame=lambda x, y, w, h: (x, y, w, h),
        resolve=lambda pid, wid, role, frame: int(frame[0]), semantic_section=section,
    )
    monkeypatch.setattr(native.NativeBridge, "ax", property(lambda _: ax))
    assert fw("start", "Manage example.test", "--app", "Calculator")[0] == 0
    code, out, err = fw("do", "click", "301", "--no-judge")
    if unreadable_peer:
        assert code == 4 and "target_ambiguous" in err and writes == [], (out, err)
    else:
        assert code == 0 and writes == ["domain-A"], (out, err)


def test_native_form_active_popup_survives_surrounding_link_budget(world, fw):
    world.base["elements"] += [
        _native_form_element(300 + i, "AXLink", f"Footer {i}") for i in range(180)
    ] + [
        _native_form_element(600, "AXComboBox", "Nameservers"),
        _native_form_element(601, "AXList", "DNS options", parent=600),
        _native_form_element(602, "AXStaticText", "Basic DNS", parent=601, selected=True),
        _native_form_element(603, "AXStaticText", "Custom DNS", parent=601),
    ]
    code, out, err = fw("start", "Select Custom DNS", "--app", "Calculator")
    assert code == 0, (out, err)
    assert 603 in {c["id"] for c in _state(fw)["last_candidates"]}
    code, out, err = fw("do", "click", "Custom DNS", "--no-judge")
    assert code == 0 and world.presses == ["Custom DNS"], (out, err)


def _install_nameserver_fields(world, monkeypatch):
    from jevdual import native

    fields = [
        _native_form_element(300 + i, "AXTextField", value=f"Nameserver {i + 1}", in_web_content=True)
        for i in range(4)
    ]
    # This independent AX view distinguishes placeholders from actual entered text. The SDK rows
    # deliberately retain its real fallback behavior: an empty field's value is its placeholder.
    actual = {row["element_index"]: "" for row in fields}
    placeholders = {row["element_index"]: row["value"] for row in fields}
    ax = SimpleNamespace(
        Frame=lambda x, y, w, h: (x, y, w, h),
        resolve=lambda pid, wid, role, frame: int(frame[0]),
        value=lambda element: actual[element],
        placeholder=lambda element: placeholders[element],
    )
    monkeypatch.setattr(native.NativeBridge, "ax", property(lambda _: ax))
    call_tool = world.call_tool

    async def write_field(name, args_json):
        args = json.loads(args_json)
        if name == "type_text":
            idx = int(args["element_token"].split(":")[1])
            actual[idx] = args["text"]
            next(row for row in fields if row["element_index"] == idx)["value"] = args["text"]
        return await call_tool(name, args_json)

    monkeypatch.setattr(world, "call_tool", write_field)
    world.base["elements"] += fields
    return fields, actual, placeholders


def test_native_form_empty_placeholders_qualify_fields_before_pruning(world, fw, monkeypatch):
    _, actual, _ = _install_nameserver_fields(world, monkeypatch)
    code, out, err = fw("start", "Set the second nameserver", "--app", "Calculator")
    assert code == 0, (out, err)
    rows = {c["id"]: c for c in _state(fw)["last_candidates"]}
    for i in range(4):
        row = rows[300 + i]
        assert row["label"] == row["placeholder"] == f"Nameserver {i + 1}"
        assert row.get("value") is None
    assert not set(range(300, 304)) & set(_state(fw)["last_native_ambiguous"])
    code, out, err = fw("do", "type", "301", "ns2.example.test", "--no-judge")
    assert code == 0, (out, err)
    assert actual == {300: "", 301: "ns2.example.test", 302: "", 303: ""}
    row = next(c for c in _state(fw)["last_candidates"] if c["id"] == 301)
    assert row["label"] == row["placeholder"] == "Nameserver 2"
    assert row["value"] == "ns2.example.test"


@pytest.mark.parametrize("when", ["before_command", "final_live"])
@pytest.mark.parametrize("change", ["delete_and_renumber", "add"])
def test_native_form_changed_field_roster_cannot_retarget_a_pending_input(world, fw, monkeypatch, when, change):
    fields, actual, placeholders = _install_nameserver_fields(world, monkeypatch)
    assert fw("start", "Set the second nameserver", "--app", "Calculator")[0] == 0

    def mutate():
        if change == "add":
            field = _native_form_element(304, "AXTextField", value="Nameserver 5", in_web_content=True)
            fields.append(field)
            world.base["elements"].append(field)
            actual[304], placeholders[304] = "", "Nameserver 5"
        else:
            # Delete the selected backing field. Its old index and placeholder now name the old
            # third field; checking only the selected label/role/section would wrongly dispatch.
            world.base["elements"].remove(fields[1])
            for i in (2, 3):
                fields[i]["element_index"] -= 1
                fields[i]["value"] = placeholders[300 + i] = f"Nameserver {i}"

    if when == "before_command":
        mutate()
    else:
        from jevdual import native

        first = world.n + 1
        observe = native.NativeBridge.observe

        async def mutate_after_command_snapshot(bridge, **kwargs):
            snapshot = await observe(bridge, **kwargs)
            if world.n == first:
                mutate()
            return snapshot

        monkeypatch.setattr(native.NativeBridge, "observe", mutate_after_command_snapshot)
    code, out, err = fw("do", "type", "301", "ns2.example.test", "--no-judge")
    assert "target_changed" in out + err, (code, out, err)
    assert not any(actual.values())


def test_native_form_placeholder_change_during_final_live_check_refuses(world, fw, monkeypatch):
    from jevdual import native

    fields, actual, placeholders = _install_nameserver_fields(world, monkeypatch)
    fields[1]["label"] = "Destination"
    assert fw("start", "Set the destination", "--app", "Calculator")[0] == 0
    first = world.n + 1
    observe = native.NativeBridge.observe

    async def mutate_after_command_snapshot(bridge, **kwargs):
        snapshot = await observe(bridge, **kwargs)
        if world.n == first:
            placeholders[301] = "Replacement destination"
        return snapshot

    monkeypatch.setattr(native.NativeBridge, "observe", mutate_after_command_snapshot)
    code, out, err = fw("do", "type", "301", "ns2.example.test", "--no-judge")
    assert "target_changed" in out + err, (code, out, err)
    assert not any(actual.values())


def test_native_form_select_all_rechecks_the_field_before_inserting(world, fw, monkeypatch):
    from tests.test_posture import _ok

    fields, actual, placeholders = _install_nameserver_fields(world, monkeypatch)
    actual[301] = fields[1]["value"] = "old.example.test"
    call_tool = world.call_tool

    async def replace_after_selection(name, args_json):
        if name == "press_key":
            placeholders[301] = "Replacement field"
            await call_tool(name, args_json)
            return _ok()
        return await call_tool(name, args_json)

    monkeypatch.setattr(world, "call_tool", replace_after_selection)
    assert fw("start", "Replace second nameserver", "--app", "Calculator")[0] == 0
    code, out, err = fw("do", "type", "301", "ns2.example.test", "--no-judge")
    assert [name for name, _ in world.tool_calls] == ["press_key"], (code, out, err, world.tool_calls)
    assert actual[301] == "old.example.test"


def test_native_form_partial_placeholder_reads_do_not_prove_unique_identity(world, fw, monkeypatch):
    from jevdual import native

    fields, actual, placeholders = _install_nameserver_fields(world, monkeypatch)
    placeholders[300] = placeholders[301] = "Nameserver 1"
    fields[0]["value"] = fields[1]["value"] = "Nameserver 1"
    ax = native.NativeBridge.ax.fget(None)
    value = ax.value

    def unreadable_peer(element):
        if element == 301:
            raise RuntimeError("unreadable field")
        return value(element)

    ax.value = unreadable_peer
    assert fw("start", "Set first nameserver", "--app", "Calculator")[0] == 0
    code, out, err = fw("do", "type", "300", "ns1.example.test", "--no-judge")
    assert not any(actual.values()), (code, out, err, actual)
    assert "target_ambiguous" in out + err


def test_native_form_truncated_duplicate_labels_require_context_for_every_peer(world, fw, monkeypatch):
    from jevdual import native

    rows, writes, _ = _install_domain_rows(world, monkeypatch)
    world.base["elements"] = [row for row in world.base["elements"] if row not in (rows[0], rows[2])]
    for row in (rows[1], rows[3]):
        row.update(parent_index=0, in_web_content=True, label="M" * 85 + "-same")
    world.base["elements"].append(
        _native_form_element(305, "AXLink", "M" * 85 + "-other", in_web_content=True)
    )

    def section(element):
        if element == 305:
            raise RuntimeError("unreadable AX parent")
        return {301: "example.test", 303: "other.test"}[element]

    ax = SimpleNamespace(
        Frame=lambda x, y, w, h: (x, y, w, h),
        resolve=lambda pid, wid, role, frame: int(frame[0]), semantic_section=section,
    )
    monkeypatch.setattr(native.NativeBridge, "ax", property(lambda _: ax))
    assert fw("start", "Manage example.test", "--app", "Calculator")[0] == 0
    code, out, err = fw("do", "click", "301", "--no-judge")
    assert code == 4 and "target_ambiguous" in err and writes == [], (out, err)
