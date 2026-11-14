"""PTD2: footwork drag-points, a real-pointer drag between two screen points with no session. The
poster and the clock are stood in for; nothing here posts an event or reads a display."""

from __future__ import annotations

import itertools
import json
import math
from typing import ClassVar

import pytest

pytest.importorskip("cua_driver")

START, END = (300.0, 400.0), (520.0, 440.0)
DISPLAY = (0.0, 0.0, 1728.0, 1117.0)


class Poster:
    """Records every post; the pointer follows moves and drags. ``foreign_after`` drags, it reports a
    foreign key press; a move past ``stall_after`` moves leaves the pointer where it was."""

    events: ClassVar[list[tuple[str, float, float]]] = []
    pointer: ClassVar[tuple[float, float]] = (900.0, 700.0)
    button: ClassVar[bool] = False
    foreign_after: ClassVar[int | None] = None
    stall_after: ClassVar[int | None] = None
    #: how many readings after a release still say the button is down (None: every one of them)
    lag_reads: ClassVar[int | None] = 0
    lagging: ClassVar[int | None] = 0

    def _count(self, kind: str) -> int:
        return sum(1 for e in Poster.events if e[0] == kind)

    def move(self, x, y):
        Poster.events.append(("move", x, y))
        if Poster.stall_after is None or self._count("move") <= Poster.stall_after:
            Poster.pointer = (x, y)

    def down(self, x, y):
        Poster.events.append(("down", x, y))
        Poster.button = True

    def drag(self, x, y):
        Poster.events.append(("drag", x, y))
        Poster.pointer = (x, y)

    def up(self, x, y):
        Poster.events.append(("up", x, y))
        Poster.button = False
        Poster.lagging = Poster.lag_reads

    def escape(self):
        Poster.events.append(("escape", 0.0, 0.0))

    def location(self):
        return Poster.pointer

    def foreign_input(self):
        if Poster.foreign_after is not None and self._count("drag") >= Poster.foreign_after:
            return "key_down"
        return None

    def left_button_down(self):
        if Poster.lagging is None:
            return True
        if Poster.lagging > 0:
            Poster.lagging -= 1
            return True
        return Poster.button


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def now(self):
        return self.t

    def sleep_until(self, t):
        self.t = max(self.t, t)


@pytest.fixture
def desk(monkeypatch):
    from jevdual import drag, point_drag

    Poster.events, Poster.pointer, Poster.button = [], (900.0, 700.0), False
    Poster.foreign_after = Poster.stall_after = None
    Poster.lag_reads = Poster.lagging = 0
    monkeypatch.setattr(drag, "QuartzPoster", Poster)
    monkeypatch.setattr(drag, "MonotonicClock", Clock)
    monkeypatch.setattr(point_drag, "display_bounds", lambda: [DISPLAY])
    return Poster


def _run(capsys, *argv):
    """The command as the launcher runs it: its exit code, its one JSON object, and what it said."""
    from jevdual.cli import main

    code = main(["drag-points", *argv])
    out, err = capsys.readouterr()
    return code, json.loads(out.strip().splitlines()[-1]), err


def _points(*extra):
    return (*(str(v) for v in (*START, *END)), "--mode", "exclusive_desktop", *extra)


def _kinds(events):
    out: list[str] = []
    for kind, _, _ in events:
        if not out or out[-1] != kind:
            out.append(kind)
    return out


def test_a_drag_between_two_points_approaches_presses_drags_and_releases_once(desk, capsys):
    """PTD1: the engine dragged only between two observed elements. A canvas has none, so the command
    takes the two points: it comes to the start with no button, presses there, drags, and lets go at
    the end."""
    code, said, err = _run(capsys, *_points())
    assert code == 0, (said, err)
    assert _kinds(desk.events) == ["move", "down", "drag", "up"]
    moves = [(x, y) for kind, x, y in desk.events if kind == "move"]
    drags = [(x, y) for kind, x, y in desk.events if kind == "drag"]
    assert moves[-1] == START and drags[-1] == END
    assert [e for e in desk.events if e[0] == "down"] == [("down", *START)]
    assert [e for e in desk.events if e[0] == "up"] == [("up", *END)]
    assert all(math.dist(a, b) < 40 for a, b in itertools.pairwise(drags))  # a path, not a jump
    assert said["outcome"] == "dropped" and said["released_at"] == list(END) and said["button_up"] is True
    assert said["pressed"] is True and said["approach_moves"] == len(moves) and said["drags"] == len(drags)
    assert said["start"] == list(START) and said["end"] == list(END) and said["escape_sent"] is False
    # what a caller sets beside its page's own pointerdown and pointerup: where and when, on a named clock
    assert said["pressed_at"] == list(START) and said["clock"] in ("CLOCK_UPTIME_RAW", "CLOCK_MONOTONIC_RAW")
    assert isinstance(said["pressed_ns"], int) and isinstance(said["released_ns"], int)
    assert said["pressed_ns"] < said["released_ns"] <= said["clock_pair"]["ns"] and said["clock_pair"]["unix_s"] > 0
    assert said["planned_motion_s"] > 0.3 and said["press_hold_s"] == 0.12 and said["settle_s"] == 0.15


