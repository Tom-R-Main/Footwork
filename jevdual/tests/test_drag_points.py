"""PTD2, PTD10: footwork drag-points, a real-pointer drag between two screen points with no session.
The poster and the clock are stood in for; nothing here posts an event or reads a display."""

from __future__ import annotations

import itertools
import json
import math
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, ClassVar

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
    #: the button reads down until this many releases have been posted
    ups_needed: ClassVar[int] = 1
    #: a post of this kind raises this many times (None: every time). ``down`` posts first, then raises:
    #: the case where it is unknown whether the press went; the others raise with nothing posted
    failing: ClassVar[dict[str, int | None]] = {}
    #: called once, at the first reading of the button (before anything is posted) or after N moves
    at_first_read: ClassVar[Any] = None
    after_moves: ClassVar[tuple[int, Any] | None] = None
    #: once a press has been posted, reading the button raises
    unreadable_after_press: ClassVar[bool] = False

    def _count(self, kind: str) -> int:
        return sum(1 for e in Poster.events if e[0] == kind)

    def _fails(self, kind: str) -> bool:
        if kind not in Poster.failing:
            return False
        left = Poster.failing[kind]
        if left is None:
            return True
        Poster.failing[kind] = left - 1
        if left <= 1:
            del Poster.failing[kind]
        return True

    def move(self, x, y):
        Poster.events.append(("move", x, y))
        if Poster.stall_after is None or self._count("move") <= Poster.stall_after:
            Poster.pointer = (x, y)
        if Poster.after_moves is not None and self._count("move") == Poster.after_moves[0]:
            Poster.after_moves[1]()

    def down(self, x, y):
        Poster.events.append(("down", x, y))
        Poster.button = True
        if self._fails("down"):
            raise OSError("the press's post did not return")

    def drag(self, x, y):
        if self._fails("drag"):
            raise OSError("a drag's post failed")
        Poster.events.append(("drag", x, y))
        Poster.pointer = (x, y)

    def up(self, x, y):
        if self._fails("up"):
            raise OSError("the release's post failed")
        Poster.events.append(("up", x, y))
        if self._count("up") >= Poster.ups_needed:
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
        if Poster.at_first_read is not None:
            hook, Poster.at_first_read = Poster.at_first_read, None
            hook()
        if Poster.unreadable_after_press and self._count("down"):
            raise OSError("the button could not be read")
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
    Poster.ups_needed, Poster.failing, Poster.at_first_read, Poster.after_moves = 1, {}, None, None
    Poster.unreadable_after_press = False
    monkeypatch.setattr(drag, "QuartzPoster", Poster)
    monkeypatch.setattr(drag, "MonotonicClock", Clock)
    monkeypatch.setattr(point_drag, "display_bounds", lambda: [DISPLAY])
    HIT.update(calls=[], answer=lambda point, call: "Canvas App")
    monkeypatch.setattr(point_drag, "app_at", _app_at)
    return Poster


#: what the accessibility hit test is stood in for with: every point asked about, and what it finds there
#: (``answer(point, call)``, the call counted from 1; raise to make the reading fail)
HIT: dict[str, Any] = {"calls": [], "answer": lambda point, call: "Canvas App"}


def _app_at(point):
    HIT["calls"].append(point)
    return HIT["answer"](point, len(HIT["calls"]))


def _revoke_own_claim():
    """What a coordinator's ``control cancel`` does to the command's request, from inside its run."""
    from jevdual.coordination import Coordinator

    registry = Coordinator()
    registry.revoke(registry.status()["requests"][0]["token"])


def _run(capsys, *argv):
    """The command as the launcher runs it: its exit code, its one JSON object, and what it said."""
    from jevdual.cli import main

    code = main(["drag-points", *argv])
    out, err = capsys.readouterr()
    return code, json.loads(out.strip().splitlines()[-1]), err


