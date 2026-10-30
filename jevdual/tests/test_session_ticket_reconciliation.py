"""Real durable admission/recovery with synthetic native attempts and an independent service ledger.

No native app is driven. One case uses actual lost-response loopback HTTP; the
SIGKILL case kills a real owned controller between durable receipt retention and
finalization. Neither should be counted as installed browser qualification.
"""

from __future__ import annotations

import contextlib
import hashlib
import http.client
import json
import multiprocessing
import os
import signal
import sys
import threading
import time
import uuid
from pathlib import Path
from types import SimpleNamespace
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest
from jevdual import cli, grants, session, ticket_evidence
from jevdual.app_oracles import check_finder, check_preview, create_fixture
from jevdual.app_qualification import HandoffRun, TicketFixture, TicketStore
from jevdual.capability.journal import Busy, JournalError
from jevdual.operator_evidence import execution_record
from jevdual.session_operations import SessionOperations, native_binding, native_resource

BINDING = {"boot": "synthetic-boot", "pid": 77, "start": "dead-browser-start", "window_id": 12}
SESSION = "synthetic-chrome-session"
URL = "http://127.0.0.1:8765"


def package(root, *, store=None, url=URL, artifact=None, completion_policy="response"):
    root.mkdir(exist_ok=True)
    if artifact is None:
        artifact = root / "renamed.png"
        artifact.write_bytes(b"synthetic independently bound artifact")
    store = store or TicketStore(root / "tickets.sqlite")
    store.bind_origin(url)
    expected = {
        "request_id": uuid.uuid4().hex,
        "artifact": artifact.name,
        "orientation": "clockwise90",
        "digest": hashlib.sha256(artifact.read_bytes()).hexdigest(),
    }
    scope = ticket_evidence.bind(
        store.path, url, expected, artifact, root, completion_policy=completion_policy
    )
    native_scope = {"url": url, "title": "Footwork owned ticket fixture"}
    prepared = ticket_evidence.prepare(scope)
    request = {
        "words": ["click", "button:Register asset"],
        "authorize": "",
        "no_judge": True,
        "from_session": None,
        "route": None,
        "native_scope": native_scope,
        "ticket_scope": scope,
    }
    projection = {
        "binding": BINDING,
        "app": "Google Chrome",
        "native_scope": native_scope,
        "ticket_submission": prepared,
        "line": "click(Register asset)",
        "step": 1,
        "driver_effect": "unverifiable",
        "op": "click",
        "target_id": 18,
        "target_label": "Register asset",
        "intended": None,
        "secret": False,
        "mode": "native",
    }
    proposal = grants.Proposal("click", url, "button", "Register asset", None, None)
    return {
        "root": str(root),
        "authority": str(root / "authority.sqlite"),
        "scope": scope,
        "prepared": prepared,
        "request": request,
        "projection": projection,
        "expected": expected,
        "proposal": proposal,
    }


def issue(operations, item, *, uses=1):
    grant = grants.issue(item["proposal"], uses=uses)
    operations.issue_grant(SESSION, grant, resource=native_binding(BINDING))
    return grant


def admit(operations, item, *, token="submit-once", projection=None, request=None):
    return operations.admit(
        session_id=SESSION,
        token=token,
        request=request or item["request"],
        resource=native_resource(BINDING),
        observation="observed-form",
        target="18",
        move="click",
        proposal=item["proposal"],
        grant_resource=native_binding(BINDING),
        authorization_basis="exact_grant",
        projection=projection or item["projection"],
    )


def unknown(operations, item, op):
    op = operations.start(op.id)
    started = time.time()
    projection = {
        **item["projection"],
        "operation_id": op.id,
        "observation": op.observation,
        "dispatched": True,
        "error": "native reply did not qualify delivery",
    }
    capsule = execution_record(
        op,
        binding=BINDING,
        started_at=started,
        ended_at=time.time(),
        producer_evidence={
            "name": "footwork.native",
            "version": 1,
            "delivery_basis": "unknown",
            "delivered_count": None,
        },
        dispatched=True,
        phase="ambiguous",
        effect="unverifiable",
        projection=projection,
        error=projection["error"],
    )
    operations.record_execution(op.id, capsule)
    return operations.finish_from_execution(op.id), capsule


def service_event(item, *, fields=None, origin=None):
    store = TicketStore(Path(item["scope"]["source"]["database"]))
    *result, ingress_id = store.record(
        ticket_evidence.form_body(fields or item["expected"]),
        origin=origin or item["scope"]["url"],
        include_ingress_id=True,
    )
    store.record_response(ingress_id, "headers_flushed")
    return tuple(result)


