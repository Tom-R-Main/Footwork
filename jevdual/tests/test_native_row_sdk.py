"""Real SDK schema/adapter boundary; requires the independently compiled SSD probe."""
import json
import os
import subprocess
from pathlib import Path

import pytest

PROBE = os.environ.get("FOOTWORK_ROW_SDK_PROBE")
pytestmark = pytest.mark.skipif(not PROBE, reason="requires compiled pinned SDK row adapter probe")

PREDICATE = {
    "version": 2, "pid": 77, "window_id": 40335,
    "document_url": "https://example.test/tasks",
    "table_headers": ["Task ID", "Actions"], "row_values": ["TASK-0", "Open menu"], "key_column": "Task ID", "key_value": "TASK-0",
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
        n = {"id": id, "pid": 77, "window_id": 40335, "role": role, "name": '', "value": None, "url": None,
                 "parent": parent, "children": [], "rows": None, "columns": None, "header": None,
                 "enabled": None, "actions": [], "error": None}
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
    return {"root": 0, "complete": True, "nodes": nodes}


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


def node(graph, id):
    return next(n for n in graph['nodes'] if n['id'] == id)


def replace_id(graph, old, new):
    for n in graph['nodes']:
        if n['id'] == old: n['id'] = new
        for k in ('parent', 'header'):
            if n[k] == old: n[k] = new
        for k in ('children', 'rows', 'columns'):
            if n[k] is not None: n[k] = [new if value == old else value for value in n[k]]
    if graph['root'] == old: graph['root'] = new


@pytest.mark.parametrize('variant', [
    'predicate_missing', 'predicate_pid', 'predicate_window', 'predicate_document', 'predicate_key',
    'wrong_recipient', 'wrong_pid', 'wrong_window', 'document_changed', 'duplicate_key',
    'key_unreadable', 'peer_unreadable', 'peer_parent_unreadable', 'header_unreadable', 'columns_unreadable',
    'rows_unreadable', 'omitted_row', 'omitted_column', 'incomplete', 'disabled', 'missing_press',
    'row_replaced', 'document_replaced', 'table_replaced', 'key_replaced', 'column_replaced',
    'header_replaced', 'recipient_replaced', 'control_swap', 'cell_text_alias', 'duplicate_control',
    'tokenless', 'background', 'two_clicks', 'coordinate_fallback', 'focus_lost',
])
def test_actual_sdk_row_negatives_send_nothing(variant):
    import copy
    graph = graph_fixture()
    binding = probe({'mode': 'discover', 'graph': graph, 'pid': 77, 'window_id': 40335, 'recipient': 940})['binding']
    wire = click_wire(copy.deepcopy(PREDICATE)); recipient = 940
    if variant.startswith('predicate_'):
        field = variant.removeprefix('predicate_')
        if field == 'missing': wire.pop('expected_row')
        else: wire['expected_row'][{'pid':'pid', 'window':'window_id', 'document':'document_url', 'key':'key_value'}[field]] = 88 if field in ('pid','window') else 'wrong'
    elif variant == 'wrong_recipient': recipient = 941
    elif variant == 'wrong_pid': node(graph, 940)['pid'] = 88
    elif variant == 'wrong_window': node(graph, 940)['window_id'] = 99
    elif variant == 'document_changed': node(graph, 1)['url'] += '/other'
    elif variant == 'duplicate_key': node(graph, 21)['value'] = 'TASK-0'
    elif variant in ('key_unreadable','peer_unreadable','header_unreadable'):
        node(graph, {'key_unreadable':11, 'peer_unreadable':941, 'header_unreadable':4}[variant])['error'] = 'AX read error'
    elif variant == 'peer_parent_unreadable': node(graph, 941)['parent'] = None
    elif variant == 'columns_unreadable': node(graph, 2)['columns'] = None
    elif variant == 'rows_unreadable': node(graph, 2)['rows'] = None
    elif variant == 'omitted_row': node(graph, 2)['rows'].remove(20)
    elif variant == 'omitted_column': node(graph, 2)['columns'].remove(31)
    elif variant == 'incomplete': graph['complete'] = False
    elif variant == 'disabled': node(graph, 940)['enabled'] = False
    elif variant == 'missing_press': node(graph, 940)['actions'] = []
    elif variant.endswith('_replaced'):
        old = {'row':10, 'document':1, 'table':2, 'key':11, 'column':30, 'header':4, 'recipient':940}[variant.removesuffix('_replaced')]
        replace_id(graph, old, old + 1000)
        if old == 940: recipient = 1940
    elif variant == 'control_swap':
        node(graph, 12)['children'] = [941]; node(graph, 22)['children'] = [940]
        node(graph, 940)['parent'] = 22; node(graph, 941)['parent'] = 12
    elif variant == 'cell_text_alias':
        node(graph, 11)['value'] = None
        node(graph, 21)['value'] = None
        text = dict(node(graph, 11), id=2000, role='AXStaticText', parent=21, children=[], value='TASK-0')
        graph['nodes'].append(text); node(graph, 11)['children'] = [2000]; node(graph, 21)['children'] = [2000]
    elif variant == 'duplicate_control':
        duplicate = dict(node(graph, 940), id=1940)
        graph['nodes'].append(duplicate); node(graph, 12)['children'].append(1940)
    elif variant == 'tokenless': wire.pop('element_token')
    elif variant == 'background': wire['delivery_mode'] = 'background'
    elif variant == 'two_clicks': wire['count'] = 2
    elif variant == 'coordinate_fallback': wire.pop('element_token');wire.update(x=20,y=30)
    answer = probe({'mode':'dispatch', 'click':wire, 'binding':binding, 'graph':graph,
                    'recipient':recipient, 'admission_error':variant == 'focus_lost'})
    assert answer['presses'] == [], (variant, answer)
    if answer.get('schema_valid'):
        assert answer['receipt']['dispatched'] is False and answer['receipt']['effect'] == 'refused'


@pytest.mark.parametrize('variant', ['unchanged', 'rows_reordered', 'object_aliases', 'press_error'])
def test_actual_sdk_positive_and_unknown_controls(variant):
    graph = graph_fixture()
    binding = probe({'mode':'discover','graph':graph,'pid':77,'window_id':40335,'recipient':940})['binding']
    if variant == 'rows_reordered': node(graph, 2)['rows'].reverse(); node(graph, 2)['children'].reverse()
    if variant == 'object_aliases': node(graph, 30)['children'] += [11, 21]; node(graph, 2)['rows'] += [10]
    answer = probe({'mode':'dispatch','click':click_wire(),'binding':binding,'graph':graph,
                    'recipient':940,'press_error':variant == 'press_error'})
    assert answer['presses'] == [940]
    receipt = answer['receipt']
    assert receipt['effect'] == 'unverifiable' and receipt['dispatched'] is True
    assert receipt['acknowledged'] is (variant != 'press_error')
