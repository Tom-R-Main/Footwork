"""The filmed page pointer probe reads its own evidence strictly and signals only its own Chrome (FP9).

``analyze`` and the cleanup are exercised on composed runs; nothing here launches a browser or moves the
pointer.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

probe = pytest.importorskip("probe_filmed_page_pointer")

CONTENT = [100.0, 180.0, 1200.0, 800.0]
#: the control rectangle of each step that reaches the page, as the page reports it during that step
RECTS = {("Alpha", "clicked"): [40, 60, 140, 44], ("Beta", "clicked"): [620, 330, 140, 44],
         ("Shy", "unpressed"): [40, 130, 140, 44], ("Dodge", "pressed"): [300, 200, 140, 44],
         ("Note", "clicked"): [620, 130, 140, 30], ("Note", "typed"): [620, 130, 140, 30],
         ("Jump down", "clicked"): [300, 60, 140, 44], ("Gamma", "clicked"): [240, 400, 140, 44]}
#: what the command prints for the two clicks that stop part way (the session's own lines)
SAID = {"unpressed": ("dispatched click [10]: driver says unverifiable (input outcome unknown: "
                      "browser_action_unavailable the pointer moved; the click was then refused: no press or click "
                      "was sent: the ref's node left the fil) in 0.4s"),
        "pressed": ("dispatched click [11]: driver says unverifiable (click_stopped_after_press: the click stopped "
                    "after mousedown and no click event was sent: the ref's node left the filmed point. The press "
                    "was sent; what it did is unverifiable, so observe before acting again.) in 0.4s")}


class Events(list):
    """The page's click handlers in order, with its ``inputs``, its ``moved`` records and its ``loaded``
    record beside them, every press, release and insertion it saw (``pressed``), and the probe's own
    pointer ``samples`` as ``[t, x, y]`` in screen points (None: no record of them was written)."""

    inputs: list
    moved: list
    loaded: dict
    pressed: list
    samples: list | None


_numbers = itertools.count(1)


def _seen(t, event, target, rect=None, point=None):
    """One press, release or insertion as the page logs it: numbered in the order it was made, at
    ``point`` (None for an input) on a control that was at ``rect``."""
    x, y = point or (None, None)
    return {"t": t, "n": next(_numbers), "type": "page_event",
            "detail": {"event": event, "trusted": False, "target": target, "x": x, "y": y, "rect": rect}}


def _screen(label, expect):
    x, y, w, h = RECTS[label, expect]
    return [CONTENT[0] + x + w / 2, CONTENT[1] + y + h / 2]


def _step(steps, label, expect):
    return next(step for step in steps if (step["label"], step["expect"]) == (label, expect))


def _events(handlers, label):
    """The page events on ``label``, in order."""
    return [e for e in handlers.pressed if e["detail"]["target"] == label]


def _gesture(steps, gestures, label, expect):
    return gestures[_step(steps, label, expect)["gestures_after"] - 1]


def _run(tmp_path, change=None, record=None):
    """A composed run in which every step went as predicted, with ``change(steps, handlers, gestures)``
    applied to the tried steps and ``record`` merged into the run record before it is written.
    Returns the output directory."""
    out = tmp_path / "out"
    (out / "session").mkdir(parents=True)
    handlers, gestures = Events(), []
    handlers.inputs, handlers.pressed, handlers.moved, handlers.samples = [], [], [], []
    handlers.loaded = {"dpr": 2, "page_says_at_forged": "Forged", "browser_says_at_forged": "lid2"}
    steps = [{"name": "00-start", "exit": 0, "t_start": 990.0, "t_end": 995.0},
             {"name": "00-park", "exit": 0, "t_start": 996.0, "t_end": 998.0}]
    for i, (label, op, expect) in enumerate(probe.STEPS):
        t0 = 1000.0 + 10 * i
        reaches = expect in probe.EXPECTED_EVENTS
        step = {"name": f"{i + 1:02d}-{op}", "label": label, "op": op, "expect": expect, "t_start": t0,
                "t_end": t0 + 3, "exit": 0 if reaches else 4,
                "stdout": SAID.get(expect, "") if reaches else f"not sent: {expect}: {label!r}: " + (
                    probe.reason(label, expect) or "why it could not be verified")}
        if reaches:
            x, y, w, h = RECTS[label, expect]
            centre = [x + w / 2, y + h / 2]
            detail = {"trusted": False, "rect": [x, y, w, h], "dpr": 2, "pinch": 1,
                      "scroll": [0, 1500 if i == len(probe.STEPS) - 1 else 0],
                      "last_trusted_pointer": {"t": t0 + 1.5, "type": "mousemove", "target": label,
                                               "x": centre[0], "y": centre[1]}}
            handlers.pressed += [_seen(t0 + 2, event, label, [x, y, w, h], None if event == "input" else centre)
                                 for event in probe.EXPECTED_EVENTS[expect]]
            if expect == "clicked":
                handlers.append({"t": t0 + 2, "n": next(_numbers), "type": "click_handler",
                                 "detail": detail | {"button": label}})
            elif expect == "typed":
                handlers.inputs.append({"t": t0 + 2, "n": next(_numbers), "type": "input",
                                        "detail": detail | {"field": label, "value": probe.TYPED}})
            else:
                handlers.moved.append({"t": t0 + 2, "n": next(_numbers), "type": "moved",
                                       "detail": detail | {"control": label, "by": probe.MOVED_BY[label]}})
            # the pointer travels in from the parking spot, arrives 0.4 s before the delivery and stays
            there = [CONTENT[0] + centre[0], CONTENT[1] + centre[1]]
            handlers.samples += [[t0 + 1.0 + 0.005 * n, 620.0 + n, 380.0] for n in range(100)]
            handlers.samples += [[round(t0 + 1.6 + 0.005 * n, 4), *there] for n in range(240)]
            gestures.append({"kind": "approach", "label": label, "outcome": "arrived",
                             "posted_samples": [{"x": 1, "y": 1}],
                             "final_location": [CONTENT[0] + centre[0], CONTENT[1] + centre[1]]})
        step["gestures_after"] = len(gestures)
        steps.append(step)
    if change is not None:
        change([step for step in steps if step.get("expect")], handlers, gestures)
    run = {"gestures_at_start": 0, "steps": steps, "chrome_closed": True,
           "chrome_launch": {"pid": 4321, "incarnation": 5.5}} | (record or {})
    if "setup" in run:
        index, code = run.pop("setup")
        steps[index]["exit"] = code
    (out / "run.json").write_text(json.dumps(run))
    (out / "session/session.json").write_text(json.dumps({"filmed": {"content": CONTENT}}))
    page = [{"t": 999.0, "type": "loaded", "detail": handlers.loaded}, *handlers, *handlers.inputs,
            *handlers.moved, *handlers.pressed]
    (out / "page-events.jsonl").write_text("".join(json.dumps(event) + "\n" for event in page))
    if handlers.samples is not None:
        (out / "pointer-samples.jsonl").write_text("".join(json.dumps(row) + "\n" for row in handlers.samples))
    (out / "session/pointer-gestures.jsonl").write_text("".join(json.dumps(g) + "\n" for g in gestures))
    return out


def _of(verdict, label, expect):
    return next(v for v in verdict["steps"] if (v["label"], v["expect"]) == (label, expect))


def test_a_run_that_went_as_predicted_holds(tmp_path):
    verdict = probe.analyze(_run(tmp_path))
    assert verdict["held"] is True and verdict["scale_factor_tested"] is True, verdict
    assert [v["held"] for v in verdict["steps"]] == [True] * len(probe.STEPS) and len(probe.STEPS) == 18
    assert verdict["page_forges_its_hit_test"] is True
    typed = _of(verdict, "Note", "typed")
    assert (typed["value"], typed["inputs"], typed["sequence"]) == (probe.TYPED, 1, ["input"])
    # FP37: every event of every step that reached the page, in order, each with about a hundred of the
    # probe's own samples around it, all on the control, none further apart than the sampling interval
    reaching = [v for v in verdict["steps"] if v["expect"] in probe.EXPECTED_EVENTS]
    assert [v["sequence"] for v in reaching if v["expect"] == "clicked"] == [
        ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]] * 5
    assert all(v["pointer_on_control_at_delivery"] and v["samples_off_control"] == 0 for v in reaching)
    assert {v["samples_around_delivery"] for v in reaching} <= {100, 101}
    assert all(v["largest_sample_gap_s"] <= 0.0051 for v in reaching)
    shy, dodge = _of(verdict, "Shy", "unpressed"), _of(verdict, "Dodge", "pressed")
    assert (shy["sequence"], shy["moves"], shy["handlers"], shy["moved"]["held"]) == ([], 1, 0, True)
    assert (dodge["sequence"], dodge["moves"], dodge["handlers"]) == (["pointerdown", "mousedown"], 1, 0)
    assert [v["page_events"] for v in verdict["steps"] if v["expect"] not in probe.EXPECTED_EVENTS] == [0] * 10


def test_the_fixture_reports_every_press_release_and_insertion_and_the_probe_samples_the_pointer_itself():
    """FP28 and FP37: the records the sixth and seventh reviews found missing."""
    logged = probe.FIXTURE.split("post('page_event'")[0].rsplit("for (const type of", 1)[1]
    assert [event for event in ("pointerdown", "mousedown", "pointerup", "mouseup", "click", "beforeinput", "input")
            if f"'{event}'" in logged] == ["pointerdown", "mousedown", "pointerup", "mouseup", "click", "beforeinput",
                                           "input"]
    assert "window.addEventListener(type, (e) => post('page_event'" in probe.FIXTURE
    # each with the control's rectangle at that moment, numbered in the order the page made them
    assert "rect: control(e.target) ? box(control(e.target)) : null" in probe.FIXTURE and "n: ++seq" in probe.FIXTURE
    assert (probe.DELIVERY_WINDOW_S, probe.MIN_SAMPLES, probe.MAX_GAP_S, probe.SAMPLE_EVERY_S) == (0.25, 20, 0.05, 0.005)


def test_the_page_events_are_read_in_the_order_the_page_made_them(tmp_path):
    """The posts of one click's events can arrive in any order and carry the same time."""
    def arrived_backwards(steps, handlers, gestures):
        handlers.pressed.reverse()

    assert probe.analyze(_run(tmp_path, arrived_backwards))["held"] is True


