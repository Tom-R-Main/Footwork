"""The filmed page pointer probe reads its own evidence strictly and signals only its own Chrome (FP9).

``analyze`` and the cleanup are exercised on composed runs; nothing here launches a browser or moves the
pointer.
"""

from __future__ import annotations

import itertools
import json
import math
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


#: the order records were made in; the page's own numbers (1, 2, ...) are given from it when the run
#: is written
_numbers = itertools.count(1)
#: how long a post takes to reach the probe, and to be answered, in a composed run
UP_S, DOWN_S = 0.002, 0.002


def _seen(t, event, target, rect=None, point=None):
    """One press, release or insertion as the page logs it: numbered in the order it was made, at
    ``point`` (None for an input) on a control that was at ``rect``."""
    x, y = point or (None, None)
    return {"t": t, "n": next(_numbers), "type": "page_event",
            "detail": {"event": event, "trusted": False, "target": target, "x": x, "y": y, "rect": rect}}


DOCUMENT = "mhx1c2-0a9f"  # the name the document under test made for itself


def _as_the_page_posts(records, *, offset, until, fence):
    """``records`` (times in the probe's clock) as the page's log file holds them: a beat twice a second
    until ``until``, the fence the probe asked for made at ``fence``, every record numbered from one in
    the order it was made, stamped with the page's own time (the probe's less ``offset``) and the
    probe's time of receiving it, and the last beat carrying the page's time of each answer."""
    records = [dict(r, n=r.get("n", 10**9)) for r in records]
    beats, t = [], 999.5
    while t <= until:
        if t - 0.5 < fence <= t:
            beats.append({"t": fence, "n": 10**9, "type": "fence", "detail": {"asked_in_answer_to": 0}})
        beats.append({"t": t, "n": 10**9, "type": "beat", "detail": {"acks": []}})
        t += 0.5
    # the page numbers its records in the order it makes them: by time, and at one time the run's own
    # records in the order they were made, then the beat
    rows = sorted([*records, *beats], key=lambda r: (r["t"], r["type"] in ("beat", "fence"), r["n"]))
    for n, row in enumerate(rows, start=1):
        row["n"], row["received"], row["doc"] = n, row["t"] + UP_S, DOCUMENT
        row["t"] -= offset
        last = (row.get("detail") or {}).get("last_trusted_pointer")
        if last:
            row["detail"] = row["detail"] | {"last_trusted_pointer": last | {"t": last["t"] - offset}}
    rows[-1]["detail"]["acks"] = [[row["n"], row["t"] + UP_S + DOWN_S] for row in rows[:-1]]
    return rows


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


#: what a run's cleanup read for itself when everything it began was ended
CLOSED = {"registry": True, "browser": True, "port": True, "holder": True}


def _run(tmp_path, change=None, record=None, *, offset=0.0, page=None):
    """A composed run in which every step went as predicted, with ``change(steps, handlers, gestures)``
    applied to the tried steps and ``record`` merged into the run record before it is written. The
    page's clock runs ``offset`` seconds behind the probe's, and ``page(rows)`` may change the page's
    log as it was received. Returns the output directory."""
    out = tmp_path / "out"
    (out / "session").mkdir(parents=True)
    handlers, gestures = Events(), []
    handlers.inputs, handlers.pressed, handlers.moved, handlers.samples = [], [], [], []
    handlers.loaded = {"dpr": 2, "page_says_at_forged": "Forged", "browser_says_at_forged": "lid2",
                       "clock_step_s": 0.0001}
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
    # the probe asks for the fence once the last step's interval (a second past its end) has closed
    run = {"gestures_at_start": 0, "steps": steps, "chrome_closed": True, "fence_asked": steps[-1]["t_end"] + 1.1,
           "chrome_launch": {"pid": 4321, "incarnation": 5.5}, "closed": dict(CLOSED)} | (record or {})
    if "setup" in run:
        index, code = run.pop("setup")
        steps[index]["exit"] = code
    (out / "run.json").write_text(json.dumps(run))
    (out / "session/session.json").write_text(json.dumps({"filmed": {"content": CONTENT}}))
    made = [{"t": 999.0, "n": 0, "type": "loaded", "detail": handlers.loaded}, *handlers, *handlers.inputs,
            *handlers.moved, *handlers.pressed]
    rows = _as_the_page_posts(made, offset=offset, until=steps[-1]["t_end"] + 2.0, fence=steps[-1]["t_end"] + 1.3)
    if page is not None:
        page(rows)
    (out / "page-events.jsonl").write_text("".join(json.dumps(event) + "\n" for event in rows))
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
    assert "rect: control(e.target) ? box(control(e.target)) : null" in probe.FIXTURE and "const n = ++seq;" in probe.FIXTURE
    assert (probe.DELIVERY_WINDOW_S, probe.MIN_SAMPLES, probe.MAX_GAP_S, probe.SAMPLE_EVERY_S) == (0.25, 20, 0.05, 0.005)


def test_the_whole_log_is_accounted_for_and_the_clocks_are_related(tmp_path):
    """FP46: what a run that went as predicted says of its own log and clocks."""
    verdict = probe.analyze(_run(tmp_path))
    log, clock = verdict["page_log"], verdict["clock"]
    assert log["held"] and log["numbered_without_gaps"] and log["one_load"] and log["fenced_after_the_last_step"]
    assert log["unaccounted"] == [] and log["ambiguous"] == [] and log["step_intervals_apart"] is True
    # the run says through where it is accounted for: the fence, asked for after the last interval closed
    fence = next(row for row in probe._jsonl(tmp_path / "out/page-events.jsonl") if row["type"] == "fence")
    assert log["accounted_through"] == {"record": fence["n"], "asked_at": 1174.1} and fence["received"] > 1174.1
    # every record of something done to the page is placed by its own post: answered 4 ms after it was
    # made by the page's clock, each of whose two readings is taken a grain off, so within 6 ms
    assert "untimed" not in clock and clock["widest_action_record_s"] == 0.006
    assert (probe.PAGE_CLOCK_GRAIN_S, probe.CLOCK_RATE_SLACK) == (0.001, 0.001)
    assert probe._elapsed(0.004) == pytest.approx(0.006006) and probe._elapsed(-0.0005) == pytest.approx(0.002002)
    assert log["missing_after_the_fence"] == [] and clock["page_clock_step_s"] == 0.0001
    assert "clock_step_s: clockStep()" in probe.FIXTURE and probe.PAGE_CLOCK_GRAIN_S == 0.001
    assert clock["held"] and (clock["low_s"], clock["high_s"], clock["width_s"]) == (-0.003, 0.003, 0.006)
    assert abs(clock["offset_s"]) < 1e-6 and clock["answers"] == log["records"] - 1
    assert "post('beat', {acks: acks.splice(0, 60)})" in probe.FIXTURE and "acks.push([n, now()])" in probe.FIXTURE
    assert "if (body === 'fence' && !fenced) { fenced = true; post('fence', {asked_in_answer_to: n}); }" in probe.FIXTURE
    assert (probe.MAX_CLOCK_WIDTH_S, probe.ACTION_RECORDS) == (0.02, ("page_event", "click_handler", "input", "moved"))


