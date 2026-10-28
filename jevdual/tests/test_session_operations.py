"""Operator admission, conservation and actual process-death boundaries."""

from __future__ import annotations

import multiprocessing
import os
import signal
from pathlib import Path

import pytest
from jevdual import grants
from jevdual.capability.journal import Busy, Journal, JournalError, JournalLocked, TokenConflict
from jevdual.session_operations import GrantRequired, SessionOperations, native_binding, native_resource

PROPOSAL = grants.Proposal("click", "native:fixture", "button", "Delete", None, None)
REQUEST = {"words": ["click", "Delete"], "no_judge": True}


def admit(store, *, session="one", token="token", gated=True, **over):
    return store.admit(
        **{
            "session_id": session,
            "token": token,
            "request": REQUEST,
            "resource": "native:boot:77:start",
            "observation": "obs1",
            "target": "target1",
            "move": "click",
            "proposal": PROPOSAL if gated else None,
            "authorization_basis": "exact_grant" if gated else "policy",
            "projection": {"line": "click(Delete)", "step": 1},
            **over,
        }
    )


def issue(store, session="one", resource="native:boot:77:start", uses=1):
    grant = grants.issue(PROPOSAL, uses=uses)
    store.issue_grant(session, grant, resource=resource)
    return grant


def test_atomic_intent_and_required_grant_reservation(tmp_path):
    with SessionOperations(tmp_path / "authority.db") as store:
        grant = issue(store)
        op = admit(store)
        assert store.receipt(op)["reservation"] == "held"
        assert store.matching_grant("one", PROPOSAL, resource=op.resource)[0] is None
        assert store.get(op.id).execution_stage == "prepared"
        assert store.get(op.id).args == REQUEST
        assert (
            store._db.execute("SELECT available FROM operator_grants WHERE id=?", (grant.id,)).fetchone()[0]
            == 0
        )


def test_no_required_grant_keeps_reservation_absent(tmp_path):
    with SessionOperations(tmp_path / "authority.db") as store:
        op = admit(store, gated=False)
        assert store.receipt(op)["reservation"] is None


def test_failed_admission_rolls_back_intent_and_use(tmp_path, monkeypatch):
    with SessionOperations(tmp_path / "authority.db") as store:
        issue(store)
        original = store._event
        monkeypatch.setattr(store, "_event", lambda *a, **k: (_ for _ in ()).throw(OSError("disk error")))
        with pytest.raises(OSError):
            admit(store)
        assert store.status() == []
        assert store.matching_grant("one", PROPOSAL, resource="native:boot:77:start")[0].uses_left == 1
        monkeypatch.setattr(store, "_event", original)


def test_required_grant_missing_or_rebound_never_admits(tmp_path):
    with SessionOperations(tmp_path / "authority.db") as store:
        with pytest.raises(GrantRequired):
            admit(store)
        issue(store, resource="different-incarnation")
        with pytest.raises(GrantRequired):
            admit(store)
        assert store.status() == []


def test_domain_barrier_covers_other_sessions_and_apps(tmp_path):
    with SessionOperations(tmp_path / "authority.db") as store:
        first = admit(store, gated=False)
        with pytest.raises(Busy) as caught:
            admit(store, session="other", token="other", resource="another-app", gated=False)
        assert caught.value.op_id == first.id


def test_replay_precedes_observation_and_ignores_new_observation(tmp_path):
    with SessionOperations(tmp_path / "authority.db") as store:
        issue(store)
        op = admit(store)
        assert store.by_request("one", "token", REQUEST).id == op.id
        assert admit(store, observation="fresh-observation", target="renumbered-target").id == op.id
        with pytest.raises(TokenConflict):
            store.by_request("one", "token", {"words": ["click", "Other"]})
        assert store.receipt(op)["reservation"] == "held"


