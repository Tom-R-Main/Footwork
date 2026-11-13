"""The filmed page pointer probe reads its own evidence strictly and signals only its own Chrome (FP9).

``analyze`` and the cleanup are exercised on composed runs; nothing here launches a browser or moves the
pointer.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

probe = pytest.importorskip("probe_filmed_page_pointer")

CONTENT = [100.0, 180.0, 1200.0, 800.0]
#: each delivered step's control rectangle as the page reports it for that step
RECTS = {("Alpha", "clicked"): [40, 60, 140, 44], ("Beta", "clicked"): [620, 330, 140, 44],
         ("Note", "clicked"): [620, 130, 140, 30],  # where the field was when the press began
         ("Note", "typed"): [620, 170, 140, 30],  # where its focus style then put it
         ("Jump down", "clicked"): [300, 60, 140, 44], ("Gamma", "clicked"): [240, 400, 140, 44]}


class Events(list):
    """The page's click handlers in order, with its ``inputs`` and its ``loaded`` record beside them,
    every press and insertion it saw (``pressed``), and the probe's own pointer ``samples`` as
    ``[t, x, y]`` in screen points (None: no record of them was written)."""

    inputs: list
    loaded: dict
    pressed: list
    samples: list | None


def _seen(t, event, target):
    return {"t": t, "type": "page_event", "detail": {"event": event, "trusted": False, "target": target}}


def _screen(label, expect):
    x, y, w, h = RECTS[label, expect]
    return [CONTENT[0] + x + w / 2, CONTENT[1] + y + h / 2]


def _step(steps, label, expect):
    return next(step for step in steps if (step["label"], step["expect"]) == (label, expect))


def _run(tmp_path, change=None, record=None):
    """A composed run in which every step went as predicted, with ``change(steps, handlers, gestures)``
    applied to the tried steps and ``record`` merged into the run record before it is written.
    Returns the output directory."""
    out = tmp_path / "out"
    (out / "session").mkdir(parents=True)
    handlers, gestures = Events(), []
    handlers.inputs, handlers.pressed, handlers.samples = [], [], []
    handlers.loaded = {"dpr": 2, "page_says_at_forged": "Forged", "browser_says_at_forged": "lid2"}
    steps = [{"name": "00-start", "exit": 0, "t_start": 990.0, "t_end": 995.0},
             {"name": "00-park", "exit": 0, "t_start": 996.0, "t_end": 998.0}]
    for i, (label, op, expect) in enumerate(probe.STEPS):
        t0 = 1000.0 + 10 * i
        delivered = expect in probe.DELIVERED
        step = {"name": f"{i + 1:02d}-{op}", "label": label, "op": op, "expect": expect, "t_start": t0,
                "t_end": t0 + 3, "exit": 0 if delivered else 4,
                "stdout": "" if delivered else f"not sent: {expect}: {label!r}: " + (
                    probe.reason(label, expect) or "why it could not be verified")}
        if delivered:
            x, y, w, h = RECTS[label, expect]
            centre = [x + w / 2, y + h / 2]
            detail = {"trusted": False, "rect": [x, y, w, h], "dpr": 2, "pinch": 1,
                      "scroll": [0, 1500 if i == len(probe.STEPS) - 1 else 0],
                      "last_trusted_pointer": {"t": t0 + 1.5, "type": "mousemove", "target": label,
                                               "x": centre[0], "y": centre[1]}}
            if expect == "clicked":
                handlers.append({"t": t0 + 2, "type": "click_handler", "detail": detail | {"button": label}})
                handlers.pressed += [_seen(t0 + 2, event, label) for event in ("pointerdown", "mousedown", "mouseup", "click")]
            else:
                handlers.inputs.append({"t": t0 + 2, "type": "input",
                                        "detail": detail | {"field": label, "value": probe.TYPED}})
                handlers.pressed.append(_seen(t0 + 2, "input", label))
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
    page = [{"t": 999.0, "type": "loaded", "detail": handlers.loaded}, *handlers, *handlers.inputs, *handlers.pressed]
    (out / "page-events.jsonl").write_text("".join(json.dumps(event) + "\n" for event in page))
    if handlers.samples is not None:
        (out / "pointer-samples.jsonl").write_text("".join(json.dumps(row) + "\n" for row in handlers.samples))
    (out / "session/pointer-gestures.jsonl").write_text("".join(json.dumps(g) + "\n" for g in gestures))
    return out


def test_a_run_that_went_as_predicted_holds(tmp_path):
    verdict = probe.analyze(_run(tmp_path))
    assert verdict["held"] is True and verdict["scale_factor_tested"] is True, verdict
    assert [v["held"] for v in verdict["steps"]] == [True] * len(probe.STEPS)
    assert verdict["page_forges_its_hit_test"] is True
    typed = verdict["steps"][10]
    assert (typed["label"], typed["expect"], typed["value"], typed["inputs"]) == ("Note", "typed", probe.TYPED, 1)
    assert verdict["note_moved_when_focused"] is True
    # FP28: about a hundred of the probe's own samples around each delivery, all on the control
    delivered = [v for v in verdict["steps"] if v["expect"] in probe.DELIVERED]
    assert all(v["pointer_on_control_at_delivery"] and v["samples_off_control"] == 0 for v in delivered)
    assert {v["samples_around_delivery"] for v in delivered} <= {100, 101} and typed["page_events"] == 1
    assert [v["page_events"] for v in verdict["steps"] if v["expect"] not in probe.DELIVERED] == [0] * 9


def test_the_fixture_reports_every_press_and_insertion_and_the_probe_samples_the_pointer_itself():
    """FP28: the two records the sixth review found missing."""
    for event in ("pointerdown", "mousedown", "mouseup", "click", "beforeinput", "input"):
        assert f"'{event}'" in probe.FIXTURE.split("post('page_event'")[0].rsplit("for (const type of", 1)[1]
    assert "window.addEventListener(type, (e) => post('page_event'" in probe.FIXTURE
    assert (probe.DELIVERY_WINDOW_S, probe.MIN_SAMPLES, probe.SAMPLE_EVERY_S) == (0.25, 20, 0.005)


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


def test_a_field_that_did_not_move_on_focus_still_holds_and_is_recorded(tmp_path):
    """FP21: in a document without focus the field's focus style does not apply; the text still goes in
    with the pointer on the field, and the run says the move was not exercised."""
    def unmoved(steps, handlers, gestures):
        x, y, w, h = RECTS["Note", "clicked"]
        handlers.inputs[0]["detail"]["rect"] = [x, y, w, h]
        handlers.inputs[0]["detail"]["last_trusted_pointer"].update(x=x + w / 2, y=y + h / 2)
        gestures[3]["final_location"] = [CONTENT[0] + x + w / 2, CONTENT[1] + y + h / 2]
        _move_samples(handlers, _step(steps, "Note", "typed"), _screen("Note", "clicked"))

    verdict = probe.analyze(_run(tmp_path, unmoved))
    assert verdict["held"] is True and verdict["note_moved_when_focused"] is False, verdict


def test_the_steps_are_the_ones_the_prediction_names():
    """FP20: the three cases of the fifth review are each tried, the refusals before their remedies."""
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
    # the fixture's page replaces its hit test for Forged and moves the field when it gains focus
    assert "Document.prototype.elementFromPoint = function" in probe.FIXTURE
    assert "#note:focus { top: 170px }" in probe.FIXTURE


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


def _typed_with_the_pointer_where_the_field_was(steps, handlers, gestures):
    """The review's case: the field moved on focus and the text went in with the pointer left behind."""
    x, y, w, h = RECTS["Note", "clicked"]
    handlers.inputs[0]["detail"]["last_trusted_pointer"].update(x=x + w / 2, y=y + h / 2)
    gestures[3]["final_location"] = [CONTENT[0] + x + w / 2, CONTENT[1] + y + h / 2]


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
    del gestures[3]
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
    _typed_with_the_pointer_where_the_field_was, _a_typed_step_at_a_ratio_of_one, _a_typed_step_that_was_refused,
    # FP28: the sixth review's two gaps in the verdict
    _a_press_on_the_overlay_in_a_refused_step, _a_click_on_nothing_in_a_refused_step,
    _an_insertion_begun_in_the_unfocused_field, _a_press_elsewhere_in_a_delivered_step,
    _a_delivered_click_the_page_saw_no_press_of, _the_pointer_gone_when_the_click_was_delivered,
    _the_pointer_leaving_just_after_the_delivery, _the_pointer_beside_the_field_when_the_text_went_in,
    _too_few_samples_around_a_delivery, _no_record_of_the_pointer, _an_unreadable_record_of_the_pointer,
    # FP29: the replacement
    _a_replacement_that_was_sent, _a_gesture_in("Note", "replace_unfilmed"),
    _a_replacement_refused_without_its_reason, _a_replacement_refused_as_unfocused,
])
def test_a_run_that_departs_from_the_prediction_does_not_hold(tmp_path, change):
    verdict = probe.analyze(_run(tmp_path, change))
    assert verdict["held"] is False, verdict


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