@pytest.mark.parametrize("offset", [3.0, -3.0, 0.31])
def test_a_page_clock_that_differs_from_the_probes_is_converted(tmp_path, offset):
    """Sol round 8: the page's time origin and the probe's clock are two clocks. Here they differ by
    more than the window read around each event; the run holds because the page's times are converted,
    and the same log read without the answers that bound the clocks does not."""
    verdict = probe.analyze(_run(tmp_path, offset=offset))
    assert verdict["held"] is True and abs(verdict["clock"]["offset_s"] - offset) < 1e-6, verdict["clock"]

    def unanswered(rows):
        rows[-1]["detail"]["acks"] = []

    blind = probe.analyze(_run(tmp_path / "unanswered", offset=offset, page=unanswered))
    assert blind["held"] is False and blind["clock"]["held"] is False
    assert "do not bound the clocks on both sides" in blind["clock"]["why"]
    # read as it stands, every delivered step fails its samples
    assert not any(v["held"] for v in blind["steps"] if v["expect"] in probe.EXPECTED_EVENTS)


def _slow_answers(rows):
    """Every post took 30 ms to be answered: the clocks are bounded, 32 ms apart and a grain each side."""
    rows[-1]["detail"]["acks"] = [[n, r + 0.028] for n, r in rows[-1]["detail"]["acks"]]


