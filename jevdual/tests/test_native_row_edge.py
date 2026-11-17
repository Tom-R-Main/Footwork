"""Scoped failure evidence uses synthetic hop operands, never a live Chrome graph."""
import json

import pytest

from jevdual.row_trace import retain


@pytest.mark.parametrize('case,want', [
    ('empty', 'absent_at_read'), ('absent', 'absent_at_read'),
    ('equal', 'raw_match_lost'), ('changed', 'changed_parent'),
    ('partial', 'unknown'), ('malformed', None), ('binding', None),
])
def test_failed_hop_retention(tmp_path, case, want):
    url = 'http://127.0.0.1:5176/tasks'
    edge = dict(root=0, outer=6, current=6, parent=2, first_parent=2,
                proof_parent=2, hop=1, raw_count=1, samples=[[5, False]], truncated=False)
    if case == 'empty':
        edge.update(raw_count=0, samples=[])
    if case == 'equal':
        edge['samples'][0][1] = True
    if case == 'changed':
        edge['first_parent'] = 4
    if case == 'partial':
        edge.update(truncated=True, samples=[])
    if case == 'malformed':
        edge['samples'][0][0] = 'private page content'
    trace = dict(version=1, pid=77, window_id=9, scope_url=url, scope_matched=False,
                 snapshot_id='s1', status='capture_refused', error='row parent/child mismatch',
                 node=6, failed_hop=edge, truncated=edge['truncated'])
    out = tmp_path / 'trace.json'
    retain(out, dict(pid=77, window_id=9, row_trace_url=url),
           dict(pid=77, window_id=9, snapshot_id='other' if case == 'binding' else 's1',
                row_trace_json=json.dumps(trace)), [])
    result = json.loads(out.read_text())
    observed = (result.get('sdk') or {}).get('failed_hop')
    if want is None:
        assert observed is None and 'private page content' not in out.read_text()
    else:
        assert observed == dict(edge, classification=want)
        assert result['sdk']['error'] == 'row parent/child mismatch'
        assert result['truncated'] is edge['truncated']
