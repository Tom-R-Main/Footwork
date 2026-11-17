"""Rich row content through production Rust adapter and public CLI; no live input."""
import copy

import pytest

from tests import test_native_row_sdk_cli as cli
from tests.fixtures.row_content import live_shape
from tests.test_native_row_identity import base, discover
from tests.test_native_row_sdk import click_wire, node, probe
from tests.test_session_scenarios import _state

fw, world = cli.fw, cli.world
pytestmark = cli.pytestmark


def dispatch(graph, binding):
    return probe({'mode': 'dispatch', 'graph': graph, 'binding': binding,
                  'recipient': 940, 'click': click_wire(binding['predicate'])})


@pytest.mark.parametrize('variant', [{}, {'link': True}, {'header_select': True}])
def test_live_shaped_content_is_qualified_but_not_an_effect(variant):
    graph = live_shape(**variant)
    binding = discover(graph).get('binding')
    assert binding, 'retained-shaped positive needs real row qualification'
    assert binding['predicate']['key_column'] == 'ID'
    assert binding['predicate']['key_value'] == 'NS-1001'
    result = dispatch(graph, binding)
    assert result['presses'] == [940]
    assert result['receipt']['effect'] == 'unverifiable'


@pytest.mark.parametrize('durable', [False, True])
@pytest.mark.parametrize('variant', ['complete', 'flattened'])
def test_public_cli_rich_row_identity_persists(world, fw, monkeypatch, tmp_path, durable, variant):
    graph, sent = cli.sdk_row_world(world, monkeypatch, variant)
    graph.update(live_shape())
    authority = cli.start_row(fw, monkeypatch, tmp_path, durable)
    offered = [c for c in _state(fw)['last_candidates'] if c.get('native_row_control')]
    assert len(offered) == 2
    assert fw('do', 'click', 'section:ID=NS-1001::combobox:Open menu',
              *(['--token', 'rich-row'] if durable else []))[0] == 0
    assert sent == [940]
    assert cli.last_receipt(fw)['effect'] == 'unverifiable'
    if durable:
        from jevdual.session_operations import SessionOperations
        with SessionOperations(authority) as ops:
            op = ops.status()[-1]
            record = ops.qualified_receipt(op)
            assert record['projection']['target_identity']['native_row_control']['row_values'] == offered[0]['native_row_control']['row_values']
        fw('do', 'click', 'section:ID=NS-1001::combobox:Open menu', '--token', 'rich-row')
        assert sent == [940]


@pytest.mark.parametrize('fault', ['text', 'text_order', 'image_name', 'checkbox_name', 'link_name',
                                  'unknown_role', 'unreadable', 'dual_parent', 'omitted_column',
                                  'nested_document', 'oversized', 'wrong_pid'])
@pytest.mark.parametrize('durable', [False, True])
def test_changed_or_incomplete_rich_row_never_dispatches(world, fw, monkeypatch, tmp_path, fault, durable):
    graph, sent = cli.sdk_row_world(world, monkeypatch, 'complete')
    graph.update(live_shape(link=fault == 'link_name'))
    cli.start_row(fw, monkeypatch, tmp_path, durable)
    binding = discover(graph).get('binding')
    assert binding, 'positive prerequisite prevents vacuous refusal'
    def first(role):
        return next(n for n in graph['nodes'] if n['role'] == role)
    if fault == 'text': node(graph, node(graph, 103)['children'][0])['value'] = 'Changed title'
    elif fault == 'text_order': node(graph, 103)['children'].reverse()
    elif fault == 'image_name': first('AXImage')['name'] = 'Changed icon'
    elif fault == 'checkbox_name': first('AXCheckBox')['name'] = 'Different row'
    elif fault == 'link_name': first('AXLink')['name'] = 'Different link'
    elif fault == 'unknown_role': first('AXImage')['role'] = 'AXSlider'
    elif fault == 'unreadable': first('AXImage')['error'] = 'attribute read failed'
    elif fault == 'dual_parent': node(graph, 103)['children'].append(940)
    elif fault == 'omitted_column': node(graph, 32)['children'].remove(103)
    elif fault == 'nested_document': node(graph, 103).update(role='AXWebArea', url='https://other.test')
    elif fault == 'oversized': first('AXImage')['name'] = 'x' * 2049
    else: first('AXImage')['pid'] = 78
    direct = dispatch(graph, binding)
    assert direct['presses'] == []
    fw('do', 'click', 'section:ID=NS-1001::combobox:Open menu',
       *(['--token', 'rich-fault'] if durable else []))
    assert sent == []


def test_plain_text_cannot_impersonate_encoded_rich_content():
    rich = live_shape()
    held = discover(rich).get('binding')
    assert held
    fingerprint = held['predicate']['row_values'][2]
    plain = copy.deepcopy(rich)
    children = node(plain, 103)['children']
    plain['nodes'] = [n for n in plain['nodes'] if n['id'] not in children]
    node(plain, 103).update(children=[], value=fingerprint)
    fresh = discover(plain).get('binding')
    assert fresh and fresh['predicate'] != held['predicate']
    assert dispatch(plain, held)['presses'] == []


def test_plain_row_positive_is_preserved():
    graph = base()
    held = discover(graph)['binding']
    assert held['predicate']['row_values'] == ['TASK-0', 'Open menu']
    assert dispatch(graph, held)['presses'] == [940]


def test_locator_only_rows_expose_documented_semantic_limit():
    # No recorded content distinguishes tasks after complete content reassignment.
    graph = base(('Status', 'Actions'), (('Open',), ('Closed',)))
    first = discover(graph, 940)['binding']['predicate']
    graph = base(('Status', 'Actions'), (('Closed',), ('Open',)))
    second = discover(graph, 941)['binding']['predicate']
    assert first == second  # A limit control, not a safety assertion or live authority.
