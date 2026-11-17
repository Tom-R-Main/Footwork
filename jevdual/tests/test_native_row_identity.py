"""Opus wrong-row and ancestry regressions, actual Rust adapter; no live input."""
import copy

import pytest

from tests import test_native_row_sdk_cli as cli
from tests.test_native_row_sdk import node, probe
from tests.test_session_scenarios import _state

fw, world = cli.fw, cli.world
pytestmark = cli.pytestmark

URL = "https://example.test/tasks"
def base(headers=("Task ID", "Actions"), rows=(("TASK-0",), ("TASK-1",))):
    nodes = []
    def add(id, role, parent, **f):
        n = {"id": id, "pid": 77, "window_id": 40335, "role": role, "name": "", "value": None, "url": None,
             "parent": parent, "children": [], "rows": None, "columns": None, "header": None,
             "enabled": None, "actions": [], "error": None}
        n.update(f); nodes.append(n)
        if parent is not None:
            next(p for p in nodes if p["id"] == parent)["children"].append(id)
        return n
    add(0, "AXWindow", None); add(1, "AXWebArea", 0, url=URL)
    ncol = len(headers)
    table = add(2, "AXTable", 1, rows=[3], columns=[])
    add(3, "AXRow", 2)
    for c, h in enumerate(headers): add(4 + c, "AXCell", 3, name=h)
    colcells = {c: [4 + c] for c in range(ncol)}
    for r, vals in enumerate(rows):
        rid = 100 + r * 20
        table["rows"].append(rid); add(rid, "AXRow", 2)
        for c in range(ncol - 1):
            add(rid + 1 + c, "AXCell", rid, value=vals[c]); colcells[c].append(rid + 1 + c)
        act = rid + 1 + (ncol - 1)
        add(act, "AXCell", rid); colcells[ncol - 1].append(act)
        add(940 + r, "AXPopUpButton", act, name="Open menu", enabled=True, actions=["AXPress"])
    for c in range(ncol):
        add(30 + c, "AXColumn", 2, children=colcells[c], header=4 + c); table["columns"].append(30 + c)
    return {"root": 0, "complete": True, "nodes": nodes}



def discover(graph, recipient=940):
    return probe({'mode': 'discover', 'graph': graph, 'pid': 77, 'window_id': 40335, 'recipient': recipient})


@pytest.mark.parametrize('durable', [False, True])
@pytest.mark.parametrize('case', ['status_swap', 'row_number_shift'])
def test_full_row_prevents_locator_reassignment(world, fw, monkeypatch, tmp_path, case, durable):
    graph, sent = cli.sdk_row_world(world, monkeypatch, 'complete')
    first, values = ('Status', ('Open', 'Closed')) if case == 'status_swap' else ('#', ('1', '2'))
    headers = (first, 'Task ID', 'Actions')
    graph.update(base(headers, ((values[0], 'TASK-0'), (values[1], 'TASK-1'))))
    cli.start_row(fw, monkeypatch, tmp_path, durable)
    offered = [c for c in _state(fw)['last_candidates'] if c['label'] == 'Open menu']
    assert len(offered) == 2 and all(c.get('native_row_control') for c in offered)
    graph.update(base(headers, ((values[1], 'TASK-0'), (values[0], 'TASK-1'))))
    fw('do', 'click', f'section:{first}={values[0]}::combobox:Open menu',
       *(['--token', 'swap'] if durable else []))
    assert sent == [], 'a changed row must refuse, never select another task by its locator'


@pytest.mark.parametrize('durable', [False, True])
def test_unqualified_twin_remains_ambiguous(world, fw, monkeypatch, tmp_path, durable):
    base_click = world.click
    _, sent = cli.sdk_row_world(world, monkeypatch, 'complete')
    row_read, row_click = world.get_window_state, world.click
    async def read(inp):
        snap = await row_read(inp)
        for e in snap['elements']:
            if e['element_index'] == 941: e.pop('expected_row', None)
        return snap
    ordinary = []
    async def click(inp):
        if getattr(inp, 'expected_row', None) is None:
            ordinary.append(inp.position.element_token)
            return await base_click(inp)
        return await row_click(inp)
    monkeypatch.setattr(world, 'get_window_state', read)
    monkeypatch.setattr(world, 'click', click)
    cli.start_row(fw, monkeypatch, tmp_path, durable)
    assert 941 in _state(fw)['last_native_ambiguous']
    fw('do', 'click', '941', *(['--token', 'twin'] if durable else []))
    assert not ordinary and not sent


