"""Owned-browser admission, no-replay recovery and separate execution evidence."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest
from jevdual.browser_authority import (
    PROTOCOL,
    ROUTE,
    BrowserAuthority,
    BrowserEvidenceError,
    browser_resource,
    canonical,
    guard_digest,
    operation_record,
    validate_binding,
)
from jevdual.capability.journal import Busy, JournalError, TokenConflict
from jevdual.operator_evidence import EvidenceError
from jevdual.operator_evidence import validate_binding as native_binding
from jevdual.session_operations import SessionOperations

BINDING = {
    "boot": "boot", "pid": 77, "start": "1.25", "browser_context": "",
    "target": "page", "cdp_session": "session", "frame": "main", "loader": "document",
    "backend_node": 11, "execution_context": 3, "document_token": "private-marker",
    "fingerprint": json.dumps({"tag": "button", "attrs": [["type", "button"]],
                               "text": "Send", "ancestors": []}),
}
REQUEST = {"ref": "observation:button", "route": ROUTE}
ACK = {"status": "ok", "dispatched": True, "route": ROUTE, "code": None}
NO_SEND = {"status": "refused", "dispatched": False, "route": None, "code": "button_changed"}
UNKNOWN = {"status": "refused", "dispatched": None, "route": ROUTE, "code": "browser_delivery_unknown"}


def guard(binding=None, request=None, session="one"):
    return {"producer": "footwork.browser.guard", "version": 1, "decision": "allow",
            "digest": guard_digest(session, request or REQUEST, binding or BINDING)}


def admit(store, *, session="one", token="token", binding=None, request=None, decision=None):
    binding, request = binding or copy.deepcopy(BINDING), request or dict(REQUEST)
    return store.admit_click(session_id=session, token=token, request=request, binding=binding,
                             guard=decision or guard(binding, request, session))


@pytest.mark.parametrize("change", [
    {"pid": True}, {"backend_node": 0}, {"execution_context": -1}, {"start": "nan"},
    {"start": "1.250"}, {"target": ""}, {"document_token": ""}, {"loader": ""},
    {"fingerprint": "{}"}, {"window_id": 12},
])
def test_binding_rejects_incomplete_or_foreign_identity(change):
    with pytest.raises(BrowserEvidenceError):
        validate_binding({**BINDING, **change})


def test_browser_and_native_bindings_remain_separate():
    validate_binding(BINDING)
    assert browser_resource(BINDING).startswith("browser:")
    with pytest.raises(EvidenceError):
        native_binding(BINDING)
    with pytest.raises(BrowserEvidenceError):
        validate_binding({"boot": "boot", "pid": 77, "start": "1.25", "window_id": 8})


@pytest.mark.parametrize("change", [
    {"decision": "deny"}, {"version": True}, {"version": 2}, {"digest": "0" * 64},
    {"producer": "caller"}, {"extra": "assertion"},
])
def test_missing_or_changed_guard_never_admits(tmp_path, change):
    with BrowserAuthority(tmp_path / "authority.db") as store:
        with pytest.raises(BrowserEvidenceError):
            admit(store, decision={**guard(), **change})
        assert store.status() == []


def test_guard_digest_binds_session_request_and_exact_subject(tmp_path):
    with BrowserAuthority(tmp_path / "authority.db") as store:
        with pytest.raises(BrowserEvidenceError):
            admit(store, binding={**BINDING, "loader": "reloaded"}, decision=guard())
        with pytest.raises(BrowserEvidenceError):
            admit(store, session="other", decision=guard())
        with pytest.raises(BrowserEvidenceError):
            admit(store, request={**REQUEST, "ref": "other"}, decision=guard())
        assert store.status() == []


@pytest.mark.parametrize("decision", [None, {}])
def test_absent_guard_never_admits(tmp_path, decision):
    with BrowserAuthority(tmp_path / "authority.db") as store:
        with pytest.raises(BrowserEvidenceError):
            store.admit_click(session_id="one", token="token", request=REQUEST,
                               binding=BINDING, guard=decision)
        assert store.status() == []


@pytest.mark.parametrize("request_value", [
    {"ref": "button", "route": "trusted"}, {"ref": "button", "route": ROUTE, "text": "password"},
    {"ref": "", "route": ROUTE}, {"ref": "button", "route": "type"},
])
def test_request_does_not_enable_typing_or_other_routes(tmp_path, request_value):
    with BrowserAuthority(tmp_path / "authority.db") as store:
        with pytest.raises(BrowserEvidenceError):
            admit(store, request=request_value)
        assert store.status() == []


def test_same_token_returns_original_before_reobservation_or_new_guard(tmp_path):
    with BrowserAuthority(tmp_path / "authority.db") as store:
        op = admit(store)
        # Deliberately invalid live identity/guard prove that replay does not reacquire a target.
        assert store.admit_click(session_id="one", token="token", request=REQUEST,
                                 binding={}, guard={}).id == op.id
        with pytest.raises(TokenConflict):
            admit(store, request={**REQUEST, "ref": "another"})
        with pytest.raises(Busy):
            admit(store, token="another")


@pytest.mark.parametrize("started", [False, True])
def test_restart_distinguishes_prepared_from_admitted_input(tmp_path, started):
    path = tmp_path / "authority.db"
    with BrowserAuthority(path) as store:
        op = admit(store)
        if started:
            store.start(op.id)
    with BrowserAuthority(path) as store:
        recovered = store.by_request("one", "token", REQUEST)
        assert recovered.id == op.id
        assert recovered.state == ("unknown" if started else "final")
        assert recovered.disposition == ("unknown" if started else "not_sent")
        assert store.reconcile(op.id).disposition == recovered.disposition
        if started:
            with pytest.raises(Busy):
                admit(store, token="new")


@pytest.mark.parametrize(("reply", "phase", "disposition"), [
    (ACK, "sent", "unknown"), (NO_SEND, "not_sent", "not_sent"),
    (UNKNOWN, "ambiguous", "unknown"),
    ({**NO_SEND, "code": "generic_failure"}, "ambiguous", "unknown"),
    ({**ACK, "dispatched": False}, "ambiguous", "unknown"),
])
def test_acknowledgement_never_claims_application_completion(tmp_path, reply, phase, disposition):
    path = tmp_path / "authority.db"
    with BrowserAuthority(path) as store:
        op = admit(store)
        store.start(op.id)
        result = store.record_reply(op.id, reply)
        assert result.phase == phase
        assert result.disposition == disposition
        report = operation_record(result)
        assert report["completion"] == "unverified"
        assert report["retryable"] is False
        record = result.evidence["execution_receipt"]
        assert record["producer"] == {"name": PROTOCOL, "version": 1}
        assert record["binding"] == BINDING
        assert record["effect"] not in {"confirmed", "partial"}
        assert record["request_digest"] == result.request_digest
    with BrowserAuthority(path) as store:
        assert store.reconcile(op.id).disposition == disposition
        assert store.by_request("one", "token", REQUEST).id == op.id


@pytest.mark.parametrize("reply", [NO_SEND, ACK, UNKNOWN])
def test_retained_result_survives_death_before_finalization(tmp_path, monkeypatch, reply):
    path = tmp_path / "authority.db"
    with BrowserAuthority(path) as store:
        op = admit(store)
        store.start(op.id)

        def die(*args, **kwargs):
            raise RuntimeError("death after receipt commit")

        monkeypatch.setattr(store, "finish_from_execution", die)
        with pytest.raises(RuntimeError):
            store.record_reply(op.id, reply)
    with BrowserAuthority(path) as store:
        recovered = store.reconcile(op.id)
        assert recovered.disposition == ("not_sent" if reply == NO_SEND else "unknown")
        assert recovered.phase == ("not_sent" if reply == NO_SEND else "sent" if reply == ACK else "ambiguous")
        assert store.reconcile(op.id) == recovered


def test_arbitrary_finish_cannot_assert_no_send_or_completion(tmp_path):
    with BrowserAuthority(tmp_path / "authority.db") as store:
        op = admit(store)
        store.start(op.id)
        for dispatched, effect, phase in [(False, "refused", "not_sent"), (True, "confirmed", "sent")]:
            with pytest.raises(BrowserEvidenceError):
                store.finish(op.id, dispatched=dispatched, effect=effect, phase=phase, evidence={})
        assert store.get(op.id).state == "dispatching"


@pytest.mark.parametrize("failure", ["digest", "binding", "producer", "effect", "guard", "request"])
def test_tampered_browser_evidence_never_releases_custody(tmp_path, monkeypatch, failure):
    path = tmp_path / "authority.db"
    with BrowserAuthority(path) as store:
        op = admit(store)
        store.start(op.id)
        monkeypatch.setattr(store, "finish_from_execution", lambda _: None)
        store.record_reply(op.id, NO_SEND)
        row = store._db.execute("SELECT body,digest FROM operator_execution_receipts").fetchone()
        record = json.loads(row["body"])
        if failure == "binding":
            record["binding"]["loader"] = "wrong"
        elif failure == "producer":
            record["producer"]["name"] = "footwork.native"
        elif failure == "effect":
            record["effect"] = "confirmed"
        elif failure == "guard":
            record["guard"]["digest"] = "0" * 64
        elif failure == "request":
            record["request_digest"] = "0" * 64
        body = canonical(record)
        digest = "invalid" if failure == "digest" else hashlib.sha256(body.encode()).hexdigest()
        store._db.execute("UPDATE operator_execution_receipts SET body=?,digest=?", (body, digest))
    with BrowserAuthority(path) as store:
        assert store.reconcile(op.id).state == "unknown"
        with pytest.raises(Busy):
            admit(store, token="new")


def test_runtime_evidence_is_immutable(tmp_path, monkeypatch):
    with BrowserAuthority(tmp_path / "authority.db") as store:
        op = admit(store)
        store.start(op.id)
        monkeypatch.setattr(store, "finish_from_execution", lambda _: None)
        store.record_reply(op.id, ACK)
        with pytest.raises(BrowserEvidenceError, match="immutable"):
            store.record_reply(op.id, NO_SEND)


def test_browser_unknown_blocks_native_and_native_unknown_blocks_browser(tmp_path):
    path = tmp_path / "authority.db"
    with BrowserAuthority(path) as store:
        op = admit(store)
        store.start(op.id)
        store.record_reply(op.id, UNKNOWN)
    with SessionOperations(path) as store:
        assert store.status()[0].id == op.id
        with pytest.raises(Busy):
            store.admit(session_id="native", token="native", request={"words": ["click", "Delete"]},
                        resource="native:fixture", observation="obs", target="button", move="click",
                        authorization_basis="policy", projection={})
    other = tmp_path / "native.db"
    with SessionOperations(other) as store:
        native = store.admit(session_id="native", token="native", request={"words": ["click", "Delete"]},
                             resource="native:fixture", observation="obs", target="button", move="click",
                             authorization_basis="policy", projection={})
        store.start(native.id)
    with BrowserAuthority(other) as store:
        assert store.status()[0].id == native.id
        assert store.reconcile(native.id).state == "unknown"
        with pytest.raises(Busy):
            admit(store)


def test_manual_resolution_remains_unsupported(tmp_path):
    with BrowserAuthority(tmp_path / "authority.db") as store, pytest.raises(JournalError):
        store.resolve("operation", disposition="applied", evidence={"dom": "looks good"})


def test_interruption_records_unknown_without_fabricating_returned_evidence(tmp_path):
    with BrowserAuthority(tmp_path / "authority.db") as store:
        op = admit(store)
        with pytest.raises(BrowserEvidenceError):
            store.mark_unknown(op.id)
        store.start(op.id)
        unknown = store.mark_unknown(op.id)
        assert unknown.state == "unknown"
        assert unknown.phase == "ambiguous"
        assert "execution_receipt" not in unknown.evidence
        assert store.mark_unknown(op.id) == unknown
        with pytest.raises(Busy):
            admit(store, token="new")


@pytest.mark.parametrize("reply", [NO_SEND, ACK])
def test_interruption_prefers_a_retained_returned_record(tmp_path, monkeypatch, reply):
    with BrowserAuthority(tmp_path / "authority.db") as store:
        op = admit(store)
        store.start(op.id)
        finish = store.finish_from_execution
        monkeypatch.setattr(store, "finish_from_execution", lambda _: None)
        store.record_reply(op.id, reply)
        monkeypatch.setattr(store, "finish_from_execution", finish)
        result = store.mark_unknown(op.id)
        assert result.disposition == ("not_sent" if reply == NO_SEND else "unknown")
        assert result.evidence["execution_receipt"]["reply"] == reply


def test_native_retained_receipt_keeps_its_native_validator_in_browser_store(tmp_path):
    import time

    from jevdual.operator_evidence import execution_record
    from jevdual.session_operations import native_resource

    binding = {"boot": "native-boot", "pid": 77, "start": "native-start", "window_id": 12}
    path = tmp_path / "authority.db"
    with BrowserAuthority(path) as store:
        op = store.admit(session_id="native", token="native", request={"words": ["click", "Delete"]},
                         resource=native_resource(binding), observation="obs", target="button", move="click",
                         authorization_basis="policy", projection={"binding": binding})
        op = store.start(op.id)
        now = time.time()
        record = execution_record(
            op, binding=binding, started_at=now, ended_at=now,
            producer_evidence={"name": "footwork.native", "version": 1,
                               "delivery_basis": "sdk_delivery_count", "delivered_count": 1},
            dispatched=True, effect="confirmed", phase="sent", projection={"binding": binding},
        )
        store.record_execution(op.id, record)
    with BrowserAuthority(path) as store:
        result = store.reconcile(op.id)
        assert result.disposition == "applied"
        assert result.evidence["execution_receipt"] == record