def _points(*extra):
    return (*(str(v) for v in (*START, *END)), "--mode", "exclusive_desktop", "--app", "Canvas App", *extra)


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


def _on_the_path(point, path) -> bool:
    return any(math.dist(a, point) + math.dist(point, b) - math.dist(a, b) < 1e-6
               for a, b in itertools.pairwise(path))


@pytest.mark.parametrize("seconds", ["1.5", "5", "30"])
def test_a_duration_slows_the_drag_along_the_same_path_and_posts_as_often(desk, capsys, tmp_path, seconds):
    """A box drawn as fast as the planner's default reads quick on film. --duration plays the same path
    over a longer time. PTD9: spreading the same samples out put a slow drag's posts up to the engine's
    50 ms limit apart, where one late post stops it mid-drag. A slower drag has more posts instead:
    every one on the plain drag's path, none planned further apart in time than the plain drag's widest."""
    plain_record, slow_record = tmp_path / "plain.jsonl", tmp_path / "slow.jsonl"
    _run(capsys, *_points("--record", str(plain_record)))
    plain = [(x, y) for kind, x, y in desk.events if kind == "drag"]
    desk.events.clear()
    desk.pointer = (900.0, 700.0)
    code, said, err = _run(capsys, *_points("--duration", seconds, "--record", str(slow_record)))
    assert code == 0, (said, err)
    slow = [(x, y) for kind, x, y in desk.events if kind == "drag"]
    assert said["planned_motion_s"] == float(seconds) and slow[-1] == END and len(slow) > len(plain)
    assert [p for p in slow if p in plain] == plain  # every point of the plain drag, in its order
    assert all(_on_the_path(p, [START, *plain]) for p in slow)

    def widest(record) -> float:
        times = [s["t_ns"] for s in json.loads(record.read_text())["planned_samples"]]
        return max(b - a for a, b in itertools.pairwise(times)) / 1e9

    assert widest(slow_record) <= widest(plain_record) + 1e-6 < 0.05


@pytest.mark.parametrize(("seconds", "code_said"), [
    ("0.1", "duration_unreachable"), ("30.5", "duration_unreachable"), ("nan", "duration_invalid"),
    ("inf", "duration_invalid"), ("-inf", "duration_invalid"), ("0", "duration_invalid"), ("-2", "duration_invalid"),
])
def test_a_duration_that_cannot_be_kept_is_refused_with_nothing_posted(desk, capsys, seconds, code_said):
    """Shorter than the planner's is faster than a hand. PTD9: ``nan`` passed every comparison and was
    played as a drag with no times at all; and a duration with no upper end held the desktop and the
    button for as long as it said."""
    from jevdual.coordination import Coordinator
    from jevdual.point_drag import EXIT_REFUSED

    code, said, err = _run(capsys, *_points(f"--duration={seconds}"))
    assert code == EXIT_REFUSED and said["code"] == code_said and desk.events == [], (said, err)
    assert Coordinator().status()["requests"] == []


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
    assert said["button_up"] is True and said["button_up_ms_after_release"] > 0, (said, err)
    assert code == (6 if interrupted else 0) and "BUTTON" not in err
    assert "extra_release" not in said and said["releases_posted"] == 1 and said["claim_kept"] is None


def test_a_button_that_reads_down_after_the_wait_gets_one_more_release(desk, capsys, monkeypatch):
    """PTD10: the reading is the only check that the button was not left down. When it still says down
    after the wait, one more release is posted where the pointer is; here that one lets go."""
    from jevdual import point_drag
    from jevdual.coordination import Coordinator
    from jevdual.point_drag import EXIT_ABORTED

    monkeypatch.setattr(point_drag, "BUTTON_UP_WAIT_S", 0.05)
    desk.ups_needed = 2
    code, said, err = _run(capsys, *_points())
    ups = [e for e in desk.events if e[0] == "up"]
    assert ups == [("up", *END), ("up", *END)] and desk.events[-1][0] == "up", desk.events[-3:]
    assert code == EXIT_ABORTED and said["outcome"] == "dropped", (said, err)  # released at the end, and yet
    assert said["button_up"] is True and said["releases_posted"] == 2 and said["claim_kept"] is None
    assert said["extra_release"] == {"posted": True, "at": list(END)}
    assert "a second release was posted before the button read up" in err
    assert Coordinator().status()["requests"] == []