@pytest.mark.parametrize(
    ("dispatched", "effect", "delivered", "state", "phase", "reservation"),
    [
        (False, "refused", None, "final", "not_sent", "released"),
        (True, "confirmed", True, "final", "sent", "spent"),
        (True, "partial", True, "final", "sent", "spent"),
        (True, "confirmed", None, "unknown", "ambiguous", "held"),
        (True, "unverifiable", None, "unknown", "ambiguous", "held"),
        (None, "refused", None, "unknown", "ambiguous", "held"),
        (True, "unverifiable", True, "unknown", "sent", "spent"),
    ],
)
def test_delivery_and_effect_do_not_conflate_operation_and_reservation(
    tmp_path, dispatched, effect, delivered, state, phase, reservation
):
    path = tmp_path / "authority.db"
    with SessionOperations(path) as store:
        issue(store)
        op = admit(store)
        store.start(op.id)
        done = store.finish(
            op.id,
            dispatched=dispatched,
            effect=effect,
            delivered=delivered,
            evidence={"dispatched": dispatched},
        )
        assert (done.state, done.phase, store.receipt(done)["reservation"]) == (state, phase, reservation)
        if state == "unknown":
            with pytest.raises(Busy):
                store.assert_available()
        else:
            store.assert_available()
        with pytest.raises(JournalError):
            store.finish(op.id, dispatched=False, effect="refused", evidence={})
    with SessionOperations(path) as reopened:
        saved = reopened.get(op.id)
        assert reopened.receipt(saved)["reservation"] == reservation
        available = reopened.matching_grant("one", PROPOSAL, resource=op.resource)[0]
        assert (available is not None) is (reservation == "released")


def test_finish_requires_started_and_manual_resolution_is_unavailable(tmp_path):
    with SessionOperations(tmp_path / "authority.db") as store:
        op = admit(store, gated=False)
        with pytest.raises(JournalError):
            store.finish(op.id, dispatched=False, effect="refused", evidence={})
        store.start(op.id)
        unknown = store.finish(op.id, dispatched=None, effect="unverifiable", evidence={})
        with pytest.raises(JournalError):
            store.resolve(unknown.id, disposition="applied", evidence={"because": "operator said so"})


def test_failed_finish_does_not_settle_reservation_or_lose_custody(tmp_path, monkeypatch):
    path = tmp_path / "authority.db"
    with SessionOperations(path) as store:
        issue(store)
        op = admit(store)
        store.start(op.id)
        monkeypatch.setattr(store, "_event", lambda *a, **k: (_ for _ in ()).throw(OSError("disk error")))
        with pytest.raises(OSError):
            store.finish(op.id, dispatched=False, effect="refused", evidence={})
        retained = store.get(op.id)
        assert retained.state == "dispatching" and store.receipt(retained)["reservation"] == "held"
    with SessionOperations(path) as store:
        retained = store.get(op.id)
        assert retained.state == "unknown" and store.receipt(retained)["reservation"] == "held"


@pytest.mark.parametrize(
    ("dispatched", "phase"), [(False, "sent"), (True, "not_sent"), (None, "sent"), (False, "ambiguous")]
)
def test_invalid_delivery_combinations_do_not_finalize(tmp_path, dispatched, phase):
    with SessionOperations(tmp_path / "authority.db") as store:
        op = admit(store, gated=False)
        store.start(op.id)
        with pytest.raises(JournalError):
            store.finish(op.id, dispatched=dispatched, effect="confirmed", phase=phase, evidence={})
        assert store.get(op.id).state == "dispatching"


def test_final_replay_projection_is_stable_and_no_second_use_is_debited(tmp_path):
    path = tmp_path / "authority.db"
    with SessionOperations(path) as store:
        issue(store, uses=2)
        op = admit(store)
        store.start(op.id)
        done = store.finish(
            op.id,
            dispatched=True,
            effect="confirmed",
            phase="sent",
            evidence={"line": "click(Delete)", "step": 1, "driver_effect": "confirmed"},
        )
        first_projection = store.projection(done)
    with SessionOperations(path) as store:
        replay = store.by_request("one", "token", REQUEST)
        assert store.projection(replay) == first_projection
        assert admit(store, observation="newobs").id == op.id
        assert store.matching_grant("one", PROPOSAL, resource=op.resource)[0].uses_left == 1


