"""Durable execution records, custody and conservative journal recovery.

Synthetic receipts here are trusted test fixtures. Public native scenarios test
the receipt producer through the actual append route at simulated OS boundaries.
"""

from __future__ import annotations

import asyncio
import json
import select
import sqlite3
import subprocess
import sys
import textwrap

import pytest
from jevdual.capability.journal import Journal
from jevdual.capability.recovery import (
    ExecutionStore,
    RecoveryError,
    binding,
    make_recovery,
    validate_recovery,
)


@pytest.fixture
def prepared(tmp_path):
    document = tmp_path / "invoice.txt"
    scope = {
        "task": "recovery-fixture",
        "source": {"pid": 1, "window_id": 2, "url": "http://127.0.0.1:8000/"},
        "destination": {"pid": 77, "window_id": 4, "document": str(document)},
    }
    identity = {
        "boot": "test-boot",
        "pid": 77,
        "start": "0x1.0p0",
        "document": str(document),
        "device": 1,
        "inode": 2,
    }
    envelope = make_recovery(
        scope, identity, "AXTextArea", (0, 0, 100, 100), "Invoice\n", "Invoice\n17.25 USD"
    )
    journal = Journal(tmp_path / "operations.sqlite")
    op, created = journal.begin(
        task=scope["task"],
        resource="native:77:4",
        observation="obs_fixture",
        target="target_fixture",
        move="append",
        args={"text": "17.25 USD"},
        client_token="one-effect",
        recovery=envelope,
    )
    assert created
    store = ExecutionStore(journal.path)
    packet = store.prepare(op)
    yield journal, store, op, packet
    journal.close()


def _applied(packet):
    envelope = packet["recovery"]
    return {
        **binding(packet),
        "disposition": "applied",
        "phase": "sent",
        "error": None,
        "evidence": {
            "driver_effect": "confirmed",
            "identity": envelope["identity"],
            "identity_after": envelope["identity"],
            "before": envelope["before"],
            "after": envelope["expected"],
            "readback": {"passed": True},
        },
    }


def test_private_immutable_packet_and_receipt_roundtrip(prepared):
    _, store, op, packet = prepared
    result = _applied(packet)
    store.write_record(op.id, "result", result)
    assert store.read_result(op) == result
    assert store.root.stat().st_mode & 0o777 == 0o700
    assert store.directory(op.id).stat().st_mode & 0o777 == 0o700
    for name in ("packet", "result"):
        assert (store.directory(op.id) / f"{name}.json").stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        store.write_record(op.id, "result", result)
    assert store.read_result(op) == result


@pytest.mark.asyncio
@pytest.mark.parametrize("completed", [False, True])
@pytest.mark.parametrize("matching_text", [False, True])
async def test_public_reporting_separates_execution_current_text_and_persistence(
    prepared, monkeypatch, completed, matching_text
):
    from jevdual.capability.service import CapabilityService

    journal, store, op, packet = prepared
    journal.start(op.id)
    if completed:
        store.write_record(op.id, "result", _applied(packet))
    journal.close()
    monkeypatch.setattr(journal, "close", lambda: None)

    class CurrentOnly:
        async def current_recovery(self, recovery):
            return {"agreement": "yes" if matching_text else "no", "persistence": "not_checked"}

    restarted = Journal(journal.path)
    try:
        reply = await CapabilityService(restarted, CurrentOnly()).status(
            task=op.task, operation=op.id, reconcile=True
        )
        assert reply["disposition"] == ("applied" if completed else "unknown")
        assert reply["current"]["agreement"] == ("yes" if matching_text else "no")
        assert reply["reporting"]["historical_effect"] == ("applied" if completed else "unknown")
        assert reply["reporting"]["disk_persistence"] == "not_checked"
    finally:
        restarted.close()


@pytest.mark.parametrize("field", ["operation_id", "request_digest", "nonce", "packet_digest", "version"])
def test_receipt_binding_mismatch_is_never_accepted(prepared, field):
    _, store, op, packet = prepared
    result = _applied(packet)
    result[field] = 99 if field == "version" else "different"
    store.write_record(op.id, "result", result)
    with pytest.raises(RecoveryError):
        store.read_result(op)


@pytest.mark.parametrize(
    "field", ["identity", "identity_after", "before", "after", "driver_effect", "readback"]
)
def test_applied_receipt_requires_every_execution_proof(prepared, field):
    _, store, op, packet = prepared
    result = _applied(packet)
    result["evidence"].pop(field)
    store.write_record(op.id, "result", result)
    with pytest.raises(RecoveryError):
        store.read_result(op)


def test_completed_receipt_safe_save_inode_change_does_not_erase_historical_effect(prepared):
    _, store, op, packet = prepared
    result = _applied(packet)
    result["evidence"]["identity_after"] = {**result["evidence"]["identity_after"], "inode": 3}
    store.write_record(op.id, "result", result)
    assert store.read_result(op)["disposition"] == "applied"


