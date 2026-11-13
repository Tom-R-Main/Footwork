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
RECTS = {"Alpha": [40, 60, 140, 44], "Beta": [620, 330, 140, 44], "Jump down": [300, 60, 140, 44],
         "Gamma": [240, 400, 140, 44]}


def _run(tmp_path, change=None, record=None):
    """A composed run in which every step went as predicted, with ``change(steps, handlers, gestures)``
    applied to the click steps and ``record`` merged into the run record before it is written.
    Returns the output directory."""
    out = tmp_path / "out"
    (out / "session").mkdir(parents=True)
    handlers, gestures = [], []
    steps = [{"name": "00-start", "exit": 0, "t_start": 990.0, "t_end": 995.0},
             {"name": "00-park", "exit": 0, "t_start": 996.0, "t_end": 998.0}]
    for i, (label, expect) in enumerate(probe.STEPS):
        t0 = 1000.0 + 10 * i
        step = {"name": f"{i + 1:02d}-click", "label": label, "expect": expect, "t_start": t0, "t_end": t0 + 3,
                "exit": 0 if expect == "clicked" else 4,
                "stdout": "" if expect == "clicked" else (
                    "not sent: target_unlocated: 'x': " + (probe.REASONS.get(label) or "not wholly in view"))}
        if expect == "clicked":
            x, y, w, h = RECTS[label]
            centre = [x + w / 2, y + h / 2]
            handlers.append({"t": t0 + 2, "type": "click_handler", "detail": {
                "button": label, "trusted": False, "rect": [x, y, w, h], "dpr": 2,
                "scroll": [0, 1500 if i == len(probe.STEPS) - 1 else 0], "pinch": 1,
                "last_trusted_pointer": {"t": t0 + 1.5, "type": "mousemove", "target": label,
                                         "x": centre[0], "y": centre[1]}}})
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
    (out / "page-events.jsonl").write_text("".join(json.dumps(h) + "\n" for h in handlers))
    (out / "session/pointer-gestures.jsonl").write_text("".join(json.dumps(g) + "\n" for g in gestures))
    return out


def test_a_run_that_went_as_predicted_holds(tmp_path):
    verdict = probe.analyze(_run(tmp_path))
    assert verdict["held"] is True and verdict["scale_factor_tested"] is True, verdict
    assert [v["held"] for v in verdict["steps"]] == [True] * len(probe.STEPS)


def test_a_pointer_that_was_already_on_its_target_holds(tmp_path):
    def already_there(steps, handlers, gestures):
        handlers[0]["detail"]["last_trusted_pointer"]["t"] = 900.0  # before the step: nothing new was posted
        gestures[0]["posted_samples"] = []

    verdict = probe.analyze(_run(tmp_path, already_there))
    assert verdict["held"] is True and verdict["steps"][0]["already_there"] is True, verdict


def _another_handler_in_a_refused_step(steps, handlers, gestures):
    handlers.append({"t": steps[2]["t_start"] + 1, "type": "click_handler",
                     "detail": {"button": "Alpha", "rect": RECTS["Alpha"], "dpr": 2}})


def _another_handler_in_a_clicked_step(steps, handlers, gestures):
    handlers.append({"t": steps[0]["t_start"] + 1, "type": "click_handler",
                     "detail": {"button": "Beta", "rect": RECTS["Beta"], "dpr": 2}})


def _ratio_of_one(steps, handlers, gestures):
    for handler in handlers:
        handler["detail"]["dpr"] = 1


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


def _a_gesture_in_a_refused_step(steps, handlers, gestures):
    gestures.insert(2, {"kind": "approach", "label": "Covered", "outcome": "arrived", "final_location": [1, 1]})
    for step in steps[2:]:
        step["gestures_after"] += 1


def _a_refusal_without_its_code(steps, handlers, gestures):
    steps[3]["stdout"] = "not sent"


def _a_pinched_page(steps, handlers, gestures):
    handlers[1]["detail"]["pinch"] = 1.25


def _a_step_without_a_pinch_scale(steps, handlers, gestures):
    del handlers[0]["detail"]["pinch"]


def _a_refusal_for_another_reason(steps, handlers, gestures):
    clipped = next(step for step in steps if step["label"] == "Clipped")
    clipped["stdout"] = "not sent: target_unlocated: 'Clipped': another element is at its centre"


def _a_step_that_could_not_be_tried(steps, handlers, gestures):
    turned = next(step for step in steps if step["label"] == "Turned")
    turned.pop("expect")
    turned["skipped"] = "not on the observation"


def _gamma_clicked_without_scrolling(steps, handlers, gestures):
    handlers[-1]["detail"]["scroll"] = [0, 0]


@pytest.mark.parametrize("change", [
    _another_handler_in_a_refused_step, _another_handler_in_a_clicked_step, _ratio_of_one,
    _pointer_event_outside_the_button, _pointer_event_without_coordinates,
    _stale_pointer_event_after_a_posted_approach, _pointer_event_on_another_button,
    _gesture_ending_off_the_button, _a_gesture_in_a_refused_step, _a_refusal_without_its_code,
    _a_refusal_for_another_reason, _a_step_that_could_not_be_tried, _gamma_clicked_without_scrolling,
    _a_pinched_page, _a_step_without_a_pinch_scale,
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
    {"setup": (0, 2)},
    {"setup": (1, 4)},
])
def test_a_run_whose_setup_or_cleanup_departs_from_the_prediction_does_not_hold(tmp_path, record):
    """FP11 predicts the start and the park succeed and the run's own Chrome is closed; seven good
    steps do not make the run hold without them."""
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
