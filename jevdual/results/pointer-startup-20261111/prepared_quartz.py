"""No-input real Quartz preparation probe on exact archived fix sources."""
import json
import time

from jevdual import drag

started = time.perf_counter()
poster = drag.QuartzPoster()
prepared_ms = (time.perf_counter() - started) * 1000
rows = []
for _ in range(50):
    started = time.perf_counter()
    poster._event(poster.q.kCGEventMouseMoved, 100.0, 100.0)
    rows.append((time.perf_counter() - started) * 1000)
print(json.dumps({'source': drag.__file__, 'preparation_ms': prepared_ms,
                  'unposted_event_ms': rows, 'native_input_posted': False}))
