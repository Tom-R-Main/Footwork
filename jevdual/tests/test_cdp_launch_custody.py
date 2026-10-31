"""Owned launch must not touch an existing Chrome profile, including through a symlink."""

from __future__ import annotations

import stat

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
