"""Offline fixture and handoff contracts; these do not qualify actual app UI."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import signal
import time
import uuid
from pathlib import Path
from types import SimpleNamespace
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest
from jevdual import ticket_evidence
from jevdual.app_qualification import (
    HandoffRun,
    QualificationError,
    TicketFixture,
    TicketStore,
    artifact_identity,
)
from jevdual.capability.journal import Busy
from jevdual.operator_evidence import execution_record
from jevdual.session_operations import SessionOperations, native_resource

BINDING = {"boot": "fixture-boot", "pid": 77, "start": "fixture-start", "window_id": 2}
EXPECTED = {
    "request_id": "d04ecb1630c74adfab25f102c01e2a7a",
    "artifact": "renamed.png",
    "orientation": "clockwise90",
    "digest": hashlib.sha256(b"fixture").hexdigest(),
}


def post(fixture, expected=EXPECTED):
    request = Request(fixture.url + "/tickets", data=urlencode(expected).encode(), method="POST")
    request.add_header("Origin", fixture.url)
    with urlopen(request, timeout=3) as reply:
        return json.loads(reply.read())


def test_real_http_form_post_and_independent_store_survive_restart(tmp_path):
    with TicketFixture(tmp_path) as fixture:
        with urlopen(fixture.url, timeout=3) as reply:
            assert b'method="post"' in reply.read()
        assert post(fixture)["recorded"]
        assert fixture.store.check(EXPECTED)["ok"]
    with TicketFixture(tmp_path) as restarted:
        assert restarted.store.check(EXPECTED)["ok"]


def test_deduplicated_row_does_not_hide_duplicate_ingress(tmp_path):
    with TicketFixture(tmp_path) as fixture:
        assert post(fixture)["recorded"]
        assert post(fixture)["recorded"]
        result = fixture.store.check(EXPECTED)
        assert len(result["tickets"]) == 1 and len(result["ingress"]) == 2
        assert not result["ok"]


def test_preheader_disconnect_keeps_ingress_but_no_qualified_boundary(tmp_path):
    with TicketFixture(tmp_path, lose_reply_once=True) as fixture:
        with pytest.raises((URLError, OSError)) as caught:
            post(fixture)
        assert caught.value is not None
        assert not fixture.store.check(EXPECTED)["ok"]
        assert len(fixture.store.snapshot()["ingress"]) == 1
        assert fixture.store.snapshot()["responses"] == []
    assert not TicketStore(tmp_path / "tickets.sqlite").check(EXPECTED)["ok"]


def test_malformed_or_duplicate_form_fields_are_retained_as_failed_ingress(tmp_path):
    store = TicketStore(tmp_path / "tickets.sqlite")
    store.record(b"request_id=one&request_id=two")
    result = store.check(EXPECTED)
    assert not result["ok"] and len(result["ingress"]) == 1
    assert result["ingress"][0]["error"] == "invalid_fields"


def test_cross_origin_post_is_refused(tmp_path):
    with TicketFixture(tmp_path) as fixture:
        request = Request(fixture.url + "/tickets", data=urlencode(EXPECTED).encode(), method="POST")
        request.add_header("Origin", "https://unrelated.invalid")
        with pytest.raises(URLError) as caught:
            urlopen(request, timeout=3)
        assert caught.value.code == 403
        assert fixture.store.snapshot()["tickets"] == []


def test_fixture_public_cli_starts_and_cleans_up_owned_listener(tmp_path):
    import select
    import subprocess
    import sys

    child = subprocess.Popen(
        [sys.executable, "-m", "jevdual.app_qualification", "--root", str(tmp_path / "server")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert select.select([child.stdout], [], [], 5)[0], "fixture CLI did not become ready"
        info = json.loads(child.stdout.readline())
        with urlopen(info["url"], timeout=3) as reply:
            assert b"Register asset" in reply.read()
        child.terminate()
        assert child.wait(5) == 0
        with pytest.raises(URLError):
            urlopen(info["url"], timeout=1)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(5)
        child.stdout.close()
        child.stderr.close()


def terminal_operation(authority, session_id="finder-session", app="Finder", *, unknown=False):
    with SessionOperations(authority) as store:
        op = store.admit(
            session_id=session_id,
            token=f"token-{time.time_ns()}",
            request={"words": ["click", "fixture"]},
            resource=native_resource(BINDING),
            observation="snapshot",
            target="1",
            move="click",
            authorization_basis="fixture_policy",
            projection={"binding": BINDING, "app": app},
        )
        store.start(op.id)
        capsule = execution_record(
            op,
            binding=BINDING,
            started_at=time.time(),
            ended_at=time.time(),
            producer_evidence={
                "name": "footwork.native",
                "version": 1,
                "delivery_basis": "sdk_delivery_count",
                "delivered_count": 1,
            },
            dispatched=True,
            effect="unverifiable" if unknown else "confirmed",
            phase="sent",
            projection={"binding": BINDING, "app": app},
        )
        store.record_execution(op.id, capsule)
        store.finish_from_execution(op.id)
        return op.id


def ticket_operation(run, fixture, artifact, expected):
    """Real pre-admission and loopback event; no browser UI is claimed."""
    scope = ticket_evidence.bind(fixture.store.path, fixture.url, expected, artifact, run.root)
    prepared = ticket_evidence.prepare(scope)
    native_scope = {"url": fixture.url, "title": "Footwork owned ticket fixture"}
    with SessionOperations(run.authority) as operations:
        op = operations.admit(
            session_id="chrome-session",
            token=uuid.uuid4().hex,
            request={
                "words": ["click", "button:Register asset"],
                "native_scope": native_scope,
                "ticket_scope": scope,
            },
            resource=native_resource(BINDING),
            observation="form",
            target="18",
            move="click",
            authorization_basis="fixture",
            projection={"binding": BINDING, "app": "Google Chrome", "ticket_submission": prepared},
        )
        operations.start(op.id)
        operations.finish(op.id, dispatched=None, effect="unverifiable", evidence={})
        post(fixture, expected)
        assert operations.reconcile(op.id).state == "final"
        return op.id


def check_bytes(path, expected):
    return lambda: SimpleNamespace(
        ok=path.read_bytes() == expected,
        detail="independent fixture bytes",
        artifact=str(path.absolute()),
        identity=artifact_identity(path.parent, path),
    )


def test_completed_handoff_is_idempotent_and_stale_next_input_refuses(tmp_path):
    artifact = tmp_path / "asset.bin"
    artifact.write_bytes(b"fixture")
    run = HandoffRun(tmp_path, tmp_path / "authority.sqlite", "epoch-1")
    run.begin("finder", session_id="finder-session")
    op_id = terminal_operation(run.authority)
    first = run.complete("finder", [op_id], check_bytes(artifact, b"fixture"), artifact)
    assert run.complete("finder", [op_id], check_bytes(artifact, b"fixture"), artifact) == first
    artifact.write_bytes(b"external edit")
    with pytest.raises(QualificationError, match="changed"):
        run.begin("preview", session_id="preview-session")


def test_unknown_domain_custody_blocks_handoff_without_oracle_call(tmp_path):
    run = HandoffRun(tmp_path, tmp_path / "authority.sqlite", "epoch")
    run.begin("finder", session_id="finder-session")
    op = terminal_operation(run.authority, unknown=True)
    with pytest.raises(Busy):
        run.complete(
            "finder",
            [op],
            lambda: pytest.fail("must not inspect after custody failure"),
            tmp_path / "missing",
        )


@pytest.mark.parametrize("variant", ["wrong_session", "wrong_app", "failed_oracle", "epoch"])
def test_handoff_never_accepts_unrelated_receipts_or_failed_oracle(tmp_path, variant):
    artifact = tmp_path / "asset.bin"
    artifact.write_bytes(b"fixture")
    run = HandoffRun(tmp_path, tmp_path / "authority.sqlite", "epoch")
    run.begin("finder", session_id="finder-session")
    op = terminal_operation(
        run.authority,
        session_id="other" if variant == "wrong_session" else "finder-session",
        app="Preview" if variant == "wrong_app" else "Finder",
    )
    if variant == "epoch":
        run = HandoffRun(tmp_path, run.authority, "changed-epoch")
    with pytest.raises(QualificationError):
        run.complete(
            "finder",
            [op],
            check_bytes(artifact, b"wrong" if variant == "failed_oracle" else b"fixture"),
            artifact,
        )


def test_unretained_manual_final_row_is_not_handoff_execution_proof(tmp_path):
    run = HandoffRun(tmp_path, tmp_path / "authority.sqlite", "epoch")
    run.begin("finder", session_id="finder-session")
    with SessionOperations(run.authority) as store:
        op = store.admit(
            session_id="finder-session",
            token="manual",
            request={},
            resource="native:fixture",
            observation="s",
            target=None,
            move="click",
            authorization_basis="fixture",
            projection={},
        )
        store.start(op.id)
        store.finish(op.id, dispatched=True, phase="sent", effect="confirmed", evidence={})
    with pytest.raises(QualificationError, match="retained"):
        run.complete("finder", [op.id], lambda: pytest.fail("not a qualified receipt"), tmp_path / "missing")


def test_artifact_identity_rejects_parent_symlink_and_wrong_root(tmp_path):
    owned = tmp_path / "owned"
    owned.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    (other / "asset").write_bytes(b"x")
    (owned / "alias").symlink_to(other, target_is_directory=True)
    with pytest.raises(QualificationError):
        artifact_identity(owned, owned / "alias" / "asset")
    with pytest.raises(QualificationError):
        artifact_identity(owned, other / "asset")


def test_three_app_handoff_protocol_with_independent_oracles_and_restarts(tmp_path):
    """App effects below are simulated; checks and durable handoff API are real."""
    from jevdual.app_oracles import check_finder, check_preview, create_fixture
    from PIL import Image

    root = tmp_path / "owned"
    root.mkdir()
    manifest = create_fixture(root / "artifacts")
    fixture_root = Path(manifest["root"])
    authority = root / "authority.sqlite"
    artifact = fixture_root / manifest["paths"]["organized"]
    run = HandoffRun(root, authority, "three-app-epoch")
    run.begin("finder", session_id="finder-session")
    (fixture_root / manifest["paths"]["source"]).rename(artifact)
    finder_op = terminal_operation(authority)
    run.complete(
        "finder", [finder_op], lambda: check_finder(manifest, manifest["paths"]["organized"]), artifact
    )

    # Reopening the controller simulates a host restart between distinct apps.
    run = HandoffRun(root, authority, "three-app-epoch")
    run.begin("preview", session_id="preview-session")
    with Image.open(artifact) as image:
        rotated = image.transpose(Image.Transpose.ROTATE_270)
        rotated.save(artifact)
    preview_ops = [
        terminal_operation(authority, session_id="preview-session", app="Preview") for _ in range(2)
    ]
    run.complete("preview", preview_ops, lambda: check_preview(manifest, artifact), artifact)

    run = HandoffRun(root, authority, "three-app-epoch")
    run.begin("chrome", session_id="chrome-session")
    expected = {**EXPECTED, "artifact": artifact.name, "digest": artifact_identity(root, artifact)["sha256"]}
    with TicketFixture(root / "ticket-server") as fixture:
        chrome_op = ticket_operation(run, fixture, artifact, expected)
        run.complete("chrome", [chrome_op], lambda: fixture.store.check(expected), artifact)
    assert [stage["stage"] for stage in run.snapshot()["completed"]] == ["finder", "preview", "chrome"]


def test_changed_handoff_manifest_is_refused(tmp_path):
    run = HandoffRun(tmp_path, tmp_path / "authority.sqlite", "epoch")
    run.begin("finder", session_id="finder-session")
    state = json.loads(run.path.read_text())
    state["active"]["session_id"] = "forged"
    run.path.write_text(json.dumps(state))
    with pytest.raises(QualificationError, match="integrity"):
        run.snapshot()


def test_handoff_rejects_oracle_for_a_different_artifact(tmp_path):
    checked, supplied = tmp_path / "checked.bin", tmp_path / "supplied.bin"
    checked.write_bytes(b"same bytes")
    supplied.write_bytes(b"same bytes")
    run = HandoffRun(tmp_path, tmp_path / "authority.sqlite", "epoch")
    run.begin("finder", session_id="finder-session")
    operation = terminal_operation(run.authority)
    with pytest.raises(QualificationError, match="different artifact identity"):
        run.complete("finder", [operation], check_bytes(checked, b"same bytes"), supplied)


def test_handoff_rechecks_artifact_after_the_oracle(tmp_path):
    artifact = tmp_path / "asset.bin"
    artifact.write_bytes(b"fixture")
    run = HandoffRun(tmp_path, tmp_path / "authority.sqlite", "epoch")
    run.begin("finder", session_id="finder-session")
    operation = terminal_operation(run.authority)

    def mutate_after_read():
        result = check_bytes(artifact, b"fixture")()
        artifact.write_bytes(b"changed after oracle read")
        return result

    with pytest.raises(QualificationError, match="changed during oracle"):
        run.complete("finder", [operation], mutate_after_read, artifact)


def prepare_preview(root):
    from jevdual.app_oracles import check_finder, create_fixture

    root.mkdir()
    manifest = create_fixture(root / "artifacts")
    artifact = Path(manifest["root"]) / manifest["paths"]["organized"]
    run = HandoffRun(root, root / "authority.sqlite", "epoch")
    run.begin("finder", session_id="finder-session")
    (Path(manifest["root"]) / manifest["paths"]["source"]).rename(artifact)
    operation = terminal_operation(run.authority)
    run.complete(
        "finder", [operation], lambda: check_finder(manifest, manifest["paths"]["organized"]), artifact
    )
    run.begin("preview", session_id="preview-session")
    return run, manifest, artifact


@pytest.mark.parametrize("variant", ["database", "nonce", "fixture_id", "origin"])
def test_chrome_handoff_rejects_another_service_source(tmp_path, variant):
    from jevdual.app_oracles import check_preview
    from PIL import Image

    run, manifest, artifact = prepare_preview(tmp_path / "run")
    with Image.open(artifact) as image:
        image.transpose(Image.Transpose.ROTATE_270).save(artifact)
    operation = terminal_operation(run.authority, session_id="preview-session", app="Preview")
    run.complete("preview", [operation], lambda: check_preview(manifest, artifact), artifact)
    run.begin("chrome", session_id="chrome-session")
    expected = {
        **EXPECTED,
        "request_id": uuid.uuid4().hex,
        "artifact": artifact.name,
        "digest": artifact_identity(run.root, artifact)["sha256"],
    }
    with TicketFixture(run.root / "admitted") as admitted, TicketFixture(run.root / "other") as other:
        operation = ticket_operation(run, admitted, artifact, expected)
        other_expected = {**expected, "request_id": uuid.uuid4().hex} if variant == "nonce" else expected
        if variant == "database":
            post(other, other_expected)
            checked = other
        else:
            checked = admitted
            with admitted.store._db() as database:
                if variant == "nonce":
                    database.execute(
                        "UPDATE ingress SET fields=?,body_sha=?",
                        (
                            json.dumps(other_expected),
                            hashlib.sha256(ticket_evidence.form_body(other_expected)).hexdigest(),
                        ),
                    )
                    database.execute(
                        "UPDATE tickets SET request_id=?,fields=?",
                        (other_expected["request_id"], json.dumps(other_expected)),
                    )
                else:
                    database.execute(
                        "UPDATE fixture_state SET value=? WHERE key=?",
                        (uuid.uuid4().hex if variant == "fixture_id" else "http://127.0.0.1:8766", variant),
                    )
        assert checked.store.check(other_expected)["ok"]
        with pytest.raises(QualificationError, match="admitted"):
            run.complete("chrome", [operation], lambda: checked.store.check(other_expected), artifact)


@pytest.mark.parametrize("legacy", [False, True])
def test_new_chrome_handoff_requires_current_service_contract(tmp_path, monkeypatch, legacy):
    from jevdual.app_oracles import check_preview
    from PIL import Image

    run, manifest, artifact = prepare_preview(tmp_path / "run")
    with Image.open(artifact) as image:
        image.transpose(Image.Transpose.ROTATE_270).save(artifact)
    operation = terminal_operation(run.authority, session_id="preview-session", app="Preview")
    run.complete("preview", [operation], lambda: check_preview(manifest, artifact), artifact)
    run.begin("chrome", session_id="chrome-session")
    expected = {
        **EXPECTED,
        "artifact": artifact.name,
        "digest": artifact_identity(run.root, artifact)["sha256"],
    }
    with TicketFixture(run.root / "service") as fixture:
        if legacy:
            operation = ticket_operation(run, fixture, artifact, expected)
            original = SessionOperations.qualified_receipt

            def historical(store, op):
                # Historical v1 parsing is exercised with literal persisted rows
                # in test_session_ticket_reconciliation; challenge this gate here.
                result = original(store, op)
                return {**result, "schema_version": 1} if op.id == operation else result

            monkeypatch.setattr(SessionOperations, "qualified_receipt", historical)
        else:
            operation = terminal_operation(run.authority, session_id="chrome-session", app="Google Chrome")
        with pytest.raises(QualificationError, match="admitted v2"):
            run.complete("chrome", [operation], lambda: fixture.store.check(expected), artifact)


def test_preview_rejects_counterclockwise_oracle_even_when_it_passes(tmp_path):
    from jevdual.app_oracles import check_preview
    from PIL import Image

    run, manifest, artifact = prepare_preview(tmp_path / "run")
    with Image.open(artifact) as image:
        image.transpose(Image.Transpose.ROTATE_90).save(artifact)
    operation = terminal_operation(run.authority, session_id="preview-session", app="Preview")
    assert check_preview(manifest, artifact, clockwise=False).ok
    with pytest.raises(QualificationError, match="clockwise transform"):
        run.complete(
            "preview", [operation], lambda: check_preview(manifest, artifact, clockwise=False), artifact
        )


@pytest.mark.parametrize("variant", ["wrong_digest", "changed_artifact", "arbitrary_ok"])
def test_chrome_ticket_evidence_is_bound_to_the_input_artifact(tmp_path, variant):
    from jevdual.app_oracles import check_preview
    from PIL import Image

    run, manifest, artifact = prepare_preview(tmp_path / "run")
    with Image.open(artifact) as image:
        image.transpose(Image.Transpose.ROTATE_270).save(artifact)
    operation = terminal_operation(run.authority, session_id="preview-session", app="Preview")
    run.complete("preview", [operation], lambda: check_preview(manifest, artifact), artifact)
    run.begin("chrome", session_id="chrome-session")
    if variant == "changed_artifact":
        artifact.write_bytes(b"browser must not modify the verified image")
    expected = {
        **EXPECTED,
        "artifact": artifact.name,
        "digest": "0" * 64 if variant == "wrong_digest" else artifact_identity(run.root, artifact)["sha256"],
    }
    with TicketFixture(run.root / "tickets") as fixture:
        post(fixture, expected)
        operation = terminal_operation(run.authority, session_id="chrome-session", app="Google Chrome")
        assert fixture.store.check(expected)["ok"]
        verify = (
            (lambda: {"ok": True}) if variant == "arbitrary_ok" else (lambda: fixture.store.check(expected))
        )
        with pytest.raises(QualificationError):
            run.complete("chrome", [operation], verify, artifact)


def _kill_handoff_child(root, boundary, channel):
    root = Path(root)
    run = HandoffRun(root, root / "authority.sqlite", "epoch")
    run.begin("finder", session_id="finder-session")
    operation = None
    if boundary != "begun":
        artifact = root / "asset.bin"
        artifact.write_bytes(b"fixture")  # simulated driver boundary, not an actual Finder action
        with (root / "independent-inputs").open("a") as stream:
            stream.write("one simulated input\n")
            stream.flush()
            os.fsync(stream.fileno())
        operation = terminal_operation(run.authority)
        if boundary == "completed":
            run.complete("finder", [operation], check_bytes(artifact, b"fixture"), artifact)
    channel.send(operation)
    signal.pause()


@pytest.mark.parametrize("boundary", ["begun", "effect", "completed"])
def test_sigkill_handoff_recovery_never_repeats_fixture_effect(tmp_path, boundary):
    context = multiprocessing.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    child = context.Process(target=_kill_handoff_child, args=(str(tmp_path), boundary, writer))
    child.start()
    try:
        assert reader.poll(10)
        operation = reader.recv()
        child.kill()
        child.join(10)
        assert child.exitcode == -signal.SIGKILL
        run = HandoffRun(tmp_path, tmp_path / "authority.sqlite", "epoch")
        if operation is None:
            assert run.begin("finder", session_id="finder-session")["stage"] == "finder"
        else:
            artifact = tmp_path / "asset.bin"
            run.complete("finder", [operation], check_bytes(artifact, b"fixture"), artifact)
            assert len(run.snapshot()["completed"]) == 1
        ledger = tmp_path / "independent-inputs"
        assert (len(ledger.read_text().splitlines()) if ledger.exists() else 0) == (
            0 if boundary == "begun" else 1
        )
    finally:
        if child.is_alive():
            child.kill()
            child.join(10)
        reader.close()
        writer.close()


def _kill_cross_app_child(root, completed_stage, channel):
    """Simulated app mutations and real oracles/receipts; parent kills this host."""
    from jevdual.app_oracles import check_finder, check_preview, create_fixture
    from PIL import Image

    root = Path(root)
    manifest = create_fixture(root / "artifacts")
    artifact_root = Path(manifest["root"])
    artifact = artifact_root / manifest["paths"]["organized"]
    run = HandoffRun(root, root / "authority.sqlite", "epoch")
    run.begin("finder", session_id="finder-session")
    (artifact_root / manifest["paths"]["source"]).rename(artifact)
    finder = terminal_operation(run.authority)
    run.complete("finder", [finder], lambda: check_finder(manifest, manifest["paths"]["organized"]), artifact)
    count = 1
    if completed_stage == "preview":
        run.begin("preview", session_id="preview-session")
        with Image.open(artifact) as image:
            image.transpose(Image.Transpose.ROTATE_270).save(artifact)
        preview = [
            terminal_operation(run.authority, session_id="preview-session", app="Preview") for _ in range(2)
        ]
        run.complete("preview", preview, lambda: check_preview(manifest, artifact), artifact)
        count += 2
    with (root / "cross-app-inputs").open("w") as ledger:
        ledger.write("simulated input\n" * count)
        ledger.flush()
        os.fsync(ledger.fileno())
    channel.send(count)
    signal.pause()


@pytest.mark.parametrize("completed_stage,next_stage", [("finder", "preview"), ("preview", "chrome")])
def test_sigkill_between_distinct_app_handoffs_preserves_identity_and_no_input(
    tmp_path, completed_stage, next_stage
):
    context = multiprocessing.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    child = context.Process(target=_kill_cross_app_child, args=(str(tmp_path), completed_stage, writer))
    child.start()
    try:
        assert reader.poll(10)
        expected_count = reader.recv()
        child.kill()
        child.join(10)
        assert child.exitcode == -signal.SIGKILL
        run = HandoffRun(tmp_path, tmp_path / "authority.sqlite", "epoch")
        first = run.begin(next_stage, session_id=next_stage + "-session")
        assert run.begin(next_stage, session_id=next_stage + "-session") == first
        assert len((tmp_path / "cross-app-inputs").read_text().splitlines()) == expected_count
    finally:
        if child.is_alive():
            child.kill()
            child.join(10)
        reader.close()
        writer.close()
