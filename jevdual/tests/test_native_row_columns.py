"""All column alias exceptions require validated table ownership; no native input."""
import copy

import pytest

from tests import test_native_row_sdk_cli as cli
from tests.test_native_row_sdk import click_wire, graph_fixture, node, probe

fw, world = cli.fw, cli.world
pytestmark = cli.pytestmark


def add_alias(graph, parent, child):
    alias = copy.deepcopy(node(graph, 30))
    alias.update(id=8000, parent=parent, children=[4, child], header=4)
    graph['nodes'].append(alias)
    node(graph, parent)['children'].append(8000)


@pytest.mark.parametrize('parent', [1, 12, 2])
@pytest.mark.parametrize('child', [941, 21])
def test_unvalidated_column_alias_refuses_discovery_and_dispatch(parent, child):
    graph = graph_fixture()
    held = probe({'mode': 'discover', 'graph': graph, 'pid': 77, 'window_id': 40335, 'recipient': 941})['binding']
    add_alias(graph, parent, child)
    assert not probe({'mode': 'discover', 'graph': graph, 'pid': 77, 'window_id': 40335, 'recipient': 941}).get('binding')
    wire = click_wire(held['predicate']); wire['element_token'] = 's00000001:941'
    result = probe({'mode': 'dispatch', 'graph': graph, 'binding': held, 'recipient': 941, 'click': wire})
    assert result['presses'] == []


@pytest.mark.parametrize('durable', [False, True])
def test_public_cli_refuses_new_orphan_column_alias(world, fw, monkeypatch, tmp_path, durable):
    graph, sent = cli.sdk_row_world(world, monkeypatch, 'complete')
    cli.start_row(fw, monkeypatch, tmp_path, durable)
    add_alias(graph, 1, 941)
    result = fw('do', 'click', 'section:Task ID=TASK-1::combobox:Open menu', *(['--token', 'alias'] if durable else []))
    assert sent == []
    assert result[0] != 0
    assert 'AssertionError' not in ''.join(result[1:])


def test_legitimate_column_cell_aliases_stay_supported():
    graph = graph_fixture()
    node(graph, 30)['children'] += [4, 11, 21]
    held = probe({'mode': 'discover', 'graph': graph, 'pid': 77, 'window_id': 40335, 'recipient': 941})['binding']
    wire = click_wire(held['predicate']); wire['element_token'] = 's00000001:941'
    result = probe({'mode': 'dispatch', 'graph': graph, 'binding': held, 'recipient': 941, 'click': wire})
    assert result['presses'] == [941]
