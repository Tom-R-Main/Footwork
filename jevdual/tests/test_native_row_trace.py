"""Offline bounded diagnostic retention; no driver or AX calls."""
import json
from types import SimpleNamespace

import pytest


def test_trace_missing_sdk_retention_is_explicit(tmp_path):
    from jevdual.row_trace import retain
    path = tmp_path / 'trace.json'
    retain(path, {'pid': 77, 'window_id': 9, 'row_trace_url': 'http://127.0.0.1:5176/tasks'},
           SimpleNamespace(pid=77, window_id=9, snapshot_id='s1', elements=[], row_trace_json=None), [])
    data = json.loads(path.read_text())
    assert data['status'] == 'missing_sdk_trace'
    assert data['input_performed'] is False
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('status', ['capture_refused', 'qualified', 'discovery_refused'])
def test_trace_preserves_actual_stage_and_projection(tmp_path, status):
    from jevdual.row_trace import retain
    path = tmp_path / 'trace.json'
    trace = {'version': 1, 'pid': 77, 'window_id': 9, 'scope_url': 'http://127.0.0.1:5176/tasks',
             'status': status, 'truncated': False, 'scope_matched': True,
             'graph': None, 'results': [], 'attachment': []}
    retain(path, {'pid': 77, 'window_id': 9, 'row_trace_url': trace['scope_url']},
           SimpleNamespace(pid=77, window_id=9, snapshot_id='s1', elements=[], row_trace_json=json.dumps(trace)), [])
    data = json.loads(path.read_text())
    assert data['sdk'] == trace
    assert data['snapshot_id'] == 's1'
    assert data['status'] == 'retained'


def test_trace_oversize_and_existing_artifact_never_silently_succeed(tmp_path):
    from jevdual.row_trace import retain, MAX_BYTES
    path = tmp_path / 'trace.json'
    snap = SimpleNamespace(pid=77, window_id=9, snapshot_id='s1', elements=[], row_trace_json='x' * (MAX_BYTES + 1))
    retain(path, {'pid': 77, 'window_id': 9, 'row_trace_url': 'http://127.0.0.1:5176/tasks'}, snap, [])
    data = json.loads(path.read_text())
    assert data['status'] == 'sdk_trace_oversize' and data['truncated']
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        retain(path, {}, snap, [])
    assert path.read_bytes() == before