def test_a_button_that_never_reads_up_keeps_the_desktop_claimed_and_says_how_to_clear_it(desk, capsys, monkeypatch):
    """PTD10: a command that cannot say the button is up does not give the desktop back as if it could.
    Its request stays in the registry, which marks it orphaned once the process is gone and refuses
    every other owner of the desktop until someone has looked and recovers it by its token."""
    from jevdual import point_drag
    from jevdual.coordination import CoordinationError, Coordinator
    from jevdual.point_drag import EXIT_HELD, EXIT_REFUSED

    monkeypatch.setattr(point_drag, "BUTTON_UP_WAIT_S", 0.05)
    desk.lag_reads = None
    code, said, err = _run(capsys, *_points())
    assert code == EXIT_HELD and said["button_up"] is False and said["button_up_ms_after_release"] is None
    assert len([e for e in desk.events if e[0] == "up"]) == 2 and said["releases_posted"] == 2
    token = said["claim_kept"]
    assert "THE LEFT BUTTON MAY STILL BE DOWN" in err and "it reads down 50 ms after 2 releases" in err
    assert f"footwork control recover {token} --input-cleaned" in err
    registry = Coordinator()
    held, = registry.status()["requests"]
    assert held["token"] == token and held["state"] == "orphaned" and "desktop" in held["resources"]
    desk.events.clear()
    desk.lag_reads = desk.lagging = 0
    desk.button = False
    code, said, _ = _run(capsys, *_points())
    assert code == EXIT_REFUSED and said["code"] == "desktop_busy" and desk.events == []
    with pytest.raises(CoordinationError):
        registry.recover("not-the-token")
    registry.recover(token)
    assert _run(capsys, *_points())[0] == 0


def test_a_press_whose_post_fails_is_still_released_and_reported(desk, capsys):
    """PTD9: the press was posted outside the block that guarantees the release, so a press that was
    posted and then raised left the button down with nothing to let it go. Whether such a press went
    is not known; it is released as if it had, and the command reports instead of dying."""
    from jevdual.coordination import Coordinator
    from jevdual.point_drag import EXIT_ABORTED

    desk.failing = {"down": 1}
    code, said, err = _run(capsys, *_points())
    assert code == EXIT_ABORTED, (said, err)
    assert _kinds(desk.events) == ["move", "down", "up"] and desk.events[-1] == ("up", *START)
    assert said["outcome"] == "error:OSError" and said["error"] == "OSError" and said["press_post_failed"] is True
    assert said["pressed"] is True and said["pressed_at"] == list(START) and said["released_at"] == list(START)
    assert said["button_up"] is True and said["releases_posted"] == 1 and said["claim_kept"] is None
    assert Coordinator().status()["requests"] == []


def test_a_drag_post_that_fails_releases_where_the_drag_had_got_to(desk, capsys):
    from jevdual.point_drag import EXIT_ABORTED

    desk.failing = {"drag": None}
    code, said, err = _run(capsys, *_points())
    assert code == EXIT_ABORTED and said["outcome"] == "error:OSError", (said, err)
    assert _kinds(desk.events) == ["move", "down", "up"] and said["releases_posted"] == 1 and said["button_up"] is True


def test_a_release_whose_post_fails_once_is_posted_again(desk, capsys):
    """PTD9: a release was marked done before its post returned, so one that raised was never posted
    again. It is posted once more, and the drag ends where it was asked to."""
    desk.failing = {"up": 1}
    code, said, err = _run(capsys, *_points())
    assert code == 0 and said["outcome"] == "dropped" and said["release_error"] == "OSError", (said, err)
    assert [e for e in desk.events if e[0] == "up"] == [("up", *END)] and said["releases_posted"] == 1
    assert said["button_up"] is True and "extra_release" not in said


