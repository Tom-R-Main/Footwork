"""The live probes' lock gate reads ioreg's plist and fails closed (notebook DC3)."""

from __future__ import annotations

import plistlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from probe_browser_holder import _console_locked


def _ioreg(*users: dict) -> bytes:
    return plistlib.dumps({"IOConsoleUsers": list(users), "IORegistryEntryName": "Root"})


def test_a_locked_console_session_nested_as_ioreg_prints_it_is_locked():
    # ioreg nests the key three tabs deep; DC3's run read this as unlocked.
    out = _ioreg({"CGSSessionScreenIsLocked": True, "kCGSSessionOnConsoleKey": True})
    assert b"<key>CGSSessionScreenIsLocked</key>\n\t\t\t<true/>" in out
    assert _console_locked(out)


def test_an_unlocked_console_session_without_the_lock_key_is_unlocked():
    assert not _console_locked(_ioreg({"kCGSSessionOnConsoleKey": True, "CGSSessionScreenIsLocked": False}))
    assert not _console_locked(_ioreg({"kCGSSessionOnConsoleKey": True}))


def test_only_the_console_session_counts():
    out = _ioreg({"CGSSessionScreenIsLocked": True}, {"kCGSSessionOnConsoleKey": True})
    assert not _console_locked(out)


def test_unreadable_or_sessionless_output_counts_as_locked():
    assert _console_locked(b"")
    assert _console_locked(b"<not a plist")
    assert _console_locked(_ioreg())
    assert _console_locked(_ioreg({"CGSSessionScreenIsLocked": False}))
