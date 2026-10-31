"""Owned executable/Unix transport qualification; local server cells are transport models."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import socket
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import psutil
import pytest
from jevdual.effectors.cdp.transport import CdpClosed, CdpConnection, CdpUnknownOutcome
from jevdual.effectors.lightpanda import launch


@pytest.fixture
def short_root():
    with tempfile.TemporaryDirectory(prefix="fw-lp-", dir="/tmp") as raw:
        yield Path(raw).resolve()


def executable(root):
    path = root / "engine"
    path.write_bytes(b"test executable bytes; not an actual engine")
    path.chmod(0o700)
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("kind", ["empty", "file", "symlink", "dangling"])
def test_existing_directory_or_symlink_is_refused_before_spawn(short_root, monkeypatch, kind):
    binary, digest = executable(short_root)
    directory = short_root / "run"
    if kind == "empty":
        directory.mkdir()
    elif kind == "file":
        directory.write_text("preserve")
    else:
        target = short_root / "elsewhere"
        if kind == "symlink":
            target.mkdir()
        directory.symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(launch.subprocess, "Popen", lambda *a, **k: pytest.fail("spawned"))
    with pytest.raises(launch.LaunchRefused):
        launch.start(str(binary), directory, expected_sha256=digest)
    assert directory.is_symlink() if kind in {"symlink", "dangling"} else directory.exists()


@pytest.mark.parametrize("problem", ["digest", "missing_digest", "not_executable", "symlink", "parent_symlink"])
def test_binary_preflight_refuses_before_directory_creation(short_root, monkeypatch, problem):
    binary, digest = executable(short_root)
    if problem == "digest":
        digest = "0" * 64
    elif problem == "missing_digest":
        digest = ""
    elif problem == "not_executable":
        binary.chmod(0o600)
    elif problem == "symlink":
        link = short_root / "linked"
        link.symlink_to(binary)
        binary = link
    else:
        linked = short_root / "linked-parent"
        linked.symlink_to(short_root, target_is_directory=True)
        binary = linked / "engine"
    monkeypatch.setattr(launch.subprocess, "Popen", lambda *a, **k: pytest.fail("spawned"))
    with pytest.raises(launch.LaunchRefused) as refused:
        launch.start(str(binary), short_root / "run", expected_sha256=digest)
    assert not hasattr(refused.value, "owned_cleanup")
    assert not hasattr(refused.value, "process_started")
    assert not (short_root / "run").exists()


def test_socket_length_is_checked_before_spawn_or_directory_creation(short_root, monkeypatch):
    binary, digest = executable(short_root)
    directory = short_root / ("x" * 100)
    monkeypatch.setattr(launch.subprocess, "Popen", lambda *a, **k: pytest.fail("spawned"))
    with pytest.raises(launch.LaunchRefused, match="shorter"):
        launch.start(str(binary), directory, expected_sha256=digest)
    assert not directory.exists()


def test_start_captures_real_handle_before_any_await(short_root, monkeypatch):
    binary, digest = executable(short_root)
    directory = short_root / "run"
    child = SimpleNamespace(pid=123, poll=lambda: None)
    inspected = SimpleNamespace(create_time=lambda: 123.5, exe=lambda: str(binary),
                                uids=lambda: SimpleNamespace(real=os.getuid()))
    calls = []

    def spawn(args, **kwargs):
        assert directory.is_dir() and stat.S_IMODE(directory.stat().st_mode) == 0o700
        assert list(directory.iterdir()) == []
        assert args == [str(binary), "serve", "--unix-socket", str(directory / "cdp.sock"),
                        "--cdp-max-connections", "1", "--cdp-max-pending-connections", "1",
                        "--log-level", "error"]
        assert kwargs["env"]["LIGHTPANDA_DISABLE_TELEMETRY"] == "true"
        assert kwargs["env"]["LIGHTPANDA_DISABLE_CORE_DUMP"] == "true"
        assert kwargs["start_new_session"] is True
        calls.append(args)
        return child

    monkeypatch.setattr(launch.subprocess, "Popen", spawn)
    monkeypatch.setattr(psutil, "Process", lambda pid: inspected)
    monkeypatch.setattr(launch, "boot_identity", lambda: "boot")
    owned = launch.start(str(binary), directory, expected_sha256=digest)
    assert len(calls) == 1 and owned.process is child
    assert owned.identity() == {"boot": "boot", "pid": 123, "start": "123.5", "binary_sha256": digest}
    assert owned.alive()


def test_wrong_executable_after_spawn_only_cleans_original_handle(short_root, monkeypatch):
    binary, digest = executable(short_root)
    child = SimpleNamespace(pid=123, poll=lambda: None)
    stopped = []
    monkeypatch.setattr(launch.subprocess, "Popen", lambda *a, **k: child)
    monkeypatch.setattr(psutil, "Process", lambda pid: SimpleNamespace(
        create_time=lambda: 123.5, exe=lambda: "/foreign", uids=lambda: SimpleNamespace(real=os.getuid())))
    monkeypatch.setattr(launch, "_terminate", lambda process, **kwargs: stopped.append((process, kwargs)))
    with pytest.raises(launch.LaunchRefused, match="pinned executable") as refused:
        launch.start(str(binary), short_root / "run", expected_sha256=digest)
    assert stopped == [(child, {"incarnation": 123.5})]
    assert refused.value.process_started is True
    assert refused.value.owned_cleanup == {"status": "bounded_owned_processes_stopped",
                                           "complete_tree_inventory": False}


@pytest.mark.parametrize("failure_type", [RuntimeError, asyncio.CancelledError, KeyboardInterrupt])
@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_post_spawn_failure_carries_cleanup_and_preserves_original_exception(
    short_root, monkeypatch, failure_type, cleanup_fails,
):
    """Injected startup failure sensitivity controls; no actual engine or process is created."""
    binary, digest = executable(short_root)
    child = SimpleNamespace(pid=123, poll=lambda: None)
    original = failure_type("injected post-spawn failure")
    attempts = []

    def fail_identity():
        raise original

    def cleanup(process, **kwargs):
        attempts.append((process, kwargs))
        if cleanup_fails:
            raise launch.CleanupUnverified("injected inventory loss")

    monkeypatch.setattr(launch.subprocess, "Popen", lambda *a, **k: child)
    monkeypatch.setattr(psutil, "Process", lambda pid: SimpleNamespace(create_time=fail_identity))
    monkeypatch.setattr(launch, "_terminate", cleanup)
    with pytest.raises(failure_type) as caught:
        launch.start(str(binary), short_root / "run", expected_sha256=digest)
    assert caught.value is original and original.process_started is True
    assert attempts == [(child, {"incarnation": None})]
    expected = {"status": "unverified", "code": "lightpanda_cleanup_unverified",
                "complete_tree_inventory": False} if cleanup_fails else {
                    "status": "bounded_owned_processes_stopped", "complete_tree_inventory": False}
    assert original.owned_cleanup == expected


def owned_model(path, *, alive=True):
    return SimpleNamespace(socket_path=path, pid=os.getpid(), alive=lambda: alive)


def test_readiness_does_not_open_any_connection_for_missing_or_wrong_socket(short_root, monkeypatch):
    path = short_root / "cdp.sock"

    async def forbidden(*a, **k):
        pytest.fail("unqualified endpoint reached connection")

    monkeypatch.setattr(launch.CdpConnection, "open_unix", forbidden)
    with pytest.raises(launch.LaunchRefused, match="ready"):
        asyncio.run(launch.connect(owned_model(path), timeout=0.03))
    path.write_text("foreign regular file")
    with pytest.raises(launch.LaunchRefused, match="private Unix socket"):
        asyncio.run(launch.connect(owned_model(path)))


def test_readiness_checks_original_incarnation_before_socket(short_root, monkeypatch):
    monkeypatch.setattr(launch.CdpConnection, "open_unix", lambda *a, **k: pytest.fail("connected"))
    with pytest.raises(launch.LaunchRefused, match="original engine"):
        asyncio.run(launch.connect(owned_model(short_root / "cdp.sock", alive=False)))


def test_readiness_cancellation_never_claims_cleanup_or_reconnect(short_root, monkeypatch):
    attempted = []

    async def forbidden(*a, **k):
        attempted.append(True)

    monkeypatch.setattr(launch.CdpConnection, "open_unix", forbidden)

    async def run():
        task = asyncio.create_task(launch.connect(owned_model(short_root / "cdp.sock")))
        await asyncio.sleep(0.005)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    assert attempted == []


def test_unix_peer_verified_before_websocket_handshake(short_root):
    """A real local Unix/WebSocket server models only transport, not Lightpanda behavior."""
    from websockets.asyncio.server import unix_serve

    async def run():
        path = short_root / "model.sock"
        messages = []

        async def handler(ws):
            async for raw in ws:
                message = json.loads(raw)
                messages.append(message)
                await ws.send(json.dumps({"id": message["id"], "result": {"model": True}}))

        async with unix_serve(handler, str(path)):
            path.chmod(0o600)
            connection = await launch.connect(owned_model(path))
            try:
                assert connection.unix_peer_identity == {"pid": os.getpid(), "uid": os.getuid()}
                assert messages == []  # no readiness CDP or fake SystemInfo query
                assert await connection.send("Model.read") == {"model": True}
            finally:
                await connection.close()
        assert [m["method"] for m in messages] == ["Model.read"]

    asyncio.run(run())


@pytest.mark.parametrize("field", ["pid", "uid"])
def test_foreign_peer_refuses_before_handshake(short_root, field):
    """Real kernel credentials; the expected PID is intentionally foreign."""
    async def run():
        path = short_root / "foreign.sock"
        received = []

        async def handler(reader, writer):
            received.append(await reader.read(1024))
            writer.close()
            await writer.wait_closed()

        async with await asyncio.start_unix_server(handler, str(path)):
            with pytest.raises(CdpClosed, match="different process"):
                await CdpConnection.open_unix(path, expected_pid=os.getpid() + (field == "pid"),
                                              expected_uid=os.getuid() + (field == "uid"))
            await asyncio.sleep(0.01)
        assert received == [b""]  # no HTTP upgrade request before peer proof

    asyncio.run(run())


@pytest.mark.parametrize("timeout", [0, -1, True, float("nan"), float("inf"), 61])
def test_unix_transport_requires_bounded_deadline(short_root, timeout):
    with pytest.raises(CdpClosed, match="invalid"):
        asyncio.run(CdpConnection.open_unix(short_root / "unused.sock", expected_pid=os.getpid(),
                                            expected_uid=os.getuid(), timeout=timeout))


def test_cancelling_handshake_closes_authenticated_socket_without_retry(short_root):
    async def run():
        path = short_root / "stalled.sock"
        entered, eof = asyncio.Event(), asyncio.Event()
        connections = []

        async def handler(reader, writer):
            connections.append(True)
            received = await reader.read(4096)
            assert received.startswith(b"GET / HTTP/1.1")
            entered.set()
            assert await reader.read(4096) == b""
            writer.close()
            await writer.wait_closed()
            eof.set()

        async with await asyncio.start_unix_server(handler, str(path)):
            task = asyncio.create_task(CdpConnection.open_unix(path, expected_pid=os.getpid(),
                                                               expected_uid=os.getuid()))
            await asyncio.wait_for(entered.wait(), 1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            await asyncio.wait_for(eof.wait(), 1)
        assert connections == [True]

    asyncio.run(run())


def test_unix_message_budget_refuses_oversized_reply_without_retry(short_root):
    """The maintained WebSocket decoder enforces the explicit wire bound."""
    from websockets.asyncio.server import unix_serve

    async def run():
        path = short_root / "bounded.sock"
        requests = []

        async def handler(ws):
            request = json.loads(await ws.recv())
            requests.append(request["method"])
            await ws.send(json.dumps({"id": request["id"], "result": {"text": "x" * 512}}))
            await ws.wait_closed()

        async with unix_serve(handler, str(path)):
            connection = await CdpConnection.open_unix(path, expected_pid=os.getpid(),
                                                       expected_uid=os.getuid(), max_message_bytes=128)
            try:
                with pytest.raises(CdpUnknownOutcome):
                    await connection.send("Model.read")
                assert connection.closed
            finally:
                await connection.close()
        assert requests == ["Model.read"]

    asyncio.run(run())


def test_socket_with_broad_permissions_refuses_before_connect(short_root, monkeypatch):
    path = short_root / "loose.sock"
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        listener.bind(str(path))
        path.chmod(0o666)
        monkeypatch.setattr(launch.CdpConnection, "open_unix", lambda *a, **k: pytest.fail("connected"))
        with pytest.raises(launch.LaunchRefused, match="private Unix socket"):
            asyncio.run(launch.connect(owned_model(path)))
    finally:
        listener.close()


def test_successful_connection_is_retired_if_original_process_changed(short_root, monkeypatch):
    path = short_root / "cdp.sock"
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(path))
    path.chmod(0o600)
    closed = []

    async def opened(*a, **k):
        assert k["max_message_bytes"] == 4 * 1024 * 1024
        async def close():
            closed.append(True)
        return SimpleNamespace(close=close)

    state = iter([True, False])
    monkeypatch.setattr(launch.CdpConnection, "open_unix", opened)
    try:
        model = SimpleNamespace(socket_path=path, pid=os.getpid(), alive=lambda: next(state))
        with pytest.raises(launch.LaunchRefused, match="changed"):
            asyncio.run(launch.connect(model))
    finally:
        listener.close()
    assert closed == [True]


def test_stop_keeps_actual_handle_and_captured_incarnation(monkeypatch):
    child = object()
    owned = SimpleNamespace(process=child, incarnation=321.0)
    called = []
    monkeypatch.setattr(launch, "_terminate", lambda process, **kwargs: called.append((process, kwargs)))
    launch.stop(owned)
    assert called == [(child, {"incarnation": 321.0})]


def test_cleanup_uncertainty_is_not_hidden(monkeypatch):
    def failed(*a, **k):
        raise launch.CleanupUnverified("captured descendants unavailable")

    monkeypatch.setattr(launch, "_terminate", failed)
    with pytest.raises(launch.CleanupUnverified):
        launch.stop(SimpleNamespace(process=object(), incarnation=1.0))


def test_stop_real_owned_child(short_root):
    """Actual process custody test; the child is Python, not a Lightpanda qualification."""
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)
    owned = launch.OwnedLightpanda(process.pid, psutil.Process(process.pid).create_time(), sys.executable,
                                  "a" * 64, short_root / "unused.sock", launch.boot_identity(), process)
    try:
        launch.stop(owned)
        assert process.poll() is not None
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=3)