def _a_clock_set_back_during_the_run(rows):
    """Posts received in the second half of the run are stamped 80 ms early."""
    for row in rows[len(rows) // 2:]:
        row["received"] -= 0.08


def _a_record_never_received(rows):
    del rows[len(rows) // 2]


def _a_number_twice(rows):
    """Two events of one click, made at one page time, with one number."""
    first = next(i for i, row in enumerate(rows) if row["type"] == "page_event")
    assert rows[first + 1]["type"] == "page_event" and rows[first + 1]["t"] == rows[first]["t"]
    rows[first + 1]["n"] = rows[first]["n"]


def _a_record_without_a_number(rows):
    """A beat, so that nothing done to the page loses its place in the order."""
    assert rows[1]["type"] == "beat"
    del rows[1]["n"]


def _a_page_loaded_twice(rows):
    """A second record of loading, made last of all."""
    rows.append(dict(rows[0], n=len(rows) + 1, t=rows[-1]["t"] + 0.1, received=rows[-1]["received"] + 0.1))


def _renumbered(rows, kept):
    """``kept`` as a whole log of its own: numbered from one, the last beat carrying every answer."""
    kept = [dict(row, n=n) for n, row in enumerate(kept, start=1)]
    for row in kept:
        if row["type"] == "beat":
            row["detail"] = {"acks": []}
    last = next(row for row in reversed(kept) if row["type"] == "beat")
    last["detail"]["acks"] = [[row["n"], row["t"] + UP_S + DOWN_S] for row in kept if row is not last]
    rows[:] = kept


def _no_fence(rows):
    """Sol round 9: the records stop arriving at shutdown. Everything up to a beat made after the last
    step is in hand, numbered whole, and nothing shows that the page made nothing more."""
    _renumbered(rows, [row for row in rows if row["type"] != "fence"])


def _a_suffix_lost_from_before_the_fence(rows):
    """The fence and everything the page made in the second before it never arrived."""
    fence = next(row for row in rows if row["type"] == "fence")
    _renumbered(rows, [row for row in rows if row["t"] < fence["t"] - 1.0])


def _a_fence_the_page_made_unasked(rows):
    """A fence record from before the probe asked: it shows nothing about the end of the run."""
    fence = next(row for row in rows if row["type"] == "fence")
    fence["t"] -= 5.0
    fence["received"] -= 5.0
    _renumbered(rows, sorted(rows, key=lambda row: row["t"]))  # numbered where it was made


def _an_unreadable_record(rows):
    rows.insert(3, {"type": "unreadable", "received": 1000.0})


@pytest.mark.parametrize(("page", "what", "says"), [
    (_slow_answers, "clock", "34.0 ms apart"),
    (_a_clock_set_back_during_the_run, "clock", "the bounds cross"),
    (_a_record_never_received, "page_log", "numbered_without_gaps"),
    (_a_number_twice, "page_log", "numbered_without_gaps"),
    (_a_record_without_a_number, "page_log", "numbered_without_gaps"),
    (_an_unreadable_record, "page_log", "numbered_without_gaps"),
    (_a_page_loaded_twice, "page_log", "one_load"),
    (_no_fence, "page_log", "fenced_after_the_last_step"),
    (_a_suffix_lost_from_before_the_fence, "page_log", "fenced_after_the_last_step"),
    (_a_fence_the_page_made_unasked, "page_log", "fenced_after_the_last_step"),
])
def test_a_log_that_is_incomplete_or_clocks_that_cannot_be_related_do_not_hold(tmp_path, page, what, says):
    """FP46: every step as predicted, and the run still does not hold, for the one reason given."""
    verdict = probe.analyze(_run(tmp_path, page=page))
    assert verdict["held"] is False, verdict[what]
    if what == "clock":
        assert verdict["clock"]["held"] is False and says in verdict["clock"]["why"] and verdict["page_log"]["held"]
    else:
        assert verdict["page_log"][says] is False and verdict["clock"]["held"] is True
        false = [name for name in ("numbered_without_gaps", "one_load", "fenced_after_the_last_step")
                 if verdict["page_log"][name] is False]
        # a number missing below the fence also leaves the fence showing nothing
        assert says in false and set(false) <= {says, "fenced_after_the_last_step"}
        assert verdict["page_log"]["accounted_through"] is None or says != "fenced_after_the_last_step"


def test_a_record_of_an_action_without_a_number_has_no_place_in_the_order(tmp_path):
    """The page's numbers are what orders its records. One without a number is bounded above by its
    own receipt and below by nothing, so it is untimed as well as leaving the numbering incomplete."""
    def unnumbered(rows):
        del next(row for row in rows if row["type"] == "page_event")["n"]

    verdict = probe.analyze(_run(tmp_path, page=unnumbered))
    assert verdict["held"] is False and verdict["page_log"]["numbered_without_gaps"] is False
    assert len(verdict["clock"]["untimed"]) == 1 and verdict["clock"]["untimed"][0]["width_s"] is None


def test_a_fence_asked_for_before_the_last_step_ended_does_not_hold(tmp_path):
    """The fence shows the log whole up to the moment it was asked for. Asked while the last step's
    interval was still open, it says nothing of the rest of that interval."""
    verdict = probe.analyze(_run(tmp_path, record={"fence_asked": 1173.9}))
    assert verdict["held"] is False and verdict["page_log"]["fenced_after_the_last_step"] is False
    assert all(v["held"] for v in verdict["steps"]) and verdict["clock"]["held"]
    assert probe.analyze(_run(tmp_path / "unasked", record={"fence_asked": None}))["held"] is False


def test_a_number_missing_before_the_fence_does_not_hold_and_one_lost_after_it_is_outside_the_run(tmp_path):
    """What the fence claims and what it does not. A record the page made before the fence and the
    probe never got leaves a hole below the fence's number. One made after the fence and lost at
    shutdown leaves the log whole through the fence: the run holds, and says through where. So does
    one lost after the fence with a later one received (Sol round 10): the hole is reported."""
    def before(rows):
        fence = next(i for i, row in enumerate(rows) if row["type"] == "fence")
        del rows[fence - 3]

    def after(rows):
        fence = next(i for i, row in enumerate(rows) if row["type"] == "fence")
        assert rows[-1]["n"] > rows[fence]["n"] + 1
        kept = rows[:-1]
        kept[-1]["detail"]["acks"] = rows[-1]["detail"]["acks"][:-1]
        rows[:] = kept

    holed = probe.analyze(_run(tmp_path / "before", page=before))
    assert holed["held"] is False and holed["page_log"]["fenced_after_the_last_step"] is False
    assert holed["page_log"]["numbered_without_gaps"] is False
    lost = probe.analyze(_run(tmp_path / "after", page=after))
    fence = next(row for row in probe._jsonl(tmp_path / "after/out/page-events.jsonl") if row["type"] == "fence")
    assert lost["held"] is True and lost["page_log"]["accounted_through"]["record"] == fence["n"]

    def a_hole_after(rows):
        fence = next(i for i, row in enumerate(rows) if row["type"] == "fence")
        assert len(rows) > fence + 2 and rows[fence + 1]["type"] == "beat"
        del rows[fence + 1]

    holed_after = probe.analyze(_run(tmp_path / "hole", page=a_hole_after))
    log = holed_after["page_log"]
    assert holed_after["held"] is True and log["numbered_without_gaps"] is True
    assert log["missing_after_the_fence"] == [log["accounted_through"]["record"] + 1]


def test_an_action_made_after_the_last_step_fails_the_run_on_either_side_of_the_fence(tmp_path):
    """Stricter than the cutoff requires, and said to be: the run is accounted for through the fence,
    and a record of something done to the page is judged by when it was made, wherever its number
    falls. Here one is made 0.3 s after the fence; one made between the last step and the fence is
    ``test_a_record_outside_every_step_is_not_ignored``."""
    def stray(steps, handlers, gestures):
        handlers.moved.append({"t": steps[-1]["t_end"] + 1.6, "n": next(_numbers), "type": "page_event",
                               "detail": {"event": "click", "trusted": False, "target": None, "x": 5, "y": 5,
                                          "rect": None}})

    verdict = probe.analyze(_run(tmp_path, stray))
    assert verdict["held"] is False and len(verdict["page_log"]["unaccounted"]) == 1
    assert verdict["page_log"]["fenced_after_the_last_step"] is True


def _at(seconds_into, label="Beta", expect="clicked", *, late=None, unanswered=False):
    """Move the page's records of one step to ``seconds_into`` it (and answer them ``late``, or not at
    all), leaving the pointer's samples on the control around that moment."""
    def change(steps, handlers, gestures):
        step = _step(steps, label, expect)
        t0, t = step["t_start"], step["t_start"] + seconds_into
        x, y, w, h = RECTS[label, expect]
        there = [CONTENT[0] + x + w / 2, CONTENT[1] + y + h / 2]
        mine = [e for e in [*handlers, *handlers.pressed] if (e["detail"].get("target") or e["detail"].get("button")) == label
                and t0 <= e["t"] <= t0 + 3]
        assert len(mine) == 6
        for e in mine:
            e["t"] = t
            e["late"], e["unanswered"] = late, unanswered
        handlers.samples += [[round(t - 0.6 + 0.005 * n, 4), *there] for n in range(240)]

    return change


def _answers(rows):
    """Apply what ``_at`` asked of the answers: later, or never."""
    answers = rows[-1]["detail"]["acks"]
    for row in rows:
        late, unanswered = row.pop("late", None), row.pop("unanswered", False)
        if unanswered:
            answers[:] = [a for a in answers if a[0] != row["n"]]
        elif late is not None:
            for a in answers:
                if a[0] == row["n"]:
                    a[1] = row["t"] + late


@pytest.mark.parametrize(("seconds_into", "where"), [(4.001, "end"), (-0.001, "start")])
def test_a_record_whose_time_reaches_across_a_steps_boundary_is_ambiguous(tmp_path, seconds_into, where):
    """Sol round 9: a record's time in the probe's clock is an interval, here 4 ms wide. Its midpoint
    would put it a millisecond inside or outside the step; the truth can be on either side, so the run
    does not hold and names the records, and it is not counted as inside or as outside."""
    verdict = probe.analyze(_run(tmp_path, _at(seconds_into), page=_answers))
    log = verdict["page_log"]
    assert verdict["held"] is False and log["held"] is False and log["unaccounted"] == []
    assert len(log["ambiguous"]) == 6 and {r["on"] for r in log["ambiguous"]} == {"Beta"}, (where, log)
    assert verdict["clock"]["held"] and log["numbered_without_gaps"] and log["fenced_after_the_last_step"]
    # 5 ms further in, the whole interval is inside and the same run holds
    inside = probe.analyze(_run(tmp_path / "inside", _at(3.995 if where == "end" else 0.005), page=_answers))
    assert inside["page_log"]["ambiguous"] == [] and inside["page_log"]["held"] is True


@pytest.mark.parametrize(("change", "width"), [(_at(2.2, late=0.030), 0.032), (_at(2.2, unanswered=True), 0.206)])
def test_a_record_of_an_action_that_its_own_post_does_not_place_within_20_ms_is_untimed(tmp_path, change, width):
    """FP54 (u): the answers to one click's posts came 30 ms after them, or never. The run's common
    bounds still agree, from all the other posts; these six records are not placed by them, because
    that would assume the two clocks kept one difference. Each is bounded by its own post, 30 ms wide
    and two grains, or, with no answer of its own, below by the last record numbered before it that was
    answered: the beat 200 ms earlier."""
    verdict = probe.analyze(_run(tmp_path, change, page=_answers))
    clock = verdict["clock"]
    assert verdict["held"] is False and clock["held"] is False and clock["width_s"] <= 0.02
    assert [r["on"] for r in clock["untimed"]] == ["Beta"] * 6 and "not placed within 20 ms" in clock["why"]
    assert {r["width_s"] for r in clock["untimed"]} == {width} and clock["widest_action_record_s"] == width
    # nothing else is wrong with the run: the step is judged over the wider interval and holds there
    assert verdict["page_log"]["held"] and all(v["held"] for v in verdict["steps"])


def test_a_record_is_bounded_by_the_ones_numbered_around_it_and_not_by_a_shared_timestamp(tmp_path):
    """Sol round 10: two records with one timestamp were not made at one moment. Here a click's posts
    were never answered, and another record carries the same timestamp and was answered at once. Made
    (numbered) before the click, it bounds the click from below and the click is placed. Made after
    it, it shows nothing about how early the click was, and the click is untimed."""
    def beside(numbered):
        def change(steps, handlers, gestures):
            _at(2.2, unanswered=True)(steps, handlers, gestures)
            t = _step(steps, "Beta", "clicked")["t_start"] + 2.2
            handlers.moved.append({"t": t, "n": numbered, "type": "scrolled", "detail": {"y": 0}})
        return change

    before = probe.analyze(_run(tmp_path / "before", beside(-1), page=_answers))
    assert before["held"] is True and before["clock"]["widest_action_record_s"] == 0.006
    later = probe.analyze(_run(tmp_path / "after", beside(10**8), page=_answers))
    assert later["held"] is False and [r["on"] for r in later["clock"]["untimed"]] == ["Beta"] * 6


def test_two_records_with_one_coarse_timestamp_are_each_placed_around_their_own_true_time():
    """Sol round 10's case. The page's clock reads in steps of 0.1 ms. A is made at probe time
    100.00001 and B 80 microseconds later; both read 10.0000, and both answers read 10.0001. Ordered by
    timestamp, each bounded the other and both were given an interval holding neither's true time.
    Ordered by number, each interval holds its own."""
    a = {"t": 10.0000, "n": 1, "type": "page_event", "received": 100.00008}
    b = {"t": 10.0000, "n": 2, "type": "page_event", "received": 100.00015}
    beat = {"t": 10.5, "n": 3, "type": "beat", "received": 100.5001, "detail": {"acks": [[1, 10.0001], [2, 10.0001]]}}
    placed, after = probe._timer([a, b, beat])
    (a_low, a_high), (b_low, b_high) = placed(a), placed(b)
    assert a_low <= 100.00001 <= a_high and b_low <= 100.00009 <= b_high
    # A is not bounded below by B, which was made after it, and B is bounded above by nothing but itself
    assert a_low == pytest.approx(100.00008 - probe._elapsed(0.0001)) and a_high == 100.00008
    assert b_low == pytest.approx(100.00015 - probe._elapsed(0.0001)) and b_high == 100.00015
    # a step that began at 100.00004, between them, does not hold A wholly: A may have come before it
    assert a_low < 100.00004 < a_high
    # an event that was not posted, read at the same timestamp, is not bounded by either record: only
    # by records clearly earlier than two grains before it
    assert after(10.0000) == -math.inf and after(10.0000 + 2 * probe.PAGE_CLOCK_GRAIN_S) == pytest.approx(b_low)


def test_an_answer_time_that_reads_a_grain_early_still_bounds_its_record():
    """The answer came 0.9 ms after the record by the page's true clock and reads the same coarse
    time as the record. Taken as reported, the record would be placed after it was made."""
    record = {"t": 10.000, "n": 1, "type": "page_event", "received": 100.0005}
    beat = {"t": 10.5, "n": 2, "type": "beat", "received": 100.5, "detail": {"acks": [[1, 10.000]]}}
    low, high = probe._timer([record, beat])[0](record)
    true = 100.0005 - 0.0004  # made 0.4 ms before the probe received it
    assert low <= true <= high and low == pytest.approx(100.0005 - probe._elapsed(0.0))


def test_a_record_read_late_and_its_answer_read_early_are_two_errors_and_both_are_allowed_for():
    """Sol check 11's case. The time from a record to its answer is the difference of two readings. The
    record, made at page time 10.0000, reads 10.0009; its answer, at 10.0018, reads 10.0009 too: both
    within a grain of the truth, in opposite directions, and their difference reads zero where 1.8 ms
    passed. With one grain allowed the record was placed from 0.5 ms after it was made."""
    record = {"t": 10.0009, "n": 1, "type": "page_event", "received": 100.0015}
    beat = {"t": 10.5, "n": 2, "type": "beat", "received": 100.5, "detail": {"acks": [[1, 10.0009]]}}
    low, high = probe._timer([record, beat])[0](record)
    assert low <= 100.0000 <= high == 100.0015
    assert low == pytest.approx(100.0015 - 2 * probe.PAGE_CLOCK_GRAIN_S * (1 + probe.CLOCK_RATE_SLACK))
    assert 100.0015 - probe.PAGE_CLOCK_GRAIN_S > 100.0000  # which one grain did not reach


def _beta_read_with_opposite_errors(rows):
    """Beta's six records, made 0.4 ms before its step began: each read 0.9 ms late, received 1.5 ms
    after it was made, and its answer, 1.8 ms after it was made, read 0.9 ms early."""
    mine = [row for row in rows if (row.get("detail") or {}).get("target") == "Beta"
            or (row.get("detail") or {}).get("button") == "Beta"]
    assert len(mine) == 6
    answers = rows[-1]["detail"]["acks"]
    for row in mine:
        made = row["t"]
        row["t"], row["received"] = made + 0.0009, made + 0.0015
        for answer in answers:
            if answer[0] == row["n"]:
                answer[1] = made + 0.0009


def test_an_action_made_before_its_step_is_not_placed_inside_it_by_two_opposite_reading_errors(tmp_path):
    """Sol check 11, as a whole run: a click made 0.4 ms before its step began. With one grain allowed
    for the two readings its interval began 0.1 ms inside the step and the run held."""
    verdict = probe.analyze(_run(tmp_path, _at(-0.0004), page=_beta_read_with_opposite_errors))
    log = verdict["page_log"]
    assert verdict["held"] is False and len(log["ambiguous"]) == 6 and {r["on"] for r in log["ambiguous"]} == {"Beta"}
    start = 1000.0 + 10 * next(i for i, step in enumerate(probe.STEPS) if (step[0], step[2]) == ("Beta", "clicked"))
    low, high = log["ambiguous"][0]["between"]
    assert low < start < high and verdict["clock"]["held"]


def _an_earlier_document(*, beat_received=None, acted=False):
    """The document the launch opened, before start navigated to the page again: its own name, numbered
    from one, a record of loading and a beat (received at ``beat_received`` when given), and when
    ``acted`` a record of something done to it."""
    def page(rows):
        loaded = rows[0]
        assert loaded["type"] == "loaded"
        at, got = loaded["t"] - 0.9, loaded["received"] - 0.9
        early = [dict(loaded, n=1, doc="launch-7f3", t=at, received=got),
                 {"t": at + 0.5, "n": 2, "doc": "launch-7f3", "type": "beat",
                  "detail": {"acks": [[1, at + UP_S + DOWN_S]]},
                  "received": got + 0.5 if beat_received is None else beat_received}]
        if acted:
            early.insert(1, dict(_seen(0.0, "click", "Alpha"), n=2, doc="launch-7f3", t=at + 0.2, received=got + 0.2))
            early[2]["n"] = 3
        rows[:0] = early
    return page


def test_a_document_the_launch_opened_before_the_one_the_steps_ran_in_does_not_fail_the_run(tmp_path):
    """FP73, FP74: a start that launches the browser opens the page and then navigates to it. Two records
    of loading and numbers that begin again failed a correct run; each record now names its document and
    the one that loaded last is the one read."""
    verdict = probe.analyze(_run(tmp_path, page=_an_earlier_document()))
    log = verdict["page_log"]
    assert verdict["held"] is True and log["held"] is True and verdict["clock"]["held"] is True
    assert (log["numbered_without_gaps"], log["one_load"], log["one_document_under_the_steps"]) == (True, True, True)
    assert log["other_documents"] == {
        "documents": 1, "records": 2, "only_loading_and_beats": True, "all_received_before_the_first_step": True,
        "this_document_loaded_before_the_first_step": True}
    alone = probe.analyze(_run(tmp_path / "alone"))
    assert alone["held"] is True and alone["page_log"]["records"] == log["records"]
    assert alone["page_log"]["other_documents"]["documents"] == 0


def test_another_document_still_posting_or_acted_on_or_loaded_under_the_steps_fails_the_run(tmp_path):
    """FP74: an earlier document may have loaded and idled. One whose record arrives once the steps have
    begun, or that something was done to, or a page that loads again after the steps, is not that."""
    def says(verdict, which):
        log = verdict["page_log"]
        assert verdict["held"] is False and log["held"] is False and log["one_document_under_the_steps"] is False
        assert [name for name, value in log["other_documents"].items() if value is False] == which

    late = probe.analyze(_run(tmp_path / "late", page=_an_earlier_document(beat_received=1000.2)))
    says(late, ["all_received_before_the_first_step"])
    acted = probe.analyze(_run(tmp_path / "acted", page=_an_earlier_document(acted=True)))
    says(acted, ["only_loading_and_beats"])

    def reloaded_after_the_steps(rows):
        rows.append(dict(rows[0], n=1, doc="again-2b1", t=rows[-1]["t"] + 0.1, received=rows[-1]["received"] + 0.1))

    again = probe.analyze(_run(tmp_path / "again", page=reloaded_after_the_steps))
    # the steps' records are then another document's, and the one read holds nothing of them
    says(again, ["only_loading_and_beats", "all_received_before_the_first_step",
                 "this_document_loaded_before_the_first_step"])


def test_a_record_that_names_no_document_is_read_as_the_documents_own(tmp_path):
    """FP74: a record without a name is judged with the document under test and not set aside with
    another's, so leaving the name off cannot take a record out of the account."""
    def unnamed(rows):
        for row in rows[1:]:
            del row["doc"]

    verdict = probe.analyze(_run(tmp_path, page=unnamed))
    assert verdict["held"] is True and verdict["page_log"]["other_documents"]["records"] == 0

    def an_unnamed_action_outside_every_step(rows):
        stray = dict(_seen(0.0, "click", "Alpha"), n=len(rows) + 1, t=rows[-1]["t"] + 0.05,
                     received=rows[-1]["received"] + 0.05)
        rows.append(stray)

    stray = probe.analyze(_run(tmp_path / "stray", page=an_unnamed_action_outside_every_step))
    assert stray["held"] is False and stray["page_log"]["unaccounted"]


def test_the_pointers_last_event_is_placed_by_the_record_that_carries_it(tmp_path):
    """Sol check 11: with no post between a step's start and the pointer's last move, nothing made
    clearly before the move is inside the step, and a correct run failed for want of an anchor. The
    record that carries the move was made after it by the time between their two readings, and its own
    earliest moment is known; that places the move. One from before the step is still refused."""
    def moved_at(seconds_into):
        def change(steps, handlers, gestures):
            step = _step(steps, "Alpha", "clicked")
            handlers[0]["detail"]["last_trusted_pointer"]["t"] = step["t_start"] + seconds_into
        return change

    def no_post_before_the_click(rows):
        _renumbered(rows, [row for row in rows if not (row["type"] == "beat" and 1000.0 <= row["t"] < 1002.0)])

    # the only records of the step before the click are gone: the move at 1.999 s has no earlier anchor
    alone = probe.analyze(_run(tmp_path / "alone", moved_at(1.999), page=no_post_before_the_click))
    assert alone["held"] is True and _of(alone, "Alpha", "clicked")["pointer_during_step"] is True
    # a move 5 ms into the step is inside it by more than the allowance; one 5 ms before it is not
    early = probe.analyze(_run(tmp_path / "early", moved_at(0.005), page=no_post_before_the_click))
    assert _of(early, "Alpha", "clicked")["pointer_during_step"] is False  # 2 s of rate slack and 4 ms of post
    inside = probe.analyze(_run(tmp_path / "inside", moved_at(0.015), page=no_post_before_the_click))
    assert _of(inside, "Alpha", "clicked")["pointer_during_step"] is True
    stale = probe.analyze(_run(tmp_path / "stale", moved_at(-0.005), page=no_post_before_the_click))
    assert stale["held"] is False and _of(stale, "Alpha", "clicked")["pointer_during_step"] is False
    # a pointer reading later than the record that carries it cannot be placed
    after = probe.analyze(_run(tmp_path / "after", moved_at(2.01), page=no_post_before_the_click))
    assert _of(after, "Alpha", "clicked")["pointer_during_step"] is False


@pytest.mark.parametrize(("step", "holds"), [(0.0001, True), (0.001, True), (0.0011, False), (None, False), (0, False)])
def test_the_grain_is_checked_against_the_step_the_page_measured_of_its_own_clock(tmp_path, step, holds):
    """FP62 (x): the bounds allow the page's times a grain of 1 ms. A page whose clock steps more
    coarsely than that, or that did not say, cannot be read by them."""
    def stepping(steps, handlers, gestures):
        handlers.loaded["clock_step_s"] = step

    verdict = probe.analyze(_run(tmp_path, stepping))
    assert verdict["held"] is holds and verdict["clock"]["held"] is holds
    assert holds or "step of its clock" in verdict["clock"]["why"]


def _common_bounds_off_by(seconds):
    def change(rows):
        for row in rows[len(rows) // 2:]:
            row["received"] -= seconds
    return change


@pytest.mark.parametrize(("seconds", "holds"), [(0.0055, True), (0.0065, False)])
def test_common_bounds_cross_only_beyond_the_grain(tmp_path, seconds, holds):
    """The common bounds are 4 ms apart in a composed run and loosened a grain each side. Receipts
    5.5 ms early in half the run leave them touching; 6.5 ms cross them: a clock changed."""
    verdict = probe.analyze(_run(tmp_path, page=_common_bounds_off_by(seconds)))
    assert verdict["clock"]["held"] is holds
    assert holds or "the bounds cross" in verdict["clock"]["why"]


def test_the_samples_must_hold_over_the_whole_interval_an_event_can_have_happened_in(tmp_path):
    """Sol round 9: a sample off the control 251 ms before the latest moment an event can have happened
    is outside the window around that moment and inside the window around the earliest. The answers
    here came 12 ms after the posts, so the interval is 14 ms wide with two grains and the run timed;
    the sample counts."""
    def off(at):
        def change(steps, handlers, gestures):
            _at(2.2, late=0.012)(steps, handlers, gestures)
            handlers.samples.append([_step(steps, "Beta", "clicked")["t_start"] + 2.202 - at, 5.0, 5.0])
        return change

    inside = probe.analyze(_run(tmp_path / "in", off(0.255), page=_answers))
    assert inside["clock"]["held"] and inside["clock"]["widest_action_record_s"] == 0.014
    assert _of(inside, "Beta", "clicked")["held"] is False and _of(inside, "Beta", "clicked")["samples_off_control"] == 5
    outside = probe.analyze(_run(tmp_path / "out", off(0.265), page=_answers))
    assert _of(outside, "Beta", "clicked")["held"] is True and outside["held"] is True


@pytest.mark.parametrize(("kind", "detail"), [
    ("page_event", {"event": "pointerdown", "trusted": True, "target": "Beta", "x": 690, "y": 352,
                    "rect": [620, 330, 140, 44]}),
    ("page_event", {"event": "click", "trusted": False, "target": None, "x": 5, "y": 5, "rect": None}),
    ("click_handler", {"button": "Alpha", "rect": [40, 60, 140, 44], "dpr": 2}),
    ("input", {"field": "Note", "value": "x"}),
    ("moved", {"control": "Dodge", "by": "mousedown", "trusted": True}),
])
@pytest.mark.parametrize("when", ["between two steps", "before the first", "after the last"])
def test_a_record_outside_every_step_is_not_ignored(tmp_path, kind, detail, when):
    """Sol round 8: Alpha's interval ends at 1004 and the next step starts at 1010; a press at 1005 was
    judged by no step. Every step still holds; the run does not, and names the record."""
    def stray(steps, handlers, gestures):
        t = {"between two steps": steps[0]["t_end"] + 2.0, "before the first": steps[0]["t_start"] - 1.5,
             "after the last": steps[-1]["t_end"] + 1.5}[when]
        handlers.moved.append({"t": t, "n": next(_numbers), "type": kind, "detail": detail})

    verdict = probe.analyze(_run(tmp_path, stray))
    assert verdict["held"] is False and all(v["held"] for v in verdict["steps"]), verdict["page_log"]
    assert [(r["type"], r["event"]) for r in verdict["page_log"]["unaccounted"]] == [(kind, detail.get("event"))]
    assert verdict["page_log"]["numbered_without_gaps"] and verdict["clock"]["held"]
    assert verdict["page_log"]["ambiguous"] == []


def test_step_intervals_that_overlap_do_not_hold(tmp_path):
    def overlapping(steps, handlers, gestures):
        steps[1]["t_start"] = steps[0]["t_end"] + 0.5

    verdict = probe.analyze(_run(tmp_path, overlapping))
    assert verdict["held"] is False and verdict["page_log"]["step_intervals_apart"] is False


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
    monkeypatch.setattr(probe, "_release_session", lambda record, env, out, session: None)
    monkeypatch.setattr(probe, "_closures", lambda record, env, out, session, said: dict(CLOSED))
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

    monkeypatch.setattr(probe, "_release_session", lambda record, env, out, session: did.append("session"))
    monkeypatch.setattr(probe, "_closures", lambda record, env, out, session, said: did.append("closures") or dict(CLOSED))
    monkeypatch.setattr(probe, "_retire_holder", retire)
    monkeypatch.setattr(probe, "_close_owned_chrome", close)
    monkeypatch.setattr(probe, "_restore_front", lambda record: did.append("front"))
    stop = probe.threading.Event()
    helper = type("Helper", (), {"join": lambda self, timeout=None: did.append("sampler"),
                                 "shutdown": lambda self: did.append("server")})()
    verdict = probe._finish(record, out, out / "session", "", stop, helper, helper)
    # the session's reservation is given up first, and what is closed is read last
    assert did == ["session", "holder", "chrome", "front", "sampler", "server", "closures"] and stop.is_set()
    written = json.loads((out / "run.json").read_text())
    assert written["cleanup_errors"] == ["holder: RuntimeError: the holder did not exit"]
    assert verdict["held"] is False and all(v["held"] for v in verdict["steps"])
    assert json.loads((out / "verdict.json").read_text())["held"] is False


class Registry:
    """Footwork's coordination registry as the probe's commands see it: ``control status`` prints it,
    ``control yield TOKEN`` and ``control cancel TOKEN`` revoke that entry unless ``stuck`` or ``refuses``.
    Every command is kept, in order."""

    def __init__(self, reservations=(), requests=(), *, stuck=False, refuses=False):
        self.reservations = [dict(row) for row in reservations]
        self.requests = [dict(row) for row in requests]
        self.stuck, self.refuses, self.commands = stuck, refuses, []

    def __call__(self, env, out, name, *argv):
        self.commands.append((name, *argv))
        reply = {"name": name, "t_start": 0.0, "t_end": 0.0, "exit": 0, "stderr": ""}
        if argv == ("control", "status"):
            return reply | {"stdout": json.dumps({"requests": self.requests, "reservations": self.reservations})}
        assert argv[:2] in (("control", "yield"), ("control", "cancel")), argv
        if self.refuses:
            return reply | {"exit": 2, "stdout": "", "stderr": "unknown ownership token"}
        if not self.stuck:
            for row in (*self.reservations, *self.requests):
                if row["token"] == argv[2]:
                    row["state"] = "revoked"
        return reply | {"stdout": "revoked; active input retains ownership until readback and cleanup finish"}


def _reserved(session, token="194718ca", **more):
    return {"token": token, "owner": str(session), "desktop": "console",
            "resources": ["app/google%20chrome", "desktop"], "state": "active"} | more


def test_the_cleanup_gives_up_what_the_runs_session_reserved(tmp_path, monkeypatch):
    """FP81, FP82: a filmed start reserves the desktop and the browser until someone yields. The second
    live run closed its browser and left that reservation active; the next start, sixteen minutes
    later, was refused for it. The cleanup yields the session's own token and reads the registry again."""
    session = tmp_path / "out/session"
    session.mkdir(parents=True)
    (session / "session.json").write_text(json.dumps({"coordination_token": "194718ca"}))
    others = [_reserved(tmp_path / "another/session", "aa11", state="revoked"), _reserved(tmp_path / "theirs", "bb22")]
    registry = Registry([*others, _reserved(session)])
    monkeypatch.setattr(probe, "_cli", registry)
    record: dict = {}
    probe._release_session(record, {}, tmp_path / "out", session)
    assert registry.commands == [("zz-registry-before-release", "control", "status"),
                                 ("zz-release-0", "control", "yield", "194718ca"),
                                 ("zz-registry-after-release", "control", "status")]
    said = record["session_reservation"]
    assert said["released"] is True and said["still_held"] == [] and said["named_by_session"] == "194718ca"
    assert said["held"] == [{"kind": "reservation", "token": "194718ca", "resources": ["app/google%20chrome", "desktop"]}]
    assert said["yields"] == [{"token": "194718ca", "exit": 0, "stderr": "",
                               "stdout": "revoked; active input retains ownership until readback and cleanup finish"}]
    # only its own: another session's active reservation is not touched
    assert [row["state"] for row in registry.reservations] == ["revoked", "active", "revoked"]


def test_a_session_that_reserved_nothing_releases_nothing_and_says_so(tmp_path, monkeypatch):
    session = tmp_path / "out/session"
    registry = Registry([_reserved(tmp_path / "theirs", "bb22")])
    monkeypatch.setattr(probe, "_cli", registry)
    record: dict = {}
    probe._release_session(record, {}, tmp_path / "out", session)
    assert [command[1:] for command in registry.commands] == [("control", "status"), ("control", "status")]
    assert record["session_reservation"] == {"released": True, "named_by_session": None, "held": [], "yields": [],
                                             "still_held": []}


def test_a_start_that_failed_after_reserving_and_wrote_no_record_is_still_released(tmp_path, monkeypatch):
    """FP82 (b): the token comes from the registry, by the session's directory, so a reservation whose
    session never wrote its record is found. A waiting request of the session's is cancelled."""
    session = tmp_path / "out/session"
    waiting = {"token": "cc33", "owner": str(session), "resources": ["desktop"], "state": "waiting", "pid": 9}
    registry = Registry([_reserved(session)], [waiting])
    monkeypatch.setattr(probe, "_cli", registry)
    record: dict = {}
    probe._release_session(record, {}, tmp_path / "out", session)
    assert [command[1:] for command in registry.commands[1:3]] == [("control", "yield", "194718ca"),
                                                                    ("control", "cancel", "cc33")]
    assert record["session_reservation"]["released"] is True and record["session_reservation"]["named_by_session"] is None


@pytest.mark.parametrize(("how", "why", "left"), [
    ({"stuck": True}, "still holds \\['194718ca'\\]", ["194718ca"]),
    ({"refuses": True}, "still holds \\['194718ca'\\]", ["194718ca"]),
])
def test_a_reservation_that_is_still_there_after_the_yield_is_an_error(tmp_path, monkeypatch, how, why, left):
    session = tmp_path / "out/session"
    monkeypatch.setattr(probe, "_cli", Registry([_reserved(session)], **how))
    record: dict = {}
    with pytest.raises(RuntimeError, match=why):
        probe._release_session(record, {}, tmp_path / "out", session)
    assert record["session_reservation"]["released"] is False and record["session_reservation"]["still_held"] == left


def test_a_registry_that_cannot_be_read_is_an_error_and_releases_nothing(tmp_path, monkeypatch):
    def unreadable(env, out, name, *argv):
        return {"name": name, "exit": 1, "stdout": "", "stderr": "database is locked", "t_start": 0.0, "t_end": 0.0}

    monkeypatch.setattr(probe, "_cli", unreadable)
    record: dict = {}
    with pytest.raises(RuntimeError, match="control status could not be read"):
        probe._release_session(record, {}, tmp_path / "out", tmp_path / "out/session")
    assert record["session_reservation"]["released"] is False


def test_a_session_left_reserved_fails_the_run_and_the_rest_of_the_cleanup_still_runs(tmp_path, monkeypatch):
    """FP82: the leak itself, end to end through the cleanup: the browser closes, the holder retires,
    and the run does not hold, because the registry still shows its session holding the desktop."""
    out = _run(tmp_path)
    record = json.loads((out / "run.json").read_text())
    del record["closed"]
    registry = Registry([_reserved(out / "session")], stuck=True)
    did: list = []
    monkeypatch.setattr(probe, "_cli", registry)
    monkeypatch.setattr(probe, "_retire_holder", lambda record, session: did.append("holder"))
    monkeypatch.setattr(probe, "_close_owned_chrome", lambda record, launch: did.append("chrome") or record.update(chrome_closed=True))
    monkeypatch.setattr(probe, "_restore_front", lambda record: did.append("front"))
    monkeypatch.setattr(probe, "_launched_chrome", lambda session, said: None)
    monkeypatch.setattr(probe, "_port_open", lambda port: False)
    import jevdual.browser_driver

    monkeypatch.setattr(jevdual.browser_driver, "chrome_pid", lambda: None)
    helper = type("Helper", (), {"join": lambda self, timeout=None: None, "shutdown": lambda self: None})()
    verdict = probe._finish(record, out, out / "session", "", probe.threading.Event(), helper, helper,
                            {"FOOTWORK_CHROME_PORT": "9466"})
    assert did == ["holder", "chrome", "front"]
    written = json.loads((out / "run.json").read_text())
    assert written["cleanup_errors"] == [
        "session: RuntimeError: this run's session still holds ['194718ca'] in Footwork's registry"]
    assert written["closed"] == {"registry": False, "browser": True, "port": True, "holder": True}
    assert verdict["held"] is False and verdict["everything_closed"] is False and verdict["closed"]["registry"] is False
    assert all(v["held"] for v in verdict["steps"])
    # and with a registry that lets go, the same cleanup holds
    record = json.loads((_run(tmp_path / "let-go") / "run.json").read_text())
    del record["closed"]
    out = tmp_path / "let-go/out"
    monkeypatch.setattr(probe, "_cli", Registry([_reserved(out / "session")]))
    verdict = probe._finish(record, out, out / "session", "", probe.threading.Event(), helper, helper,
                            {"FOOTWORK_CHROME_PORT": "9466"})
    assert verdict["held"] is True and verdict["closed"] == CLOSED


@pytest.mark.parametrize("name", sorted(CLOSED))
@pytest.mark.parametrize("read", [False, None, "missing"])
def test_a_run_holds_only_if_each_thing_it_began_was_read_as_closed(tmp_path, name, read):
    """FP81: "Chrome closed" was checked and "session ended" was said with it and was false. The four
    are read separately and the verdict needs each; a reading that was not made is not a closure."""
    closed = {key: value for key, value in CLOSED.items() if not (key == name and read == "missing")}
    if read != "missing":
        closed[name] = read
    verdict = probe.analyze(_run(tmp_path, record={"closed": closed}))
    assert verdict["held"] is False and verdict["everything_closed"] is False
    assert verdict["closed"][name] is (None if read == "missing" else read)
    assert all(v["held"] for v in verdict["steps"]) and verdict["own_chrome_closed"] is True
    legacy = probe.analyze(_run(tmp_path / "legacy", record={"closed": None}))
    assert legacy["held"] is False and legacy["closed"] == dict.fromkeys(CLOSED)


def test_what_is_closed_is_read_each_for_itself(tmp_path, monkeypatch):
    """FP82: the registry by a fresh reading, the browser by its process, the port by connecting, the
    holder by its process; one that cannot be read is None and not True."""
    import jevdual.browser_driver

    session = tmp_path / "out/session"
    session.mkdir(parents=True)
    (session / "session.json").write_text(json.dumps({"browser_holder": {"pid": 700, "start": "12.5"}}))
    registry = Registry([_reserved(session, state="revoked")])
    gone = {(800, 5.5): True, (700, "12.5"): True}
    monkeypatch.setattr(probe, "_cli", registry)
    monkeypatch.setattr(probe, "_launched_chrome", lambda session, said: {"pid": 800, "incarnation": 5.5})
    monkeypatch.setattr(probe, "_gone", lambda pid, started=None: gone[pid, started])
    monkeypatch.setattr(probe, "_port_open", lambda port: port != 9466)
    env = {"FOOTWORK_CHROME_PORT": "9466"}
    assert probe._closures({}, env, tmp_path / "out", session, "") == CLOSED
    assert registry.commands == [("zz-registry-final", "control", "status")]
    gone[800, 5.5] = False
    assert probe._closures({}, env, tmp_path / "out", session, "")["browser"] is False
    gone[800, 5.5], gone[700, "12.5"] = True, False
    assert probe._closures({}, env, tmp_path / "out", session, "")["holder"] is False
    gone[700, "12.5"] = True
    monkeypatch.setattr(probe, "_port_open", lambda port: True)
    assert probe._closures({}, env, tmp_path / "out", session, "")["port"] is False
    registry.reservations[0]["state"] = "active"
    monkeypatch.setattr(probe, "_port_open", lambda port: False)
    assert probe._closures({}, env, tmp_path / "out", session, "")["registry"] is False

    def unreadable(env, out, name, *argv):
        raise OSError("no such command")

    monkeypatch.setattr(probe, "_cli", unreadable)
    assert probe._closures({}, env, tmp_path / "out", session, "")["registry"] is None
    # no browser was launched: closed only if no Chrome matches this run's profile and port
    monkeypatch.setattr(probe, "_launched_chrome", lambda session, said: None)
    monkeypatch.setattr(jevdual.browser_driver, "chrome_pid", lambda: 4242)
    assert probe._closures({}, env, tmp_path / "out", session, "")["browser"] is False


def test_a_process_is_gone_when_its_number_is_free_or_belongs_to_another(monkeypatch):
    import os

    import psutil

    me = psutil.Process(os.getpid())
    assert probe._gone(os.getpid(), me.create_time()) is False and probe._gone(os.getpid()) is False
    assert probe._gone(os.getpid(), me.create_time() - 100.0) is True  # the number is another process's now
    assert probe._gone(2 ** 22 + 12345) is True
    assert probe._gone(None) is False and probe._gone("700") is False and probe._gone(True) is False


def test_a_desktop_someone_holds_refuses_the_run_before_the_gate_and_says_whose(tmp_path, monkeypatch):
    """FP81: the third run waited at start for thirty seconds and was refused, in a slot three tracks
    had arranged. The registry is read before the idle gate; nothing is launched and nothing waited for."""
    out = tmp_path / "out"
    registry = Registry([_reserved("/somewhere/else/session", "bb22")])
    monkeypatch.setattr(probe, "_cli", registry)
    monkeypatch.setattr(probe, "preflight", lambda *args, **kwargs: None)
    monkeypatch.setattr(probe, "_wait_idle", lambda: pytest.fail("the gate was reached"))
    monkeypatch.setattr(probe.sys, "argv", ["probe", "--out", str(out)])
    with pytest.raises(SystemExit, match="registry shows something held: reservation bb22 on .*desktop.* by /somewhere/else/session"):
        probe.main()
    assert registry.commands == [("00-registry-at-start", "control", "status")]


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
    monkeypatch.setattr(probe, "_release_session", lambda record, env, out, session: None)
    monkeypatch.setattr(probe, "_closures", lambda record, env, out, session, said: dict(CLOSED))
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
