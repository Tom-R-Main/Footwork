"""The live probe of drag-points: what it reads from the page's title and how it judges a run.
Nothing here launches a browser or posts an event."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import probe_drag_points as probe

START = "PD n0 u0 x0 h0 l0 o0 t0 g0 k0 d- r-"
DRAGGED = "PD n1 u1 x0 h71 l0 o0 t0 g17 k0 d300,300 r520,440 - Google Chrome"
SAID = {"outcome": "dropped", "button_up": True}


def _page(text: str) -> dict:
    found = probe.parse(text)
    assert found is not None
    return found


def test_the_pages_summary_is_read_from_a_window_title_and_nothing_else_is():
    assert probe.parse("about:blank - Google Chrome") is None and probe.parse("") is None
    assert _page(START) == {"downs": 0, "ups": 0, "cancels": 0, "held_moves": 0, "loose_moves": 0,
                            "off_canvas": 0, "untrusted": 0, "max_move_gap_ms": 0, "keydowns": 0,
                            "down_at": None, "up_at": None}
    page = _page(DRAGGED)
    assert page["down_at"] == [300.0, 300.0] and page["up_at"] == [520.0, 440.0] and page["held_moves"] == 71


def test_the_page_counts_what_the_summary_claims():
    """The summary is only as good as the page's own listeners: each count has one, in the capture
    phase on the window, and a move counts as held only when the page says the left button is down."""
    for needle in ("addEventListener('pointerdown'", "addEventListener('pointermove'", "addEventListener('pointerup'",
                   "addEventListener('pointercancel'", "addEventListener('keydown'", "e.buttons === 1",
                   "!e.isTrusted", "e.target !== c", "e.clientX, e.clientY"):
        assert needle in probe.PAGE, needle
    assert probe.PAGE.count(", true);") == 5
    assert probe.page_url().startswith("data:text/html;base64,")


def test_a_drag_that_reached_the_page_as_one_held_trusted_drag_holds():
    verdict = probe.judge_drag(_page(START), _page(DRAGGED), SAID, 0)
    assert verdict["held"] and all(verdict["checks"].values())


@pytest.mark.parametrize(("title", "said", "code", "fails"), [
    (DRAGGED.replace("d300,300", "d301.5,300"), SAID, 0, "pressed_within_1px"),
    (DRAGGED.replace("r520,440", "r520,442"), SAID, 0, "released_within_1px"),
    (DRAGGED.replace("l0", "l3"), SAID, 0, "button_held_through_every_move"),
    (DRAGGED.replace("h71", "h4"), SAID, 0, "button_held_through_every_move"),
    (DRAGGED.replace("g17", "g64"), SAID, 0, "no_gap_over_the_limit"),
    (DRAGGED.replace("o0", "o1"), SAID, 0, "all_on_the_canvas"),
    (DRAGGED.replace("t0", "t2"), SAID, 0, "all_trusted"),
    (DRAGGED.replace("n1 u1", "n2 u2"), SAID, 0, "one_press_one_release"),
    (DRAGGED.replace("u1 x0", "u0 x1"), SAID, 0, "one_press_one_release"),
    (DRAGGED, {**SAID, "button_up": False}, 0, "button_reads_up"),
    (DRAGGED, {**SAID, "outcome": "aborted:playback_stall"}, 6, "exit_0_and_dropped"),
])
def test_each_way_a_drag_can_fall_short_fails_its_own_check(title, said, code, fails):
    verdict = probe.judge_drag(_page(START), _page(title), said, code)
    assert not verdict["held"] and [k for k, v in verdict["checks"].items() if not v] == [fails]


ORIGIN = (22.0, 142.0)  # the screen point of the page's 0,0
INTERRUPTED = "PD n2 u2 x0 h22 l0 o0 t0 g12 k2 d300,300 r371,345"
SAID_STOPPED = {"outcome": "aborted:pointer_contended:key_down", "pressed": True, "escape_sent": True,
                "released_at": [393.4, 487.2], "end": [542.0, 582.0], "button_up": True}


def test_an_interrupted_drag_holds_when_the_page_saw_one_held_drag_end_where_the_command_said():
    verdict = probe.judge_abort(_page(DRAGGED), _page(INTERRUPTED), SAID_STOPPED, 6, 6, ORIGIN)
    assert verdict["held"] and all(verdict["checks"].values())


@pytest.mark.parametrize(("title", "change", "code", "fails"), [
    (INTERRUPTED, {"escape_sent": False}, 6, "escape_was_sent"),
    (INTERRUPTED, {"button_up": False}, 6, "button_reads_up"),
    (INTERRUPTED, {"outcome": "dropped"}, 6, "exit_says_pressed_then_stopped"),
    (INTERRUPTED, {}, 0, "exit_says_pressed_then_stopped"),
    (INTERRUPTED, {"extra_release": {"posted": True}}, 6, "no_second_release"),
    # PTD9: each of these held under the first form of the judgment
    (INTERRUPTED.replace("u2 x0", "u1 x1"), {}, 6, "one_release_and_no_cancel"),  # a cancel, not a release
    (INTERRUPTED.replace("u2", "u3"), {}, 6, "one_release_and_no_cancel"),
    (INTERRUPTED.replace("r371,345", "r380,345"), {}, 6, "released_where_it_said"),
    (INTERRUPTED.replace("h22 l0", "h22 l4"), {}, 6, "button_held_through_every_move"),  # the button came up early
    (INTERRUPTED.replace("h22", "h0"), {}, 6, "button_held_through_every_move"),
    (INTERRUPTED.replace("g12", "g71"), {}, 6, "no_gap_over_the_limit"),
    (INTERRUPTED.replace("d300,300", "d304,300"), {}, 6, "pressed_within_1px"),
    (INTERRUPTED.replace("t0", "t1"), {}, 6, "all_trusted"),
    (INTERRUPTED.replace("o0", "o2"), {}, 6, "all_on_the_canvas"),
])
def test_each_way_an_interrupted_drag_can_fall_short_fails_its_own_check(title, change, code, fails):
    verdict = probe.judge_abort(_page(DRAGGED), _page(title), {**SAID_STOPPED, **change}, code, 6, ORIGIN)
    assert not verdict["held"] and [k for k, v in verdict["checks"].items() if not v] == [fails]


def test_a_drag_released_at_its_end_point_or_nowhere_is_not_an_interrupted_one():
    for released in ([542.0, 582.0], None):
        said = {**SAID_STOPPED, "released_at": released}
        failed = [k for k, v in probe.judge_abort(_page(DRAGGED), _page(INTERRUPTED), said, 6, 6, ORIGIN)["checks"].items()
                  if not v]
        assert "released_short_of_the_end" in failed and "released_where_it_said" in failed


def test_a_drag_stopped_by_sigterm_holds_only_when_it_says_so_and_gives_up_its_claim():
    """PTD10: the same page-side judgment as an interrupted drag, and the command's own account."""
    said = {**SAID_STOPPED, "outcome": "aborted:cancelled", "stopped_by": "SIGTERM", "claim_kept": None}
    assert probe.judge_stop(_page(DRAGGED), _page(INTERRUPTED), said, 6, 6, ORIGIN)["held"]
    for change, fails in (({"stopped_by": None}, "says_what_stopped_it"), ({"claim_kept": "abc"}, "claim_given_up"),
                          ({"outcome": "aborted:pointer_contended:key_down"}, "exit_says_pressed_then_stopped")):
        verdict = probe.judge_stop(_page(DRAGGED), _page(INTERRUPTED), {**said, **change}, 6, 6, ORIGIN)
        assert [k for k, v in verdict["checks"].items() if not v] == [fails]


