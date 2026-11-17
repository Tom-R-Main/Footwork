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
    from jevdual.row_trace import MAX_BYTES, retain
    path = tmp_path / 'trace.json'
    snap = SimpleNamespace(pid=77, window_id=9, snapshot_id='s1', elements=[], row_trace_json='x' * (MAX_BYTES + 1))
    retain(path, {'pid': 77, 'window_id': 9, 'row_trace_url': 'http://127.0.0.1:5176/tasks'}, snap, [])
    data = json.loads(path.read_text())
    assert data['status'] == 'sdk_trace_oversize' and data['truncated']
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        retain(path, {}, snap, [])
    assert path.read_bytes() == before


def test_unscoped_failure_keeps_reason_but_never_graph_or_proofs(tmp_path):
    from jevdual.row_trace import retain
    trace = {'version': 1, 'pid': 77, 'window_id': 9, 'scope_url': 'http://127.0.0.1:5176/tasks',
             'status': 'capture_refused', 'scope_matched': False, 'truncated': False,
             'error': 'AXHeader has unsupported text type', 'node': 17, 'role': 'AXColumn',
             'reads': {'attribute_action_reads': 91, 'first_read_refusal': None},
             'graph': {'unscoped': 'must not retain'}, 'keys': ['unscoped']}
    path = tmp_path / 'trace.json'
    retain(path, {'pid': 77, 'window_id': 9, 'row_trace_url': trace['scope_url']},
           {'snapshot_id': 's1', 'row_trace_json': json.dumps(trace), 'elements': ['private']}, ['private'])
    data = json.loads(path.read_text())
    assert data['status'] == 'scope_unproven'
    assert data['sdk']['error'] == trace['error'] and data['sdk']['reads'] == trace['reads']
    assert 'graph' not in data['sdk'] and 'keys' not in data['sdk']
    assert 'typed_elements' not in data and 'candidates' not in data


@pytest.mark.parametrize('field,value', [('pid', 78), ('pid', 77.0), ('window_id', 9.0),
    ('scope_url', 'http://127.0.0.1:5176/other'), ('version', True)])
def test_mismatched_sdk_scope_is_explicitly_invalid(tmp_path, field, value):
    from jevdual.row_trace import retain
    trace = {'version': 1, 'pid': 77, 'window_id': 9, 'scope_url': 'http://127.0.0.1:5176/tasks',
             'status': 'qualified', 'scope_matched': True, 'truncated': False}
    request = {'pid': 77, 'window_id': 9, 'row_trace_url': trace['scope_url']}
    trace[field] = value
    path = tmp_path / 'trace.json'
    retain(path, request, {'row_trace_json': json.dumps(trace)}, [])
    assert json.loads(path.read_text())['status'] == 'invalid_sdk_trace'


def test_configuration_is_opt_in_exact_target_and_create_once(tmp_path, monkeypatch):
    from jevdual.row_trace import configuration
    monkeypatch.delenv('FOOTWORK_ROW_TRACE_CONFIG', raising=False)
    assert configuration(77, 9) is None
    path = tmp_path / 'config.json'
    output = tmp_path / 'result.json'
    data = {'pid': 77, 'window_id': 9, 'url': 'http://127.0.0.1:5176/tasks', 'output': str(output)}
    path.write_text(json.dumps(data))
    monkeypatch.setenv('FOOTWORK_ROW_TRACE_CONFIG', str(path))
    assert configuration(77, 9) == (output, data['url'])
    with pytest.raises(ValueError, match='target'): configuration(88, 9)
    output.write_text('prior')
    with pytest.raises(ValueError, match='new regular'): configuration(77, 9)


def test_projection_loss_and_count_truncation_are_visible(tmp_path):
    from jevdual.row_trace import retain
    trace = {'version': 1, 'pid': 77, 'window_id': 9, 'scope_url': 'http://127.0.0.1:5176/tasks',
             'status': 'qualified', 'scope_matched': True, 'truncated': False,
             'attachment': [{'index': 3, 'generated_proof_present': True, 'proof_present': True, 'token_present': True}]}
    path = tmp_path / 'trace.json'
    retain(path, {'pid': 77, 'window_id': 9, 'row_trace_url': trace['scope_url']},
           {'row_trace_json': json.dumps(trace), 'elements': [{'element_index': 3, 'element_token': 's1:3'}]},
           [{'id': 3, 'native_row_control': None}] * 1001)
    data = json.loads(path.read_text())
    assert data['sdk']['attachment'][0]['proof_present']
    assert data['typed_elements'][0]['expected_row'] is None
    assert data['candidates'][0]['native_row_control'] is None
    assert len(data['candidates']) == 1000 and data['truncated']