@pytest.mark.parametrize("mode", ["disconnect", "normal", "truncated"])
def test_reconcile_before_preheader_disconnect_keeps_unknown(tmp_path, monkeypatch, mode):
    """The first committed ingress precedes the response that can trigger a replay."""
    committed, release = threading.Event(), threading.Event()
    original = TicketStore.record

    def pause_after_commit(store, *args, **kwargs):
        result = original(store, *args, **kwargs)
        committed.set()
        assert release.wait(5), "test did not release the owned handler"
        return result

    monkeypatch.setattr(TicketStore, "record", pause_after_commit)
    with TicketFixture(
        tmp_path / "service",
        lose_reply_once=mode != "normal",
        reply_loss=mode if mode != "normal" else "disconnect",
    ) as fixture:
        item = package(tmp_path, store=fixture.store, url=fixture.url)
        failures = []

        def submit():
            try:
                request = Request(
                    fixture.url + "/tickets", data=ticket_evidence.form_body(item["expected"]), method="POST"
                )
                request.add_header("Origin", fixture.url)
                with urlopen(request, timeout=5) as response:
                    response.read()
            except (URLError, OSError, http.client.IncompleteRead) as error:
                failures.append(error)

        with SessionOperations(Path(item["authority"])) as operations:
            issue(operations, item)
            op, _ = unknown(operations, item, admit(operations, item))
            child = threading.Thread(target=submit)
            child.start()
            try:
                assert committed.wait(5)
                assert len(fixture.store.snapshot()["ingress"]) == 1
                repeated = operations.reconcile(op.id)
                assert repeated.state == "unknown"
                assert (
                    operations._db.execute("SELECT COUNT(*) FROM operator_service_receipts").fetchone()[0]
                    == 0
                )
            finally:
                release.set()
                child.join(5)
            assert not child.is_alive()
            assert bool(failures) is (mode != "normal")
            assert operations.reconcile(op.id).state == ("unknown" if mode == "disconnect" else "final")


def install_historical_v1(operations, item, *, final):
    """Construct an old producer's retained row; production never migrates it."""
    issue(operations, item)
    op = admit(operations, item)
    operations.start(op.id)
    op = operations.finish(op.id, dispatched=None, effect="unverifiable", evidence={})
    service_event(item)
    record = ticket_evidence.qualify(op, item["prepared"], BINDING)

    def old(value):
        if isinstance(value, list):
            return [old(part) for part in value]
        if not isinstance(value, dict):
            return "footwork.ticket_ledger/v1" if value == "footwork.ticket_ledger/v2" else value
        result = {key: old(part) for key, part in value.items() if key not in ("responses", "response_mode")}
        if result.get("schema_version") == 2:
            result["schema_version"] = 1
        if "baseline_sha256" in result:
            result["baseline_sha256"] = ticket_evidence.digest(result["baseline"])
        return result

    request, projection, record = old(item["request"]), old(item["projection"]), old(record)
    prepared = projection["ticket_submission"]
    request_digest = ticket_evidence.digest({"session": SESSION, "request": request})
    record["request_digest"] = request_digest
    record["preparation_sha256"] = ticket_evidence.digest(prepared)
    body = ticket_evidence.canonical(record)
    with operations._tx() as db:
        db.execute(
            "UPDATE operations SET args=?,request_digest=?,state=?,disposition=?,phase=?,evidence=?,resolved_by=? WHERE id=?",
            (
                ticket_evidence.canonical(request),
                request_digest,
                "final" if final else "unknown",
                "applied" if final else "unknown",
                "sent" if final else "ambiguous",
                ticket_evidence.canonical({"service_receipt": record}) if final else "{}",
                "ticket_ledger" if final else None,
                op.id,
            ),
        )
        db.execute(
            "UPDATE operator_admissions SET request=?,projection=? WHERE operation=?",
            (ticket_evidence.canonical(request), ticket_evidence.canonical(projection), op.id),
        )
        db.execute(
            "INSERT INTO operator_service_receipts VALUES (?,?,?,?)",
            (op.id, body, hashlib.sha256(body.encode()).hexdigest(), time.time()),
        )
        if final:
            operations._settle(db, op.id, "spent")
    item.update(request=request, scope=request["ticket_scope"], prepared=prepared, projection=projection)
    assert operations._retained_service(operations.get(op.id)) == record
    return op.id