def test_a_release_that_cannot_be_posted_keeps_the_desktop_claimed(desk, capsys):
    """PTD10: two failed posts in the engine and one more by the command, and then nothing has let go
    of the button: the desktop stays claimed whatever the button reads."""
    from jevdual.coordination import Coordinator
    from jevdual.point_drag import EXIT_HELD

    desk.failing = {"up": None}
    code, said, err = _run(capsys, *_points())
    assert code == EXIT_HELD, (said, err)
    assert not [e for e in desk.events if e[0] == "up"] and said["releases_posted"] == 0
    assert said["outcome"] == "error:ButtonMayBeDown" and said["release_error"] == "OSError"
    assert said["released_at"] is None and said["button_up"] is False
    assert said["extra_release"] == {"posted": False, "at": list(END), "error": "OSError"}
    assert "no release could be posted" in err and f"recover {said['claim_kept']} --input-cleaned" in err
    held, = Coordinator().status()["requests"]
    assert held["token"] == said["claim_kept"] and held["state"] == "orphaned"


def test_a_button_that_cannot_be_read_after_a_press_keeps_the_desktop_claimed(desk, capsys):
    """PTD12: the reading was outside any handler and before the claim was marked kept, so a reading
    that raised gave the desktop back and printed nothing. A check that fails counts as the thing it
    checks having failed: the button is not known to be up, so the claim stays and the report says why."""
    from jevdual.coordination import Coordinator
    from jevdual.point_drag import EXIT_HELD

    desk.unreadable_after_press = True
    code, said, err = _run(capsys, *_points())
    assert code == EXIT_HELD, (said, err)
    assert said["outcome"] == "dropped" and said["button_up"] is False and said["button_read_error"] == "OSError"
    assert said["releases_posted"] == 2 and said["extra_release"]["posted"] is True
    assert f"recover {said['claim_kept']} --input-cleaned" in err
    held, = Coordinator().status()["requests"]
    assert held["token"] == said["claim_kept"] and held["state"] == "orphaned" and "desktop" in held["resources"]


def test_the_time_to_the_button_reading_up_is_counted_from_the_releases_post(desk, capsys):
    """PTD12: nothing held the number to the release. It lies between the release's post and the
    command's own later reading of the clock, and covers the readings that still said down."""
    desk.lag_reads = 3
    code, said, _ = _run(capsys, *_points())
    since_release_ms = (said["clock_pair"]["ns"] - said["released_ns"]) / 1e6
    assert code == 0 and 3 * 2.0 <= said["button_up_ms_after_release"] <= since_release_ms


def test_a_command_that_cannot_take_the_stop_signals_posts_nothing(desk, capsys):
    """PTD12: off the main thread the handlers cannot be installed, and the command went on without
    the protection it promises. It refuses instead."""
    import asyncio
    import threading

    from jevdual import point_drag
    from jevdual.coordination import Coordinator
    from jevdual.point_drag import EXIT_REFUSED

    codes: list[int] = []
    worker = threading.Thread(target=lambda: codes.append(asyncio.run(
        point_drag.cmd_drag_points(point_drag.arguments(*_points())))))
    worker.start()
    worker.join(timeout=20)
    said = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert codes == [EXIT_REFUSED] and said["code"] == "no_stop_signals" and desk.events == [], said
    assert Coordinator().status()["requests"] == []