@pytest.mark.parametrize(("label", "expect", "code"), [("Shy", "unpressed", 1), ("Dodge", "pressed", 4)])
def test_the_exit_code_of_a_click_that_stopped_part_way_is_recorded_and_not_judged(tmp_path, label, expect, code):
    """FP37, alternative (r)."""
    def exited(steps, handlers, gestures):
        _step(steps, label, expect)["exit"] = code

    verdict = probe.analyze(_run(tmp_path, exited))
    assert verdict["held"] is True and _of(verdict, label, expect)["exit"] == code


@pytest.mark.parametrize(("before", "holds"), [(0.26, True), (0.24, False), (-0.24, False), (-0.26, True)])
def test_the_pointer_is_judged_only_in_the_window_around_the_delivery(tmp_path, before, holds):
    def one_sample_elsewhere(steps, handlers, gestures):
        handlers.samples.append([steps[0]["t_start"] + 2 - before, 5.0, 5.0])

    verdict = probe.analyze(_run(tmp_path, one_sample_elsewhere))
    assert verdict["steps"][0]["held"] is holds and verdict["held"] is holds, verdict["steps"][0]


def _move_samples(handlers, step, to, *, after=1.55):
    """Put the probe's samples of ``step`` from ``after`` seconds into it at screen point ``to``."""
    for row in handlers.samples:
        if step["t_start"] + after <= row[0] <= step["t_start"] + 9:
            row[1:] = to


def test_the_steps_are_the_ones_the_prediction_names():
    """FP20, FP29 and FP37: each review's cases are tried, the refusals before their remedies."""
    order = [(label, op, expect) for label, op, expect in probe.STEPS]
    assert order.index(("Beta", "trusted", "route_unfilmed")) < order.index(("Beta", "click", "clicked"))
    assert ("Forged", "click", "target_unlocated") in order and probe.REASONS["Forged"] == probe.REASONS["Covered"]
    note = [step for step in order if step[0] == "Note"]
    assert note == [("Note", "type", "target_unfocused"), ("Note", "click", "clicked"), ("Note", "type", "typed"),
                    ("Note", "type", "replace_unfilmed")]
    # nothing between the click that focuses the field and the type that needs the focus, nor between
    # that type and the one refused because the field then holds text (FP29)
    assert order.index(note[2]) == order.index(note[1]) + 1 and order.index(note[3]) == order.index(note[2]) + 1
    assert probe.reason("Note", "replace_unfilmed") == "types only into an empty field"
    assert probe.reason("Note", "target_unfocused") == "" and probe.reason("Covered", "target_unlocated")
    # FP37: the seventh review's three, in this order straight after Turned
    turned = order.index(("Turned", "click", "target_unlocated"))
    assert order[turned + 1:turned + 4] == [("Hidden", "click", "target_unlocated"), ("Shy", "click", "unpressed"),
                                            ("Dodge", "click", "pressed")]
    assert probe.reason("Hidden", "target_unlocated") == "hides or replaces the pointer"
    assert probe.EXPECTED_EVENTS["pressed"] == ("pointerdown", "mousedown") and probe.EXPECTED_EVENTS["unpressed"] == ()
    assert probe.EXPECTED_EVENTS["clicked"] == ("pointerdown", "mousedown", "pointerup", "mouseup", "click")
    assert probe.EXPECTED_EVENTS["typed"] == ("input",)


