"""Owned launch must not touch an existing Chrome profile, including through a symlink."""

from __future__ import annotations

import os
import signal
import stat
import subprocess
import sys
import time

import pytest
from jevdual.effectors.cdp import launch as cdp_launch


@pytest.mark.parametrize("kind", ["empty", "populated", "symlink", "file", "dangling_symlink"])
def test_existing_profile_paths_are_refused_without_mutation(tmp_path, monkeypatch, kind):
    profile = tmp_path / "profile"
    target = tmp_path / "target"
    if kind in {"symlink", "dangling_symlink"}:
        if kind == "symlink":
            target.mkdir()
        profile.symlink_to(target, target_is_directory=True)
    elif kind == "file":
        profile.write_bytes(b"an unrelated file")
    else:
        profile.mkdir()
    contents = {"DevToolsActivePort": b"9222\n/devtools/browser/original\n", "Preferences": b"untouched"}
    directory = target if kind == "symlink" else profile
    if kind in {"populated", "symlink"}:
        for name, value in contents.items():
            (directory / name).write_bytes(value)

    def forbidden_launch(*args, **kwargs):
        pytest.fail("an existing profile reached process creation")

    monkeypatch.setattr(cdp_launch.subprocess, "Popen", forbidden_launch)
    with pytest.raises(cdp_launch.LaunchRefused) as refused:
        cdp_launch.launch("unused-chrome", profile)
    assert refused.value.code == "browser_profile_unavailable"
    assert refused.value.dispatched is False
    if kind in {"populated", "symlink"}:
        assert {p.name: p.read_bytes() for p in directory.iterdir()} == contents
    elif kind == "empty":
        assert list(profile.iterdir()) == []
    elif kind == "file":
        assert profile.read_bytes() == b"an unrelated file"
    else:
        assert profile.is_symlink() and not target.exists()
    if kind == "symlink":
        assert profile.is_symlink() and profile.readlink() == target


def test_fresh_profile_is_created_private_before_process_launch(tmp_path, monkeypatch):
    profile = tmp_path / "parent" / "profile"

    class AtLaunch(Exception):
        pass

    def stop_at_launch(*args, **kwargs):
        assert profile.is_dir() and not profile.is_symlink()
        assert stat.S_IMODE(profile.stat().st_mode) & 0o077 == 0
        assert list(profile.iterdir()) == []
        raise AtLaunch

    monkeypatch.setattr(cdp_launch.subprocess, "Popen", stop_at_launch)
    with pytest.raises(AtLaunch):
        cdp_launch.launch("unused-chrome", profile)


def _handle(process, tmp_path):
    import psutil

    return cdp_launch.OwnedChrome(
        process.pid, psutil.Process(process.pid).create_time(), sys.executable,
        tmp_path / "profile", True, "ws://127.0.0.1:1/devtools/browser/test", process,
    )


def _running(process):
    import psutil

    try:
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def test_stop_cleans_a_captured_term_resistant_child_without_touching_a_sentinel(tmp_path, monkeypatch):
    import psutil

    ready = tmp_path / "ready"
    child_code = (
        "import os,signal,sys,time; from pathlib import Path; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)"
    )
    root_code = (
        "import subprocess,sys,time; "
        f"subprocess.Popen([sys.executable, '-c', {child_code!r}, sys.argv[1]]); time.sleep(60)"
    )
    root = subprocess.Popen([sys.executable, "-c", root_code, str(ready)], start_new_session=True)
    sentinel = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
    child = None
    try:
        deadline = time.monotonic() + 5
        while not ready.exists():
            assert time.monotonic() < deadline, "the child never installed its TERM handler"
            time.sleep(0.01)
        child = psutil.Process(int(ready.read_text()))
        chrome = _handle(root, tmp_path)
        group_signals = []
        killpg = os.killpg

        def observed_group_signal(group, sig):
            # No group signal is safe after the root has been reaped.
            assert root.returncode is None
            group_signals.append((group, sig))
            killpg(group, sig)

        monkeypatch.setattr(cdp_launch.os, "killpg", observed_group_signal)
        cdp_launch.stop(chrome)
        assert root.returncode is not None
        assert not _running(child), "cleanup returned with the owned TERM-resistant child alive"
        assert sentinel.poll() is None
        assert group_signals == [(root.pid, signal.SIGTERM)]
    finally:
        # Fixture-only cleanup is pinned to these Popen/psutil objects and runs on failures too.
        if root.poll() is None:
            root.kill()
        root.wait(timeout=5)
        if child is not None and _running(child):
            child.kill()
        sentinel.terminate()
        sentinel.wait(timeout=5)


def test_stop_reports_uncertainty_when_the_root_exited_before_inventory(tmp_path):
    process = subprocess.Popen(
        [sys.executable, "-c", "import sys; sys.stdin.buffer.read(1)"], stdin=subprocess.PIPE,
    )
    chrome = _handle(process, tmp_path)
    process.communicate(input=b"x", timeout=5)
    with pytest.raises(cdp_launch.CleanupUnverified) as uncertain:
        cdp_launch.stop(chrome)
    assert uncertain.value.code == "browser_cleanup_unverified"


def test_a_descendant_exiting_during_identity_capture_does_not_block_root_cleanup(tmp_path, monkeypatch):
    import psutil

    root = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
    chrome = _handle(root, tmp_path)
    real_process = psutil.Process

    class Gone:
        pid = 123456789

        def create_time(self):
            raise psutil.NoSuchProcess(self.pid)

    class Root:
        def create_time(self):
            return chrome.incarnation

        def children(self, recursive):
            return [Gone()]

    monkeypatch.setattr(psutil, "Process", lambda pid: Root() if pid == root.pid else real_process(pid))
    try:
        cdp_launch.stop(chrome)
        assert root.returncode is not None
    finally:
        if root.poll() is None:
            root.kill()
        root.wait(timeout=5)


def test_changed_root_incarnation_is_never_signaled(tmp_path, monkeypatch):
    from dataclasses import replace

    root = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
    chrome = replace(_handle(root, tmp_path), incarnation=0)

    def forbidden_group_signal(*args):
        pytest.fail("changed root incarnation reached group signaling")

    monkeypatch.setattr(cdp_launch.os, "killpg", forbidden_group_signal)
    try:
        with pytest.raises(cdp_launch.CleanupUnverified, match="incarnation"):
            cdp_launch.stop(chrome)
        assert root.poll() is None
    finally:
        root.kill()
        root.wait(timeout=5)
