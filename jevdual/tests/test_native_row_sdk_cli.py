"""Public CLI -> typed wire -> actual Rust row adapter; only AX reads/press are simulated."""
from types import SimpleNamespace

import pytest

from tests import test_session_scenarios as scenarios
from tests.test_native_row_contract import row_world
from tests.test_native_row_sdk import PROBE, click_wire, graph_fixture, probe
from tests.test_session_scenarios import _durable_start, _state

fw = scenarios.fw
world = scenarios.world
pytestmark = pytest.mark.skipif(not PROBE, reason='requires compiled pinned SDK row adapter probe')


def sdk_row_world(world, monkeypatch, variant):
    from jevdual.effectors import cua

    row_world(world, monkeypatch, variant)
    graph = graph_fixture()
    held = {}
    sent = []
    original_read = world.get_window_state

    async def read(inp):
        snap = await original_read(inp)
        for row in snap['elements']:
            if row['element_index'] not in (940, 941) or not row.get('element_token'):
                continue
            observed = probe({'mode': 'discover', 'graph': graph, 'pid': 77,
                              'window_id': 40335, 'recipient': row['element_index']})
            assert observed.get('binding'), observed
            held[row['element_token']] = observed['binding']
            row['expected_row'] = observed['binding']['predicate']
        return snap

    async def click(inp):
        token = inp.position.element_token
        assert token in held, 'Only SDK-owned current token bindings can dispatch'
        expected = getattr(inp, 'expected_row', None)
        if isinstance(expected, SimpleNamespace):
            expected = vars(expected)
        wire = click_wire(expected)
        wire['element_token'] = token
        wire['target'] = {'kind': 'window', 'pid': inp.target.pid, 'window_id': inp.target.window_id}
        wire['delivery_mode'] = 'foreground' if str(inp.delivery_mode).endswith('FOREGROUND') else 'background'
        answer = probe({'mode': 'dispatch', 'click': wire, 'binding': held[token],
                        'graph': graph, 'recipient': int(token.split(':')[-1])})
        assert answer['schema_valid'], answer
        sent.extend(answer['presses'])
        receipt = answer['receipt']
        # Mirror the production typed projection. The Rust adapter supplies all
        # predicate/dispatch/acknowledgement facts; this fixture never approves them.
        return {'effect': receipt['effect'], 'route': 'accessibility',
                'delivery': {'mode': 'foreground', 'delivered_count': receipt['delivered_count']}
                if receipt['dispatched'] else None,
                'row_receipt': receipt, 'evidence': None}

    # The host's existing installed SDK lacks the new generated record. This
    # proxy only marshals fields; production Rust schema and validator above
    # still decide every dispatch. Final wheel contract checks are separate.
    original_sdk = cua._sdk
    class Types:
        def __getattr__(self, name):
            if name in ('ExpectedRow', 'ClickInput', 'GetWindowStateInput'):
                return lambda **fields: SimpleNamespace(**fields)
            return getattr(original_sdk(), name)
    monkeypatch.setattr(cua, '_sdk', lambda *args: Types())
    monkeypatch.setattr(world, 'get_window_state', read)
    monkeypatch.setattr(world, 'click', click)
    return graph, sent


@pytest.mark.parametrize('durable', [False, True])
@pytest.mark.parametrize('variant', ['complete', 'flattened'])
def test_public_cli_uses_actual_sdk_row_contract(world, fw, monkeypatch, tmp_path, durable, variant):
    from jevdual.session import SessionState
    _graph, sent = sdk_row_world(world, monkeypatch, variant)
    if durable:
        _durable_start(fw, monkeypatch, tmp_path)
        state = SessionState.load(fw.session); state.posture = 'exclusive_desktop'; state.save()
    else:
        assert fw('start', 'Open TASK-0', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0
    offered = [c for c in _state(fw)['last_candidates'] if c['label'] == 'Open menu']
    assert len(offered) == 2
    assert offered[0]['native_row_control']['key_value'] == 'TASK-0'
    result = fw('do', 'click', 'section:Task ID=TASK-0::combobox:Open menu',
                *(['--token', 'row-contract'] if durable else []))
    assert result[0] == 0, result
    assert sent == [940]
    assert _state(fw)['last_receipt']['effect'] == 'unverifiable'


def test_tokenless_row_stays_unavailable(world, fw, monkeypatch):
    _graph, sent = sdk_row_world(world, monkeypatch, 'tokenless')
    assert fw('start', 'Open TASK-0', '--app', 'Calculator')[0] == 0
    assert not [c for c in _state(fw)['last_candidates'] if c['label'] == 'Open menu']
    assert fw('do', 'click', 'section:Task ID=TASK-0::combobox:Open menu')[0] != 0
    assert not sent
