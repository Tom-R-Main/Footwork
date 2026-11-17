"""Public CLI -> typed wire -> actual Rust row adapter; only AX reads/press are simulated."""
import sys
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
    from jevdual import ax, posture
    from jevdual.effectors import cua

    from tests.test_posture import Activity

    monkeypatch.setattr(posture, "MacActivity", lambda: Activity(idle=60, fronts=(77,)))
    monkeypatch.setattr(ax, "raise_window", lambda *args: None)
    monkeypatch.setattr(ax, "focused_window_id", lambda pid: 40335)

    row_world(world, monkeypatch, variant)
    # The recorded calculator fixture carries its historical PID; this synthetic
    # SDK instance and actual row graph are bound to the fixture process 77.
    world.base["pid"] = 77
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
            # Production discovery withholds metadata on refusal. This must not
            # become a fixture exception masquerading as a targeting refusal.
            if not observed.get('binding'):
                row.pop('expected_row', None)
                continue
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
    assert len(offered) == 2, _state(fw)
    assert offered[0]['native_row_control']['key_value'] == 'TASK-0'
    result = fw('do', 'click', 'section:Task ID=TASK-0::combobox:Open menu',
                *(['--token', 'row-contract'] if durable else []))
    assert result[0] == 0, result
    assert sent == [940], result
    assert last_receipt(fw)['effect'] == 'unverifiable'


def test_tokenless_row_stays_unavailable(world, fw, monkeypatch):
    _graph, sent = sdk_row_world(world, monkeypatch, 'tokenless')
    assert fw('start', 'Open TASK-0', '--app', 'Calculator')[0] == 0
    assert not [c for c in _state(fw)['last_candidates'] if c['label'] == 'Open menu']
    assert fw('do', 'click', 'section:Task ID=TASK-0::combobox:Open menu')[0] != 0
    assert not sent


def last_receipt(fw):
    import json
    return [json.loads(line) for line in (fw.session / 'session.jsonl').read_text().splitlines()
            if json.loads(line)['kind'] == 'receipt'][-1]


