"""Linux policy admission never invents shared-desktop activity evidence."""

from types import SimpleNamespace

import pytest
from jevdual import posture


@pytest.fixture
def linux_host(monkeypatch):
    monkeypatch.setattr(posture, "sys", SimpleNamespace(platform="linux"))


@pytest.mark.parametrize("mode", posture.MODES)
def test_linux_background_admission_preserves_unknown_lock_policy(linux_host, mode):
    policy = posture.ExecutionPolicy(mode)
    assert policy.permits("background") is None
    assert isinstance(policy.activity, posture.LinuxActivity)
    assert policy.activity.lock_detection_available is False
    assert policy.activity.frontmost_pid() is None
    assert policy.foreground_tracking_available() is False
    assert policy.foreground_log == []


def test_linux_shared_foreground_refused_before_activity_or_input(linux_host, monkeypatch):
    def unexpected(*_args):
        pytest.fail("an unavailable idle or focus observer must not run")

    monkeypatch.setattr(posture.LinuxActivity, "idle_seconds", unexpected)
    monkeypatch.setattr(posture.LinuxActivity, "watch", unexpected)
    policy = posture.ExecutionPolicy("foreground_permitted")
    refusal = policy.permits("foreground", why="save the document")
    assert refusal is not None
    assert refusal.code == "platform_posture_unavailable"
    assert "save the document" in refusal.reason
    assert "exclusive_desktop" in refusal.reason
    assert policy.foreground_log == []


def test_linux_exclusive_admission_has_no_fabricated_foreground_receipt(linux_host):
    policy = posture.ExecutionPolicy("exclusive_desktop")
    for delivery in ("background", "foreground", "desktop"):
        assert policy.permits(delivery) is None
    with pytest.raises(posture.PlatformPostureUnavailable):
        policy.before_foreground()
    with pytest.raises(posture.PlatformPostureUnavailable):
        policy.after_foreground({})
    assert policy.foreground_log == []
    assert not hasattr(policy, "_watch")


@pytest.mark.parametrize("method,args", [("idle_seconds", ()), ("watch", ()), ("activate", (42,))])
def test_linux_unavailable_observation_and_activation_raise(method, args):
    with pytest.raises(posture.PlatformPostureUnavailable) as exc:
        getattr(posture.LinuxActivity(), method)(*args)
    assert exc.value.code == "platform_posture_unavailable"


def test_linux_mode_boundaries_and_observed_lock_take_precedence(linux_host, monkeypatch):
    refusal = posture.ExecutionPolicy("background_only").permits("foreground")
    assert refusal is not None and refusal.code == "requires_foreground"
    refusal = posture.ExecutionPolicy("foreground_permitted").permits("desktop")
    assert refusal is not None and refusal.code == "requires_desktop"
    monkeypatch.setattr(posture, "screen_locked", lambda: True)
    for mode in posture.MODES:
        for delivery in ("background", "foreground", "desktop"):
            refusal = posture.ExecutionPolicy(mode).permits(delivery)
            assert refusal is not None and refusal.code == "screen_locked"


class InjectedActivity:
    def __init__(self, idle=10.0):
        self.idle = idle
        self.watched = False

    def idle_seconds(self):
        return self.idle

    def frontmost_pid(self):
        return 17

    def activate(self, pid):
        return pid == 17

    def watch(self):
        self.watched = True
        return SimpleNamespace(fronts=[17], stop=lambda: [17])


def test_injected_activity_remains_authoritative_on_linux(linux_host):
    activity = InjectedActivity()
    policy = posture.ExecutionPolicy("foreground_permitted", activity=activity)
    assert policy.foreground_tracking_available() is True
    assert policy.permits("foreground") is None
    before = policy.before_foreground()
    result = policy.after_foreground(before)
    assert activity.watched
    assert result["idle_before"] == 10.0
    assert result["front_before"] == result["front_after"] == 17
    assert result["restored"] is True
    activity.idle = 0.2
    refusal = policy.permits("foreground")
    assert refusal is not None and refusal.code == "human_active"


def test_macos_keeps_existing_activity_selection(monkeypatch):
    monkeypatch.setattr(posture, "sys", SimpleNamespace(platform="darwin"))
    policy = posture.ExecutionPolicy()
    assert isinstance(policy._activity(), posture.MacActivity)
    assert policy.foreground_tracking_available() is True
