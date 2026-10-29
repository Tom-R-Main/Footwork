"""Independent ticket ingress can qualify only a pre-bound attempt, never matching state alone."""

from __future__ import annotations

import copy
import hashlib
import http.client
import json
import sqlite3
import subprocess
import sys
import time
import uuid
from types import SimpleNamespace
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest
from jevdual import ticket_evidence as te
from jevdual.app_qualification import TicketFixture, TicketStore

BINDING = {"boot": "test-boot", "pid": 77, "start": "test-start", "window_id": 12}
URL = "http://127.0.0.1:8765"


def setup(tmp_path, *, response_mode="normal"):
    root = tmp_path / "owned"
    root.mkdir()
    artifact = root / "renamed.png"
    artifact.write_bytes(b"independently preserved synthetic artifact")
    store = TicketStore(root / "tickets.sqlite")
    store.bind_origin(URL)
    store.bind_response_mode(response_mode)
    expected = {
        "request_id": uuid.uuid4().hex,
        "artifact": artifact.name,
        "orientation": "clockwise90",
        "digest": hashlib.sha256(artifact.read_bytes()).hexdigest(),
    }
    scope = te.bind(store.path, URL, expected, artifact, root)
    prepared = te.prepare(scope)
    op = SimpleNamespace(
        id="op_one",
        task="session_one",
        request_digest="request-one",
        resource="native:test",
        observation="obs_one",
        target="18",
        move="click",
        created=time.time(),
        execution_stage="started",
        state="unknown",
        phase="ambiguous",
        disposition="unknown",
        args={
            "words": ["click", "button:Register asset"],
            "ticket_scope": scope,
            "native_scope": {"url": URL, "title": "Footwork owned ticket fixture"},
        },
    )
    return root, artifact, store, expected, scope, prepared, op


def submit(store, expected):
    *result, ingress_id = store.record(te.form_body(expected), origin=URL, include_ingress_id=True)
    store.record_response(ingress_id, "headers_flushed")
    return tuple(result)


def test_unique_prebound_ingress_qualifies_and_receipt_is_historical(tmp_path):
    _, _, store, expected, _, prepared, op = setup(tmp_path)
    submit(store, expected)
    receipt = te.qualify(op, prepared, BINDING)
    assert receipt["kind"] == "ticket_submission"
    assert receipt["producer"] == "footwork.ticket_ledger/v2"
    assert receipt["operation_id"] == op.id and receipt["phase"] == "sent"
    assert receipt["effect"] == "confirmed"
    assert "delivered_count" not in receipt
    # Retained receipt validation dispatches/reads nothing after capture.
    store.path.unlink()
    assert te.validate_receipt(receipt, op, prepared, BINDING) == receipt


def test_no_ingress_stays_unknown(tmp_path):
    *_, prepared, op = setup(tmp_path)
    assert te.qualify(op, prepared, BINDING) is None


def test_no_retroactive_enrollment_after_existing_ticket(tmp_path):
    _, artifact, store, expected, scope, _, _ = setup(tmp_path)
    submit(store, expected)
    with pytest.raises(te.TicketEvidenceError):
        te.prepare(scope)
    with pytest.raises(te.TicketEvidenceError):
        te.bind(store.path, URL, expected, artifact, artifact.parent)


@pytest.mark.parametrize(
    "change",
    [
        "duplicates",
        "wrong_fields",
        "wrong_origin",
        "old_timestamp",
        "bad_hash",
        "missing_row",
        "conflicting_row",
    ],
)
def test_conflicting_or_uncorrelated_ingress_does_not_qualify(tmp_path, change):
    _, _, store, expected, _, prepared, op = setup(tmp_path)
    submit(store, expected)
    if change == "duplicates":
        submit(store, expected)
    with sqlite3.connect(store.path) as db:
        if change == "wrong_fields":
            db.execute("UPDATE ingress SET fields=?", (json.dumps({**expected, "digest": "0" * 64}),))
        elif change == "wrong_origin":
            db.execute("UPDATE ingress SET origin='http://127.0.0.1:8766'")
        elif change == "old_timestamp":
            db.execute("UPDATE ingress SET received=?", (op.created - 1,))
        elif change == "bad_hash":
            db.execute("UPDATE ingress SET body_sha=?", ("f" * 64,))
        elif change == "missing_row":
            db.execute("DELETE FROM tickets")
        elif change == "conflicting_row":
            db.execute("UPDATE tickets SET fields=?", (json.dumps({**expected, "artifact": "other.png"}),))
    assert te.qualify(op, prepared, BINDING) is None