def test_the_fixture_has_the_cases_the_prediction_names():
    # the page replaces its hit test for Forged
    assert "Document.prototype.elementFromPoint = function" in probe.FIXTURE
    # FP37: the field no longer moves on focus; Hidden hides the pointer; Shy moves for an untrusted
    # pointerover only; Dodge moves when pressed; and each move is recorded with where the control was
    assert ":focus" not in probe.FIXTURE
    assert 'id="hidden" style="position: absolute; left: 300px; top: 130px; width: 140px; height: 44px; cursor: none"' in probe.FIXTURE
    shy = probe.FIXTURE.split("shy.addEventListener('pointerover', (e) => {")[1].split("});")[0]
    assert shy.strip().startswith("if (e.isTrusted) return;") and "shy.style.top = '430px'" in shy
    assert "post('moved', {control: 'Shy', by: 'pointerover'" in shy and shy.index("box(shy)") < shy.index("style.top")
    dodge = probe.FIXTURE.split("dodge.addEventListener('mousedown', (e) => {")[1].split("});")[0]
    assert "dodge.style.top = '500px'" in dodge and "post('moved', {control: 'Dodge', by: 'mousedown'" in dodge
    assert dodge.index("box(dodge)") < dodge.index("style.top")
    # no control of the page is at the parking spot or shares a place with another
    import re
    boxes = [tuple(int(n) for n in found) for found in re.findall(
        r'id="(?:alpha|beta|covered|jump|forged|hidden|shy|dodge)" style="position: absolute; left: (\d+)px; '
        r'top: (\d+)px; width: (\d+)px; height: (\d+)px', probe.FIXTURE)] + [(620, 130, 140, 30)]
    assert len(boxes) == 9
    for i, (x, y, w, h) in enumerate(boxes):
        assert not probe._inside(probe.EMPTY_SPOT, (x - 20, y - 20, w + 40, h + 40))
        for ox, oy, ow, oh in boxes[i + 1:]:
            assert x + w <= ox or ox + ow <= x or y + h <= oy or oy + oh <= y, ((x, y), (ox, oy))


def test_a_look_names_a_control_of_any_role():
    look = "  [   3] button     'Beta'\n  [  11] textbox    'Note'\n  [  12] button     'Note taker'\n"
    assert (probe._ref(look, "Beta"), probe._ref(look, "Note"), probe._ref(look, "Gone")) == (3, 11, None)


def test_a_pointer_that_was_already_on_its_target_holds(tmp_path):
    def already_there(steps, handlers, gestures):
        handlers[0]["detail"]["last_trusted_pointer"]["t"] = 900.0  # before the step: nothing new was posted
        gestures[0]["posted_samples"] = []

    verdict = probe.analyze(_run(tmp_path, already_there))
    assert verdict["held"] is True and verdict["steps"][0]["already_there"] is True, verdict


def _another_handler_in_a_refused_step(steps, handlers, gestures):
    handlers.append({"t": _step(steps, "Covered", "target_unlocated")["t_start"] + 1, "type": "click_handler",
                     "detail": {"button": "Alpha", "rect": RECTS["Alpha", "clicked"], "dpr": 2}})


def _the_forged_button_clicked(steps, handlers, gestures):
    handlers.append({"t": _step(steps, "Forged", "target_unlocated")["t_start"] + 1, "type": "click_handler",
                     "detail": {"button": "Forged", "rect": [620, 60, 140, 44], "dpr": 2}})


def _a_trusted_click_that_was_sent(steps, handlers, gestures):
    handlers.append({"t": _step(steps, "Beta", "route_unfilmed")["t_start"] + 1, "type": "click_handler",
                     "detail": {"button": "Beta", "rect": RECTS["Beta", "clicked"], "dpr": 2, "trusted": True}})


def _text_inserted_into_the_unfocused_field(steps, handlers, gestures):
    handlers.inputs.append({"t": _step(steps, "Note", "target_unfocused")["t_start"] + 1, "type": "input",
                            "detail": {"field": "Note", "value": probe.TYPED}})


def _another_handler_in_a_clicked_step(steps, handlers, gestures):
    handlers.append({"t": steps[0]["t_start"] + 1, "type": "click_handler",
                     "detail": {"button": "Beta", "rect": RECTS["Beta", "clicked"], "dpr": 2}})


def _a_click_handler_in_the_typed_step(steps, handlers, gestures):
    handlers.append({"t": _step(steps, "Note", "typed")["t_start"] + 1, "type": "click_handler",
                     "detail": {"button": "Note", "rect": RECTS["Note", "typed"], "dpr": 2}})


def _the_field_holding_other_text(steps, handlers, gestures):
    handlers.inputs[0]["detail"]["value"] = probe.TYPED + probe.TYPED


def _two_inputs_in_the_typed_step(steps, handlers, gestures):
    handlers.inputs.append(json.loads(json.dumps(handlers.inputs[0])))


def _typed_with_the_pointer_beside_the_field(steps, handlers, gestures):
    """The text went in with the pointer left 40 px below the field."""
    x, y, w, h = RECTS["Note", "typed"]
    handlers.inputs[0]["detail"]["last_trusted_pointer"].update(x=x + w / 2, y=y + h / 2 + 40)
    _gesture(steps, gestures, "Note", "typed")["final_location"] = [CONTENT[0] + x + w / 2, CONTENT[1] + y + h / 2 + 40]


# FP28: what only the pointer samples and the page's own press log can show


