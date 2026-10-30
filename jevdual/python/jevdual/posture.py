"""Execution posture: how the harness may reach its target, declared once per session and enforced at
dispatch (2026-09-25).

The authorizer (``jevdual.authorize``) decides what may change. Posture decides how the harness may get
there. An authorized save is still the wrong action when it takes the foreground from a person typing in
another app, so the two are separate checks and neither implies the other.

Every dispatch declares its delivery before anything is sent:

* ``background``: addressed to one window or element (an AX press, an AX value write, an AX insertion, a
  key posted to a process that owns exactly one eligible window). The front app, the key window and the
  person's pointer are untouched.
* ``foreground``: the target window is brought to the front for the action. On a shared Mac the
  person's chosen app is restored afterwards. Linux currently supports this only on an explicitly
  exclusive desktop; its scoped driver transaction may leave the target active.
* ``desktop``: acts on whatever the desktop routes to: the real pointer, the frontmost app, a screen point.

The session's mode decides which deliveries it may use:

* ``background_only``: background only. A step that needs more returns a typed ``requires_foreground``
  result, nothing is sent, and the caller chooses another route or stops. The default for an operator
  session, because the person is assumed present.
* ``foreground_permitted``: background, and foreground when the person has been idle for ``idle_s``; with
  recent input the step yields (``human_active``) instead of taking the front. Never desktop.
* ``exclusive_desktop``: everything; the harness assumes a desktop reserved for automation (the native
  evaluation runs, a VM). No gate.

Restoring the front app afterwards does not make a foreground step equivalent to a background one: the
person's keystrokes during the interval land in the agent's window. The idle gate makes that unlikely;
the coexistence suite (``docs/experiments/Q15.md``) measures it.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from typing import Literal, Protocol

Mode = Literal["background_only", "foreground_permitted", "exclusive_desktop"]
Delivery = Literal["background", "foreground", "desktop"]
MODES: tuple[Mode, ...] = ("background_only", "foreground_permitted", "exclusive_desktop")
_ALLOWED: dict[Mode, frozenset[Delivery]] = {
    "background_only": frozenset({"background"}),
    "foreground_permitted": frozenset({"background", "foreground"}),
    "exclusive_desktop": frozenset({"background", "foreground", "desktop"}),
}
#: seconds without human input before a foreground step may take the front (foreground_permitted)
IDLE_S = 3.0


class Activity(Protocol):
    """What the posture reads about the person: seconds since the last input and the front app."""

    def idle_seconds(self) -> float: ...

    def frontmost_pid(self) -> int | None: ...

    def activate(self, pid: int) -> bool: ...

    def watch(self) -> FrontWatch: ...


class FrontWatch:
    """The front app sampled every 20 ms while a foreground step runs, so the step can tell where the
    person went during it (a front-before read alone cannot: it predates their move)."""

    def __init__(self, read: object = None) -> None:
        import threading

        self.fronts: list[int | None] = []
        self._read = read or frontmost_pid
        self._halt = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def _run(self) -> None:
        import time

        while not self._halt.is_set():
            f = self._read()  # type: ignore[operator]
            if not self.fronts or self.fronts[-1] != f:
                self.fronts.append(f)
            time.sleep(0.02)

    def stop(self) -> list[int | None]:
        self._halt.set()
        self._t.join(timeout=1)
        return self.fronts


class MacActivity:
    """The HID system's idle counter and LaunchServices' front app. Posted HID events count as input
    (measured 2026-09-25: a CGEventPost at the HID tap reset both the HID and the combined counters), so
    the coexistence suite's scripted person registers exactly as a person would."""

    def idle_seconds(self) -> float:
        import Quartz

        return float(
            Quartz.CGEventSourceSecondsSinceLastEventType(
                Quartz.kCGEventSourceStateHIDSystemState, Quartz.kCGAnyInputEventType
            )
        )

    def frontmost_pid(self) -> int | None:
        return frontmost_pid()

    def activate(self, pid: int) -> bool:
        """Activate exactly this process. The Driver's ``bring_to_front`` resolves an app by bundle and
        activated the wrong one of two Python processes (2026-09-25); NSRunningApplication takes the pid."""
        return activate(pid)

    def watch(self) -> FrontWatch:
        return FrontWatch()

    def screen_locked(self) -> bool:
        return screen_locked()


class PlatformPostureUnavailable(RuntimeError):
    """The host cannot observe or preserve shared-desktop foreground ownership."""

    code = "platform_posture_unavailable"


class LinuxActivity:
    """Conservative admission until Linux shared-desktop coexistence is qualified.

    The lock state is unknown, matching the existing unknown-lock admission policy.
    Exclusive desktop dispatch uses the driver's exact-window transaction, without
    claiming an idle reading, observed foreground ownership, or focus restoration.
    """

    foreground_tracking_available = False
    lock_detection_available = False

    def idle_seconds(self) -> float:
        raise PlatformPostureUnavailable("Linux human-input idle observation is not qualified")

    def frontmost_pid(self) -> int | None:
        return None

    def activate(self, pid: int) -> bool:
        raise PlatformPostureUnavailable("Linux shared-desktop focus restoration is not qualified")

    def watch(self) -> FrontWatch:
        raise PlatformPostureUnavailable("Linux shared-desktop foreground tracking is not qualified")

    def screen_locked(self) -> bool:
        return screen_locked()


