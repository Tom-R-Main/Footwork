"""The holder retains admission across client loss; transport convenience never grants replay."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import psutil
import pytest
from jevdual import browser_holder as broker
from jevdual.browser_authority import BrowserAuthority, guard_digest
from jevdual.browser_guard import GuardRefused
from jevdual.effectors.base import BrowserReply
from jevdual.effectors.cdp.click import ACTIVATE, ROUTE, ButtonTarget
from jevdual.effectors.cdp.operations import CdpBrowserOperations, RefBinding

FINGERPRINT = json.dumps({"tag": "button", "attrs": [["type", "button"]],
                          "text": "Commit fixture", "ancestors": []}, separators=(",", ":"))


class Connection:
    def __init__(self):
        self.sent = []
        self.activations = 0
        self.failure = None
        self.on_activation = None
        self.activated = asyncio.Event()
        self.release = None

    async def send(self, method, params=None, **kwargs):
        self.sent.append((method, params))
        if method == "Target.getTargets":
            return {"targetInfos": [{"type": "page", "targetId": "tab", "browserContextId": "ctx"}]}
        if method == "Page.getFrameTree":
            return {"frameTree": {"frame": {"id": "frame", "loaderId": "loader"}}}
        if method == "DOM.describeNode":
            return {"node": {"backendNodeId": 10}}
        if method == "DOM.resolveNode":
            return {"object": {"objectId": "exact-object"}}
        if method == "Runtime.callFunctionOn" and params["functionDeclaration"] == ACTIVATE:
            if self.on_activation:
                self.on_activation()
            self.activations += 1
            self.activated.set()
            if self.release is not None:
                await self.release.wait()
            if self.failure:
                raise self.failure
            return {"result": {"value": {"status": "invoked"}}}
        return {}

    async def close(self):
        pass


def make_holder(tmp_path):
    authority = BrowserAuthority(tmp_path / "authority.db")
    chrome = SimpleNamespace(pid=os.getpid(), incarnation=psutil.Process().create_time(), alive=lambda: True)
    connection = Connection()
    operations = CdpBrowserOperations(chrome, connection)
    operations._contexts["tab"] = "ctx"
    operations._sessions["tab"] = "session"
    binding = RefBinding(chrome.incarnation, "ctx", "tab", "session", "frame", "loader", 10, 99,
                         ButtonTarget(FINGERPRINT), "document-token")

    async def snapshot(**kwargs):
        operations._refs = {"snap:1": binding}
        return BrowserReply("ok", "", False, MappingProxyType({
            "snapshot_id": "snap", "refs": [{"ref": "snap:1", "name": "Commit fixture", "role": "button"}],
            "page": {"url": "https://fixture.invalid/", "title": "Fixture"},
        }))

    operations.snapshot = snapshot
    calls = []

    async def authorize(config, record, snapshot, ref, digest):
        calls.append((record, ref, digest))
        assert connection.activations == 0
        assert digest == guard_digest(config["session_id"], {"ref": ref, "route": ROUTE}, record)
        return {"producer": "footwork.browser.guard", "version": 1, "decision": "allow", "digest": digest}

    config = {"version": 1, "session_id": "test-session", "task": "Commit the fixture once",
              "chrome": "/fixture/chrome", "initial_url": "https://fixture.invalid/",
              "authority": str(tmp_path / "authority.db"), "guard_command": None}
    holder = broker.BrowserHolder(config, authority, chrome, operations, "tab", authorize)
    return holder, authority, connection, calls


@pytest.fixture
def runtime(tmp_path):
    holder, authority, connection, calls = make_holder(tmp_path)
    yield holder, authority, connection, calls
    authority.close()


async def call(holder, method, **fields):
    return await holder.handle({"nonce": holder.nonce, "session_id": holder.config["session_id"],
                                "method": method, **fields})


def test_admission_and_started_stage_are_committed_before_possible_activation(runtime):
    holder, authority, connection, guards = runtime

    def boundary():
        op = authority.status()[0]
        assert op.state == "dispatching" and op.execution_stage == "started"
        assert op.client_token == "once"
        assert not holder.operations._refs

    connection.on_activation = boundary

    async def run():
        assert (await call(holder, "look"))["ok"]
        result = await call(holder, "click", token="once", ref="snap:1")
        assert result["operation"]["state"] == "unknown"
        assert result["operation"]["phase"] == "sent"
        assert result["operation"]["completion"] == "unverified"
        assert len(guards) == connection.activations == 1

    asyncio.run(run())


def test_replay_returns_retained_operation_before_observation_or_guard(runtime):
    holder, _, connection, guards = runtime

    async def run():
        await call(holder, "look")
        first = await call(holder, "click", token="once", ref="snap:1")
        holder.snapshot = None
        holder.operations._refs.clear()
        again = await call(holder, "click", token="once", ref="snap:1")
        assert again["replayed"]
        assert again["operation"]["id"] == first["operation"]["id"]
        assert len(guards) == connection.activations == 1
        changed = await call(holder, "click", token="once", ref="another-ref")
        assert changed["code"] == "client_token_conflict"
        new = await call(holder, "click", token="another-token", ref="snap:1")
        assert new["code"] == "browser_operation_unresolved"
        assert len(guards) == connection.activations == 1

    asyncio.run(run())


def test_guard_refusal_retains_refs_and_never_admits_or_activates(runtime):
    holder, authority, connection, _ = runtime

    async def refuse(*args):
        raise GuardRefused("guard_unavailable", "fixture judgment missing")

    holder.authorize = refuse

    async def run():
        await call(holder, "look")
        response = await call(holder, "click", token="once", ref="snap:1")
        assert response["code"] == "guard_unavailable" and response["dispatched"] is False
        assert authority.status() == [] and connection.activations == 0
        assert "snap:1" in holder.operations._refs
        assert not holder.operations._click_unknown
        assert connection.sent[-1][0] == "Runtime.releaseObject"

    asyncio.run(run())


@pytest.mark.parametrize("failure", [RuntimeError("lost reply"), asyncio.CancelledError()])
def test_post_admission_failure_and_cancellation_retain_unknown(runtime, failure):
    holder, authority, connection, _ = runtime
    connection.failure = failure

    async def run():
        await call(holder, "look")
        if isinstance(failure, asyncio.CancelledError):
            with pytest.raises(asyncio.CancelledError):
                await call(holder, "click", token="once", ref="snap:1")
        else:
            result = await call(holder, "click", token="once", ref="snap:1")
            assert result["operation"]["state"] == "unknown"
        op = authority.status()[0]
        assert op.state == "unknown" and op.disposition == "unknown"
        assert op.execution_stage == "started"
        assert (await call(holder, "click", token="once", ref="snap:1"))["replayed"]
        assert connection.activations == 1

    asyncio.run(run())


@pytest.mark.parametrize("extra", [{"nonce": "wrong"}, {"session_id": "another-session"},
                                   {"method": "type"}, {"method": "navigate"}, {"url": "https://x.invalid"}])
def test_wrong_session_and_unbounded_methods_never_touch_browser(runtime, extra):
    holder, authority, connection, _ = runtime

    async def run():
        request = {"nonce": holder.nonce, "session_id": holder.config["session_id"], "method": "look", **extra}
        result = await holder.handle(request)
        assert not result["ok"] and result["dispatched"] is False
        assert not connection.sent and not authority.status()

    asyncio.run(run())


def test_close_uses_only_original_handle_and_does_not_settle_unknown(runtime, monkeypatch):
    holder, authority, _, _ = runtime
    stopped = []
    monkeypatch.setattr(broker.launch, "stop", stopped.append)

    async def run():
        await call(holder, "look")
        await call(holder, "click", token="once", ref="snap:1")
        result = await call(holder, "stop")
        assert result["cleanup"]["status"] == "bounded_owned_processes_stopped"
        assert result["cleanup"]["complete_tree_inventory"] is False
        assert stopped == [holder.chrome]
        assert authority.status()[0].state == "unknown"
        assert not (await call(holder, "look"))["ok"]

    asyncio.run(run())


def test_cleanup_failure_is_reported_without_claiming_all_processes_stopped(runtime, monkeypatch):
    holder, _, _, _ = runtime

    def fail(chrome):
        raise RuntimeError("inventory unavailable")

    monkeypatch.setattr(broker.launch, "stop", fail)
    result = asyncio.run(call(holder, "stop"))
    assert result["cleanup"] == {"status": "unverified", "code": "browser_cleanup_unverified"}


def test_private_files_and_descriptor_incarnation_are_checked_before_connect(runtime, monkeypatch):
    holder, _, _, _ = runtime

    async def forbidden(*args, **kwargs):
        pytest.fail("must not connect to a stale or foreign holder")

    monkeypatch.setattr(asyncio, "open_unix_connection", forbidden)
    with tempfile.TemporaryDirectory(prefix="fwh-") as raw:
        directory = Path(raw)
        broker._write_private(directory / broker.CONFIG_FILE, holder.config)
        identity = broker.process_identity(os.getpid())
        descriptor = {"version": 1, **identity, "nonce": holder.nonce,
                      "session_id": holder.config["session_id"], "socket": str(directory / broker.SOCKET_FILE)}
        descriptor["start"] = "0.0"
        broker._write_private(directory / broker.HOLDER_FILE, descriptor)
        with pytest.raises(broker.HolderRefused, match="identity changed"):
            asyncio.run(broker.request(directory, "status"))
        (directory / broker.HOLDER_FILE).chmod(0o644)
        with pytest.raises(broker.HolderRefused, match="private regular"):
            asyncio.run(broker.request(directory, "status"))


def test_lost_socket_response_then_repeat_token_has_one_activation(runtime):
    holder, _, connection, guards = runtime

    async def run(directory):
        socket_path = directory / broker.SOCKET_FILE
        server = await asyncio.start_unix_server(holder.serve, path=str(socket_path), limit=broker.MAX_REQUEST)
        socket_path.chmod(0o600)
        broker._write_private(directory / broker.CONFIG_FILE, holder.config)
        broker._write_private(directory / broker.HOLDER_FILE, {
            "version": 1, **broker.process_identity(os.getpid()), "nonce": holder.nonce,
            "session_id": holder.config["session_id"], "socket": str(socket_path),
        })
        try:
            assert (await broker.request(directory, "look"))["ok"]
            connection.release = asyncio.Event()
            _reader, writer = await asyncio.open_unix_connection(str(socket_path))
            writer.write(json.dumps({"nonce": holder.nonce, "session_id": holder.config["session_id"],
                                     "method": "click", "token": "once", "ref": "snap:1"}).encode() + b"\n")
            await writer.drain()
            await asyncio.wait_for(connection.activated.wait(), 2)
            writer.close()  # lose the response after activation; the holder still owns the attempt
            await writer.wait_closed()
            connection.release.set()
            # A serial status request is a barrier after the earlier connection is admitted.
            for _ in range(50):
                result = await broker.request(directory, "status")
                if result["operations"]:
                    break
                await asyncio.sleep(0.01)
            assert result["operations"][0]["state"] == "unknown"
            repeated = await broker.request(directory, "click", token="once", ref="snap:1")
            assert repeated["replayed"]
            assert connection.activations == len(guards) == 1
        finally:
            server.close()
            await server.wait_closed()

    with tempfile.TemporaryDirectory(prefix="fwh-") as raw:
        asyncio.run(run(Path(raw)))


def test_oversize_request_refuses_without_browser_or_journal_activity(runtime):
    holder, authority, connection, _ = runtime

    async def run(directory):
        server = await asyncio.start_unix_server(holder.serve, path=str(directory / "s"), limit=broker.MAX_REQUEST)
        try:
            reader, writer = await asyncio.open_unix_connection(str(directory / "s"))
            writer.write(b"x" * (broker.MAX_REQUEST + 1) + b"\n")
            await writer.drain()
            result = json.loads(await reader.readline())
            assert result["code"] == "browser_request_invalid" and result["dispatched"] is False
            assert not connection.sent and not authority.status()
            writer.close()
            await writer.wait_closed()
        finally:
            server.close()
            await server.wait_closed()

    with tempfile.TemporaryDirectory(prefix="fwh-") as raw:
        asyncio.run(run(Path(raw)))


def test_rpc_deadline_after_admission_retains_unknown_without_retry(runtime, monkeypatch):
    holder, authority, connection, _ = runtime
    monkeypatch.setattr(broker, "REQUEST_TIMEOUT", 0.05)

    async def run(directory):
        server = await asyncio.start_unix_server(holder.serve, path=str(directory / "s"), limit=broker.MAX_REQUEST)
        try:
            await call(holder, "look")
            connection.release = asyncio.Event()
            reader, writer = await asyncio.open_unix_connection(str(directory / "s"))
            writer.write(json.dumps({"nonce": holder.nonce, "session_id": holder.config["session_id"],
                                     "method": "click", "token": "once", "ref": "snap:1"}).encode() + b"\n")
            await writer.drain()
            result = json.loads(await reader.readline())
            assert result["code"] == "browser_response_unknown" and result["dispatched"] is None
            assert authority.status()[0].state == "unknown"
            assert (await call(holder, "click", token="once", ref="snap:1"))["replayed"]
            assert connection.activations == 1
            writer.close()
            await writer.wait_closed()
        finally:
            server.close()
            await server.wait_closed()

    with tempfile.TemporaryDirectory(prefix="fwh-") as raw:
        asyncio.run(run(Path(raw)))


def test_foreign_socket_peer_is_refused_before_request_read(runtime, monkeypatch):
    holder, authority, connection, _ = runtime
    monkeypatch.setattr(broker, "_peer_credentials", lambda writer: (os.getpid(), os.getuid() + 1))

    async def run(directory):
        server = await asyncio.start_unix_server(holder.serve, path=str(directory / "s"), limit=broker.MAX_REQUEST)
        try:
            reader, writer = await asyncio.open_unix_connection(str(directory / "s"))
            result = json.loads(await reader.readline())
            assert result["code"] == "browser_peer_mismatch" and result["dispatched"] is False
            assert not connection.sent and not authority.status()
            writer.close()
            await writer.wait_closed()
        finally:
            server.close()
            await server.wait_closed()

    with tempfile.TemporaryDirectory(prefix="fwh-") as raw:
        asyncio.run(run(Path(raw)))


def test_stale_holder_record_refuses_start_without_launch_or_cleanup(runtime, monkeypatch):
    holder, _, _, _ = runtime
    launched = []
    monkeypatch.setattr(broker.launch, "launch", lambda *a, **k: launched.append(a))
    monkeypatch.setattr(broker.launch, "stop", lambda *a: pytest.fail("stale metadata gives no cleanup authority"))
    with tempfile.TemporaryDirectory(prefix="fwh-") as raw:
        directory = Path(raw)
        broker._write_private(directory / broker.CONFIG_FILE, holder.config)
        broker._write_private(directory / broker.HOLDER_FILE, {"pid": 99999999})
        original = (directory / broker.HOLDER_FILE).read_bytes()
        with pytest.raises(broker.HolderRefused, match="no implicit restart"):
            asyncio.run(broker.run(directory))
        assert not launched
        assert (directory / broker.HOLDER_FILE).read_bytes() == original