def _a_press_on_the_overlay_in_a_refused_step(steps, handlers, gestures):
    """Sol round 6: a press that reached the lid runs no control's handler."""
    handlers.pressed.append(_seen(_step(steps, "Covered", "target_unlocated")["t_start"] + 1, "pointerdown", "lid"))


def _a_click_on_nothing_in_a_refused_step(steps, handlers, gestures):
    handlers.pressed.append(_seen(_step(steps, "Gamma", "target_unlocated")["t_start"] + 1, "click", None))


def _an_insertion_begun_in_the_unfocused_field(steps, handlers, gestures):
    handlers.pressed.append(_seen(_step(steps, "Note", "target_unfocused")["t_start"] + 1, "beforeinput", "Note"))


def _a_press_elsewhere_in_a_delivered_step(steps, handlers, gestures):
    handlers.pressed.append(_seen(steps[0]["t_start"] + 2, "mousedown", "Beta"))


def _a_delivered_click_the_page_saw_no_press_of(steps, handlers, gestures):
    handlers.pressed[:] = [e for e in handlers.pressed if e["detail"]["target"] != "Alpha"]


def _the_pointer_gone_when_the_click_was_delivered(steps, handlers, gestures):
    """The approach ended on the control and the page's last pointer event was on it; the pointer then
    left before the delivery. Only the probe's own samples show it."""
    _move_samples(handlers, steps[0], [5.0, 5.0], after=1.9)


def _the_pointer_leaving_just_after_the_delivery(steps, handlers, gestures):
    _move_samples(handlers, steps[0], [5.0, 5.0], after=2.1)


def _the_pointer_beside_the_field_when_the_text_went_in(steps, handlers, gestures):
    x, y = _screen("Note", "typed")
    _move_samples(handlers, _step(steps, "Note", "typed"), [x, y + 16.0])  # one px below the field


def _too_few_samples_around_a_delivery(steps, handlers, gestures):
    t = steps[0]["t_start"] + 2
    near = [row for row in handlers.samples if abs(row[0] - t) <= probe.DELIVERY_WINDOW_S]
    for row in near[probe.MIN_SAMPLES - 1:]:
        handlers.samples.remove(row)


# FP37: what only the order of the events, the control's place at each, and unbroken sampling can show


def _a_sampler_that_stalled_across_a_click(steps, handlers, gestures):
    """Sol round 7: a hundred samples on the control and none for 80 ms around the click itself."""
    t = steps[0]["t_start"] + 2
    handlers.samples[:] = [row for row in handlers.samples if abs(row[0] - t) > 0.04]


def _a_sampler_that_stopped_before_the_window_ended(steps, handlers, gestures):
    t = _step(steps, "Gamma", "clicked")["t_start"] + 2
    handlers.samples[:] = [row for row in handlers.samples if not t + 0.19 < row[0] < t + 9]


def _a_sampler_that_started_inside_the_window(steps, handlers, gestures):
    t = steps[0]["t_start"] + 2
    handlers.samples[:] = [row for row in handlers.samples if not t - 9 < row[0] < t - 0.19]


def _a_click_that_came_after_the_pointer_had_gone(steps, handlers, gestures):
    """The press and the release with the pointer on the control; the click 0.6 s later, when it was not."""
    _events(handlers, "Alpha")[-1]["t"] = steps[0]["t_start"] + 2.6
    _move_samples(handlers, steps[0], [5.0, 5.0], after=2.3)


def _a_press_sent_while_the_pointer_was_still_travelling(steps, handlers, gestures):
    """The click and its handler with the pointer on the control; the press 0.8 s earlier, before it arrived."""
    for event in _events(handlers, "Alpha")[:2]:
        event["t"] = steps[0]["t_start"] + 1.2


def _a_click_without_its_pointerup(steps, handlers, gestures):
    handlers.pressed.remove(_events(handlers, "Alpha")[2])


def _a_click_without_its_press(steps, handlers, gestures):
    for event in _events(handlers, "Beta")[:2]:
        handlers.pressed.remove(event)


def _a_click_whose_events_came_in_another_order(steps, handlers, gestures):
    events = _events(handlers, "Alpha")
    events[3]["detail"]["event"], events[4]["detail"]["event"] = "click", "mouseup"


def _a_second_click_event(steps, handlers, gestures):
    x, y, w, h = RECTS["Alpha", "clicked"]
    handlers.pressed.append(_seen(steps[0]["t_start"] + 2, "click", "Alpha", [x, y, w, h], [x + 70, y + 22]))


def _a_release_outside_the_control(steps, handlers, gestures):
    _events(handlers, "Alpha")[3]["detail"].update(x=10, y=10)


def _an_event_without_a_position(steps, handlers, gestures):
    del _events(handlers, "Alpha")[1]["detail"]["x"]


def _a_click_on_a_control_that_had_moved_away(steps, handlers, gestures):
    """The review's case: the click event went to the control where it had moved to, 300 px from the
    pointer, at the old point."""
    x, y, w, h = RECTS["Alpha", "clicked"]
    _events(handlers, "Alpha")[4]["detail"]["rect"] = [x, y + 300, w, h]


def _an_event_without_the_controls_rectangle(steps, handlers, gestures):
    _events(handlers, "Alpha")[0]["detail"]["rect"] = None


def _a_beforeinput_in_the_typed_step(steps, handlers, gestures):
    x, y, w, h = RECTS["Note", "typed"]
    handlers.pressed.append(_seen(_step(steps, "Note", "typed")["t_start"] + 2, "beforeinput", "Note", [x, y, w, h]))


def _a_control_that_moved_in_a_clicked_step(steps, handlers, gestures):
    handlers.moved.append({"t": steps[0]["t_start"] + 2, "type": "moved",
                           "detail": {"control": "Dodge", "by": "mousedown", "trusted": False}})


def _dodge(event):
    def change(steps, handlers, gestures):
        x, y, w, h = RECTS["Dodge", "pressed"]
        handlers.pressed.append(_seen(_step(steps, "Dodge", "pressed")["t_start"] + 2, event, "Dodge",
                                      [x, y + 300, w, h], [x + 70, y + 22]))

    change.__name__ = f"a_{event}_on_dodge"
    return change


def _dodges_click_handler_ran(steps, handlers, gestures):
    handlers.append({"t": _step(steps, "Dodge", "pressed")["t_start"] + 2, "type": "click_handler",
                     "detail": {"button": "Dodge", "rect": RECTS["Dodge", "pressed"], "dpr": 2}})