@pytest.mark.parametrize(
    "change", ["artifact", "database", "fixture_id", "origin", "source_symlink", "ancestor_symlink"]
)
def test_changed_bound_source_or_artifact_refuses(tmp_path, change):
    root, artifact, store, expected, _, prepared, op = setup(tmp_path)
    submit(store, expected)
    if change == "artifact":
        artifact.write_bytes(b"changed")
    elif change == "database":
        replacement = root / "replacement.sqlite"
        with sqlite3.connect(store.path) as source, sqlite3.connect(replacement) as destination:
            source.backup(destination)
        store.path.replace(root / "retained.sqlite")
        replacement.replace(store.path)
    elif change == "fixture_id":
        with sqlite3.connect(store.path) as db:
            db.execute("UPDATE fixture_state SET value=? WHERE key='fixture_id'", (uuid.uuid4().hex,))
    elif change == "origin":
        store.bind_origin("http://127.0.0.1:8766")
    elif change == "source_symlink":
        retained = root / "retained.sqlite"
        store.path.rename(retained)
        store.path.symlink_to(retained)
    else:
        moved = root.with_name("moved")
        root.rename(moved)
        root.symlink_to(moved, target_is_directory=True)
    with pytest.raises(te.TicketEvidenceError):
        te.qualify(op, prepared, BINDING)


@pytest.mark.parametrize(
    "change", ["operation", "digest", "binding", "fields", "preparation", "predicate", "snapshot", "version"]
)
def test_retained_receipt_cannot_be_transplanted_or_rewritten(tmp_path, change):
    _, _, store, expected, _, prepared, op = setup(tmp_path)
    submit(store, expected)
    receipt = te.qualify(op, prepared, BINDING)
    altered = copy.deepcopy(receipt)
    if change == "operation":
        altered["operation_id"] = "op_other"
    elif change == "digest":
        altered["request_digest"] = "other"
    elif change == "binding":
        altered["binding"]["window_id"] = 99
    elif change == "fields":
        altered["expected"]["artifact"] = "other.png"
    elif change == "preparation":
        altered["preparation_sha256"] = "0" * 64
    elif change == "predicate":
        altered["predicate"] = "current_matching_row"
    elif change == "snapshot":
        altered["capture"]["snapshot"]["ingress"] *= 2
    else:
        altered["schema_version"] = True
    with pytest.raises(te.TicketEvidenceError):
        te.validate_receipt(altered, op, prepared, BINDING)


def test_restart_same_origin_keeps_fixture_identity_and_qualifies_lost_response(tmp_path):
    _, _, store, expected, scope, prepared, op = setup(tmp_path, response_mode="truncated")
    _, error, lost, ingress_id = store.record(
        te.form_body(expected), origin=URL, lose_reply_once=True, include_ingress_id=True
    )
    store.record_response(ingress_id, "headers_flushed")
    assert error is None and lost
    restarted = TicketStore(store.path)
    restarted.bind_origin(URL)
    receipt = te.qualify(op, prepared, BINDING)
    assert receipt["source"]["fixture_id"] == scope["source"]["fixture_id"]


@pytest.mark.parametrize("request_id", ["short", "dev-request-1", "0" * 32, "A" * 32])
def test_scope_requires_a_fresh_nonce(tmp_path, request_id):
    root, artifact, store, expected, *_ = setup(tmp_path)
    with pytest.raises(te.TicketEvidenceError):
        te.bind(store.path, URL, {**expected, "request_id": request_id}, artifact, root)


def test_preparation_cannot_follow_operation_or_use_another_scope(tmp_path):
    _, _, store, expected, _, prepared, op = setup(tmp_path)
    submit(store, expected)
    later = copy.deepcopy(prepared)
    later["captured_at"] = op.created + 1
    with pytest.raises(te.TicketEvidenceError):
        te.qualify(op, later, BINDING)
    changed = copy.deepcopy(prepared)
    changed["scope"]["expected"]["request_id"] = uuid.uuid4().hex
    with pytest.raises(te.TicketEvidenceError):
        te.qualify(op, changed, BINDING)


def test_known_no_send_cannot_be_overruled_by_a_service_event(tmp_path):
    _, _, store, expected, _, prepared, op = setup(tmp_path)
    submit(store, expected)
    op.state, op.disposition, op.phase = "final", "not_sent", "not_sent"
    with pytest.raises(te.TicketEvidenceError):
        te.qualify(op, prepared, BINDING)