def screen_locked() -> bool:
    """True while the login session's screen is locked. Accessibility cannot reach windows then: the
    G4 run kept deciding and pressing keys for 25 steps against a locked screen, every step answered
    "no AX window" (2026-09-26)."""
    if sys.platform.startswith("linux"):
        # No qualified session-lock observer yet. False is the existing admission
        # convention for unknown, not evidence that a Linux session is unlocked.
        return False
    try:
        import Quartz

        d = Quartz.CGSessionCopyCurrentDictionary() or {}
        return bool(d.get("CGSSessionScreenIsLocked"))
    except Exception:  # noqa: BLE001 - unknown is not locked; the Driver's own errors still apply
        return False


def activate(pid: int) -> bool:
    import time

    from AppKit import NSRunningApplication

    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    if app is None:
        return False
    app.activateWithOptions_(1 << 1)  # NSApplicationActivateIgnoringOtherApps
    for _ in range(25):
        if frontmost_pid() == pid:
            return True
        time.sleep(0.02)
    return False


def frontmost_pid() -> int | None:
    """The pid of the app that receives the person's keystrokes now (``lsappinfo front``: current on every
    call, unlike NSWorkspace in a process without a run loop)."""
    try:
        asn = subprocess.run(
            ["lsappinfo", "front"], capture_output=True, text=True, timeout=5, check=False
        ).stdout.strip()
        out = subprocess.run(
            ["lsappinfo", "info", "-only", "pid", asn], capture_output=True, text=True, timeout=5, check=False
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    digits = "".join(ch for ch in out.split("=")[-1] if ch.isdigit())
    return int(digits) if digits else None


@dataclass(frozen=True)
class Refusal:
    """A step the posture will not take. ``code`` is ``requires_foreground``, ``requires_desktop``,
    ``human_active``, ``screen_locked`` or ``platform_posture_unavailable``;
    nothing was sent to any target."""

    code: str
    reason: str


@dataclass
class ExecutionPolicy:
    mode: Mode = "background_only"
    idle_s: float = IDLE_S
    activity: Activity | None = None
    #: every foreground step taken: (front pid before, front pid after, idle seconds before) for the receipt
    foreground_log: list[dict[str, object]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {', '.join(MODES)}, not {self.mode!r}")

    def _activity(self) -> Activity:
        if self.activity is None:
            self.activity = LinuxActivity() if sys.platform.startswith("linux") else MacActivity()
        return self.activity

    def foreground_tracking_available(self) -> bool:
        """Whether this activity can observe and restore a shared foreground step.

        Injected providers retain their existing contract unless they explicitly
        declare the capability unavailable.
        """
        return bool(getattr(self._activity(), "foreground_tracking_available", True))

    def permits(self, delivery: Delivery, *, why: str = "") -> Refusal | None:
        """None when this session may deliver this way now; otherwise the typed refusal."""
        if self.locked():
            return Refusal("screen_locked", f"{why or 'this step'}: the screen is locked; nothing is sent")
        if delivery not in _ALLOWED[self.mode]:
            code = "requires_desktop" if delivery == "desktop" else "requires_foreground"
            return Refusal(
                code, f"{why or 'this step'} needs {delivery} delivery; the session is {self.mode}"
            )
        if delivery == "foreground" and self.mode == "foreground_permitted":
            if not self.foreground_tracking_available():
                return Refusal(
                    "platform_posture_unavailable",
                    f"{why or 'this step'} needs qualified shared-desktop idle and focus observation; "
                    "this host supports foreground delivery only with explicit exclusive_desktop mode",
                )
            idle = self._activity().idle_seconds()
            if idle < self.idle_s:
                return Refusal(
                    "human_active",
                    f"{why or 'this step'} needs the foreground and the person gave input {idle:.1f}s ago "
                    f"(needs {self.idle_s:.0f}s idle); yielding",
                )
        return None

    def locked(self) -> bool:
        """The screen is locked (activities that cannot tell answer False)."""
        check = getattr(self._activity(), "screen_locked", None)
        return bool(check()) if callable(check) else False

    def before_foreground(self) -> dict[str, object]:
        """What the receipt records about a foreground step, read just before it; the front app is sampled
        from here until ``after_foreground``."""
        if not self.foreground_tracking_available():
            raise PlatformPostureUnavailable("Shared-desktop foreground tracking is unavailable")
        act = self._activity()
        self._watch = act.watch()
        return {"front_before": act.frontmost_pid(), "idle_before": round(act.idle_seconds(), 3)}

    def persons_choice(self, own_pid: int, front_before: object) -> object:
        """Where the person last went during the step: the last app other than ours seen in front after
        ours first took it, else the app that was in front before the step."""
        fronts = list(getattr(getattr(self, "_watch", None), "fronts", []) or [])
        if own_pid in fronts:
            after = fronts[fronts.index(own_pid) + 1 :]
            others = [f for f in after if f not in (None, own_pid)]
            if others:
                return others[-1]
        return front_before

    def after_foreground(self, before: dict[str, object]) -> dict[str, object]:
        """Front app after the step and whether the person gave input during it (idle shorter than the
        time since ``before`` was read cannot be told apart from our own events, so it is reported, never
        counted as success)."""
        if not self.foreground_tracking_available():
            raise PlatformPostureUnavailable("Shared-desktop foreground tracking is unavailable")
        act = self._activity()
        watch = getattr(self, "_watch", None)
        if watch is not None:
            before = {**before, "fronts_during": watch.stop()}
            self._watch = None
        rec = {**before, "front_after": act.frontmost_pid(), "idle_after": round(act.idle_seconds(), 3)}
        rec["restored"] = rec["front_after"] == rec["front_before"]
        self.foreground_log.append(rec)
        return rec
