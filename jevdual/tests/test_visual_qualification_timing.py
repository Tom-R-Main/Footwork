"""Workflow timing must be measured wall time, with explicit phase completeness."""
import pytest

from evals.visual_qualification.timing import PHASES, WorkflowTimer


def test_measured_total_includes_gaps_and_does_not_sum_nested_phases():
    clock = [1.0]
    timer = WorkflowTimer(clock=lambda: clock[0])
    with timer.measure('capture'):
        clock[0] += .1
        with timer.measure('ocr'):
            clock[0] += .2
    for phase in PHASES - {'capture', 'ocr'}:
        timer.skip(phase)
    clock[0] += .5  # Real wall time outside instrumented phases remains in total.
    result = timer.finish(verified_outcome=True, interventions=1)
    assert result['elapsed_ms'] == pytest.approx(800)
    assert result['phases_ms']['capture'] == pytest.approx(300)
    assert result['phases_ms']['ocr'] == pytest.approx(200)
    assert result['scope'] == 'workflow'
    with pytest.raises(ValueError):
        timer.finish(verified_outcome=True, interventions=1)


def test_incomplete_phase_cannot_be_called_zero_time():
    timer = WorkflowTimer()
    timer.skip('provider')
    with pytest.raises(ValueError, match='incomplete_workflow_timing'):
        timer.finish(verified_outcome=True, interventions=0)
    with pytest.raises(ValueError, match='phase_unavailable'):
        timer.skip('provider')


def test_reversed_clock_and_nonfinite_clock_refuse():
    clock = [1.0]
    timer = WorkflowTimer(clock=lambda: clock[0])
    with pytest.raises(ValueError, match='clock_reversed'), timer.measure('capture'):
        clock[0] = .5
    with pytest.raises(ValueError, match='invalid_clock'):
        WorkflowTimer(clock=lambda: float('nan'))
