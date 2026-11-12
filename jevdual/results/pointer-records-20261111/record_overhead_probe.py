"""Read-only display metadata and bounded fixture-record encoding/append costs; no pointer posts."""
import json
import sys
from pathlib import Path

from jevdual.filmed import Filmed
from jevdual.pointer_trace import GestureTrace, uptime_raw_ns

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
record = json.loads((root / 'example-one-second.jsonl').read_text())
scratch = root / 'overhead-scratch.jsonl'
prepare_ns, encode_append_ns = [], []
filmed = Filmed((0, 0, 1000, 1000), (0, 0, 1000, 1000))
for _ in range(30):
    began = uptime_raw_ns()
    GestureTrace(filmed, 'park', 'offline metadata probe', (100, 100), (500, 100))
    prepare_ns.append(uptime_raw_ns() - began)
    began = uptime_raw_ns()
    with scratch.open('a') as stream:
        stream.write(json.dumps(record, separators=(',', ':')) + '\n')
    encode_append_ns.append(uptime_raw_ns() - began)
scratch.unlink()
report = {'iterations': 30, 'prepare_metadata_ns': prepare_ns, 'encode_append_ns': encode_append_ns,
          'native_input_posted': False, 'record_bytes': len(json.dumps(record, separators=(',', ':')).encode()) + 1}
(root / 'record-overhead.json').write_text(json.dumps(report, indent=2) + '\n')
print({key: {'p50_ms': sorted(values)[len(values)//2]/1e6, 'max_ms': max(values)/1e6}
       for key, values in [('prepare', prepare_ns), ('encode_append', encode_append_ns)]})