def test_preheader_disconnect_does_not_qualify_even_after_server_exit(tmp_path):
    root = tmp_path / "owned"
    root.mkdir()
    artifact = root / "renamed.png"
    artifact.write_bytes(b"synthetic independent artifact")
    expected = {
        "request_id": uuid.uuid4().hex,
        "artifact": artifact.name,
        "orientation": "clockwise90",
        "digest": hashlib.sha256(artifact.read_bytes()).hexdigest(),
    }
    with TicketFixture(root / "service", lose_reply_once=True) as fixture:
        scope = te.bind(fixture.store.path, fixture.url, expected, artifact, root)
        prepared = te.prepare(scope)
        op = SimpleNamespace(
            id="op_http",
            task="session_http",
            request_digest="http-request",
            resource="native:test",
            observation="obs_http",
            target="18",
            move="click",
            created=time.time(),
            execution_stage="started",
            state="unknown",
            phase="ambiguous",
            disposition="unknown",
            args={
                "words": ["click", "button:Register asset"],
                "ticket_scope": scope,
                "native_scope": {"url": fixture.url, "title": "Footwork owned ticket fixture"},
            },
        )
        request = Request(fixture.url + "/tickets", data=te.form_body(expected), method="POST")
        request.add_header("Origin", fixture.url)
        with pytest.raises((URLError, OSError)):
            urlopen(request, timeout=3)
        before = fixture.store.snapshot()
    receipt = te.qualify(op, prepared, BINDING)
    assert receipt is None
    after = TicketStore(fixture.store.path).snapshot()
    assert after == before and len(after["ingress"]) == 1


def test_ingress_without_response_boundary_does_not_qualify(tmp_path):
    _, _, store, expected, _, prepared, op = setup(tmp_path)
    store.record(te.form_body(expected), origin=URL)
    assert te.qualify(op, prepared, BINDING) is None


@pytest.mark.parametrize(
    "variant", ["missing", "foreign_ingress", "mode", "before_ingress", "future", "boolean_time", "boundary"]
)
def test_response_boundary_must_match_its_ingress(tmp_path, variant):
    _, _, store, expected, _, prepared, op = setup(tmp_path)
    submit(store, expected)
    receipt = te.qualify(op, prepared, BINDING)
    response = receipt["capture"]["snapshot"]["responses"][0]
    if variant == "missing":
        receipt["capture"]["snapshot"]["responses"] = []
    elif variant == "foreign_ingress":
        response["ingress_id"] += 1
    elif variant == "mode":
        response["mode"] = "disconnect"
    elif variant == "before_ingress":
        response["completed"] = op.created - 1
    elif variant == "future":
        response["completed"] = time.time() + 100
    elif variant == "boolean_time":
        response["completed"] = True
    else:
        response["boundary"] = "ingress_committed"
    with pytest.raises(te.TicketEvidenceError):
        te.validate_receipt(receipt, op, prepared, BINDING)


def test_bound_response_mode_cannot_change_or_forge_completion(tmp_path):
    _, _, store, expected, _, prepared, op = setup(tmp_path, response_mode="disconnect")
    *_, ingress_id = store.record(
        te.form_body(expected), origin=URL, lose_reply_once=True, include_ingress_id=True
    )
    with pytest.raises(ValueError, match="response mode"):
        store.bind_response_mode("truncated")
    with pytest.raises(ValueError, match="response boundary"):
        store.record_response(ingress_id, "headers_flushed")
    assert te.qualify(op, prepared, BINDING) is None


@pytest.mark.parametrize("field", ["counts", "binding"])
def test_boolean_numeric_receipt_metadata_refuses(tmp_path, field):
    _, _, store, expected, _, prepared, op = setup(tmp_path)
    submit(store, expected)
    binding = {**BINDING, "window_id": 1}
    receipt = te.qualify(op, prepared, binding)
    if field == "counts":
        receipt["capture"]["snapshot"]["counts"]["ingress"] = True
    else:
        receipt["binding"]["window_id"] = True
    with pytest.raises(te.TicketEvidenceError):
        te.validate_receipt(receipt, op, prepared, binding)


def test_artifact_mutation_refuses_preparation_before_input(tmp_path):
    _, artifact, _, _, scope, *_ = setup(tmp_path)
    artifact.write_bytes(b"changed before admission")
    with pytest.raises(te.TicketEvidenceError):
        te.prepare(scope)


def test_future_receipt_capture_refuses(tmp_path):
    _, _, store, expected, _, prepared, op = setup(tmp_path)
    submit(store, expected)
    receipt = te.qualify(op, prepared, BINDING)
    receipt["capture"]["checked_at"] = time.time() + 100
    receipt["interval"]["end"] = receipt["capture"]["checked_at"]
    with pytest.raises(te.TicketEvidenceError):
        te.validate_receipt(receipt, op, prepared, BINDING)


def test_atomic_admission_validation_accepts_prepared_but_receipt_requires_started(tmp_path):
    _, _, store, expected, _, prepared, op = setup(tmp_path)
    op.execution_stage = "prepared"
    assert te.validate_preparation(op, prepared, BINDING) == prepared
    submit(store, expected)
    with pytest.raises(te.TicketEvidenceError):
        te.qualify(op, prepared, BINDING)
    op.execution_stage = "started"
    assert te.qualify(op, prepared, BINDING) is not None


