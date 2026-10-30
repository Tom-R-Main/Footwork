"""Replay the captured real SDK refusal, without starting a driver or sending input."""
import copy
import json
from pathlib import Path

import cua_driver as cd
from jevdual.native import _linux_foreground_no_send

root = Path('/workspace/Footwork/jevdual/results/linux-vm-save-receipt-20261030')
r = json.loads((root / '045fc5d-refused-profile-sdk.json').read_text())
assert r['action'] == 'None'
outcome = cd.ToolResult(text=r['text'], images=[], structured_json=r['structured_json'],
                       is_error=r['is_error'], error_code=r['error_code'], action=None,
                       verification=None, degraded=r['degraded'], raw_json=r['raw_json'])
structured = json.loads(r['structured_json'])
control = copy.copy(outcome)
control.structured_json = json.dumps({k: structured[k] for k in ['code', 'detail', 'effect', 'suggestion']})
result = {'real_structured_fields': sorted(structured),
          'real_envelope_recognized': _linux_foreground_no_send(outcome),
          'four_field_control_recognized': _linux_foreground_no_send(control),
          'input_dispatched_by_replay': False}
(root / 'sdk-replay.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
assert result['real_envelope_recognized'], 'Actual pinned SDK foreground refusal rejected by 045fc5d recognizer'
