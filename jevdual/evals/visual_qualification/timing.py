"""Measured workflow wall time and named phases; caller owns independent outcome readback."""
from __future__ import annotations

import math
import time
from collections.abc import Callable
from contextlib import contextmanager

PHASES = frozenset(('route', 'capture', 'ocr', 'encoding', 'provider', 'validation', 'escalation',
                    'review', 'dispatch', 'settle', 'readback'))


class WorkflowTimer:
    """Explicitly measure or skip every phase; never reconstruct total by summing phases.

    Start before the workflow begins, not immediately before a network call. A
    skipped phase is explicitly unused in that workflow, not an unmeasured phase.
    This recorder does not itself observe an app or establish the outcome.
    """
    def __init__(self, *, clock: Callable[[], float] = time.perf_counter):
        self._clock = clock
        self._start = self._read()
        self._phases = {}
        self._active = set()
        self._finished = False

    def _read(self):
        now = self._clock()
        if type(now) not in (int, float) or not math.isfinite(now):
            raise ValueError('invalid_clock')
        return now

    def _phase(self, name):
        if name not in PHASES or self._finished or name in self._phases or name in self._active:
            raise ValueError('phase_unavailable')

    @contextmanager
    def measure(self, name):
        self._phase(name)
        start = self._read()
        self._active.add(name)
        try:
            yield
        finally:
            elapsed = (self._read() - start) * 1000
            self._active.remove(name)
            if elapsed < 0:
                raise ValueError('clock_reversed')
            self._phases[name] = elapsed

    def skip(self, name):
        self._phase(name)
        self._phases[name] = 0.0

    def finish(self, *, verified_outcome: bool, interventions: int) -> dict:
        if (self._finished or self._active or set(self._phases) != PHASES
                or type(verified_outcome) is not bool or type(interventions) is not int or interventions < 0):
            raise ValueError('incomplete_workflow_timing')
        elapsed = (self._read() - self._start) * 1000
        if elapsed < 0 or any(v > elapsed + 1e-6 for v in self._phases.values()):
            raise ValueError('clock_reversed')
        self._finished = True
        return {'scope': 'workflow', 'elapsed_ms': elapsed, 'phases_ms': dict(self._phases),
                'verified_outcome': verified_outcome, 'interventions': interventions}
