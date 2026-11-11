"""Diagnostic-only installed CLI: time real calls, retaining rows in memory until exit."""
import atexit
import json
import os
from pathlib import Path
import time

from jevdual import drag

rows = []
origin = time.perf_counter()


def timed(name, fn, *args):
    start = time.perf_counter()
    value = fn(*args)
    row = {'stage': name, 'start_ms': (start-origin)*1000,
           'duration_ms': (time.perf_counter()-start)*1000}
    if name == 'location':
        row['point'] = value
    elif name == 'foreign_input':
        row['cause'] = value
    rows.append(row)
    return value


Original = drag.QuartzPoster


class Proxy:
    def __init__(self, quartz):
        self.quartz = quartz

    def __getattr__(self, name):
        value = getattr(self.quartz, name)
        if name not in {'CGEventCreateMouseEvent', 'CGEventSetIntegerValueField', 'CGEventPost'}:
            return value
        def call(*args):
            result = timed(name, value, *args)
            if name == 'CGEventPost':
                point = self.quartz.CGEventGetLocation(args[1])
                rows[-1]['submitted'] = [point.x, point.y]
            return result
        return call


class Poster(Original):
    def __init__(self):
        timed('poster_init', super().__init__)
        self.q = Proxy(self.q)

    def location(self):
        return timed('location', super().location)

    def foreign_input(self):
        return timed('foreign_input', super().foreign_input)


Clock = drag.MonotonicClock


class MeasuredClock(Clock):
    def sleep_until(self, deadline):
        return timed('sleep_until', super().sleep_until, deadline)


check = drag.checkpoint
drag.checkpoint = lambda: timed('checkpoint', check)
drag.QuartzPoster = Poster
drag.MonotonicClock = MeasuredClock


@atexit.register
def save():
    Path(os.environ['FOOTWORK_TRACE_PATH']).write_text(json.dumps(rows, indent=2)+'\n')


from jevdual.cli import main

raise SystemExit(main())