def test_a_kept_record_is_judged_again_from_what_it_stored():
    """The stricter judgment is applied to the two live runs already kept, without running anything."""
    record = {"content": [*ORIGIN, 1200.0, 780.0], "page_at_start": _page(START), "runs": {
        "drag": {"exit": 0, "said": SAID, "page": _page(DRAGGED), "held": True},
        "interrupted": {"exit": 6, "said": SAID_STOPPED, "page": _page(INTERRUPTED), "held": True},
        "short": {"exit": 4, "said": {"outcome": "refused", "code": "drag_too_short"}, "page": _page(INTERRUPTED),
                  "held": True}}}
    assert probe.rejudge(record, 6, 4) == {name: {"held": True, "failed": [], "held_when_run": True}
                                           for name in ("drag", "interrupted", "short")}
    record["runs"]["interrupted"]["page"] = _page(INTERRUPTED.replace("r371,345", "r390,345"))
    assert probe.rejudge(record, 6, 4)["interrupted"] == {"held": False, "failed": ["released_where_it_said"],
                                                          "held_when_run": True}


def test_a_refused_short_drag_holds_only_when_the_page_saw_nothing():
    page = _page(DRAGGED)
    said = {"outcome": "refused", "code": "drag_too_short"}
    assert probe.judge_short(page, page, said, 4, 4)["held"]
    assert not probe.judge_short(page, _page(DRAGGED.replace("n1", "n2")), said, 4, 4)["held"]
    assert not probe.judge_short(page, page, {"outcome": "dropped"}, 0, 4)["held"]


def test_a_drag_naming_another_application_holds_only_when_refused_for_what_was_found():
    """PTD16: the run that shows the hit test refusing at a real page."""
    page = _page(DRAGGED)
    said = {"outcome": "refused", "code": "point_covered",
            "reason": "the start point 322,442 is on Google Chrome, not Finder: a press there would not go where it was meant"}
    assert probe.judge_wrong_app(page, page, said, 4, 4, "Finder")["held"]
    for change, code, title, fails in (
            ({"code": "app_busy"}, 4, DRAGGED, "refused_as_covered"), ({}, 0, DRAGGED, "refused_as_covered"),
            ({"reason": "the end point is on Google Chrome, not Finder"}, 4, DRAGGED, "says_what_it_found_and_what_was_named"),
            ({}, 4, DRAGGED.replace("n1", "n2"), "the_page_saw_nothing")):
        verdict = probe.judge_wrong_app(page, _page(title), {**said, **change}, code, 4, "Finder")
        assert [k for k, v in verdict["checks"].items() if not v] == [fails]
