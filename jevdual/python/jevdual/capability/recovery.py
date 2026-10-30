"""Private process-crash records for one fixed native append, never a replay API.

Completion attests historical execution. Current agreement and execution custody
are separate facts. No record, PID, exit code or matching text substitutes for a
qualified effect receipt. This is process-crash durability, not power-loss proof.
"""

from __future__ import annotations

import asyncio
import fcntl
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jevdual.platform_identity import boot_identity

if TYPE_CHECKING:
    from .journal import Operation

VERSION = 1
ROUTE = "textedit-ax-append-v1"
LINUX_ROUTE = "mousepad-atspi-append-v1"
_ROUTE_FIELDS = {
    ROUTE: ("darwin", "AXTextArea"),
    LINUX_ROUTE: ("linux", "text"),
}
MAX_RECORD_BYTES = 131072
PARENT_WAIT_S = 35.0
WORKER_DEADLINE_S = 25.0
OP_ID = re.compile(r"op_[0-9a-f]{12}\Z")


class RecoveryError(ValueError):
    """Unsupported or inconsistent recovery evidence; no execution authority."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def fingerprint(text: str) -> dict[str, Any]:
    return {"sha256": hashlib.sha256(text.encode()).hexdigest(), "length": len(text)}


def _hash(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _fingerprint(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"sha256", "length"}
        and _hash(value["sha256"])
        and type(value["length"]) is int
        and value["length"] >= 0
    )


def validate_recovery(value: Any) -> dict[str, Any]:
    from .backend import ScopedBackend

    fields = {"version", "route", "nonce", "scope", "scope_digest", "identity", "field", "before", "expected"}
    if (
        not isinstance(value, dict)
        or set(value) != fields
        or type(value["version"]) is not int
        or value["version"] != VERSION
        or not isinstance(value["route"], str)
        or value["route"] not in _ROUTE_FIELDS
    ):
        raise RecoveryError("unsupported recovery envelope")
    if not isinstance(value["nonce"], str) or re.fullmatch(r"[0-9a-f]{32}", value["nonce"]) is None:
        raise RecoveryError("invalid attempt nonce")
    from .contracts import CapabilityError

    try:
        ScopedBackend._check_scope(value["scope"])
    except CapabilityError as exc:
        raise RecoveryError("invalid recovery scope") from exc
    if value["scope_digest"] != digest(value["scope"]):
        raise RecoveryError("scope fingerprint changed")
    field = value["field"]
    if (
        not isinstance(field, dict)
        or set(field) != {"role", "frame"}
        or field["role"] != _ROUTE_FIELDS[value["route"]][1]
        or not isinstance(field["frame"], list)
        or len(field["frame"]) != 4
        or any(type(x) not in (int, float) or not math.isfinite(x) for x in field["frame"])
        or field["frame"][2] <= 0
        or field["frame"][3] <= 0
    ):
        raise RecoveryError("unsupported field identity")
    identity = value["identity"]
    if (
        not isinstance(identity, dict)
        or set(identity) != {"boot", "pid", "start", "document", "device", "inode"}
        or not isinstance(identity["boot"], str)
        or not identity["boot"]
        or not isinstance(identity["start"], str)
        or not identity["start"]
        or identity["pid"] != value["scope"]["destination"]["pid"]
        or type(identity["pid"]) is not int
        or any(type(identity[k]) is not int or identity[k] < 0 for k in ("device", "inode"))
        or not isinstance(identity["document"], str)
        or not Path(identity["document"]).is_absolute()
    ):
        raise RecoveryError("unsupported native identity")
    if not _fingerprint(value["before"]) or not _fingerprint(value["expected"]):
        raise RecoveryError("invalid content fingerprint")
    if len(canonical(value)) > MAX_RECORD_BYTES:
        raise RecoveryError("oversized recovery envelope")
    return value


def make_recovery(scope: dict, identity: dict, role: str, frame: Any, before: str, expected: str) -> dict:
    # Generation attests the currently qualified platform/field route. Validation
    # remains host-independent so historical packets can still be inspected.
    route = next((name for name, pair in _ROUTE_FIELDS.items() if pair == (sys.platform, role)), None)
    if route is None:
        raise RecoveryError("unsupported recovery platform or field role")
    return validate_recovery(
        {
            "version": VERSION,
            "route": route,
            "nonce": uuid.uuid4().hex,
            "scope": scope,
            "scope_digest": digest(scope),
            "identity": identity,
            "field": {"role": role, "frame": list(frame)},
            "before": fingerprint(before),
            "expected": fingerprint(expected),
        }
    )


def process_identity(pid: int) -> dict[str, Any]:
    import psutil  # existing pinned browser-use dependency; no PID-only fallback

    proc = psutil.Process(pid)
    return {"pid": pid, "start": proc.create_time().hex()}


def native_identity(scope: dict) -> dict[str, Any]:
    try:
        boot = boot_identity()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise RecoveryError("native restart boot identity unavailable") from exc
    spec = scope["destination"]
    document = Path(spec["document"]).resolve(strict=True)
    info = document.stat()
    return {
        **process_identity(spec["pid"]),
        "boot": boot,
        "document": str(document),
        "device": info.st_dev,
        "inode": info.st_ino,
    }


def same_native_identity(left: dict, right: dict) -> bool:
    """NSDocument safe-save replaces inode; live AX identity is distinct from disk identity."""
    return all(left.get(k) == right.get(k) for k in ("boot", "pid", "start", "document"))


def _private_info(info: os.stat_result, *, directory: bool = False) -> None:
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise RecoveryError("execution artifact is not owner-only")
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise RecoveryError("execution artifact has unsupported type")


def _directory(path: Path, *, create: bool = False) -> None:
    if create:
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            pass
    _private_info(path.lstat(), directory=True)  # symlinks never qualify


def _sync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def read_private(path: Path) -> dict[str, Any]:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        _private_info(info)
        if info.st_size > MAX_RECORD_BYTES:
            raise RecoveryError("oversized execution artifact")
        with os.fdopen(fd, "rb", closefd=False) as src:
            value = json.loads(src.read(MAX_RECORD_BYTES + 1))
        if not isinstance(value, dict):
            raise RecoveryError("execution artifact is not an object")
        return value
    finally:
        os.close(fd)


def write_private(path: Path, value: dict) -> None:
    """Publish a bounded immutable record atomically, syncing data and directory."""
    _directory(path.parent)
    data = canonical(value)
    if len(data) > MAX_RECORD_BYTES:
        raise RecoveryError("oversized execution artifact")
    tmp = path.parent / (".tmp-" + uuid.uuid4().hex)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as out:
            out.write(data)
            out.flush()
            os.fsync(fd)
        # link is an atomic exclusive publication; no overwriting an existing receipt.
        os.link(tmp, path, follow_symlinks=False)
        _sync_dir(path.parent)
    finally:
        os.close(fd)
        tmp.unlink(missing_ok=True)
        _sync_dir(path.parent)


def packet_for(op: Operation) -> dict:
    recovery = validate_recovery(op.recovery)
    if (
        op.task != recovery["scope"]["task"]
        or op.resource
        != (
            f"native:{recovery['scope']['destination']['pid']}:{recovery['scope']['destination']['window_id']}"
        )
        or op.move != "append"
        or set(op.args) != {"text"}
    ):
        raise RecoveryError("operation does not match recovery scope")
    text = op.args["text"]
    if not isinstance(text, str) or not text.strip() or len(text) > 4096:
        raise RecoveryError("unsupported execution payload")
    return validate_packet(
        {
            "version": VERSION,
            "operation_id": op.id,
            "request_digest": op.request_digest,
            "request": {
                "task": op.task,
                "resource": op.resource,
                "observation": op.observation,
                "target": op.target,
                "move": op.move,
                "args": op.args,
            },
            "recovery": recovery,
            "args": op.args,
        }
    )


def validate_packet(packet: Any) -> dict:
    from .journal import request_digest

    if (
        not isinstance(packet, dict)
        or set(packet) != {"version", "operation_id", "request_digest", "request", "recovery", "args"}
        or type(packet["version"]) is not int
        or packet["version"] != VERSION
        or not isinstance(packet["operation_id"], str)
        or not OP_ID.fullmatch(packet["operation_id"])
    ):
        raise RecoveryError("unsupported execution packet")
    recovery = validate_recovery(packet["recovery"])
    request = packet["request"]
    if (
        not isinstance(request, dict)
        or set(request) != {"task", "resource", "observation", "target", "move", "args"}
        or packet["request_digest"] != request_digest(**request)
        or request["args"] != packet["args"]
        or request["task"] != recovery["scope"]["task"]
        or request["move"] != "append"
        or request["resource"]
        != f"native:{recovery['scope']['destination']['pid']}:{recovery['scope']['destination']['window_id']}"
        or not isinstance(packet["args"], dict)
        or set(packet["args"]) != {"text"}
        or not isinstance(packet["args"]["text"], str)
        or not packet["args"]["text"].strip()
        or len(packet["args"]["text"]) > 4096
    ):
        raise RecoveryError("packet does not match admitted request")
    return packet


def binding(packet: dict) -> dict:
    return {
        "version": VERSION,
        "operation_id": packet["operation_id"],
        "request_digest": packet["request_digest"],
        "nonce": packet["recovery"]["nonce"],
        "packet_digest": digest(packet),
    }


def validate_result(packet: dict, result: dict) -> dict:
    if set(result) != {*binding(packet), "disposition", "phase", "evidence", "error"}:
        raise RecoveryError("unsupported terminal receipt")
    if type(result.get("version")) is not int or any(result.get(k) != v for k, v in binding(packet).items()):
        raise RecoveryError("terminal receipt binding changed")
    disposition, phase, evidence = result["disposition"], result["phase"], result["evidence"]
    if (
        disposition not in {"applied", "partial", "refused", "not_sent", "unknown"}
        or phase not in {"not_sent", "sent", "ambiguous"}
        or not isinstance(evidence, dict)
        or (result["error"] is not None and not isinstance(result["error"], str))
    ):
        raise RecoveryError("invalid terminal outcome")
    if disposition in {"refused", "not_sent"} and phase != "not_sent":
        raise RecoveryError("no-send receipt has a sent phase")
    if disposition == "applied":
        expected = packet["recovery"]
        if (
            phase != "sent"
            or evidence.get("driver_effect") != "confirmed"
            or evidence.get("identity") != expected["identity"]
            or not isinstance(evidence.get("identity_after"), dict)
            or not same_native_identity(evidence["identity_after"], expected["identity"])
            or evidence.get("before") != expected["before"]
            or evidence.get("after") != expected["expected"]
            or not isinstance(evidence.get("readback"), dict)
            or evidence["readback"].get("passed") is not True
        ):
            raise RecoveryError("receipt lacks qualified exact execution evidence")
    return result


class ExecutionStore:
    def __init__(self, journal_path: Path) -> None:
        self._children: list[subprocess.Popen] = []
        self.root = Path(str(Path(journal_path).absolute()) + ".executions")

    def directory(self, op_id: str) -> Path:
        if not OP_ID.fullmatch(op_id):
            raise RecoveryError("invalid operation path")
        return self.root / op_id

    def _check(self, op_id: str, *, create: bool = False) -> Path:
        _directory(self.root, create=create)
        path = self.directory(op_id)
        _directory(path, create=create)
        if create:
            _sync_dir(self.root)
            _sync_dir(self.root.parent)
        return path

    def write_record(self, op_id: str, name: str, value: dict) -> None:
        if name not in {"packet", "registration", "claimed", "input_started", "result"}:
            raise RecoveryError("unsupported record name")
        write_private(self._check(op_id) / (name + ".json"), value)

    def read_record(self, op_id: str, name: str) -> dict | None:
        if name not in {"packet", "registration", "claimed", "input_started", "result"}:
            raise RecoveryError("unsupported record name")
        try:
            return read_private(self._check(op_id) / (name + ".json"))
        except FileNotFoundError:
            return None

    def prepare(self, op: Operation) -> dict:
        packet = packet_for(op)
        path = self._check(op.id, create=True)
        write_private(path / "packet.json", packet)
        return packet

    def read_result(self, op: Operation) -> dict | None:
        packet = self.read_record(op.id, "packet")
        if packet is None:
            return None
        if packet != packet_for(op):
            raise RecoveryError("execution packet changed")
        result = self.read_record(op.id, "result")
        return validate_result(packet, result) if result is not None else None

    def custody(self, op: Operation) -> str:
        try:
            path = self._check(op.id) / "worker.lock"
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return "unattested"
        try:
            _private_info(os.fstat(fd))
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return "active"
            fcntl.flock(fd, fcntl.LOCK_UN)
            return "unattested"  # a launched child may not have acquired its lock yet
        finally:
            os.close(fd)

    def _launch(self, op: Operation) -> subprocess.Popen:
        return subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-m",
                "jevdual.capability.execution_worker",
                "--packet",
                str(self.directory(op.id) / "packet.json"),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
        )

    async def execute(self, op: Operation) -> dict | None:
        # No timeout/cancellation handler kills the detached effect owner.
        self._children = [child for child in self._children if child.poll() is None]
        proc = self._launch(op)
        self._children.append(proc)
        deadline = time.monotonic() + PARENT_WAIT_S
        while proc.poll() is None:
            if time.monotonic() >= deadline:
                return self.read_result(op)  # bounded wait; execution may continue, never killed here
            await asyncio.sleep(0.025)
        return self.read_result(op)  # never infer an effect from exit code/stdout