@pytest.mark.parametrize('fault', ['none', 'incomplete', 'read', 'header', 'duplicate'])
def test_actual_discovery_trace_preserves_result(fault):
    import os
    import subprocess

    from tests.test_native_row_sdk import graph_fixture, node
    executable = os.environ.get('FOOTWORK_ROW_TRACE_PROBE')
    if not executable:
        pytest.skip('requires compiled trace adapter')
    graph = graph_fixture()
    if fault == 'incomplete': graph['complete'] = False
    if fault == 'read': node(graph, 4)['error'] = 'AXHeader unreadable (-25212)'
    if fault == 'header': node(graph, 30)['header'] = None
    if fault == 'duplicate': node(graph, 21)['value'] = 'TASK-0'
    result = subprocess.run([executable], input=json.dumps({'mode': 'trace', 'graph': graph,
        'pid': 77, 'window_id': 40335, 'recipient': 940}), text=True, capture_output=True, check=True)
    data = json.loads(result.stdout)
    assert data['on'] == data['off']
    if fault == 'none': assert 'Ok' in data['on'] and data['keys'][-1]['qualified']
    else: assert 'Err' in data['on']


@pytest.mark.parametrize('enabled', [False, True])
def test_public_start_observes_once_and_retains_only_when_enabled(world, fw, monkeypatch, tmp_path, enabled):
    from tests.test_native_row_sdk import PROBE
    if not PROBE: pytest.skip('requires compiled SDK row adapter')
    from tests.test_native_row_sdk_cli import sdk_row_world
    from tests.test_session_scenarios import _state
    graph, sent = sdk_row_world(world, monkeypatch, 'complete')
    url = 'http://127.0.0.1:5176/tasks'
    graph['nodes'][1]['url'] = url
    path = tmp_path / 'trace.json'
    config = tmp_path / 'config.json'
    config.write_text(json.dumps({'pid': 77, 'window_id': 40335, 'url': url, 'output': str(path)}))
    if enabled: monkeypatch.setenv('FOOTWORK_ROW_TRACE_CONFIG', str(config))
    else: monkeypatch.delenv('FOOTWORK_ROW_TRACE_CONFIG', raising=False)
    original = world.get_window_state
    requests = []
    async def read(inp):
        requests.append(inp)
        snapshot = await original(inp)
        if getattr(inp, 'row_trace_url', None):
            snapshot['row_trace_json'] = json.dumps({'version': 1, 'pid': 77, 'window_id': 40335,
                'scope_url': url, 'scope_matched': True, 'status': 'qualified', 'truncated': False,
                'graph': graph, 'attachment': [{'index': 940, 'proof_present': True, 'token_present': True}]})
        return snapshot
    monkeypatch.setattr(world, 'get_window_state', read)
    code, out, err = fw('start', 'Observe exact row', '--app', 'Calculator', '--mode', 'exclusive_desktop')
    assert code == 0, (out, err)
    assert len(requests) == 1 and sent == []
    assert requests[0].qualify_rows is True and requests[0].full_output is True
    offered = [c for c in _state(fw)['last_candidates'] if c['label'] == 'Open menu']
    assert len(offered) == 2 and all(c['native_row_control'] is not None for c in offered)
    assert path.exists() is enabled
    if enabled:
        retained = json.loads(path.read_text())
        assert retained['status'] == 'retained'
        assert any(e['expected_row'] for e in retained['typed_elements'])
        assert any(c['native_row_control'] for c in retained['candidates'])


from tests import test_session_scenarios as scenarios

fw = scenarios.fw
world = scenarios.world


@pytest.mark.parametrize('fault', ['sdk_id', 'envelope_id', 'pid', 'window', 'missing_sdk_id', 'missing_envelope_id', 'matching'])
def test_review_trace_envelope_binding(tmp_path, fault):
    from jevdual.row_trace import retain
    trace = {'version': 1, 'pid': 77, 'window_id': 9, 'scope_url': 'http://127.0.0.1:5176/tasks',
             'status': 'qualified', 'scope_matched': True, 'truncated': False, 'snapshot_id': 's00000001'}
    snap = {'pid': 77, 'window_id': 9, 'snapshot_id': 's00000001', 'elements': []}
    if fault == 'sdk_id': trace['snapshot_id'] = 's00000002'
    if fault == 'envelope_id': snap['snapshot_id'] = 's00000002'
    if fault == 'pid': snap['pid'] = 88
    if fault == 'window': snap['window_id'] = 10
    if fault == 'missing_sdk_id': trace.pop('snapshot_id')
    if fault == 'missing_envelope_id': snap['snapshot_id'] = None
    snap['row_trace_json'] = json.dumps(trace)
    path = tmp_path / 'trace.json'
    retain(path, {'pid': 77, 'window_id': 9, 'row_trace_url': trace['scope_url']}, snap, [])
    data = json.loads(path.read_text())
    expected = 'retained' if fault == 'matching' else 'snapshot_unproven' if fault.startswith('missing') else 'invalid_sdk_trace'
    assert data['status'] == expected
    if expected != 'retained':
        assert not data.get('sdk') and 'typed_elements' not in data and 'candidates' not in data