def _dodge_pressed_once_only(steps, handlers, gestures):
    handlers.pressed.remove(_events(handlers, "Dodge")[1])


def _dodge_pressed_with_the_pointer_elsewhere(steps, handlers, gestures):
    _move_samples(handlers, _step(steps, "Dodge", "pressed"), [5.0, 5.0], after=1.9)


def _a_press_on(label, expect):
    def change(steps, handlers, gestures):
        handlers.pressed.append(_seen(_step(steps, label, expect)["t_start"] + 2, "pointerdown", label,
                                      [40, 130, 140, 44], [110, 152]))

    change.__name__ = f"a_press_on_{label}"
    return change


def _moved(label, **detail):
    def change(steps, handlers, gestures):
        record = next(m for m in handlers.moved if m["detail"]["control"] == label)
        if detail:
            record["detail"].update(detail)
        else:
            handlers.moved.remove(record)

    change.__name__ = f"{label}_moved_{'_'.join(f'{k}_{v}' for k, v in detail.items()) or 'not_at_all'}"
    return change


def _shy_approached_and_missed(steps, handlers, gestures):
    _gesture(steps, gestures, "Shy", "unpressed")["final_location"] = [CONTENT[0] + 400, CONTENT[1] + 400]


def _shy_hovered_with_the_pointer_elsewhere(steps, handlers, gestures):
    _move_samples(handlers, _step(steps, "Shy", "unpressed"), [5.0, 5.0], after=1.9)


def _said(label, expect, text):
    def change(steps, handlers, gestures):
        _step(steps, label, expect)["stdout"] = text

    change.__name__ = f"{label}_said_{len(text)}"
    return change


def _hidden_refused_for_another_reason(steps, handlers, gestures):
    _step(steps, "Hidden", "target_unlocated")["stdout"] = "not sent: target_unlocated: 'Hidden': not wholly in view"


def _no_record_of_the_pointer(steps, handlers, gestures):
    handlers.samples = None


def _an_unreadable_record_of_the_pointer(steps, handlers, gestures):
    handlers.samples.append(["when", "x", "y"])


def _a_page_whose_hit_test_was_not_replaced(steps, handlers, gestures):
    handlers.loaded["page_says_at_forged"] = "lid2"


def _a_page_that_did_not_say_what_its_hit_test_answers(steps, handlers, gestures):
    del handlers.loaded["page_says_at_forged"]


def _a_forged_button_nothing_covers(steps, handlers, gestures):
    handlers.loaded["browser_says_at_forged"] = "Forged"


def _ratio_of_one(steps, handlers, gestures):
    for handler in handlers:
        handler["detail"]["dpr"] = 1


def _a_typed_step_at_a_ratio_of_one(steps, handlers, gestures):
    handlers.inputs[0]["detail"]["dpr"] = 1


def _pointer_event_outside_the_button(steps, handlers, gestures):
    handlers[1]["detail"]["last_trusted_pointer"].update(x=10, y=10)


def _pointer_event_without_coordinates(steps, handlers, gestures):
    del handlers[1]["detail"]["last_trusted_pointer"]["x"]


def _stale_pointer_event_after_a_posted_approach(steps, handlers, gestures):
    handlers[0]["detail"]["last_trusted_pointer"]["t"] = 900.0


def _pointer_event_on_another_button(steps, handlers, gestures):
    handlers[0]["detail"]["last_trusted_pointer"]["target"] = "Beta"


def _gesture_ending_off_the_button(steps, handlers, gestures):
    gestures[0]["final_location"] = [CONTENT[0] + 400, CONTENT[1] + 400]


def _a_gesture_in(label, expect):
    def change(steps, handlers, gestures):
        refused = _step(steps, label, expect)
        gestures.insert(refused["gestures_after"],
                        {"kind": "approach", "label": label, "outcome": "arrived", "final_location": [1, 1]})
        for step in steps[steps.index(refused):]:
            step["gestures_after"] += 1

    change.__name__ = f"a_gesture_in_{label}_{expect}"
    return change


def _a_refusal_without_its_code(steps, handlers, gestures):
    _step(steps, "Covered", "target_unlocated")["stdout"] = "not sent"


def _a_trusted_click_refused_for_another_reason(steps, handlers, gestures):
    _step(steps, "Beta", "route_unfilmed")["stdout"] = "not sent: target_unlocated: 'Beta': not wholly in view"


def _a_replacement_that_was_sent(steps, handlers, gestures):
    again = _step(steps, "Note", "replace_unfilmed")
    handlers.inputs.append({"t": again["t_start"] + 1, "type": "input",
                            "detail": {"field": "Note", "value": probe.TYPED + probe.TYPED}})


def _a_replacement_refused_without_its_reason(steps, handlers, gestures):
    _step(steps, "Note", "replace_unfilmed")["stdout"] = "not sent: replace_unfilmed: 'Note'"


def _a_replacement_refused_as_unfocused(steps, handlers, gestures):
    _step(steps, "Note", "replace_unfilmed")["stdout"] = "not sent: target_unfocused: 'Note': it does not have focus"


def _an_unfocused_field_refused_for_another_reason(steps, handlers, gestures):
    _step(steps, "Note", "target_unfocused")["stdout"] = "not sent: target_unlocated: 'Note': not wholly in view"


def _a_pinched_page(steps, handlers, gestures):
    handlers[1]["detail"]["pinch"] = 1.25


def _a_step_without_a_pinch_scale(steps, handlers, gestures):
    del handlers[0]["detail"]["pinch"]


def _a_refusal_for_another_reason(steps, handlers, gestures):
    clipped = _step(steps, "Clipped", "target_unlocated")
    clipped["stdout"] = "not sent: target_unlocated: 'Clipped': another element is at its centre"


def _forged_refused_for_another_reason(steps, handlers, gestures):
    forged = _step(steps, "Forged", "target_unlocated")
    forged["stdout"] = "not sent: target_unlocated: 'Forged': the driver could not locate it (world_unavailable)"


def _a_step_that_could_not_be_tried(steps, handlers, gestures):
    turned = _step(steps, "Turned", "target_unlocated")
    turned.pop("expect")
    turned["skipped"] = "not on the observation"


def _a_typed_step_that_was_refused(steps, handlers, gestures):
    typed = _step(steps, "Note", "typed")
    typed.update(exit=4, stdout="not sent: target_unfocused: 'Note': the page does not have the keyboard")
    handlers.inputs.clear()
    handlers.pressed[:] = [e for e in handlers.pressed if e["detail"]["event"] != "input"]
    del gestures[typed["gestures_after"] - 1]
    for step in steps[steps.index(typed):]:
        step["gestures_after"] -= 1


