"""Kernel boot identity participates in native admission and restart binding."""

from __future__ import annotations

import subprocess

import pytest
from jevdual import platform_identity, session_operations
from jevdual.capability import recovery
from jevdual.capability.journal import JournalError

BOOT = "e71abdd8-dc51-42d4-a90e-e8f5c179a22c"
OTHER_BOOT = "223c0539-4a48-45cc-9b50-6a6c0e0ea3b9"


@pytest.fixture
def linux_identity(tmp_path, monkeypatch):
    boot_file = tmp_path / "boot_id"
    boot_file.write_text(BOOT + "\n")
    document = tmp_path / "owned-document.txt"
    document.write_text("original text\n")
    scope = {"destination": {"pid": 77, "window_id": 123, "document": str(document)}}
    monkeypatch.setattr(platform_identity.sys, "platform", "linux")
    monkeypatch.setattr(platform_identity, "_LINUX_BOOT_ID", boot_file)
    monkeypatch.setattr(recovery, "process_identity", lambda pid: {"pid": pid, "start": "0x1.0p0"})

    def no_sysctl(*args, **kwargs):
        pytest.fail("Linux boot identity must not invoke macOS sysctl")

    monkeypatch.setattr(platform_identity.subprocess, "check_output", no_sysctl)
    return boot_file, document, scope


def test_linux_kernel_boot_identity_binds_both_operator_and_recovery(linux_identity):
    _, document, scope = linux_identity
    operator = session_operations.native_identity(77, 123)
    native = recovery.native_identity(scope)
    assert operator == {"pid": 77, "start": "0x1.0p0", "boot": BOOT, "window_id": 123}
    assert native == {
        "pid": 77, "start": "0x1.0p0", "boot": BOOT, "document": str(document),
        "device": document.stat().st_dev, "inode": document.stat().st_ino,
    }
    assert BOOT in session_operations.native_resource(operator)
    assert '"window_id":123' in session_operations.native_binding(operator)


@pytest.mark.parametrize("invalid", [
    "", "boot-time-123", BOOT.replace("-", ""), "{" + BOOT + "}",
    "00000000-0000-0000-0000-000000000000", BOOT + "\n" + OTHER_BOOT, "x" * 1024,
    BOOT + " " * 128 + "not-a-boot-id", "π",
])
def test_malformed_linux_boot_id_refuses_both_identity_routes(linux_identity, invalid, monkeypatch):
    boot_file, _, scope = linux_identity
    boot_file.write_text(invalid)

    def no_process_query(pid):
        pytest.fail("invalid boot identity must refuse before any process fallback")

    monkeypatch.setattr(recovery, "process_identity", no_process_query)
    with pytest.raises(JournalError, match="native_identity_unavailable"):
        session_operations.native_identity(77, 123)
    with pytest.raises(recovery.RecoveryError, match="boot identity unavailable"):
        recovery.native_identity(scope)


def test_unavailable_linux_boot_id_refuses_without_fallback(linux_identity):
    boot_file, _, scope = linux_identity
    boot_file.unlink()
    with pytest.raises(JournalError, match="native_identity_unavailable"):
        session_operations.native_identity(77, 123)
    with pytest.raises(recovery.RecoveryError, match="boot identity unavailable"):
        recovery.native_identity(scope)


def test_new_boot_and_reused_pid_do_not_preserve_native_identity(linux_identity, monkeypatch):
    boot_file, _, scope = linux_identity
    first_operator = session_operations.native_identity(77, 123)
    first_native = recovery.native_identity(scope)
    boot_file.write_text(OTHER_BOOT + "\n")
    assert session_operations.native_resource(session_operations.native_identity(77, 123)) != (
        session_operations.native_resource(first_operator)
    )
    assert not recovery.same_native_identity(first_native, recovery.native_identity(scope))
    boot_file.write_text(BOOT + "\n")
    monkeypatch.setattr(recovery, "process_identity", lambda pid: {"pid": pid, "start": "0x2.0p0"})
    assert not recovery.same_native_identity(first_native, recovery.native_identity(scope))


def test_process_identity_failure_and_missing_document_still_refuse(linux_identity, monkeypatch):
    _, document, scope = linux_identity

    def disappeared(pid):
        raise ProcessLookupError("process exited")

    monkeypatch.setattr(recovery, "process_identity", disappeared)
    with pytest.raises(JournalError, match="native_identity_unavailable"):
        session_operations.native_identity(77, 123)
    with pytest.raises(ProcessLookupError):
        recovery.native_identity(scope)
    document.unlink()
    with pytest.raises(FileNotFoundError):
        recovery.native_identity(scope)


@pytest.mark.parametrize(("pid", "window"), [(0, 123), (-1, 123), (77, 0), (77, -1)])
def test_invalid_operator_target_still_refuses(linux_identity, pid, window):
    with pytest.raises(JournalError, match="native_identity_unavailable"):
        session_operations.native_identity(pid, window)


def test_darwin_keeps_existing_sysctl_contract_and_identifier_spelling(monkeypatch):
    calls = []
    monkeypatch.setattr(platform_identity.sys, "platform", "darwin")

    def sysctl(command, **kwargs):
        calls.append((command, kwargs))
        return BOOT.upper() + "\n"

    monkeypatch.setattr(platform_identity.subprocess, "check_output", sysctl)
    assert platform_identity.boot_identity() == BOOT.upper()
    assert calls == [(["sysctl", "-n", "kern.bootsessionuuid"], {"text": True, "timeout": 2})]


def test_darwin_unavailable_boot_id_and_unsupported_platform_refuse(monkeypatch):
    monkeypatch.setattr(platform_identity.sys, "platform", "darwin")

    def timed_out(*args, **kwargs):
        raise subprocess.TimeoutExpired("sysctl", 2)

    monkeypatch.setattr(platform_identity.subprocess, "check_output", timed_out)
    with pytest.raises(JournalError, match="native_identity_unavailable"):
        session_operations.native_identity(77, 123)
    with pytest.raises(recovery.RecoveryError, match="boot identity unavailable"):
        recovery.native_identity({})
    monkeypatch.setattr(platform_identity.sys, "platform", "win32")
    with pytest.raises(ValueError, match="unsupported"):
        platform_identity.boot_identity()
