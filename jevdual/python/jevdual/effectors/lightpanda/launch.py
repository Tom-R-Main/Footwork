"""Own a pinned prebuilt Lightpanda process and its private Unix connection.

Only a handle created by ``start`` grants cleanup authority. A socket path,
process name or returned CDP identifier never grants ownership. The server's
connection has its own Browser; readiness must not create a disposable probe
connection before the one used for observation.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import os
import re
import stat
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jevdual.platform_identity import boot_identity

from ..cdp.launch import CleanupUnverified, _terminate
from ..cdp.transport import CdpClosed, CdpConnection

__all__ = ["MAX_MESSAGE_BYTES", "CleanupUnverified", "LaunchRefused", "OwnedLightpanda",
           "connect", "engine_args", "start", "stop"]

MAX_MESSAGE_BYTES = 4 * 1024 * 1024


class LaunchRefused(RuntimeError):
    dispatched = False

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class OwnedLightpanda:
    pid: int
    incarnation: float
    executable: str
    binary_sha256: str
    socket_path: Path
    boot: str
    process: subprocess.Popen = field(compare=False, repr=False)

    def alive(self) -> bool:
        import psutil

        try:
            return (self.process.poll() is None and boot_identity() == self.boot
                    and psutil.Process(self.pid).create_time() == self.incarnation)
        except psutil.Error:
            return False

    def identity(self) -> dict[str, Any]:
        """Captured launch identity; continued liveness requires a fresh ``alive`` check."""
        return {"boot": self.boot, "pid": self.pid, "start": repr(self.incarnation),
                "binary_sha256": self.binary_sha256}


def _physical(path: Path) -> None:
    if not path.is_absolute() or ".." in path.parts:
        raise LaunchRefused("lightpanda_path_invalid", "owned paths must be absolute physical paths")
    for part in (path, *path.parents):
        if part.is_symlink():
            raise LaunchRefused("lightpanda_path_invalid", "owned paths must not contain symlinks")


def _digest_executable(path: Path, expected_sha256: str) -> tuple[str, os.stat_result]:
    if not isinstance(expected_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None:
        raise LaunchRefused("lightpanda_digest_required", "provide the pinned executable SHA256")
    _physical(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or not before.st_mode & 0o111 or not os.access(path, os.X_OK):
                raise LaunchRefused("lightpanda_binary_unavailable", "the pinned engine must be an executable regular file")
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
            after = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise LaunchRefused("lightpanda_binary_changed", "the pinned engine changed during verification")
        if digest != expected_sha256:
            raise LaunchRefused("lightpanda_digest_mismatch", "the engine does not match its declared SHA256")
        return digest, after
    except OSError as exc:
        raise LaunchRefused("lightpanda_binary_unavailable", "the pinned engine could not be opened") from exc


def engine_args(executable: str, socket_path: Path) -> list[str]:
    # Config.zig serve options and README telemetry contract at Lightpanda49d717.
    return [executable, "serve", "--unix-socket", str(socket_path), "--cdp-max-connections", "1",
            "--cdp-max-pending-connections", "1", "--log-level", "error"]


def start(executable: str, directory: Path, *, expected_sha256: str) -> OwnedLightpanda:
    """Capture the actual child handle synchronously, before any cancellable await."""
    import psutil

    binary, directory = Path(executable), Path(directory)
    digest, binary_stat = _digest_executable(binary, expected_sha256)
    _physical(directory)
    socket_path = directory / "cdp.sock"
    if len(os.fsencode(socket_path)) > 100:
        raise LaunchRefused("lightpanda_path_invalid", "choose a shorter private Unix socket path")
    if directory.exists() or directory.is_symlink():
        raise LaunchRefused("lightpanda_directory_unavailable", "Lightpanda requires a fresh private directory")
    try:
        directory.mkdir(mode=0o700)
    except OSError as exc:
        raise LaunchRefused("lightpanda_directory_unavailable", "the private engine directory could not be created") from exc
    environment = dict(os.environ)
    environment["LIGHTPANDA_DISABLE_TELEMETRY"] = "true"
    environment["LIGHTPANDA_DISABLE_CORE_DUMP"] = "true"
    process = subprocess.Popen(
        engine_args(str(binary), socket_path), env=environment,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    incarnation = None
    try:
        child = psutil.Process(process.pid)
        incarnation = child.create_time()
        current = binary.stat()
        if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (
                binary_stat.st_dev, binary_stat.st_ino, binary_stat.st_size, binary_stat.st_mtime_ns):
            raise LaunchRefused("lightpanda_binary_changed", "the pinned engine changed before launch completed")
        if child.exe() != str(binary) or child.uids().real != os.getuid():
            raise LaunchRefused("lightpanda_identity_mismatch", "the launched process is not the pinned executable")
        boot = boot_identity()
        if not boot or not math.isfinite(incarnation) or incarnation <= 0 or process.poll() is not None:
            raise LaunchRefused("lightpanda_identity_unavailable", "the engine process incarnation is unavailable")
        return OwnedLightpanda(process.pid, incarnation, str(binary), digest, socket_path, boot, process)
    except BaseException as exc:
        # The caller never received an OwnedLightpanda, but a real child was created.
        # Carry the attempted handle cleanup separately from the original startup
        # failure. In particular, do not turn uncertain cleanup into "not_started".
        exc.process_started = True
        try:
            _terminate(process, incarnation=incarnation)
        except BaseException as cleanup:  # noqa: BLE001 - preserve the original failure and report all cleanup loss
            exc.owned_cleanup = {"status": "unverified", "code": "lightpanda_cleanup_unverified",
                                 "complete_tree_inventory": False}
            exc.add_note(f"owned startup cleanup unverified ({type(cleanup).__name__})")
        else:
            exc.owned_cleanup = {"status": "bounded_owned_processes_stopped", "complete_tree_inventory": False}
        raise


async def connect(owned: OwnedLightpanda, *, timeout: float = 15.0) -> CdpConnection:
    """Wait for one socket and establish exactly one authenticated WebSocket."""
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 60:
        raise LaunchRefused("lightpanda_timeout_invalid", "readiness requires a finite bounded timeout")
    deadline = time.monotonic() + timeout
    while True:
        if not owned.alive():
            raise LaunchRefused("lightpanda_identity_changed", "the original engine exited or changed incarnation")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise LaunchRefused("lightpanda_readiness_timeout", "the owned engine did not become ready in time")
        try:
            row = owned.socket_path.lstat()
        except FileNotFoundError:
            await asyncio.sleep(min(0.02, remaining))
            continue
        if (not stat.S_ISSOCK(row.st_mode) or row.st_uid != os.getuid()
                or stat.S_IMODE(row.st_mode) != 0o600):
            raise LaunchRefused("lightpanda_socket_unqualified", "the endpoint is not the owned private Unix socket")
        try:
            connection = await CdpConnection.open_unix(
                owned.socket_path, expected_pid=owned.pid, expected_uid=os.getuid(), timeout=remaining,
                max_message_bytes=MAX_MESSAGE_BYTES,
            )
        except (FileNotFoundError, ConnectionRefusedError):
            # Before a connection exists only. Do not probe/close a Browser or retry a
            # WebSocket handshake, protocol error, peer mismatch or command failure.
            await asyncio.sleep(min(0.02, remaining))
            continue
        except CdpClosed as exc:
            raise LaunchRefused("lightpanda_peer_unqualified", "the Unix peer is not the original owned engine") from exc
        if not owned.alive():
            await connection.close()
            raise LaunchRefused("lightpanda_identity_changed", "the engine changed while its endpoint connected")
        return connection


def stop(owned: OwnedLightpanda) -> None:
    """Stop this actual launch handle or report bounded cleanup uncertainty."""
    _terminate(owned.process, incarnation=owned.incarnation)
