"""Parent-liveness supervisor for a tool-free planner, never a body dispatcher.

An inherited pipe closes on host death. The supervisor holds an inherited flock
until the planner group has been terminated and reaped. Restart only waits on
that lock; it never kills a process based on a retained PID.
"""
import argparse
import contextlib
import fcntl
import os
import select
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

import order_protocol as protocol

RECOVERY_TIMEOUT = 12
REASONS = {"completed", "host exited before planner startup", "host liveness pipe closed",
           "host cancelled planner", "planner watchdog timeout", "planner failed", "planner guardian failed"}


def _positive_pid(value):
    return type(value) is int and value > 0


def _bound_record(value, intent):
    return (isinstance(value, dict) and all(value.get(k) == intent[k] for k in ("host_pid", "owner", "request_sha256"))
            and _positive_pid(value.get("guardian_pid")))


def _present(path):
    return path.exists() or path.is_symlink()


def lock_call(root):
    root = protocol.directory(root)
    fd = os.open(root / "planner.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        os.close(fd)
        raise protocol.Refusal("planner lock must be a private regular file")
    return fd


def recover(root):
    """Wait for prior writers before exposing a restarted host; no PID signals."""
    root = protocol.directory(root)
    if not _present(root / "planner-intent.json"):
        if any(_present(root / name) for name in ("planner-process.json", "planner-closure.json", "planner.lock")):
            raise protocol.Refusal("planner ownership artifacts have no intent")
        return None
    intent = protocol.decode(protocol.read_bytes(root / "planner-intent.json"))
    protocol.fields(intent, ("version", "host_pid", "owner", "request_sha256"), "planner intent")
    if type(intent["version"]) is not int or intent["version"] != 1 or type(intent["host_pid"]) is not int or intent["host_pid"] <= 0:
        raise protocol.Refusal("invalid planner intent")
    protocol.identity(intent["owner"])
    if not isinstance(intent["request_sha256"], str) or not protocol.DIGEST.fullmatch(intent["request_sha256"]):
        raise protocol.Refusal("invalid planner request digest")
    reservation = protocol.decode(protocol.read_bytes(root / "reservation.json"))
    if not isinstance(reservation, dict) or reservation.get("planner_owner", intent["owner"]) != intent["owner"]:
        raise protocol.Refusal("planner intent differs from its reservation owner")
    fd = lock_call(root)
    try:
        deadline = time.monotonic() + RECOVERY_TIMEOUT
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise protocol.Refusal("prior planner ownership has not closed; restart refused") from None
                time.sleep(.05)
        started = root / "planner-process.json"
        closed = root / "planner-closure.json"
        if _present(started) and not _present(closed):
            raise protocol.Refusal("planner ownership ended without group cleanup proof")
        if _present(closed):
            if not _present(started):
                raise protocol.Refusal("planner cleanup has no startup identity")
            startup = protocol.decode(protocol.read_bytes(started))
            base = {"owner", "request_sha256", "guardian_pid", "host_pid", "process_exit_observed", "group_closed"}
            if (not isinstance(startup, dict) or set(startup) not in (base, base | {"planner_pid", "planner_pgid"}) or not _bound_record(startup, intent) or
                    startup["group_closed"] is not False or startup["process_exit_observed"] is not False or
                    "planner_pid" in startup and (not _positive_pid(startup["planner_pid"]) or startup["planner_pgid"] != startup["planner_pid"])):
                raise protocol.Refusal("planner startup proof is inconsistent")
            closure = protocol.decode(protocol.read_bytes(closed))
            if (not isinstance(closure, dict) or set(closure) != base | {"reason", "exit_code"} or
                    not _bound_record(closure, intent) or closure["guardian_pid"] != startup["guardian_pid"] or
                    closure["group_closed"] is not True or closure["process_exit_observed"] is not True or
                    not isinstance(closure["reason"], str) or closure["reason"] not in REASONS or
                    closure["exit_code"] is not None and type(closure["exit_code"]) is not int):
                raise protocol.Refusal("planner cleanup proof is inconsistent")
            return closure
        # Intent was saved before launch. The inherited lock was never handed to
        # a supervisor which published startup, so no planner can have started.
        return {"owner": intent["owner"], "request_sha256": intent["request_sha256"],
                "reason": "host exited before planner startup", "group_closed": True, "process_exit_observed": True}
    finally:
        os.close(fd)


def _close_group(child):
    # The group is created by this supervisor, not identified from disk. Always
    # terminate descendants even if the leader has already exited.
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(child.pid, signal.SIGTERM)
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            child.wait(timeout=3)
            return
        except PermissionError:
            # Darwin may return EPERM while only unsignalable zombie members
            # remain. Reap our child and require ESRCH before claiming closure.
            pass
        child.poll()
        time.sleep(.05)
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(child.pid, signal.SIGKILL)
    child.wait(timeout=3)
    # A zombie descendant can briefly retain group membership while its new
    # parent reaps it. Refuse proof rather than releasing uncertain ownership.
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            return
        except PermissionError:
            pass
        time.sleep(.05)
    raise protocol.Refusal("planner process group did not close")


def supervise(root, executable, lifetime_fd, lock_fd):
    root = protocol.directory(root)
    intent = protocol.decode(protocol.read_bytes(root / "planner-intent.json"))
    request = protocol.decode(protocol.read_bytes(root / "request.json"))
    cancelled = False
    def stop(*_):
        nonlocal cancelled
        cancelled = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    child = None
    reason = "completed"
    closure = {"owner": intent["owner"], "request_sha256": intent["request_sha256"],
               "guardian_pid": os.getpid(), "host_pid": intent["host_pid"], "process_exit_observed": False, "group_closed": False}
    try:
        # Publish before spawning: missing closure after this point is ambiguous
        # and restart refuses even if a guardian was itself killed.
        protocol.create_file(root / "planner-process.json", protocol.encoded({**closure, "host_pid": intent["host_pid"]}))
        readable, _, _ = select.select([lifetime_fd], [], [], 0)
        if readable and not os.read(lifetime_fd, 1):
            reason = "host exited before planner startup"
        else:
            child = subprocess.Popen([executable, "exec", *request["flags"]], stdin=subprocess.PIPE,
                stdout=sys.stdout, stderr=sys.stderr, start_new_session=True, close_fds=True)
            protocol.persist(root / "planner-process.json", {**closure, "host_pid": intent["host_pid"],
                "planner_pid": child.pid, "planner_pgid": child.pid})
            child.stdin.write(protocol.read_bytes(root / "prompt.txt"))
            child.stdin.close()
            started = time.monotonic()
            while child.poll() is None:
                readable, _, _ = select.select([lifetime_fd], [], [], .05)
                if readable and not os.read(lifetime_fd, 1):
                    reason = "host liveness pipe closed"
                    break
                if cancelled:
                    reason = "host cancelled planner"
                    break
                if time.monotonic() - started > 105:
                    reason = "planner watchdog timeout"
                    break
            if reason == "completed" and child.returncode != 0:
                reason = "planner failed"
    except Exception:
        reason = "planner guardian failed"
        raise
    finally:
        try:
            if child is not None:
                _close_group(child)
            closure.update(reason=reason, exit_code=child.returncode if child else None,
                           process_exit_observed=True, group_closed=True)
            protocol.create_file(root / "planner-closure.json", protocol.encoded(closure))
        finally:
            os.close(lifetime_fd)
            os.close(lock_fd)
    return child.returncode if reason == "completed" and child else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--executable", required=True)
    parser.add_argument("--lifetime-fd", type=int, required=True)
    parser.add_argument("--lock-fd", type=int, required=True)
    args = parser.parse_args()
    raise SystemExit(supervise(args.root, args.executable, args.lifetime_fd, args.lock_fd))