@pytest.mark.parametrize("off", [0.0, 1.5])
def test_a_pointer_already_at_the_start_is_not_moved_before_the_press(desk, capsys, off):
    """The caller may have brought the pointer there itself. Within two points there is no approach, and
    the press is posted at the start point itself."""
    desk.pointer = (START[0] + off, START[1])
    code, said, _ = _run(capsys, *_points())
    assert code == 0 and _kinds(desk.events) == ["down", "drag", "up"] and said["approach_moves"] == 0
    assert desk.events[0] == ("down", *START) and said["pointer_before"] == [START[0] + off, START[1]]


def test_a_pointer_two_points_away_is_brought_to_the_start(desk, capsys):
    desk.pointer = (START[0] + 2.0, START[1])
    code, said, _ = _run(capsys, *_points())
    assert code == 0 and _kinds(desk.events)[0] == "move" and said["approach_moves"] >= 1


def test_a_duration_stretches_the_planned_drag_and_keeps_its_path(desk, capsys):
    """A box drawn as fast as the planner's default reads quick on film. --duration plays the same
    path over a longer time; the press hold and the settle are apart from it."""
    _run(capsys, *_points())
    plain = [e for e in desk.events if e[0] == "drag"]
    desk.events.clear()
    desk.pointer = (900.0, 700.0)
    code, said, err = _run(capsys, *_points("--duration", "1.5"))
    assert code == 0, (said, err)
    assert said["planned_motion_s"] == 1.5 and [e for e in desk.events if e[0] == "drag"] == plain


@pytest.mark.parametrize("seconds", ["0.1", "30"])
def test_a_duration_the_engine_cannot_keep_is_refused_with_nothing_posted(desk, capsys, seconds):
    """Shorter than the planner's is faster than a hand; too long leaves posts further apart than the
    engine's 50 ms limit, which it would stop on mid-drag with the button down."""
    from jevdual.point_drag import EXIT_REFUSED

    code, said, err = _run(capsys, *_points("--duration", seconds))
    assert code == EXIT_REFUSED and said["code"] == "duration_unreachable" and desk.events == [], (said, err)
    assert ("shorter than the planned" in said["reason"]) is (seconds == "0.1")
    assert ("the longest this path takes is" in said["reason"]) is (seconds == "30")


@pytest.mark.parametrize(("argv", "code_said"), [
    ((*(str(v) for v in (*START, *END)),), "requires_desktop"),
    ((*(str(v) for v in (*START, *END)), "--mode", "background_only"), "requires_desktop"),
    (("300", "400", "303", "402", "--mode", "exclusive_desktop"), "drag_too_short"),
    (("300", "400", "5000", "440", "--mode", "exclusive_desktop"), "point_off_display"),
    (("-40", "400", "520", "440", "--mode", "exclusive_desktop"), "point_off_display"),
])
def test_what_the_arguments_refuse_posts_nothing(desk, capsys, argv, code_said):
    """PTD2: the posture, a drag too short for an app to take as one (the engine's rule), and a point
    on no display are refused before anything is posted and before the desktop is claimed."""
    from jevdual.coordination import Coordinator
    from jevdual.point_drag import EXIT_REFUSED

    code, said, err = _run(capsys, *argv)
    assert code == EXIT_REFUSED and said["outcome"] == "refused" and said["code"] == code_said, (said, err)
    assert desk.events == [] and said["pressed"] is False
    assert err.startswith(f"not dragged: {code_said}: ")
    assert Coordinator().status()["requests"] == []


def test_a_button_already_down_is_refused_with_nothing_posted(desk, capsys):
    """Pressing over a button someone holds would end their press, not begin this drag."""
    from jevdual.point_drag import EXIT_REFUSED

    desk.button = True
    code, said, _ = _run(capsys, *_points())
    assert code == EXIT_REFUSED and said["code"] == "button_down" and desk.events == []


async def test_a_desktop_another_owner_holds_is_refused_with_nothing_posted(desk, capsys, tmp_path):
    """PTD2: the command belongs to no session, so nothing else would stop it dragging across a desktop
    a filmed take has reserved. It claims the desktop as a session's command does, and does not wait."""
    from jevdual import point_drag
    from jevdual.coordination import Coordinator
    from jevdual.point_drag import EXIT_REFUSED

    registry = Coordinator()
    async with registry.claim(str(tmp_path / "film"), ["desktop"]) as claim:
        token = registry.reserve(claim, ["desktop"])
    args = point_drag.arguments(*_points("--owner", str(tmp_path / "caller")))
    assert await point_drag.cmd_drag_points(args) == EXIT_REFUSED
    said = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert said["outcome"] == "refused" and said["code"] == "desktop_busy" and desk.events == []
    registry.revoke(token)
    assert await point_drag.cmd_drag_points(args) == 0  # and with the reservation gone it drags