def test_unsupported_prepared_protocol_does_not_acquire_no_send_authority(tmp_path):
    path = tmp_path / "authority.db"
    with SessionOperations(path) as store:
        issue(store)
        op = admit(store)
        store._db.execute("UPDATE operator_admissions SET protocol=999 WHERE operation=?", (op.id,))
    with SessionOperations(path) as store:
        retained = store.get(op.id)
        assert retained.state == "unknown" and retained.phase == "ambiguous"
        assert store.matching_grant("one", PROPOSAL, resource=op.resource)[0] is None
        with pytest.raises(Busy):
            store.assert_available()


def test_owner_lock_and_existing_capability_schema_are_reused(tmp_path):
    path = tmp_path / "authority.db"
    Journal(path).close()
    with SessionOperations(path), pytest.raises(JournalLocked):
        SessionOperations(path)
    with SessionOperations(path) as store:
        assert store.status() == []


def test_unknown_version_refuses_before_recovering_operations(tmp_path):
    path = tmp_path / "authority.db"
    with SessionOperations(path) as store:
        op = admit(store, gated=False)
        store._db.execute("UPDATE operator_metadata SET version=999")
    with pytest.raises(JournalError, match="unsupported"):
        SessionOperations(path)
    import sqlite3

    with sqlite3.connect(path) as db:
        assert db.execute("SELECT state FROM operations WHERE id=?", (op.id,)).fetchone()[0] == "dispatching"


def _crash_child(path: str, boundary: str, channel):
    with SessionOperations(Path(path)) as store:
        issue(store)
        if boundary == "before_intent":
            channel.send(None)
        else:
            op = admit(store)
            if boundary != "prepared":
                store.start(op.id)
            if boundary in ("effect", "finish"):
                with open(path + ".inputs", "a") as ledger:
                    ledger.write(op.id + "\n")
                    ledger.flush()
                    os.fsync(ledger.fileno())
            if boundary == "finish":
                store.finish(
                    op.id,
                    dispatched=True,
                    effect="confirmed",
                    phase="sent",
                    evidence={"step": 1, "driver_effect": "confirmed"},
                )
            channel.send(op.id)
        # Parent uses SIGKILL, so neither this context manager nor finally executes.
        signal.pause()


@pytest.mark.parametrize("boundary", ["before_intent", "prepared", "started", "effect", "finish"])
def test_sigkill_preserves_custody_and_never_repeats_input(tmp_path, boundary):
    path = tmp_path / "authority.db"
    context = multiprocessing.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    child = context.Process(target=_crash_child, args=(str(path), boundary, writer))
    child.start()
    try:
        assert reader.poll(10), "child did not reach injected boundary"
        op_id = reader.recv()
        os.kill(child.pid, signal.SIGKILL)
        child.join(10)
        assert not child.is_alive() and child.exitcode == -signal.SIGKILL
        with SessionOperations(path) as store:
            if op_id is None:
                assert store.status() == []
                assert (
                    store.matching_grant("one", PROPOSAL, resource="native:boot:77:start")[0].uses_left == 1
                )
            else:
                op = store.by_request("one", "token", REQUEST)
                assert op.id == op_id
                if boundary == "prepared":
                    assert op.phase == "not_sent" and store.receipt(op)["reservation"] == "released"
                    assert store.projection(op)["dispatched"] is False
                elif boundary in ("started", "effect"):
                    assert op.state == "unknown" and store.receipt(op)["reservation"] == "held"
                    assert store.projection(op)["dispatched"] is None
                    with pytest.raises(Busy):
                        admit(store, session="another", token="another", gated=False)
                else:
                    assert op.state == "final" and store.receipt(op)["reservation"] == "spent"
                    assert store.projection(op)["driver_effect"] == "confirmed"
            ledger = Path(str(path) + ".inputs")
            assert (len(ledger.read_text().splitlines()) if ledger.exists() else 0) == (
                1 if boundary in ("effect", "finish") else 0
            )
    finally:
        if child.is_alive():
            child.kill()
            child.join(10)
        reader.close()
        writer.close()


