"""Real SDK schema/adapter boundary; requires the independently compiled SSD probe."""
import json
import os
import subprocess
from pathlib import Path

import pytest

PROBE = os.environ.get("FOOTWORK_ROW_SDK_PROBE")
pytestmark = pytest.mark.skipif(not PROBE, reason="requires compiled pinned SDK row adapter probe")

PREDICATE = {
    "version": 1, "pid": 77, "window_id": 40335,
    "document_url": "https://example.test/tasks",
    "table_headers": ["Task ID", "Actions"], "key_column": "Task ID", "key_value": "TASK-0",
    "role": "AXPopUpButton", "name": "Open menu", "action": "AXPress",
}


def probe(data):
    assert PROBE and Path(PROBE).is_file()
    process = subprocess.run([PROBE], input=json.dumps(data), text=True, capture_output=True, check=True)
    return json.loads(process.stdout)


def test_expected_row_is_admitted_by_actual_sdk_typed_schema():
    result = probe({"click": {
        "target": {"kind": "window", "pid": 77, "window_id": 40335},
        "element_token": "s00000001:0", "delivery_mode": "foreground", "expected_row": PREDICATE,
    }})
    assert result["schema_valid"], result