@pytest.mark.parametrize("key", ["boot", "pid", "start", "document"])
def test_completed_receipt_replaced_native_identity_never_claims_applied(prepared, key):
    _, store, op, packet = prepared
    result = _applied(packet)
    result["evidence"]["identity_after"] = {
        **result["evidence"]["identity_after"],
        key: 99 if key == "pid" else "changed",
    }
    store.write_record(op.id, "result", result)
    with pytest.raises(RecoveryError):
        store.read_result(op)


@pytest.mark.parametrize("malformation", ["symlink", "public_mode", "oversized", "bad_json"])
def test_untrusted_receipt_artifact_is_rejected(prepared, malformation, tmp_path):
    _, store, op, packet = prepared
    path = store.directory(op.id) / "result.json"
    if malformation == "symlink":
        target = tmp_path / "outside.json"
        target.write_text(json.dumps(_applied(packet)))
        path.symlink_to(target)
    else:
        path.write_text(
            "{}" * 70000
            if malformation == "oversized"
            else "{"
            if malformation == "bad_json"
            else json.dumps(_applied(packet))
        )
        path.chmod(0o644 if malformation == "public_mode" else 0o600)
    with pytest.raises((RecoveryError, OSError, json.JSONDecodeError)):
        store.read_result(op)


def test_prepared_only_restart_proves_not_sent(prepared, monkeypatch):
    journal, store, op, _ = prepared
    journal.close()
    monkeypatch.setattr(journal, "close", lambda: None)
    reopened = Journal(journal.path)
    try:
        retained = reopened.by_token(op.task, op.client_token)
        assert retained.state == "final" and retained.disposition == "not_sent"
        assert retained.resolved_by == "recovery" and store.read_result(retained) is None
    finally:
        reopened.close()


def test_started_without_receipt_stays_unknown_after_restart(prepared, monkeypatch):
    journal, store, op, _ = prepared
    journal.start(op.id)
    journal.close()
    monkeypatch.setattr(journal, "close", lambda: None)
    reopened = Journal(journal.path)
    try:
        retained = reopened.by_token(op.task, op.client_token)
        assert retained.state == retained.disposition == "unknown"
        assert store.read_result(retained) is None and store.custody(retained) == "unattested"
    finally:
        reopened.close()


def test_unknown_envelope_version_is_rejected(prepared):
    _, _, _, packet = prepared
    with pytest.raises(RecoveryError):
        validate_recovery({**packet["recovery"], "version": 99})


@pytest.mark.parametrize("disposition", ["refused", "not_sent"])
def test_no_send_receipt_requires_no_send_phase(prepared, disposition):
    _, store, op, packet = prepared
    result = {**binding(packet), "disposition": disposition, "phase": "sent", "evidence": {}, "error": None}
    store.write_record(op.id, "result", result)
    with pytest.raises(RecoveryError):
        store.read_result(op)


@pytest.mark.parametrize("corruption", ["{", '{"version":99}', "[]"])
def test_malformed_recovery_preserves_block_on_reopen(prepared, monkeypatch, corruption):
    journal, _, op, _ = prepared
    path = journal.path
    journal.close()
    monkeypatch.setattr(journal, "close", lambda: None)
    with sqlite3.connect(path) as db:
        db.execute("UPDATE operations SET recovery=? WHERE id=?", (corruption, op.id))
    reopened = Journal(path)
    try:
        retained = reopened.by_token(op.task, op.client_token)
        assert retained.state == retained.disposition == "unknown" and retained.unresolved
    finally:
        reopened.close()


def test_legacy_schema_migration_does_not_invent_execution_authority(prepared, monkeypatch):
    journal, _, op, _ = prepared
    path = journal.path
    journal.close()
    monkeypatch.setattr(journal, "close", lambda: None)
    with sqlite3.connect(path) as db:
        db.execute("ALTER TABLE operations DROP COLUMN recovery")
        db.execute("ALTER TABLE operations DROP COLUMN execution_stage")
    reopened = Journal(path)
    try:
        retained = reopened.by_token(op.task, op.client_token)
        assert retained.state == retained.disposition == "unknown"
        assert retained.recovery is retained.execution_stage is None
    finally:
        reopened.close()


