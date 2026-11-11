"""Cold bridge timings without posting any input event."""
import json
import time

import Quartz as q

rows = []
for i in range(50):
    row = {'iteration': i}
    def measure(name, fn):
        start = time.perf_counter()
        value = fn()
        row[name] = (time.perf_counter() - start) * 1000
        return value
    source = measure('source_ms', lambda: q.CGEventSourceCreate(q.kCGEventSourceStateHIDSystemState))
    event = measure('create_mouse_ms', lambda: q.CGEventCreateMouseEvent(
        source, q.kCGEventMouseMoved, q.CGPointMake(100, 100), q.kCGMouseButtonLeft))
    measure('tag_ms', lambda: q.CGEventSetIntegerValueField(event, q.kCGEventSourceUserData, 0x46574447))
    measure('location_ms', lambda: q.CGEventGetLocation(q.CGEventCreate(None)))
    measure('counter_ms', lambda: q.CGEventSourceCounterForEventType(
        q.kCGEventSourceStateCombinedSessionState, q.kCGEventKeyDown))
    # Resolve the callable only: CGEventPost is never called by this probe.
    measure('resolve_post_ms', lambda: q.CGEventPost)
    rows.append(row)
print(json.dumps(rows))