def test_the_claim_is_given_up_when_the_command_ends(desk, capsys):
    from jevdual.coordination import Coordinator

    code, _, _ = _run(capsys, *_points())
    status = Coordinator().status()
    assert code == 0 and status["requests"] == [] and status["reservations"] == []


def test_foreign_input_during_the_drag_cancels_it_and_releases_once(desk, capsys):
    """PTD2: every exit after the press lets go exactly once, after Escape, and says where."""
    from jevdual.point_drag import EXIT_ABORTED

    desk.foreign_after = 5
    code, said, err = _run(capsys, *_points())
    assert code == EXIT_ABORTED, (said, err)
    assert _kinds(desk.events) == ["move", "down", "drag", "escape", "up"]
    ups = [e for e in desk.events if e[0] == "up"]
    last_drag = [e for e in desk.events if e[0] == "drag"][-1]
    assert len(ups) == 1 and ups[0][1:] == last_drag[1:] != END
    assert said["outcome"] == "aborted:pointer_contended:key_down"
    assert said["released_at"] == list(last_drag[1:]) and said["escape_sent"] is True
    assert said["pressed"] is True and said["button_up"] is True
    assert "released at" in err and "not at the end point" in err


@pytest.mark.parametrize("interrupted", [False, True])
def test_a_release_the_system_has_not_yet_shown_is_waited_for_and_reported_up(desk, capsys, interrupted):
    """PTD4: the one live interrupted drag read the button 0.2 ms after posting its release, was told it
    was still down, and said so; the page had the release and the button read up afterwards. The command
    reads until the button is up, for a bounded time, and says how long that took."""
    desk.lag_reads = 3
    if interrupted:
        desk.foreign_after = 5
    code, said, err = _run(capsys, *_points())
    assert said["button_up"] is True and said["button_up_after_ms"] > 0, (said, err)
    assert code == (6 if interrupted else 0) and "STILL READS DOWN" not in err


def test_a_button_that_never_reads_up_is_reported_down_after_the_wait(desk, capsys, monkeypatch):
    """The reading is the only check that the button was not left down, so a wait that runs out is said."""
    from jevdual import point_drag
    from jevdual.point_drag import EXIT_ABORTED

    monkeypatch.setattr(point_drag, "BUTTON_UP_WAIT_S", 0.05)
    desk.lag_reads = None
    code, said, err = _run(capsys, *_points())
    assert code == EXIT_ABORTED and said["outcome"] == "dropped", (said, err)  # released at the end, and yet
    assert said["button_up"] is False and said["button_up_after_ms"] is None
    assert "THE LEFT BUTTON STILL READS DOWN after 50 ms" in err


def test_an_approach_that_does_not_arrive_never_presses(desk, capsys):
    from jevdual.point_drag import EXIT_APPROACH

    desk.stall_after = 3
    code, said, err = _run(capsys, *_points())
    assert code == EXIT_APPROACH, (said, err)
    assert _kinds(desk.events) == ["move"] and said["pressed"] is False
    assert said["outcome"].startswith("approach_aborted:") and said["released_at"] is None


def test_a_recorded_drag_appends_one_pointer_record_with_its_posts(desk, capsys, tmp_path):
    """PTD2: the same pointer_gesture/1 line a filmed drag writes, with no window to name."""
    record = tmp_path / "gestures.jsonl"
    code, _, _ = _run(capsys, *_points("--record", str(record)))
    assert code == 0
    line, = record.read_text().splitlines()
    kept = json.loads(line)
    assert kept["schema"] == "pointer_gesture/1" and kept["kind"] == "drag" and kept["outcome"] == "dropped"
    assert kept["start"] == list(START) and kept["requested_target"] == list(END)
    assert kept["window_origin"] == [None, None] and kept["content_origin"] == [None, None]
    events = [s["event"] for s in kept["posted_samples"]]
    assert events[0] == "down" and events[-1] == "up" and set(events[1:-1]) == {"drag"}
    code, _, _ = _run(capsys, *_points("--record", str(record)))
    assert code == 0 and len(record.read_text().splitlines()) == 2


def test_the_command_is_listed_and_takes_points_left_of_the_main_display(desk, capsys, monkeypatch):
    """A display to the left of the main one has negative x; the parser must take it as a number."""
    from jevdual import point_drag

    monkeypatch.setattr(point_drag, "display_bounds", lambda: [(-1920.0, 0.0, 1920.0, 1080.0), DISPLAY])
    desk.pointer = (-900.0, 500.0)
    code, said, err = _run(capsys, "-800", "400", "-600", "440", "--mode", "exclusive_desktop")
    assert code == 0 and said["released_at"] == [-600.0, 440.0], (said, err)