@pytest.mark.parametrize(
    ("hang", "pre_boundary_delay"), [("before", 0), ("after", 0), ("before", 0.4), ("after", 0.4)]
)
def test_fixed_worker_deadline_fences_admission_and_preserves_uncertainty(
    prepared, tmp_path, hang, pre_boundary_delay
):
    """Run the fixed worker; trigger its original deadline at an observed blocked OS-read boundary."""
    journal, store, op, _ = prepared
    op = journal.start(op.id)
    packet_path = store.directory(op.id) / "packet.json"
    effect = tmp_path / "observed-effect.json"
    boundary = tmp_path / "observed-boundary.json"
    child_code = textwrap.dedent(
        """
        import asyncio,json,os,sys,threading
        from pathlib import Path
        from types import SimpleNamespace
        import pytest
        from jevdual.capability import execution_worker,recovery
        from tests.fixtures.native_world import TextWorld
        packet_path,effect,hang=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]
        pre_boundary_delay,boundary=float(sys.argv[4]),Path(sys.argv[5])
        packet=json.loads(packet_path.read_text())
        scope=packet['recovery']['scope']
        world=TextWorld(Path(scope['destination']['document']),content='Invoice\\n',window_id=4,frame=(0,0,100,100))
        patch=pytest.MonkeyPatch()
        world.install(patch)
        patch.setattr(recovery,'native_identity',lambda scope:packet['recovery']['identity'])
        patch.setattr(execution_worker,'native_identity',lambda scope:packet['recovery']['identity'])
        original_timer=threading.Timer
        boundary_reached=threading.Event()
        def at_boundary(interval,fn):
            def fire():
                if not boundary_reached.wait(timeout=3):
                    os._exit(3)  # unqualified boundary, never manufacture a deadline receipt
                fn()  # the unchanged production admission fence and deadline writer
            return original_timer(0,fire)
        patch.setattr(threading,'Timer',at_boundary)
        original_read=world.get_window_state
        first_read=True
        async def blocked_read(inp):
            global first_read
            if first_read:
                first_read=False
                await asyncio.sleep(pre_boundary_delay)
            if hang=='before' or world.content.endswith('17.25 USD'):
                if hang=='after':
                    assert effect.exists()
                    assert json.loads(effect.read_text())['actual']==world.content=='Invoice\\n17.25 USD'
                boundary.write_text(json.dumps({'phase':hang,'actual':world.content}))
                boundary_reached.set()
                await asyncio.sleep(10)
            return await original_read(inp)
        patch.setattr(world,'get_window_state',blocked_read)
        import ApplicationServices
        def record_set(el,name,value):
            result=world._set(el,name,value)
            if name=='AXSelectedText':
                effect.write_text(json.dumps({'actual':world.content}))
            return result
        patch.setattr(ApplicationServices,'AXUIElementSetAttributeValue',record_set)
        raise SystemExit(asyncio.run(execution_worker.run(packet_path)))
        """
    )
    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            child_code,
            str(packet_path),
            str(effect),
            hang,
            str(pre_boundary_delay),
            str(boundary),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = child.communicate(timeout=5)
    except BaseException:
        child.kill()
        child.communicate(timeout=3)
        raise
    assert child.returncode == 2, (stdout, stderr)
    assert boundary.exists(), "the requested observation boundary was never reached"
    observed_boundary = json.loads(boundary.read_text())
    assert observed_boundary["phase"] == hang
    assert observed_boundary["actual"] == ("Invoice\n" if hang == "before" else "Invoice\n17.25 USD")
    result = store.read_result(op)
    assert result["error"] == "worker_deadline"
    assert result["disposition"] == ("not_sent" if hang == "before" else "unknown")
    assert result["phase"] == ("not_sent" if hang == "before" else "ambiguous")
    assert result["evidence"]["input_admitted"] is (hang == "after")
    assert effect.exists() is (hang == "after")
    if effect.exists():
        assert json.loads(effect.read_text())["actual"] == "Invoice\n17.25 USD"
    assert store.custody(op) == "unattested"


async def test_real_child_lock_custody_exit_without_receipt_does_not_imply_no_send(prepared, monkeypatch):
    journal, store, op, _ = prepared
    op = journal.start(op.id)
    lock_path = store.directory(op.id) / "worker.lock"
    child = await asyncio.to_thread(
        subprocess.Popen,
        [
            sys.executable,
            "-c",
            (
                "import fcntl,os,sys; f=os.open(sys.argv[1],os.O_CREAT|os.O_RDWR,0o600); "
                "fcntl.flock(f,fcntl.LOCK_EX); print('ready',flush=True); sys.stdin.readline()"
            ),
            str(lock_path),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        ready = await asyncio.to_thread(select.select, [child.stdout], [], [], 5)
        assert ready[0] and child.stdout.readline().strip() == "ready"
        assert store.custody(op) == "active"
        launches = []

        def launch(request):
            launches.append(request.id)
            return child

        monkeypatch.setattr(store, "_launch", launch)
        pending = asyncio.create_task(store.execute(op))
        await asyncio.sleep(0.03)
        assert not pending.done() and store.read_result(op) is None
        child.stdin.close()
        await asyncio.to_thread(child.wait, timeout=5)
        assert await pending is None
        assert launches == [op.id] and store.custody(op) == "unattested"
    finally:
        if child.poll() is None:
            child.kill()
        await asyncio.to_thread(child.wait, timeout=5)