def start_row(fw, monkeypatch, tmp_path, durable):
    if durable:
        from jevdual.session import SessionState
        authority = _durable_start(fw, monkeypatch, tmp_path)
        state = SessionState.load(fw.session)
        state.posture = 'exclusive_desktop'
        state.save()
        return authority
    assert fw('start', 'Open TASK-0', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0


@pytest.mark.parametrize('durable', [False, True])
def test_row_metadata_downgrade_cannot_become_generic_confirmation(world, fw, monkeypatch, tmp_path, durable):
    from jevdual import operator_evidence, session
    from jevdual.session_operations import SessionOperations

    _graph, sent = sdk_row_world(world, monkeypatch, 'complete')
    authority = start_row(fw, monkeypatch, tmp_path, durable)
    original_click = world.click
    async def click(inp):
        result = await original_click(inp)
        world.toggles[990] = ['Unrelated UI update', '1']
        return result
    monkeypatch.setattr(world, 'click', click)

    def downgrade(p):
        p['target_identity'].pop('native_row_control')
        p.pop('native_readback', None)
        p['native_delivery']['delivery_basis'] = 'sdk_delivery_count'
        p['driver_effect'] = 'confirmed'

    if durable:
        original = operator_evidence.execution_record
        def corrupt(*args, **kwargs):
            rec = original(*args, **kwargs)
            downgrade(rec['projection'])
            rec['producer']['delivery_basis'] = 'sdk_delivery_count'
            rec['effect'] = 'confirmed'
            return rec
        monkeypatch.setattr(operator_evidence, 'execution_record', corrupt)
    else:
        original = session._outside_receipt
        def corrupt(r, pending, **kwargs):
            downgrade(pending)
            return original(r, pending, **kwargs)
        monkeypatch.setattr(session, '_outside_receipt', corrupt)
    result = fw('do', 'click', 'section:Task ID=TASK-0::combobox:Open menu',
                *(['--token', 'downgrade'] if durable else []))
    assert sent == [940]
    if durable:
        with SessionOperations(authority) as ops:
            op = ops.status()[-1]
            assert ops._retained_execution(op) is None
            status = ops.receipt(op)
        assert result[0] != 0 and status['state'] == 'unknown'
        fw('do', 'click', 'section:Task ID=TASK-0::combobox:Open menu', '--token', 'downgrade')
        assert sent == [940]
    else:
        assert result[0] == 0
        assert last_receipt(fw)['effect'] == 'unverifiable'


@pytest.mark.parametrize('durable', [False, True])
def test_row_default_exception_after_sdk_attempt_is_unknown(world, fw, monkeypatch, tmp_path, durable):
    from jevdual.native import NativeBridge, NativeBridgeError
    from jevdual.session_operations import SessionOperations
    _graph, sent = sdk_row_world(world, monkeypatch, 'complete')
    authority = start_row(fw, monkeypatch, tmp_path, durable)
    original = NativeBridge.act
    async def fail_after(self, *args, **kwargs):
        await original(self, *args, **kwargs)
        raise NativeBridgeError('late_error', 'reply lost after actual row press')
    monkeypatch.setattr(NativeBridge, 'act', fail_after)
    fw('do', 'click', 'section:Task ID=TASK-0::combobox:Open menu',
       *(['--token', 'late-error'] if durable else []))
    assert sent == [940]
    assert last_receipt(fw)['effect'] == 'unverifiable'
    if durable:
        with SessionOperations(authority) as ops:
            op = ops.status()[-1]
            assert ops._retained_execution(op) is None
            assert ops.receipt(op)['state'] == 'unknown'


@pytest.mark.parametrize('selector', ['Open menu', 'label:Open menu', 'combobox:Open menu', 'Open',
                                     'section:Task ID=TASK-0::Open menu', '940'])
@pytest.mark.parametrize('durable', [False, True])
def test_row_prior_selector_cannot_downgrade_to_ordinary_control(world, fw, monkeypatch, tmp_path, selector, durable):
    _graph, sent = sdk_row_world(world, monkeypatch, 'complete')
    start_row(fw, monkeypatch, tmp_path, durable)
    original = world.get_window_state
    async def ordinary_now(inp):
        snap = await original(inp)
        snap['elements'] = [e for e in snap['elements'] if e['element_index'] not in (941, 820, 821, 822)]
        for e in snap['elements']:
            e.pop('expected_row', None)
            if e['element_index'] == 810: e['label'] = 'Task ID=TASK-0'
        return snap
    monkeypatch.setattr(world, 'get_window_state', ordinary_now)
    original_click = world.click
    calls = []
    async def click(inp):
        calls.append(inp)
        return await original_click(inp)
    monkeypatch.setattr(world, 'click', click)
    fw('do', 'click', selector, *(['--token', 'stale-row'] if durable else []))
    assert not calls and not sent


@pytest.mark.parametrize('durable', [False, True])
@pytest.mark.parametrize('outcome', ['ack', 'sdk_refusal', 'unacknowledged', 'preinput_error', 'rpc_error'])
def test_row_dispatch_boundaries_keep_honest_receipts(world, fw, monkeypatch, tmp_path, durable, outcome):
    from jevdual.native import NativeBridge, NativeBridgeError
    from jevdual.session_operations import SessionOperations

    from tests.test_native_row_sdk import node
    graph, sent = sdk_row_world(world, monkeypatch, 'complete')
    authority = start_row(fw, monkeypatch, tmp_path, durable)
    if outcome == 'preinput_error':
        async def refuse(*args, **kwargs):
            raise NativeBridgeError('census_failed', 'synthetic unreadable current recipient')
        monkeypatch.setattr(NativeBridge, '_live', refuse)
    elif outcome == 'rpc_error':
        original = world.click
        async def lose_reply(inp):
            await original(inp)
            raise RuntimeError('synthetic lost reply')
        monkeypatch.setattr(world, 'click', lose_reply)
    elif outcome == 'sdk_refusal':
        original = world.click
        async def changed_recipient(inp):
            node(graph, 940)['enabled'] = False
            try:
                return await original(inp)
            finally:
                node(graph, 940)['enabled'] = True
        monkeypatch.setattr(world, 'click', changed_recipient)
    elif outcome == 'unacknowledged':
        original = probe
        def unack(data):
            if data.get('mode') == 'dispatch': data = {**data, 'press_error': 'AX action response lost'}
            return original(data)
        monkeypatch.setattr(sys.modules[__name__], 'probe', unack)
    result = fw('do', 'click', 'section:Task ID=TASK-0::combobox:Open menu',
                *(['--token', 'delivery-boundary'] if durable else []))
    assert result[0] == 0, result
    no_send = outcome in ('preinput_error', 'sdk_refusal')
    assert sent == ([] if no_send else [940])
    assert last_receipt(fw)['effect'] == ('refused' if no_send else 'unverifiable')
    if durable:
        with SessionOperations(authority) as ops:
            op = ops.status()[-1]
            assert ops._retained_execution(op) is not None
            status = ops.receipt(op)
        assert (status['state'], status['disposition']) == (('final', 'not_sent') if no_send else ('unknown', 'unknown'))
        fw('do', 'click', 'section:Task ID=TASK-0::combobox:Open menu', '--token', 'delivery-boundary')
        assert sent == ([] if no_send else [940])