@pytest.mark.parametrize("pointer_at_start", [True, False])
def test_a_claim_revoked_before_anything_is_posted_reports_nothing_posted(desk, capsys, pointer_at_start):
    """PTD9: a revocation before the press raised out of the command through a record that could not be
    written with no posts in it. It is an exit like the others: nothing posted, exit 4."""
    from jevdual.coordination import Coordinator
    from jevdual.point_drag import EXIT_REFUSED

    if pointer_at_start:
        desk.pointer = START
    desk.at_first_read = _revoke_own_claim
    code, said, err = _run(capsys, *_points())
    assert code == EXIT_REFUSED and desk.events == [], (said, err)
    assert said["outcome"] == "refused" and said["code"] == "cancelled" and said["pressed"] is False
    assert Coordinator().status()["requests"] == []


def test_a_claim_revoked_during_the_approach_reports_the_pointer_moved_and_no_press(desk, capsys):
    from jevdual.coordination import Coordinator
    from jevdual.point_drag import EXIT_APPROACH

    desk.after_moves = (3, _revoke_own_claim)
    code, said, err = _run(capsys, *_points())
    assert code == EXIT_APPROACH and _kinds(desk.events) == ["move"], (said, err)
    assert said["outcome"] == "approach_aborted:cancelled" and said["approach_moves"] == 3 and said["pressed"] is False
    assert Coordinator().status()["requests"] == []


def test_a_claim_revoked_during_the_drag_cancels_it_and_releases_once(desk, capsys):
    from jevdual.point_drag import EXIT_ABORTED

    desk.pointer = START
    original = desk.drag

    def drag(self, x, y):
        original(self, x, y)
        if self._count("drag") == 4:
            _revoke_own_claim()

    desk.drag = drag
    try:
        code, said, err = _run(capsys, *_points())
    finally:
        desk.drag = original
    assert code == EXIT_ABORTED and said["outcome"] == "aborted:cancelled", (said, err)
    assert _kinds(desk.events) == ["down", "drag", "escape", "up"] and said["releases_posted"] == 1


async def test_the_named_application_is_claimed_with_the_desktop(desk, capsys, tmp_path):
    """PTD9: the command claimed the desktop and nothing else, so a session that owned the application
    under the pointer, with no claim on the desktop, was no obstacle to a drag across its window."""
    from jevdual import point_drag
    from jevdual.coordination import Coordinator, app_resource
    from jevdual.point_drag import EXIT_REFUSED

    registry = Coordinator()
    args = point_drag.arguments(*_points("--owner", str(tmp_path / "caller")))
    async with registry.claim(str(tmp_path / "session"), [app_resource("Canvas App")]):
        assert await point_drag.cmd_drag_points(args) == EXIT_REFUSED
        said = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert said["code"] == "app_busy" and "Canvas App" in said["reason"] and desk.events == []
        assert said["app"] == "Canvas App" and said["claimed"] == ["app/canvas%20app", "desktop"]
    assert await point_drag.cmd_drag_points(args) == 0
    assert registry.status()["requests"] == []


def test_the_application_has_to_be_named(desk, capsys):
    """PTD15: the command used to work out the application from the window list, which named an owner
    of a window and not what would take the press. The caller says which application it means."""
    from jevdual.point_drag import EXIT_REFUSED

    code, said, _ = _run(capsys, *(str(v) for v in (*START, *END)), "--mode", "exclusive_desktop")
    assert code == EXIT_REFUSED and said["code"] == "app_required" and desk.events == [] and HIT["calls"] == []


@pytest.mark.parametrize(("covered", "name"), [(START, "start"), (END, "end")])
def test_an_end_that_lands_on_another_application_is_refused_with_nothing_posted(desk, capsys, covered, name):
    """PTD15: a system prompt sat over the screen while a live run waited, and the command would have
    pressed on it: it looked only at ordinary windows. Both ends are hit-tested, and a press that would
    land on anything but the named application is not posted."""
    from jevdual.coordination import Coordinator
    from jevdual.point_drag import EXIT_REFUSED

    HIT["answer"] = lambda point, call: "UserNotificationCenter" if point == covered else "Canvas App"
    code, said, err = _run(capsys, *_points())
    assert code == EXIT_REFUSED and said["code"] == "point_covered" and desk.events == [], (said, err)
    assert "UserNotificationCenter" in said["reason"] and f"the {name} point" in said["reason"]
    assert "Canvas App" in said["reason"] and Coordinator().status()["requests"] == []


