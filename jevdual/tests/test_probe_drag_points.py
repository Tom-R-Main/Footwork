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


def test_an_interrupted_drag_holds_only_when_it_let_go_once_and_said_where():
    before = _page(DRAGGED)
    after = _page("PD n2 u2 x0 h22 l0 o0 t0 g12 k2 d300,300 r371,345")
    said = {"outcome": "aborted:pointer_contended:key_down", "pressed": True, "escape_sent": True,
            "released_at": [393.0, 487.0], "end": [542.0, 582.0], "button_up": True}
    assert probe.judge_abort(before, after, said, 6, 6)["held"]
    cancelled = _page("PD n2 u1 x1 h22 l0 o0 t0 g12 k2 d300,300 r520,440")
    assert probe.judge_abort(before, cancelled, said, 6, 6)["held"]  # a release the page saw as a cancel
    for change, fails in (({"escape_sent": False}, "escape_was_sent"), ({"button_up": False}, "button_reads_up"),
                          ({"released_at": [542.0, 582.0]}, "released_short_of_the_end"),
                          ({"outcome": "dropped"}, "exit_says_pressed_then_aborted")):
        verdict = probe.judge_abort(before, after, {**said, **change}, 6, 6)
        assert [k for k, v in verdict["checks"].items() if not v] == [fails]
    held_down = _page("PD n2 u1 x0 h22 l0 o0 t0 g12 k2 d300,300 r520,440")
    assert not probe.judge_abort(before, held_down, said, 6, 6)["checks"]["one_release_or_cancel"]


def test_a_refused_short_drag_holds_only_when_the_page_saw_nothing():
    page = _page(DRAGGED)
    said = {"outcome": "refused", "code": "drag_too_short"}
    assert probe.judge_short(page, page, said, 4, 4)["held"]
    assert not probe.judge_short(page, _page(DRAGGED.replace("n1", "n2")), said, 4, 4)["held"]
    assert not probe.judge_short(page, page, {"outcome": "dropped"}, 0, 4)["held"]
