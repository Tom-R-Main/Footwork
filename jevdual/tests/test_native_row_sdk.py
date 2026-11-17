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


def graph_fixture():
    nodes = []
    def add(id, role, parent, **fields):
        n = dict(id=id, pid=77, window_id=40335, role=role, name='', value=None, url=None,
                 parent=parent, children=[], rows=None, columns=None, header=None,
                 enabled=None, actions=[], error=None)
        n.update(fields); nodes.append(n)
        if parent is not None:
            next(p for p in nodes if p['id'] == parent)['children'].append(id)
        return n
    add(0, 'AXWindow', None)
    add(1, 'AXWebArea', 0, url=PREDICATE['document_url'])
    table = add(2, 'AXTable', 1, rows=[3, 10, 20], columns=[30, 31])
    add(3, 'AXRow', 2)
    add(4, 'AXCell', 3, name='Task ID'); add(5, 'AXCell', 3, name='Actions')
    for row, key, popup in [(10, 'TASK-0', 940), (20, 'TASK-1', 941)]:
        add(row, 'AXRow', 2)
        add(row + 1, 'AXCell', row, value=key)
        add(row + 2, 'AXCell', row)
        add(popup, 'AXPopUpButton', row + 2, name='Open menu', enabled=True, actions=['AXPress'])
    add(30, 'AXColumn', 2, children=[4, 11, 21], header=4)
    add(31, 'AXColumn', 2, children=[5, 12, 22], header=5)
    assert table['columns'] == [30, 31]
    return dict(root=0, complete=True, nodes=nodes)


def click_wire(expected=PREDICATE):
    wire = {'target': {'kind': 'window', 'pid': 77, 'window_id': 40335},
            'element_token': 's00000001:940', 'delivery_mode': 'foreground'}
    if expected is not None: wire['expected_row'] = expected
    return wire


def test_actual_adapter_discovers_and_dispatches_expected_held_recipient():
    graph = graph_fixture()
    observed = probe({'mode': 'discover', 'graph': graph, 'pid': 77, 'window_id': 40335, 'recipient': 940})
    assert observed['binding']['predicate'] == PREDICATE, observed
    delivered = probe({'mode': 'dispatch', 'click': click_wire(), 'binding': observed['binding'],
                       'graph': graph, 'recipient': 940})
    assert delivered['presses'] == [940] and delivered['receipt']['acknowledged'] is True
    assert delivered['receipt']['effect'] == 'unverifiable'
