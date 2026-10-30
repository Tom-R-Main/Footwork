"""Record real CUA hotkey results and return them unchanged."""
import dataclasses
import json
import os
from pathlib import Path
import runpy
import sys

import cua_driver as cd
from jevdual.native import _linux_foreground_no_send

original = cd.CuaDriver.call_tool


async def recorded(self, name, arguments_json):
    outcome = await original(self, name, arguments_json)
    if name == 'hotkey':
        result = {key: getattr(outcome, key, None) for key in
                  ['text', 'structured_json', 'is_error', 'error_code', 'degraded', 'raw_json']}
        action = getattr(outcome, 'action', None)
        result['action'] = dataclasses.asdict(action) if dataclasses.is_dataclass(action) else repr(action)
        result['recognizer_result'] = _linux_foreground_no_send(outcome)
        result['arguments'] = json.loads(arguments_json)
        Path(os.environ['FOOTWORK_SAVE_DIAGNOSTIC_PATH']).write_text(json.dumps(result, indent=2) + '\n')
    return outcome


cd.CuaDriver.call_tool = recorded
harness, *args = sys.argv[1:]
sys.argv = [harness, *args]
runpy.run_path(harness, run_name='__main__')