@pytest.mark.parametrize('fault', ['dual_parent', 'document_inside_row'])
def test_complete_reciprocal_ordered_ancestry(fault):
    graph = base()
    if fault == 'dual_parent':
        node(graph, 102)['children'].append(941)
        recipient = 941
    else:
        node(graph, 1).update(role='AXGroup', url=None)
        node(graph, 102)['children'] = [950]
        graph['nodes'].append(dict(node(graph, 1), id=950, role='AXWebArea', parent=102,
                                   url='https://ads.example/frame', children=[940]))
        node(graph, 940)['parent'] = 950
        recipient = 940
    assert not discover(graph, recipient).get('binding')


@pytest.mark.parametrize('change', ['value', 'cell_replaced', 'omitted_mapping'])
def test_non_key_row_cell_is_bound(change):
    graph = base(('Task ID', 'Title', 'Actions'), (('TASK-0', 'Alpha'), ('TASK-1', 'Beta')))
    binding = discover(graph)['binding']
    if change == 'value': node(graph, 102)['value'] = 'Changed'
    elif change == 'cell_replaced':
        from tests.test_native_row_sdk import replace_id
        replace_id(graph, 102, 1102)
    else: node(graph, 31)['children'].remove(102)
    result = probe({'mode': 'dispatch', 'graph': graph, 'binding': binding, 'recipient': 940,
                    'click': {'target': {'kind': 'window', 'pid': 77, 'window_id': 40335},
                              'element_token': 's00000001:940', 'delivery_mode': 'foreground',
                              'expected_row': binding['predicate']}})
    assert result['presses'] == []


@pytest.mark.parametrize('reorder', [False, True])
def test_complete_row_positive_control(reorder):
    graph = base(('Task ID', 'Title', 'Actions'), (('TASK-0', 'Alpha'), ('TASK-1', 'Beta')))
    binding = discover(graph)['binding']
    if reorder: node(graph, 2)['rows'].reverse()
    result = probe({'mode': 'dispatch', 'graph': graph, 'binding': binding, 'recipient': 940,
                    'click': {'target': {'kind': 'window', 'pid': 77, 'window_id': 40335},
                              'element_token': 's00000001:940', 'delivery_mode': 'foreground',
                              'expected_row': copy.deepcopy(binding['predicate'])}})
    assert result['presses'] == [940] and result['receipt']['effect'] == 'unverifiable'


@pytest.mark.parametrize('fault', ['missing', 'null', 'bool', 'short', 'long', 'wrong_key', 'old_version'])
def test_full_row_schema_refuses_incomplete_or_malformed_identity(fault):
    graph = base()
    binding = discover(graph)['binding']
    expected = copy.deepcopy(binding['predicate'])
    assert expected['row_values'] == ['TASK-0', 'Open menu']
    if fault == 'missing': expected.pop('row_values')
    elif fault == 'null': expected['row_values'] = None
    elif fault == 'bool': expected['row_values'][0] = True
    elif fault == 'short': expected['row_values'].pop()
    elif fault == 'long': expected['row_values'].append('extra')
    elif fault == 'wrong_key': expected['row_values'][0] = 'TASK-1'
    else: expected['version'] = 1
    result = probe({'mode': 'dispatch', 'graph': graph, 'binding': binding, 'recipient': 940,
                    'click': {'target': {'kind': 'window', 'pid': 77, 'window_id': 40335},
                              'element_token': 's00000001:940', 'delivery_mode': 'foreground',
                              'expected_row': expected}})
    assert result['presses'] == []