def test_identity_distinguishes_process_reincarnation_and_window_binding():
    identity = {"boot": "boot", "pid": 77, "start": "start", "window_id": 12}
    assert native_resource(identity) == native_resource({**identity, "window_id": 13})
    assert native_binding(identity) != native_binding({**identity, "window_id": 13})
    assert native_resource(identity) != native_resource({**identity, "start": "new"})
    with pytest.raises(JournalError):
        native_binding({"pid": 77, "window_id": 12})


EXEC_BINDING = {"boot": "fixture-boot", "pid": 77, "start": "fixture-start", "window_id": 12}


def execution_admit(store, *, gated=True):
    if gated:
        issue(store, resource=native_resource(EXEC_BINDING))
    op = admit(
        store,
        gated=gated,
        resource=native_resource(EXEC_BINDING),
        projection={"step": 1, "line": "click(Delete)", "binding": EXEC_BINDING},
    )
    store.start(op.id)
    return store.get(op.id)


def capsule_for(op, *, phase="sent", effect="confirmed", error=None):
    import time

    from jevdual.operator_evidence import execution_record

    now = time.time()
    return execution_record(
        op,
        binding=EXEC_BINDING,
        started_at=now,
        ended_at=now,
        producer_evidence={
            "name": "footwork.native",
            "version": 1,
            "delivery_basis": "sdk_delivery_count"
            if phase == "sent"
            else "qualified_gate"
            if phase == "not_sent"
            else "unknown",
            "delivered_count": 1 if phase == "sent" else 0,
        },
        dispatched=False if phase == "not_sent" else True if phase == "sent" else None,
        effect=effect,
        phase=phase,
        projection={
            "step": 1,
            "line": "click(Delete)",
            "driver_effect": effect,
            "binding": EXEC_BINDING,
            "operation_id": op.id,
        },
        error=error,
    )


@pytest.mark.parametrize(
    ("phase", "effect", "state", "reservation"),
    [
        ("sent", "confirmed", "final", "spent"),
        ("not_sent", "refused", "final", "released"),
        ("sent", "unverifiable", "unknown", "spent"),
        ("ambiguous", "unverifiable", "unknown", "held"),
    ],
)
def test_retained_execution_reconciles_only_qualified_outcomes(tmp_path, phase, effect, state, reservation):
    path = tmp_path / "authority.db"
    with SessionOperations(path) as store:
        op = execution_admit(store)
        store.record_execution(op.id, capsule_for(op, phase=phase, effect=effect))
    with SessionOperations(path) as store:
        assert store.get(op.id).state == "unknown"
        reconciled = store.reconcile(op.id)
        assert reconciled.state == state and store.receipt(reconciled)["reservation"] == reservation
        assert "recovered_unknown" in [event["kind"] for event in store.events(op.id)]
        assert "execution_reconciled" in [event["kind"] for event in store.events(op.id)]
        events, evidence = store.events(op.id), reconciled.evidence
        again = store.reconcile(op.id)
        assert again.state == state and store.receipt(again)["reservation"] == reservation
        assert store.events(op.id) == events and again.evidence == evidence
        assert again.evidence["prior_uncertainty"]["phase"] == "ambiguous"
        available = store.matching_grant("one", PROPOSAL, resource=op.resource)[0]
        assert (available is not None) is (reservation == "released")
        if state == "unknown":
            with pytest.raises(Busy):
                store.assert_available()


def test_execution_receipt_is_immutable_and_normal_finish_uses_it(tmp_path):
    with SessionOperations(tmp_path / "authority.db") as store:
        op = execution_admit(store)
        capsule = capsule_for(op)
        store.record_execution(op.id, capsule)
        store.record_execution(op.id, capsule)
        changed = {**capsule, "error": "another outcome"}
        with pytest.raises(JournalError, match="immutable"):
            store.record_execution(op.id, changed)
        done = store.finish_from_execution(op.id)
        assert done.disposition == "applied" and done.evidence["execution_receipt"] == capsule