def test_a_start_covered_after_the_approach_is_not_pressed(desk, capsys):
    """The reading before anything is posted can be out of date by the time the pointer arrives: it is
    taken again immediately before the press."""
    from jevdual.coordination import Coordinator
    from jevdual.point_drag import EXIT_APPROACH

    HIT["answer"] = lambda point, call: "UserNotificationCenter" if call > 2 and point == START else "Canvas App"
    code, said, err = _run(capsys, *_points())
    assert code == EXIT_APPROACH and _kinds(desk.events) == ["move"], (said, err)
    assert said["outcome"] == "approach_aborted:point_covered" and said["pressed"] is False
    assert "UserNotificationCenter" in said["reason"] and HIT["calls"] == [START, END, START]
    assert Coordinator().status()["requests"] == []


def test_a_start_covered_just_before_the_press_with_no_approach_posts_nothing(desk, capsys):
    from jevdual.point_drag import EXIT_REFUSED

    desk.pointer = START
    HIT["answer"] = lambda point, call: "UserNotificationCenter" if call > 2 else "Canvas App"
    code, said, _ = _run(capsys, *_points())
    assert code == EXIT_REFUSED and said["code"] == "point_covered" and desk.events == []


def test_a_hit_test_that_cannot_be_read_is_refused(desk, capsys):
    """Not knowing what is at a point is not the same as knowing the named application is."""
    from jevdual.coordination import Coordinator
    from jevdual.point_drag import EXIT_REFUSED

    def unreadable(point, call):
        raise LookupError("accessibility error -25204")

    HIT["answer"] = unreadable
    code, said, err = _run(capsys, *_points())
    assert code == EXIT_REFUSED and said["code"] == "recipient_unreadable" and desk.events == [], (said, err)
    assert Coordinator().status()["requests"] == []


@pytest.mark.parametrize(("named", "found"), [("canvas app", "Canvas App"), ("Chrome", "Google Chrome")])
def test_the_application_is_matched_as_the_registry_names_it(desk, capsys, named, found):
    HIT["answer"] = lambda point, call: found
    code, said, err = _run(capsys, *_points("--app", named))
    assert code == 0, (said, err)
    assert HIT["calls"] == [START, END, START, END]  # before anything is posted, and again before the press


STAND_IN = r'''
"""drag-points with a stand-in poster on the real clock, so a signal can arrive while the button is down."""
import json, sys
from pathlib import Path
from jevdual import drag, point_drag
from jevdual.cli import main
from jevdual.coordination import Coordinator

log, registry = Path(sys.argv[1]), Path(sys.argv[2])
state = {"pointer": (900.0, 700.0), "button": False}

def note(kind, x=0.0, y=0.0):
    with log.open("a") as stream:
        stream.write(json.dumps([kind, x, y]) + "\n")

class Poster:
    def move(self, x, y): note("move", x, y); state["pointer"] = (x, y)
    def down(self, x, y): note("down", x, y); state["button"] = True
    def drag(self, x, y): note("drag", x, y); state["pointer"] = (x, y)
    def up(self, x, y): note("up", x, y); state["button"] = False
    def escape(self): note("escape")
    def location(self): return state["pointer"]
    def foreign_input(self): return None
    def left_button_down(self): return state["button"]

original = Coordinator.__init__
Coordinator.__init__ = lambda self, path=None: original(self, path or registry)
drag.QuartzPoster = Poster
point_drag.display_bounds = lambda: [(0.0, 0.0, 1728.0, 1117.0)]
point_drag.app_at = lambda point: "Canvas App"
sys.exit(main(["drag-points", *sys.argv[3:]]))
'''