def _gamma_clicked_without_scrolling(steps, handlers, gestures):
    handlers[-1]["detail"]["scroll"] = [0, 0]


@pytest.mark.parametrize("change", [
    _another_handler_in_a_refused_step, _another_handler_in_a_clicked_step, _ratio_of_one,
    _pointer_event_outside_the_button, _pointer_event_without_coordinates,
    _stale_pointer_event_after_a_posted_approach, _pointer_event_on_another_button,
    _gesture_ending_off_the_button, _a_gesture_in("Covered", "target_unlocated"), _a_refusal_without_its_code,
    _a_refusal_for_another_reason, _a_step_that_could_not_be_tried, _gamma_clicked_without_scrolling,
    _a_pinched_page, _a_step_without_a_pinch_scale,
    # FP20: the fifth review's three cases
    _the_forged_button_clicked, _a_gesture_in("Forged", "target_unlocated"), _forged_refused_for_another_reason,
    _a_page_whose_hit_test_was_not_replaced, _a_page_that_did_not_say_what_its_hit_test_answers,
    _a_forged_button_nothing_covers,
    _a_trusted_click_that_was_sent, _a_gesture_in("Beta", "route_unfilmed"),
    _a_trusted_click_refused_for_another_reason,
    _text_inserted_into_the_unfocused_field, _a_gesture_in("Note", "target_unfocused"),
    _an_unfocused_field_refused_for_another_reason,
    _a_click_handler_in_the_typed_step, _the_field_holding_other_text, _two_inputs_in_the_typed_step,
    _typed_with_the_pointer_beside_the_field, _a_typed_step_at_a_ratio_of_one, _a_typed_step_that_was_refused,
    # FP28: the sixth review's two gaps in the verdict
    _a_press_on_the_overlay_in_a_refused_step, _a_click_on_nothing_in_a_refused_step,
    _an_insertion_begun_in_the_unfocused_field, _a_press_elsewhere_in_a_delivered_step,
    _a_delivered_click_the_page_saw_no_press_of, _the_pointer_gone_when_the_click_was_delivered,
    _the_pointer_leaving_just_after_the_delivery, _the_pointer_beside_the_field_when_the_text_went_in,
    _too_few_samples_around_a_delivery, _no_record_of_the_pointer, _an_unreadable_record_of_the_pointer,
    # FP29: the replacement
    _a_replacement_that_was_sent, _a_gesture_in("Note", "replace_unfilmed"),
    _a_replacement_refused_without_its_reason, _a_replacement_refused_as_unfocused,
    # FP37: the seventh review's gaps in the verdict, and its three cases
    _a_sampler_that_stalled_across_a_click, _a_sampler_that_stopped_before_the_window_ended,
    _a_sampler_that_started_inside_the_window, _a_click_that_came_after_the_pointer_had_gone,
    _a_press_sent_while_the_pointer_was_still_travelling, _a_click_without_its_pointerup, _a_click_without_its_press, _a_click_whose_events_came_in_another_order,
    _a_second_click_event, _a_release_outside_the_control, _an_event_without_a_position,
    _a_click_on_a_control_that_had_moved_away, _an_event_without_the_controls_rectangle,
    _a_beforeinput_in_the_typed_step, _a_control_that_moved_in_a_clicked_step,
    _dodge("pointerup"), _dodge("mouseup"), _dodge("click"), _dodges_click_handler_ran, _dodge_pressed_once_only,
    _dodge_pressed_with_the_pointer_elsewhere, _moved("Dodge"), _moved("Dodge", by="pointerover"),
    _moved("Dodge", trusted=True), _a_gesture_in("Dodge", "pressed"),
    _said("Dodge", "pressed", SAID["pressed"].replace("after mousedown", "after pointerup")),
    _said("Dodge", "pressed", SAID["pressed"].replace("no click event was sent", "the click was sent")),
    _said("Dodge", "pressed", ""),
    _a_press_on("Shy", "unpressed"), _moved("Shy"), _moved("Shy", trusted=True), _moved("Shy", by="mousedown"),
    _shy_approached_and_missed, _shy_hovered_with_the_pointer_elsewhere, _a_gesture_in("Shy", "unpressed"),
    _said("Shy", "unpressed", SAID["unpressed"].replace("no press or click was sent", "")),
    _a_press_on("Hidden", "target_unlocated"), _a_gesture_in("Hidden", "target_unlocated"),
    _hidden_refused_for_another_reason,
])
def test_a_run_that_departs_from_the_prediction_does_not_hold(tmp_path, change):
    verdict = probe.analyze(_run(tmp_path, change))
    assert verdict["held"] is False, verdict


@pytest.mark.parametrize(("change", "step", "why"), [
    (_a_sampler_that_stalled_across_a_click, ("Alpha", "clicked"), "pointer_on_control_at_delivery"),
    (_a_sampler_that_stopped_before_the_window_ended, ("Gamma", "clicked"), "pointer_on_control_at_delivery"),
    (_a_sampler_that_started_inside_the_window, ("Alpha", "clicked"), "pointer_on_control_at_delivery"),
    (_a_click_that_came_after_the_pointer_had_gone, ("Alpha", "clicked"), "pointer_on_control_at_delivery"),
    (_a_press_sent_while_the_pointer_was_still_travelling, ("Alpha", "clicked"), "pointer_on_control_at_delivery"),
    (_dodge_pressed_with_the_pointer_elsewhere, ("Dodge", "pressed"), "pointer_on_control_at_delivery"),
    (_shy_hovered_with_the_pointer_elsewhere, ("Shy", "unpressed"), "pointer_on_control_at_delivery"),
    (_a_click_without_its_pointerup, ("Alpha", "clicked"), "in_order"),
    (_a_click_whose_events_came_in_another_order, ("Alpha", "clicked"), "in_order"),
    (_a_second_click_event, ("Alpha", "clicked"), "in_order"),
    (_a_beforeinput_in_the_typed_step, ("Note", "typed"), "in_order"),
    # a release or a click on Dodge went to it where it had moved to, away from the pointer
    (_dodge("pointerup"), ("Dodge", "pressed"), "in_order pointer_on_control_at_delivery"),
    (_dodge("click"), ("Dodge", "pressed"), "in_order pointer_on_control_at_delivery"),
    (_dodge_pressed_once_only, ("Dodge", "pressed"), "in_order"),
    (_a_press_on("Shy", "unpressed"), ("Shy", "unpressed"), "in_order"),
    (_said("Shy", "unpressed", SAID["unpressed"].replace("no press or click was sent", "")), ("Shy", "unpressed"), "said"),
    (_said("Dodge", "pressed", SAID["pressed"].replace("after mousedown", "after pointerup")), ("Dodge", "pressed"), "said"),
])
def test_each_departure_fails_its_own_step_for_its_own_reason(tmp_path, change, step, why):
    """Sol round 7: the verdict could hold without these; each now fails the one step it concerns, on
    the one condition it breaks."""
    verdict = probe.analyze(_run(tmp_path, change))
    assert [(v["label"], v["expect"]) for v in verdict["steps"] if not v["held"]] == [step], verdict
    mine = _of(verdict, *step)
    conditions = {name: mine[name] for name in ("in_order", "said", "pointer_on_control_at_delivery")}
    assert conditions == ({"in_order": True, "said": True, "pointer_on_control_at_delivery": True}
                          | dict.fromkeys(why.split(), False))