def test_retained_v1_unknown_cannot_gain_new_qualification(tmp_path):
    item = package(tmp_path / "owned")
    with SessionOperations(Path(item["authority"])) as operations:
        op_id = install_historical_v1(operations, item, final=False)
        before = operations._db.execute(
            "SELECT * FROM operator_service_receipts WHERE operation=?", (op_id,)
        ).fetchone()
        previous = operations.receipt(operations.get(op_id))
        assert operations.reconcile(op_id).state == "unknown"
        assert operations.receipt(operations.get(op_id)) == previous
        after = operations._db.execute(
            "SELECT * FROM operator_service_receipts WHERE operation=?", (op_id,)
        ).fetchone()
        assert tuple(before) == tuple(after)
        with pytest.raises(ticket_evidence.TicketEvidenceError):
            ticket_evidence.qualify(operations.get(op_id), item["prepared"], BINDING)


def test_final_v1_public_status_and_token_replay_preserve_raw_evidence(tmp_path, monkeypatch, capsys):
    item = package(tmp_path / "owned")
    with SessionOperations(Path(item["authority"])) as operations:
        op_id = install_historical_v1(operations, item, final=True)
        before = tuple(
            operations._db.execute(
                "SELECT * FROM operator_service_receipts WHERE operation=?", (op_id,)
            ).fetchone()
        )
        previous = operations.receipt(operations.get(op_id))
    directory = Path(item["root"]) / "session"
    directory.mkdir()
    state = session.SessionState(
        dir=str(directory),
        app="Google Chrome",
        pid=BINDING["pid"],
        window_id=BINDING["window_id"],
        task="Historical ticket",
        authority=item["authority"],
        session_id=SESSION,
        native_binding=BINDING,
        native_scope=item["request"]["native_scope"],
        ticket_scope=item["scope"],
    )
    state.save()

    def forbidden(*_, **__):
        raise AssertionError("historical status/replay must not recapture or dispatch")

    monkeypatch.setattr(ticket_evidence, "_capture", forbidden)
    monkeypatch.setattr(session, "bind", forbidden)
    assert cli.main(["status", "--reconcile", "--session", str(directory)]) == 0
    assert json.loads(capsys.readouterr().out)["operations"][0]["state"] == "final"
    assert (
        cli.main(
            [
                "do",
                "click",
                "button:Register asset",
                "--no-judge",
                "--token",
                "submit-once",
                "--session",
                str(directory),
            ]
        )
        == 0
    )
    assert "replay" in capsys.readouterr().out.lower()
    with SessionOperations(Path(item["authority"])) as operations:
        assert operations.qualified_receipt(operations.get(op_id))["schema_version"] == 1
        assert operations.receipt(operations.get(op_id)) == previous
        after = tuple(
            operations._db.execute(
                "SELECT * FROM operator_service_receipts WHERE operation=?", (op_id,)
            ).fetchone()
        )
        assert after == before


def test_independent_receipt_settles_once_and_preserves_native_unknown(tmp_path):
    item = package(tmp_path / "owned")
    with SessionOperations(Path(item["authority"])) as operations:
        grant = issue(operations, item)
        op, capsule = unknown(operations, item, admit(operations, item))
        assert operations.receipt(op)["reservation"] == "held"
        prior_history = op.history
        service_event(item)
        done = operations.reconcile(op.id)
        assert (done.state, done.disposition, done.phase, done.resolved_by) == (
            "final",
            "applied",
            "sent",
            "ticket_ledger",
        )
        assert operations.receipt(done)["reservation"] == "spent"
        assert done.history[: len(prior_history)] == prior_history
        assert any(row["kind"] == "finish" and row["disposition"] == "unknown" for row in done.history)
        assert done.evidence["prior_uncertainty"] == {"phase": "ambiguous", "error": op.error}
        assert operations._retained_execution(done) == capsule
        assert done.evidence["execution_receipt"]["producer"]["delivered_count"] is None
        receipt = operations.qualified_receipt(done)
        assert receipt["kind"] == "ticket_submission" and "delivered_count" not in receipt
        assert operations.reconcile(op.id).history == done.history
        assert operations.by_request(SESSION, "submit-once", item["request"]).id == op.id
        assert admit(operations, item).id == op.id  # Token lookup precedes another debit/preparation.
        assert (
            operations._db.execute(
                "SELECT available FROM operator_grants WHERE id=?", (grant.id,)
            ).fetchone()[0]
            == 0
        )
    assert len(TicketStore(Path(item["scope"]["source"]["database"])).snapshot()["ingress"]) == 1