@pytest.mark.parametrize(
    "failure",
    [
        "missing",
        "body",
        "digest",
        "wrong_binding",
        "wrong_version",
        "boolean_protocol",
        "boolean_producer",
        "boolean_binding",
    ],
)
def test_missing_or_tampered_execution_never_releases_custody(tmp_path, failure):
    import hashlib
    import json

    path = tmp_path / "authority.db"
    with SessionOperations(path) as store:
        op = execution_admit(store)
        if failure != "missing":
            capsule = capsule_for(op)
            store.record_execution(op.id, capsule)
            if failure in (
                "wrong_binding",
                "wrong_version",
                "boolean_protocol",
                "boolean_producer",
                "boolean_binding",
            ):
                if failure == "wrong_binding":
                    capsule["binding"] = {**EXEC_BINDING, "window_id": 99}
                elif failure == "wrong_version":
                    capsule["schema_version"] = "99"
                elif failure == "boolean_protocol":
                    capsule["protocol"] = True
                elif failure == "boolean_producer":
                    capsule["producer"]["version"] = True
                else:
                    capsule["binding"]["pid"] = True
                raw = json.dumps(capsule, sort_keys=True, separators=(",", ":"))
                store._db.execute(
                    "UPDATE operator_execution_receipts SET body=?,digest=?",
                    (raw, hashlib.sha256(raw.encode()).hexdigest()),
                )
            else:
                store._db.execute(f"UPDATE operator_execution_receipts SET {failure}='corrupt'")
    with SessionOperations(path) as store:
        assert store.reconcile(op.id).state == "unknown"
        assert store.receipt(store.get(op.id))["reservation"] == "held"
        with pytest.raises(Busy):
            store.assert_available()


def test_current_text_or_caller_assertion_cannot_reconcile(tmp_path):
    with SessionOperations(tmp_path / "authority.db") as store:
        op = execution_admit(store)
        store.finish(op.id, dispatched=None, effect="unverifiable", evidence={"current_text": "matches"})
        assert store.reconcile(op.id).state == "unknown"
        with pytest.raises(JournalError):
            store.resolve(op.id, evidence={"operator_says": "done"}, disposition="applied")


def _execution_crash_child(path, boundary, channel):
    with SessionOperations(Path(path)) as store:
        op = execution_admit(store)
        with open(path + ".inputs", "a") as ledger:
            ledger.write(op.id + "\n")
            ledger.flush()
            os.fsync(ledger.fileno())
        if boundary != "before_receipt":
            store.record_execution(op.id, capsule_for(op))
        if boundary == "after_finish":
            store.finish_from_execution(op.id)
        channel.send(op.id)
        signal.pause()


@pytest.mark.parametrize("boundary", ["before_receipt", "after_receipt", "after_finish"])
def test_sigkill_around_retained_receipt_never_redispatches(tmp_path, boundary):
    path = tmp_path / "authority.db"
    context = multiprocessing.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    child = context.Process(target=_execution_crash_child, args=(str(path), boundary, writer))
    child.start()
    try:
        assert reader.poll(10)
        op_id = reader.recv()
        os.kill(child.pid, signal.SIGKILL)
        child.join(10)
        assert child.exitcode == -signal.SIGKILL
        with SessionOperations(path) as store:
            result = store.reconcile(op_id)
            assert result.state == ("unknown" if boundary == "before_receipt" else "final")
            assert store.by_request("one", "token", REQUEST).id == op_id
            assert Path(str(path) + ".inputs").read_text().splitlines() == [op_id]
            assert store.receipt(result)["reservation"] == (
                "held" if boundary == "before_receipt" else "spent"
            )
    finally:
        if child.is_alive():
            child.kill()
            child.join(10)
        reader.close()
        writer.close()