def test_a_stalled_sampler_is_caught_by_the_gap_and_by_nothing_else(tmp_path):
    """Sol round 7: every sample on the control and enough of them; only the 80 ms without one around
    the click shows that the probe did not see the pointer at it."""
    alpha = probe.analyze(_run(tmp_path, _a_sampler_that_stalled_across_a_click))["steps"][0]
    assert alpha["samples_off_control"] == 0 and alpha["samples_around_delivery"] >= probe.MIN_SAMPLES
    assert 0.08 <= alpha["largest_sample_gap_s"] <= 0.09 and alpha["held"] is False
    assert all(event["inside"] and event["held"] is False for event in alpha["events"])


def test_a_click_event_on_a_control_that_had_moved_is_judged_where_the_control_then_was(tmp_path):
    """Sol round 7: the old verdict read every event against the rectangle at the press."""
    alpha = probe.analyze(_run(tmp_path, _a_click_on_a_control_that_had_moved_away))["steps"][0]
    assert [event["inside"] for event in alpha["events"]] == [True, True, True, True, False]
    assert [event["held"] for event in alpha["events"]] == [True, True, True, True, False] and alpha["held"] is False


def test_the_run_record_keeps_the_first_and_the_last_words_of_a_long_output(tmp_path, monkeypatch):
    """FP37: the line that says what the driver did comes first and a long observation follows it."""
    out = _run(tmp_path)
    record = json.loads((out / "run.json").read_text())
    dodge = next(step for step in record["steps"] if step.get("label") == "Dodge")
    dodge["stdout"] = SAID["pressed"] + "\n" + "  [  1] button 'Alpha'\n" * 300 + "the last line"
    monkeypatch.setattr(probe, "_retire_holder", lambda record, session: None)
    monkeypatch.setattr(probe, "_close_owned_chrome", lambda record, launch: record.update(chrome_closed=True))
    monkeypatch.setattr(probe, "_restore_front", lambda record: None)
    helper = type("Helper", (), {"join": lambda self, timeout=None: None, "shutdown": lambda self: None})()
    verdict = probe._finish(record, out, out / "session", "", probe.threading.Event(), helper, helper)
    kept = next(step for step in json.loads((out / "run.json").read_text())["steps"] if step.get("label") == "Dodge")
    assert kept["stdout"].startswith(SAID["pressed"]) and kept["stdout"].endswith("the last line")
    assert len(kept["stdout"]) < 2200 and verdict["held"] is True


def _a_clicked_step_without_a_ratio(steps, handlers, gestures):
    del handlers[1]["detail"]["dpr"]


def test_a_clicked_step_that_reported_no_device_pixel_ratio_does_not_hold(tmp_path):
    verdict = probe.analyze(_run(tmp_path, _a_clicked_step_without_a_ratio))
    assert verdict["held"] is False and verdict["scale_factor_tested"] is False, verdict


@pytest.mark.parametrize("record", [
    {"chrome_closed": False},
    {"chrome_closed": None},
    {"chrome_launch": None},
    {"cleanup_errors": ["holder: HolderUnavailable: the holder did not exit"]},
    {"cleanup_errors": ["front: RuntimeError: pid 501 was frontmost at the start and pid 4321 is at the end"]},
    {"setup": (0, 2)},
    {"setup": (1, 4)},
])
def test_a_run_whose_setup_or_cleanup_departs_from_the_prediction_does_not_hold(tmp_path, record):
    """FP11 predicts the start and the park succeed and the run's own Chrome is closed; good steps do
    not make the run hold without them."""
    verdict = probe.analyze(_run(tmp_path, record=record))
    assert verdict["held"] is False and all(v["held"] for v in verdict["steps"]), verdict


def test_a_missing_directory_does_not_hold(tmp_path):
    assert probe.analyze(tmp_path / "absent")["held"] is False


# ---- cleanup


def test_a_cleanup_step_that_raises_does_not_skip_the_others(tmp_path, monkeypatch):
    """Sol round 4: retiring the holder raises when it survives; Chrome must still be closed, the
    front application restored, and the run's records written, with the run not holding."""
    out = _run(tmp_path)
    record = json.loads((out / "run.json").read_text())
    did: list = []

    def retire(record, session):
        did.append("holder")
        raise RuntimeError("the holder did not exit")

    def close(record, launch):
        did.append("chrome")
        record["chrome_closed"] = True

    monkeypatch.setattr(probe, "_retire_holder", retire)
    monkeypatch.setattr(probe, "_close_owned_chrome", close)
    monkeypatch.setattr(probe, "_restore_front", lambda record: did.append("front"))
    stop = probe.threading.Event()
    helper = type("Helper", (), {"join": lambda self, timeout=None: did.append("sampler"),
                                 "shutdown": lambda self: did.append("server")})()
    verdict = probe._finish(record, out, out / "session", "", stop, helper, helper)
    assert did == ["holder", "chrome", "front", "sampler", "server"] and stop.is_set()
    written = json.loads((out / "run.json").read_text())
    assert written["cleanup_errors"] == ["holder: RuntimeError: the holder did not exit"]
    assert verdict["held"] is False and all(v["held"] for v in verdict["steps"])
    assert json.loads((out / "verdict.json").read_text())["held"] is False