@pytest.mark.parametrize(
    "variant", ["duplicates", "wrong_fields", "wrong_origin", "artifact_changed", "replaced_ledger"]
)
def test_conflicting_service_evidence_never_clears_custody(tmp_path, variant):
    item = package(tmp_path / "owned")
    with SessionOperations(Path(item["authority"])) as operations:
        issue(operations, item)
        op, _ = unknown(operations, item, admit(operations, item))
        service_event(item)
        if variant == "duplicates":
            service_event(item)
        elif variant == "wrong_fields":
            database = TicketStore(Path(item["scope"]["source"]["database"]))
            with database._db() as db:
                db.execute(
                    "UPDATE tickets SET fields=?",
                    (json.dumps({**item["expected"], "artifact": "wrong.png"}),),
                )
        elif variant == "wrong_origin":
            TicketStore(Path(item["scope"]["source"]["database"])).bind_origin("http://127.0.0.1:8766")
        elif variant == "artifact_changed":
            Path(item["scope"]["artifact"]["path"]).write_bytes(b"changed")
        else:
            database = Path(item["scope"]["source"]["database"])
            database.rename(database.with_name("retained.sqlite"))
            TicketStore(database).bind_origin(URL)
        repeated = operations.reconcile(op.id)
        assert repeated.state == "unknown" and operations.receipt(repeated)["reservation"] == "held"
        assert repeated.history == op.history
        with pytest.raises(Busy):
            operations.assert_available()


def test_bad_preparation_rolls_back_admission_claim_and_grant(tmp_path):
    item = package(tmp_path / "owned")
    with SessionOperations(Path(item["authority"])) as operations:
        grant = issue(operations, item)
        bad = {**item["request"], "ticket_scope": {**item["scope"], "url": "http://127.0.0.1:8766"}}
        with pytest.raises(ticket_evidence.TicketEvidenceError):
            admit(operations, item, request=bad)
        assert operations.status() == []
        assert operations._db.execute("SELECT COUNT(*) FROM operator_ticket_claims").fetchone()[0] == 0
        assert (
            operations._db.execute(
                "SELECT available FROM operator_grants WHERE id=?", (grant.id,)
            ).fetchone()[0]
            == 1
        )


def test_matching_current_ledger_cannot_retroactively_enroll_old_unknown(tmp_path):
    item = package(tmp_path / "owned")
    legacy_projection = {
        key: value for key, value in item["projection"].items() if key != "ticket_submission"
    }
    legacy_request = {key: value for key, value in item["request"].items() if key != "ticket_scope"}
    with SessionOperations(Path(item["authority"])) as operations:
        issue(operations, item)
        op = admit(operations, item, projection=legacy_projection, request=legacy_request)
        operations.start(op.id)
        op = operations.finish(op.id, dispatched=None, effect="unverifiable", evidence=legacy_projection)
        service_event(item)
        assert operations.reconcile(op.id).history == op.history
        assert operations.get(op.id).state == "unknown"


def test_nonce_cannot_be_reused_after_applied_submission(tmp_path):
    item = package(tmp_path / "owned")
    with SessionOperations(Path(item["authority"])) as operations:
        issue(operations, item, uses=2)
        op, _ = unknown(operations, item, admit(operations, item))
        service_event(item)
        operations.reconcile(op.id)
        with pytest.raises(JournalError, match="nonce"):
            admit(operations, item, token="different-attempt")
        assert len(operations.status()) == 1


def test_nonce_can_transfer_only_after_qualified_no_send(tmp_path):
    item = package(tmp_path / "owned")
    with SessionOperations(Path(item["authority"])) as operations:
        issue(operations, item)
        op = admit(operations, item)
        operations.start(op.id)
        operations.finish(op.id, dispatched=False, phase="not_sent", effect="refused", evidence={})
        fresh = {**item["projection"], "ticket_submission": ticket_evidence.prepare(item["scope"])}
        other = admit(operations, item, token="new-qualified-attempt", projection=fresh)
        assert other.id != op.id and operations.receipt(other)["reservation"] == "held"
        claim = operations._db.execute("SELECT operation FROM operator_ticket_claims").fetchone()[0]
        assert claim == other.id


