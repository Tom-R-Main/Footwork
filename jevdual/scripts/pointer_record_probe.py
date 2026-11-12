"""Offline timing/clock probe. Uses real clocks and a fake poster; posts no native input."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import platform
import subprocess
import sys
import time
import types
from pathlib import Path

from jevdual import drag
from jevdual.filmed import Filmed
from jevdual.pointer_trace import GestureTrace, uptime_raw_ns


class Poster:
    def __init__(self):
        self.point = (100.0, 100.0)

    def move(self, x, y):
        self.point = x, y

    def down(self, x, y):
        self.point = x, y

    drag = move
    up = down

    def escape(self):
        pass

    def location(self):
        return self.point

    def foreign_input(self):
        return None


def percentile(values, fraction):
    return sorted(values)[round((len(values) - 1) * fraction)]


def clock_probe():
    lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib')
    lib.mach_absolute_time.restype = ctypes.c_uint64

    class Timebase(ctypes.Structure):
        _fields_ = [('numer', ctypes.c_uint32), ('denom', ctypes.c_uint32)]

    base = Timebase()
    lib.mach_timebase_info(ctypes.byref(base))
    samples = []
    for _ in range(100):
        raw_before = uptime_raw_ns()
        ticks = lib.mach_absolute_time()
        raw_after = uptime_raw_ns()
        mono_before = uptime_raw_ns()
        mono = time.monotonic_ns()
        mono_after = uptime_raw_ns()
        samples.append({'raw_before': raw_before, 'mach_ns': ticks * base.numer // base.denom,
                        'raw_after': raw_after, 'monotonic_ns': mono,
                        'mono_raw_before': mono_before, 'mono_raw_after': mono_after})
    return {'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
            'monotonic_implementation': time.get_clock_info('monotonic').implementation,
            'timebase': {'numer': base.numer, 'denom': base.denom},
            'raw_brackets_mach': all(s['raw_before'] <= s['mach_ns'] <= s['raw_after'] for s in samples),
            'raw_brackets_monotonic': all(s['mono_raw_before'] <= s['monotonic_ns'] <= s['mono_raw_after']
                                           for s in samples),
            'monotonic_minus_raw_midpoint_ns': [s['monotonic_ns'] -
                                               (s['mono_raw_before'] + s['mono_raw_after']) // 2
                                               for s in samples],
            'samples': samples}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--baseline', default='b6a291b77a07dc78bee603ce1c026690050c74f5')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = subprocess.check_output(['git', 'show', f'{args.baseline}:jevdual/python/jevdual/drag.py']).decode()
    baseline = types.ModuleType('_pointer_baseline')
    sys.modules[baseline.__name__] = baseline
    exec(compile(source, '<named-baseline>', 'exec'), baseline.__dict__)  # noqa: S102
    plan = drag.DragPlan((100, 100), (500, 100),
                         tuple(drag.Sample(i / 120, 100 + 400 * i / 120, 100) for i in range(121)),
                         'probe', 400 / 120)
    filmed = Filmed((0, 0, 1000, 1000), (0, 0, 1000, 1000),
                    trace_path=str(args.output / 'benchmark-gestures.jsonl'))

    class FixtureClock:
        def __init__(self):
            self.value = 100.0
            self.deadlines = []

        def now(self):
            return self.value

        def sleep_until(self, deadline):
            self.deadlines.append(deadline)
            self.value = max(self.value, deadline)

    class EventPoster(Poster):
        def __init__(self):
            super().__init__()
            self.events = []

        def move(self, x, y):
            self.events.append(('move', x, y))
            super().move(x, y)

        def drag(self, x, y):
            self.events.append(('drag', x, y))
            super().move(x, y)

        def down(self, x, y):
            self.events.append(('down', x, y))
            super().down(x, y)

        def up(self, x, y):
            self.events.append(('up', x, y))
            super().down(x, y)

    equality = []
    for name in ('play_move', 'play_drag'):
        a, b, ca, cb = EventPoster(), EventPoster(), FixtureClock(), FixtureClock()
        trace = GestureTrace(filmed, 'fixture', name, plan.start, plan.end, plan)
        expected = getattr(baseline, name)(plan, a, ca)
        actual = getattr(drag, name)(plan, trace.poster(b), cb, trace=trace)
        assert ca.deadlines == cb.deadlines and a.point == b.point and a.events == b.events
        assert expected.outcome == actual.outcome and expected.lateness_s == actual.lateness_s
        equality.append({'player': name, 'deadlines_equal': True, 'outcome_equal': True,
                         'final_point_equal': True, 'post_sequence_equal': True, 'lateness_equal': True})
    runs = []
    example = None
    for pair in range(6):
        for instrumented in ([False, True] if pair % 2 == 0 else [True, False]):
            poster = Poster()
            trace = GestureTrace(filmed, 'park', 'offline fake poster', plan.start, plan.end, plan) if instrumented else None
            before = uptime_raw_ns()
            result = (drag.play_move(plan, trace.poster(poster), drag.MonotonicClock(), trace=trace)
                      if trace else baseline.play_move(plan, poster, drag.MonotonicClock()))
            after = uptime_raw_ns()
            finalize_ns = 0
            if trace:
                finalize_start = uptime_raw_ns()
                example = trace.finish(poster, result.outcome, result)
                assert all(before <= s['t_ns'] <= s['post_returned_ns'] <= after
                           for s in example['posted_samples'])
                finalize_ns = uptime_raw_ns() - finalize_start
            runs.append({'pair': pair, 'instrumented': instrumented, 'outcome': result.outcome,
                         'duration_ns': after - before, 'record_finalize_ns': finalize_ns, 'lateness_s': result.lateness_s,
                         'max_gap_s': result.max_gap_s, 'posted': result.posted_drags})
    summary = {}
    for label, flag in [('baseline', False), ('instrumented', True)]:
        values = [s * 1000 for run in runs if run['instrumented'] == flag for s in run['lateness_s']]
        summary[label] = {'p50_ms': percentile(values, .5), 'p95_ms': percentile(values, .95), 'max_ms': max(values),
                          'max_gap_ms': max(r['max_gap_s'] for r in runs if r['instrumented'] == flag) * 1000}
    summary['p95_delta_ms'] = summary['instrumented']['p95_ms'] - summary['baseline']['p95_ms']
    line = json.dumps(example, separators=(',', ':')) + '\n'
    (args.output / 'example-one-second.jsonl').write_text(line)
    tiny_plan = drag.DragPlan((100, 100), (101, 100),
                              (drag.Sample(0, 100, 100), drag.Sample(.002, 101, 100)), 'fixture', 1)
    tiny_poster = Poster()
    tiny = GestureTrace(filmed, 'park', 'offline fixture', tiny_plan.start, tiny_plan.end, tiny_plan)
    tiny_result = drag.play_move(tiny_plan, tiny.poster(tiny_poster), drag.MonotonicClock(), trace=tiny)
    tiny_record = tiny.finish(tiny_poster, tiny_result.outcome, tiny_result)
    (args.output / 'example-line.jsonl').write_text(json.dumps(tiny_record, separators=(',', ':')) + '\n')
    report = {'baseline_sha': args.baseline,
              'candidate_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip(),
              'source_sha256': {name: hashlib.sha256(Path('python/jevdual', name).read_bytes()).hexdigest()
                                for name in ('drag.py', 'pointer_trace.py', 'filmed.py')},
              'clock': clock_probe(), 'summary': summary, 'record_bytes': len(line.encode()),
              'runs': runs, 'fixture_comparison': equality, 'native_input_posted': False}
    (args.output / 'probe.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'summary': summary, 'record_bytes': report['record_bytes'],
                      'clock_raw_brackets_mach': report['clock']['raw_brackets_mach'],
                      'clock_raw_brackets_monotonic': report['clock']['raw_brackets_monotonic']}, indent=2))


if __name__ == '__main__':
    main()