def _front(monkeypatch, record, fronts):
    """Run the restoration with the frontmost pid read as ``fronts`` in turn (the last one repeating);
    return the pids it activated."""
    activated: list = []
    reads = list(fronts)
    monkeypatch.setattr(probe, "_front_pid", lambda: reads.pop(0) if len(reads) > 1 else reads[0])
    monkeypatch.setattr(probe, "_activate_pid", activated.append)
    monkeypatch.setattr(probe.time, "sleep", lambda seconds: None)
    probe._restore_front(record)
    return activated


def test_the_front_application_is_brought_back_and_left_alone_when_it_never_left(monkeypatch):
    record = {"front_pid_at_start": 501}
    assert _front(monkeypatch, record, [4321, 4321, 501]) == [501] and record["front_pid_at_end"] == 501
    assert _front(monkeypatch, {"front_pid_at_start": 501}, [501]) == []


@pytest.mark.parametrize(("record", "fronts", "why"), [
    ({"front_pid_at_start": 501}, [4321], "pid 501 was frontmost at the start and pid 4321 is at the end"),
    ({"front_pid_at_start": 501}, [4321, None], "pid None is at the end"),
    ({}, [4321], "did not record which application was frontmost"),
    ({"front_pid_at_start": None}, [4321], "did not record which application was frontmost"),
])
def test_a_front_application_that_did_not_come_back_is_an_error(monkeypatch, record, fronts, why):
    """Sol round 5: recording the final frontmost application is not requiring that it was restored."""
    with pytest.raises(RuntimeError, match=why):
        _front(monkeypatch, record, fronts)
    assert "front_pid_at_end" in record


def test_a_front_application_that_did_not_come_back_fails_the_run(tmp_path, monkeypatch):
    out = _run(tmp_path)
    record = json.loads((out / "run.json").read_text()) | {"front_pid_at_start": 501}
    monkeypatch.setattr(probe, "_retire_holder", lambda record, session: None)
    monkeypatch.setattr(probe, "_close_owned_chrome", lambda record, launch: record.update(chrome_closed=True))
    monkeypatch.setattr(probe, "_front_pid", lambda: 4321)
    monkeypatch.setattr(probe, "_activate_pid", lambda pid: None)
    monkeypatch.setattr(probe.time, "sleep", lambda seconds: None)
    helper = type("Helper", (), {"join": lambda self, timeout=None: None, "shutdown": lambda self: None})()
    verdict = probe._finish(record, out, out / "session", "", probe.threading.Event(), helper, helper)
    written = json.loads((out / "run.json").read_text())
    assert written["cleanup_errors"] == [
        "front: RuntimeError: pid 501 was frontmost at the start and pid 4321 is at the end"]
    assert written["front_pid_at_end"] == 4321
    assert verdict["held"] is False and verdict["own_chrome_closed"] is False
    assert all(v["held"] for v in verdict["steps"])


def _session(tmp_path, launch):
    session = tmp_path / "session"
    session.mkdir()
    if launch is not None:
        (session / "session.json").write_text(json.dumps({"browser_launch": launch}))
    return session


def test_the_launched_chrome_is_the_one_the_session_recorded_launching(tmp_path):
    session = _session(tmp_path, {"pid": 4321, "incarnation": 1794531565.474952, "new_process": True})
    assert probe._launched_chrome(session, "") == {"pid": 4321, "incarnation": 1794531565.474952}


@pytest.mark.parametrize("launch", [
    {"pid": 4321, "incarnation": 1794531565.474952, "new_process": False},
    {"pid": 4321, "incarnation": 1794531565.474952},
    {"pid": "x", "incarnation": 1.0, "new_process": True},
    {},
])
def test_a_chrome_the_session_found_or_did_not_identify_is_not_this_runs(tmp_path, launch):
    assert probe._launched_chrome(_session(tmp_path, launch), "") is None


def test_a_start_that_failed_after_binding_still_says_what_it_launched(tmp_path):
    session = _session(tmp_path, None)
    said = "footwork's Chrome pid 4321 started 1794531565.474952: launched by this start\nnot starting: x\n"
    assert probe._launched_chrome(session, said) == {"pid": 4321, "incarnation": 1794531565.474952}
    found = "footwork's Chrome pid 4321 started 1794531565.474952: already running\n"
    assert probe._launched_chrome(session, found) is None
    assert probe._launched_chrome(session, "bound nothing") is None


def _cleanup(monkeypatch, *, matching, started, launch):
    """Run the cleanup against a process table of one Chrome ``matching`` (a pid or None) that started
    at ``started``; return the record and the signals sent."""
    import psutil
    from jevdual import browser_driver

    sent: list = []
    alive = {"pid": matching}

    def kill(pid, sig):
        sent.append((pid, sig))
        alive["pid"] = None

    class Process:
        def __init__(self, pid):
            if pid != alive["pid"]:
                raise psutil.NoSuchProcess(pid)

        def create_time(self):
            return started

    monkeypatch.setattr(browser_driver, "chrome_pid", lambda: alive["pid"])
    monkeypatch.setattr(psutil, "Process", Process)
    monkeypatch.setattr(probe.os, "kill", kill)
    record: dict = {}
    probe._close_owned_chrome(record, launch)
    return record, sent


def test_the_cleanup_signals_the_chrome_this_run_launched(monkeypatch):
    record, sent = _cleanup(monkeypatch, matching=4321, started=5.5, launch={"pid": 4321, "incarnation": 5.5})
    assert sent == [(4321, probe.signal.SIGTERM)] and record["chrome_closed"] is True


@pytest.mark.parametrize(("launch", "why"), [
    (None, "did not record launching it"),
    ({"pid": 999, "incarnation": 5.5}, "not the process the session launched"),
    ({"pid": 4321, "incarnation": 4.0}, "not the process the session launched"),
])
def test_the_cleanup_leaves_a_chrome_it_cannot_prove_is_its_own(monkeypatch, launch, why):
    record, sent = _cleanup(monkeypatch, matching=4321, started=5.5, launch=launch)
    assert sent == [] and record["chrome_closed"] is False and why in record["chrome_not_signalled"]


def test_the_cleanup_has_nothing_to_do_when_no_chrome_matches(monkeypatch):
    record, sent = _cleanup(monkeypatch, matching=None, started=5.5, launch={"pid": 4321, "incarnation": 5.5})
    assert sent == [] and record["chrome_closed"] is True