def _crash_after_service_receipt(item, writer):
    with SessionOperations(Path(item["authority"])) as operations:
        issue(operations, item)
        op, _ = unknown(operations, item, admit(operations, item))
        service_event(item)
        original = operations._tx

        @contextlib.contextmanager
        def crash_boundary():
            row = operations._db.execute(
                "SELECT 1 FROM operator_service_receipts WHERE operation=?", (op.id,)
            ).fetchone()
            if row is not None:
                writer.send({"operation_id": op.id, "state": operations.get(op.id).state})
                os.kill(os.getpid(), signal.SIGKILL)
            with original() as database:
                yield database

        operations._tx = crash_boundary
        operations.reconcile(op.id)
        raise AssertionError("test failed to interrupt before finalization")


def test_sigkill_after_retention_recovers_without_source_or_input(tmp_path, monkeypatch):
    item = package(tmp_path / "owned")
    context = multiprocessing.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    child = context.Process(target=_crash_after_service_receipt, args=(item, writer))
    child.start()
    try:
        assert reader.poll(10), "controller did not reach retained-service boundary"
        checkpoint = reader.recv()
        child.join(5)
        assert child.exitcode == -signal.SIGKILL and checkpoint["state"] == "unknown"
    finally:
        if child.is_alive():
            child.kill()
            child.join(5)
        reader.close()
        writer.close()
    database = Path(item["scope"]["source"]["database"])
    database.rename(database.with_name("source-retained-after-crash.sqlite"))

    def forbidden(*_, **__):
        raise AssertionError("retained recovery must not read/re-dispatch")

    monkeypatch.setattr(ticket_evidence, "qualify", forbidden)
    monkeypatch.setattr(session, "bind", forbidden)
    with SessionOperations(Path(item["authority"])) as operations:
        before = operations.get(checkpoint["operation_id"])
        assert before.state == "unknown"
        assert operations._retained_service(before)["kind"] == "ticket_submission"
        after = operations.reconcile(before.id)
        assert (after.state, after.disposition) == ("final", "applied")
        assert operations.receipt(after)["reservation"] == "spent"
        assert after.evidence["execution_receipt"]["producer"]["delivered_count"] is None


