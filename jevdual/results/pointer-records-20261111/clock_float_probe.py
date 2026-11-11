"""Read-only calibration of Footwork's scheduling float clock, not just monotonic_ns."""
import json
import time
from pathlib import Path

rows = []
for _ in range(100):
    before = time.clock_gettime_ns(time.CLOCK_UPTIME_RAW)
    mono_ns = round(time.monotonic() * 1e9)
    after = time.clock_gettime_ns(time.CLOCK_UPTIME_RAW)
    rows.append({'raw_before_ns': before, 'monotonic_as_ns': mono_ns, 'raw_after_ns': after})
report = {'all_bracketed': all(r['raw_before_ns'] <= r['monotonic_as_ns'] <= r['raw_after_ns'] for r in rows),
          'samples': rows, 'clock_implementation': time.get_clock_info('monotonic').implementation}
Path(__file__).with_name('clock-float.json').write_text(json.dumps(report, indent=2) + '\n')
print({'all_bracketed': report['all_bracketed'], 'clock_implementation': report['clock_implementation']})
