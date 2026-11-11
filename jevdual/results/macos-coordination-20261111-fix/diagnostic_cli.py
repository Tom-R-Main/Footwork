"""Timing-only wrapper: public CLI, original input methods and safety gates unchanged."""
import dataclasses
import json
import sys
import time
from pathlib import Path

from jevdual import cli, coordination, drag

trace = []
output = Path(sys.argv[1])


def timed(cls, name):
    original = getattr(cls, name)

    def call(*args, **kwargs):
        start = time.perf_counter()
        row = {'method': f'{cls.__name__}.{name}', 'start': start}
        trace.append(row)
        try:
            result = original(*args, **kwargs)
            if name == 'now':
                row['value'] = result
            return result
        finally:
            row['duration_ms'] = (time.perf_counter() - start) * 1000
    setattr(cls, name, call)


for cls, names in [(coordination.Claim, ['check']),
                   (drag.QuartzPoster, ['_mouse', 'foreign_input', 'location']),
                   (drag.MonotonicClock, ['now', 'sleep_until'])]:
    for name in names:
        timed(cls, name)

original_move = drag.play_move


def move(plan, *args, **kwargs):
    trace.append({'plan': dataclasses.asdict(plan)})
    result = original_move(plan, *args, **kwargs)
    trace.append({'result': dataclasses.asdict(result)})
    return result


drag.play_move = move
try:
    code = cli.main(sys.argv[2:])
finally:
    output.write_text(json.dumps(trace, indent=2) + '\n')
sys.exit(code)