def test_public_status_reconciles_dead_browser_and_replay_avoids_driver(tmp_path, monkeypatch, capsys):
    item = package(tmp_path / "owned")
    with SessionOperations(Path(item["authority"])) as operations:
        issue(operations, item)
        op, _ = unknown(operations, item, admit(operations, item))
        service_event(item)
    directory = Path(item["root"]) / "session"
    directory.mkdir()
    state = session.SessionState(
        dir=str(directory),
        app="Google Chrome",
        pid=BINDING["pid"],
        window_id=BINDING["window_id"],
        task="Synthetic qualified ticket",
        authority=item["authority"],
        session_id=SESSION,
        native_binding=BINDING,
        native_scope=item["request"]["native_scope"],
        ticket_scope=item["scope"],
    )
    state.save()
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("status/replay must not create a driver")

    monkeypatch.setattr(session, "bind", forbidden)
    monkeypatch.setitem(
        sys.modules, "cua_driver", SimpleNamespace(CuaDriver=SimpleNamespace(create=forbidden))
    )
    assert cli.main(["status", "--reconcile", "--session", str(directory)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["operations"][0]["disposition"] == "applied" and result["domain_unresolved"] == []
    assert (
        cli.main(
            [
                "do",
                "click",
                "button:Register asset",
                "--no-judge",
                "--token",
                "submit-once",
                "--session",
                str(directory),
            ]
        )
        == 0
    )
    assert "replay" in capsys.readouterr().out.lower()
    assert cli.main(["status", "--reconcile", "--session", str(directory)]) == 0
    assert calls == []
    with SessionOperations(Path(item["authority"])) as operations:
        assert len(operations.status()) == 1 and operations.get(op.id).state == "final"


def test_actual_lost_http_reply_reconciles_without_second_request(tmp_path):
    root = tmp_path / "owned"
    root.mkdir()
    with TicketFixture(root / "service", lose_reply_once=True, reply_loss="truncated") as fixture:
        item = package(root, store=fixture.store, url=fixture.url)
        with SessionOperations(Path(item["authority"])) as operations:
            issue(operations, item)
            op, _ = unknown(operations, item, admit(operations, item))
            request = Request(
                fixture.url + "/tickets", data=ticket_evidence.form_body(item["expected"]), method="POST"
            )
            request.add_header("Origin", fixture.url)
            with urlopen(request, timeout=3) as response, pytest.raises(http.client.IncompleteRead):
                response.read()
            assert operations.reconcile(op.id).state == "final"
            assert operations.reconcile(op.id).state == "final"
            assert len(fixture.store.snapshot()["ingress"]) == 1


def test_independent_service_receipt_completes_three_stage_simulated_handoff(tmp_path):
    """Simulated app effects plus real artifact oracles; not installed UI evidence."""
    from PIL import Image

    root = tmp_path / "owned"
    root.mkdir()
    manifest = create_fixture(root / "fixture")
    artifact = root / "fixture/organized/renamed.png"
    authority = root / "authority.sqlite"
    run = HandoffRun(root, authority, "simulated-service-chain")

    def native_terminal(app, runtime_session):
        with SessionOperations(authority) as operations:
            op = operations.admit(
                session_id=runtime_session,
                token=app,
                request={"words": ["click", "synthetic-effect"]},
                resource=native_resource(BINDING),
                observation=app,
                target="1",
                move="click",
                authorization_basis="explicit_simulated_effect",
                projection={"binding": BINDING, "app": app},
            )
            op = operations.start(op.id)
            now = time.time()
            capsule = execution_record(
                op,
                binding=BINDING,
                started_at=now,
                ended_at=time.time(),
                producer_evidence={
                    "name": "footwork.native",
                    "version": 1,
                    "delivery_basis": "sdk_delivery_count",
                    "delivered_count": 1,
                },
                dispatched=True,
                phase="sent",
                effect="confirmed",
                projection={"binding": BINDING, "app": app},
            )
            operations.record_execution(op.id, capsule)
            return operations.finish_from_execution(op.id).id

    run.begin("finder", session_id="finder-runtime")
    (root / "fixture/inbox/asset.png").rename(artifact)  # Explicit simulation of Finder's effect.
    finder = native_terminal("Finder", "finder-runtime")
    run.complete("finder", [finder], lambda: check_finder(manifest, "organized/renamed.png"), artifact)
    run.begin("preview", session_id="preview-runtime")
    with Image.open(artifact) as image:
        rotated = image.transpose(Image.Transpose.ROTATE_270)
    rotated.save(artifact)  # Explicit simulation of Preview's effect.
    preview = native_terminal("Preview", "preview-runtime")
    run.complete("preview", [preview], lambda: check_preview(manifest, str(artifact)), artifact)
    item = package(root, artifact=artifact)
    run.begin("chrome", session_id=SESSION)
    with SessionOperations(authority) as operations:
        issue(operations, item)
        op, _ = unknown(operations, item, admit(operations, item))
        service_event(item)
        applied = operations.reconcile(op.id)
        assert operations.qualified_receipt(applied)["kind"] == "ticket_submission"
        assert operations._retained_execution(applied)["phase"] == "ambiguous"
    run.complete(
        "chrome",
        [op.id],
        lambda: TicketStore.readonly_check(Path(item["scope"]["source"]["database"]), item["expected"]),
        artifact,
    )
    assert [
        row["stage"] for row in HandoffRun(root, authority, "simulated-service-chain").snapshot()["completed"]
    ] == ["finder", "preview", "chrome"]


@pytest.mark.parametrize("duplicate", [False, True])
def test_preadmitted_sealed_source_reconciles_only_after_real_closure(tmp_path, duplicate):
    root = tmp_path / "owned"
    root.mkdir()
    with SessionOperations(root / "authority.sqlite") as operations:
        with TicketFixture(
            root / "service", lose_reply_once=True, completion_policy="sealed_fixture"
        ) as fixture:
            item = package(root, store=fixture.store, url=fixture.url, completion_policy="sealed_fixture")
            issue(operations, item)
            op, capsule = unknown(operations, item, admit(operations, item))
            request = Request(
                fixture.url + "/tickets", data=ticket_evidence.form_body(item["expected"]), method="POST"
            )
            with pytest.raises((OSError, http.client.HTTPException)):
                urlopen(request, timeout=3)
            if duplicate:
                with urlopen(request, timeout=3) as response:
                    response.read()
            assert operations.reconcile(op.id).state == "unknown"
            assert operations._retained_service(operations.get(op.id)) is None
        done = operations.reconcile(op.id)
        if duplicate:
            assert done.state == "unknown"
            assert operations._retained_service(done) is None
        else:
            assert (done.state, done.disposition) == ("final", "applied")
            assert operations.qualified_receipt(done)["schema_version"] == 3
            assert operations._retained_execution(done) == capsule
            assert operations.reconcile(op.id).history == done.history
            assert admit(operations, item).id == op.id