def test_atomic_admission_refuses_other_request_scope(tmp_path):
    _, _, _, _, _, prepared, op = setup(tmp_path)
    op.execution_stage = "prepared"
    op.args["ticket_scope"] = {**op.args["ticket_scope"], "url": "http://127.0.0.1:8766"}
    with pytest.raises(te.TicketEvidenceError):
        te.validate_preparation(op, prepared, BINDING)


def test_truncated_body_loses_application_reply_after_headers_with_one_ingress(tmp_path, monkeypatch):
    root = tmp_path / "owned"
    root.mkdir()
    artifact = root / "renamed.png"
    artifact.write_bytes(b"synthetic independently bound artifact")
    expected = {
        "request_id": uuid.uuid4().hex,
        "artifact": artifact.name,
        "orientation": "clockwise90",
        "digest": hashlib.sha256(artifact.read_bytes()).hexdigest(),
    }
    with TicketFixture(root / "service", lose_reply_once=True, reply_loss="truncated") as fixture:
        scope = te.bind(fixture.store.path, fixture.url, expected, artifact, root)
        prepared = te.prepare(scope)
        op = SimpleNamespace(
            id="op_truncated",
            task="session_truncated",
            request_digest="truncated-request",
            resource="native:test",
            observation="obs_truncated",
            target="18",
            move="click",
            created=time.time(),
            execution_stage="started",
            state="unknown",
            phase="ambiguous",
            disposition="unknown",
            args={
                "words": ["click", "button:Register asset"],
                "ticket_scope": scope,
                "native_scope": {"url": fixture.url, "title": "Footwork owned ticket fixture"},
            },
        )
        request = Request(fixture.url + "/tickets", data=te.form_body(expected), method="POST")
        request.add_header("Origin", fixture.url)
        with urlopen(request, timeout=3) as response:
            assert response.status == 200 and int(response.headers["Content-Length"]) > 0
            with pytest.raises(http.client.IncompleteRead) as error:
                response.read()
            assert error.value.partial == b"" and error.value.expected > 0
        assert len(fixture.store.snapshot()["ingress"]) == 1
        receipt = te.qualify(op, prepared, BINDING)
        assert receipt["kind"] == "ticket_submission" and receipt["effect"] == "confirmed"

    def forbidden(*_, **__):
        raise AssertionError("historical validation must not recapture the service")

    monkeypatch.setattr(te, "_capture", forbidden)
    assert te.validate_receipt(receipt, op, prepared, BINDING) == receipt


def test_truncated_reply_fault_occurs_once_across_server_restart(tmp_path):
    expected = {
        "request_id": uuid.uuid4().hex,
        "artifact": "renamed.png",
        "orientation": "clockwise90",
        "digest": "f" * 64,
    }
    with TicketFixture(tmp_path / "service", lose_reply_once=True, reply_loss="truncated") as fixture:
        request = Request(fixture.url + "/tickets", data=te.form_body(expected), method="POST")
        request.add_header("Origin", fixture.url)
        with urlopen(request, timeout=3) as response, pytest.raises(http.client.IncompleteRead):
            response.read()
        original_fixture_id = te._snapshot(fixture.store.path, tmp_path)[0]["fixture_id"]
    with TicketFixture(tmp_path / "service", lose_reply_once=True, reply_loss="truncated") as restarted:
        next_expected = {**expected, "request_id": uuid.uuid4().hex}
        request = Request(restarted.url + "/tickets", data=te.form_body(next_expected), method="POST")
        request.add_header("Origin", restarted.url)
        with urlopen(request, timeout=3) as response:
            assert json.loads(response.read())["recorded"] is True
        snapshot = restarted.store.snapshot()
        assert len(snapshot["ingress"]) == 2 and len(snapshot["tickets"]) == 2
        assert te._snapshot(restarted.store.path, tmp_path)[0]["fixture_id"] == original_fixture_id


@pytest.mark.parametrize("mode", ["unknown", None, False])
def test_invalid_reply_loss_mode_refuses_before_server_creation(tmp_path, mode):
    with pytest.raises(ValueError):
        TicketFixture(tmp_path / "service", lose_reply_once=True, reply_loss=mode)
    assert not (tmp_path / "service").exists()


def test_truncated_mode_requires_loss_flag(tmp_path):
    with pytest.raises(ValueError):
        TicketFixture(tmp_path / "service", reply_loss="truncated")
    assert not (tmp_path / "service").exists()


@pytest.mark.parametrize(
    "arguments", [["--reply-loss", "truncated"], ["--lose-reply-once", "--reply-loss", "unknown"]]
)
def test_reply_loss_cli_refuses_invalid_configuration_without_startup(tmp_path, arguments):
    root = tmp_path / "server"
    result = subprocess.run(
        [sys.executable, "-m", "jevdual.app_qualification", "--root", str(root), *arguments],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 2 and not root.exists()
