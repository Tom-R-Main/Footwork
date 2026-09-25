"""Execution posture: how the harness may reach its target, declared once per session and enforced at
dispatch (2026-09-25).

The authorizer (``jevdual.authorize``) decides what may change. Posture decides how the harness may get
there. An authorized save is still the wrong action when it takes the foreground from a person typing in
another app, so the two are separate checks and neither implies the other.

Every dispatch declares its delivery before anything is sent:

* ``background``: addressed to one window or element (an AX press, an AX value write, an AX insertion, a
  key posted to a process that owns exactly one eligible window). The front app, the key window and the
  person's pointer are untouched.
* ``foreground``: the target window is brought to the front for the action and the previous front app
  restored afterwards (the Driver's foreground ladder rung, ``invoke_menu``, ``bring_to_front``).
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
    """A step the posture will not take. ``code`` is ``requires_foreground``, ``requires_desktop`` or
    ``human_active``; nothing was sent to any target."""

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
            self.activity = MacActivity()
        return self.activity

    def permits(self, delivery: Delivery, *, why: str = "") -> Refusal | None:
        """None when this session may deliver this way now; otherwise the typed refusal."""
        if delivery not in _ALLOWED[self.mode]:
            code = "requires_desktop" if delivery == "desktop" else "requires_foreground"
            return Refusal(
                code, f"{why or 'this step'} needs {delivery} delivery; the session is {self.mode}"
            )
        if delivery == "foreground" and self.mode == "foreground_permitted":
            idle = self._activity().idle_seconds()
            if idle < self.idle_s:
                return Refusal(
                    "human_active",
                    f"{why or 'this step'} needs the foreground and the person gave input {idle:.1f}s ago "
                    f"(needs {self.idle_s:.0f}s idle); yielding",
                )
        return None

    def before_foreground(self) -> dict[str, object]:
        """What the receipt records about a foreground step, read just before it."""
        act = self._activity()
        return {"front_before": act.frontmost_pid(), "idle_before": round(act.idle_seconds(), 3)}

    def after_foreground(self, before: dict[str, object]) -> dict[str, object]:
        """Front app after the step and whether the person gave input during it (idle shorter than the
        time since ``before`` was read cannot be told apart from our own events, so it is reported, never
        counted as success)."""
        act = self._activity()
        rec = {**before, "front_after": act.frontmost_pid(), "idle_after": round(act.idle_seconds(), 3)}
        rec["restored"] = rec["front_after"] == rec["front_before"]
        self.foreground_log.append(rec)
        return rec