def _events(log: Path) -> list[list]:
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def _stand_in(tmp_path, *extra) -> tuple[subprocess.Popen, Path, Path]:
    script, log, registry = tmp_path / "stand_in.py", tmp_path / "events.jsonl", tmp_path / "registry.sqlite"
    script.write_text(STAND_IN)
    process = subprocess.Popen(
        [sys.executable, str(script), str(log), str(registry), *_points(*extra)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parent.parent / "python")})
    return process, log, registry


def _wait_for(log: Path, kind: str, count: int, process: subprocess.Popen) -> None:
    deadline = time.time() + 20
    while sum(1 for e in _events(log) if e[0] == kind) < count:
        assert process.poll() is None and time.time() < deadline, (process.poll(), _events(log)[-3:])
        time.sleep(0.01)


@pytest.mark.parametrize("told", [signal.SIGTERM, signal.SIGHUP, signal.SIGINT])
def test_a_command_told_to_stop_while_the_button_is_down_releases_it_and_reports(tmp_path, told):
    """PTD9: SIGTERM ended the process where it stood, with the button down and nothing to release it;
    the registry held the desktop afterwards and the button stayed pressed. Told to stop, the command
    stops as foreign input stops it (Escape, then one release where the drag had got to) and prints
    what it did before it exits."""
    from jevdual.coordination import Coordinator
    from jevdual.point_drag import EXIT_ABORTED

    process, log, registry = _stand_in(tmp_path, "--duration", "8")
    try:
        _wait_for(log, "drag", 5, process)
        process.send_signal(told)
        out, err = process.communicate(timeout=20)
    finally:
        if process.poll() is None:
            process.kill()
    said = json.loads(out.strip().splitlines()[-1])
    events = _events(log)
    assert process.returncode == EXIT_ABORTED, (process.returncode, said, err)
    assert [e[0] for e in events].count("up") == 1 and [e[0] for e in events[-2:]] == ["escape", "up"]
    assert said["outcome"] == "aborted:cancelled" and said["stopped_by"] == told.name
    assert said["button_up"] is True and said["releases_posted"] == 1 and said["claim_kept"] is None
    assert said["released_at"] == events[-3][1:] != list(END) and f"stopped by {told.name}" in err
    assert Coordinator(registry).status()["requests"] == []


def test_a_command_told_to_stop_during_the_approach_never_presses(tmp_path):
    from jevdual.coordination import Coordinator
    from jevdual.point_drag import EXIT_APPROACH

    process, log, registry = _stand_in(tmp_path)
    try:
        _wait_for(log, "move", 2, process)
        process.send_signal(signal.SIGTERM)
        out, err = process.communicate(timeout=20)
    finally:
        if process.poll() is None:
            process.kill()
    said = json.loads(out.strip().splitlines()[-1])
    assert process.returncode == EXIT_APPROACH, (process.returncode, said, err)
    assert {e[0] for e in _events(log)} == {"move"} and said["pressed"] is False
    assert said["outcome"] == "approach_aborted:cancelled" and said["stopped_by"] == "SIGTERM"
    assert Coordinator(registry).status()["requests"] == []


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
    code, said, err = _run(capsys, "-800", "400", "-600", "440", "--mode", "exclusive_desktop", "--app", "Canvas App")
    assert code == 0 and said["released_at"] == [-600.0, 440.0], (said, err)


def test_the_command_is_one_the_launcher_lists(capsys):
    """PTD9: the launcher's help and catalog listed every command but this one."""
    from jevdual.agent_cli import LEGACY
    from jevdual.cli import main

    assert "drag-points" in LEGACY
    assert main(["--help"]) == 0 and "drag-points" in capsys.readouterr().out
    assert main(["--json", "tools"]) == 0 and "drag-points" in json.loads(capsys.readouterr().out)["data"]["commands"]
