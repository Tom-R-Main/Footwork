"""Fixed-purpose native infobar action through the real public operator CLI."""
import copy
import json
import sys

import pytest

from tests import test_session_scenarios as scenarios
from tests.test_session_scenarios import _durable_start, _fullscreen_actions, _state

fw = scenarios.fw
world = scenarios.world


def infobar_world(world, monkeypatch, *, disappear=True):
    win, _buttons, _ = _fullscreen_actions(world, monkeypatch)
    def node(role, parent, number, **attrs):
        n = dict(AXRole=role, AXParent=parent, AXWindow=win, AXChildren=[],
                 _pid=77, _hash=number, **attrs)
        parent['AXChildren'].append(n)
        return n
    container = node('AXGroup', win, 200, AXTitle='Infobar Container', AXSubrole='AXApplicationGroup')
    alert = node('AXGroup', container, 201, AXTitle='Infobar', AXSubrole='AXApplicationAlertDialog')
    close = node('AXButton', alert, 202, AXTitle='Close', AXDescription='Close', AXEnabled=True, _actions=['AXPress'])
    tabs = node('AXTabGroup', win, 203)
    tab = node('AXRadioButton', tabs, 204, AXSubrole='AXTabButton', AXTitle='Demo fixture')
    tab_close = node('AXButton', tab, 205, AXTitle='Close', AXDescription='Close', AXEnabled=True, _actions=['AXPress'])
    for idx in (99, 100):
        world.base['elements'].append({'element_index': idx, 'role': 'AXButton', 'label': 'Close',
                                       'enabled': True, 'actions': ['AXPress'], 'parent_index': 0})
    attempts = []
    def press(el, action):
        attempts.append(el)
        assert el is close and action == 'AXPress', 'tab/window Close must never be dispatched'
        if disappear:
            container['AXChildren'].remove(alert)
        return 0
    monkeypatch.setattr(sys.modules['ApplicationServices'], 'AXUIElementPerformAction', press)
    return win, container, alert, close, tab, tab_close, attempts


def test_infobar_public_cli_qualifies_persists_and_verifies(world, fw, monkeypatch):
    *_, attempts = infobar_world(world, monkeypatch)
    assert fw('start', 'Dismiss native infobar', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0
    candidates = _state(fw)['last_candidates']
    target = next((c for c in candidates if c['id'] == -3), None)
    assert target is not None, 'native infobar is missing from public look'
    assert target['native_infobar_control']['pid'] == 77
    assert fw('do', 'click', '-3')[0] == 0
    assert len(attempts) == 1
    rows = [json.loads(line) for line in (fw.session/'session.jsonl').read_text().splitlines()]
    receipt = next(row for row in rows if row['kind'] == 'receipt')
    assert receipt['effect'] == 'confirmed'
    assert receipt['action']['native_readback']['transition_observed'] is True


@pytest.mark.parametrize('change', ['wrong_pid', 'duplicate', 'unreadable', 'disabled', 'no_press', 'missing'])
def test_infobar_negative_controls_never_press(world, fw, monkeypatch, change):
    _win, container, alert, close, _tab, tab_close, attempts = infobar_world(world, monkeypatch)
    if change == 'wrong_pid': close['_pid'] = 88
    elif change == 'duplicate': alert['AXChildren'].append(dict(close))
    elif change == 'unreadable': tab_close['_errors'] = {'AXSubrole': -25202}
    elif change == 'disabled': close['AXEnabled'] = False
    elif change == 'no_press': close['_actions'] = []
    elif change == 'missing': container['AXChildren'] = []
    assert fw('start', 'Dismiss native infobar', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0
    assert not any(c['id'] == -3 for c in _state(fw)['last_candidates'])
    fw('do', 'click', '-3')
    assert not attempts


def receipt(fw):
    return next(json.loads(line) for line in (fw.session/'session.jsonl').read_text().splitlines()
                if json.loads(line)['kind'] == 'receipt')


@pytest.mark.parametrize('durable', [False, True])
@pytest.mark.parametrize('disappear', [False, True])
def test_infobar_ack_effect_and_durable_replay(world, fw, monkeypatch, tmp_path, durable, disappear):
    *_, attempts = infobar_world(world, monkeypatch, disappear=disappear)
    if durable:
        from jevdual.session import SessionState
        _durable_start(fw, monkeypatch, tmp_path)
        state = SessionState.load(fw.session)
        state.posture = 'exclusive_desktop'
        state.save()
    else:
        assert fw('start', 'Dismiss', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0
    words = ['do', 'click', 'Dismiss browser infobar'] + (['--token', 'infobar-once'] if durable else [])
    code, out, err = fw(*words)
    assert code == 0, (out, err)
    assert len(attempts) == 1 and all(name == 'bring_to_front' for name, _ in world.tool_calls)
    assert receipt(fw)['effect'] == ('confirmed' if disappear else 'unverifiable')
    if durable:
        assert receipt(fw)['action']['execution_receipt']['producer']['delivery_basis'] == 'ax_infobar_disappearance_readback'
        assert fw(*words)[0] == 0
        assert len(attempts) == 1


@pytest.mark.parametrize('change', ['wrong_pid', 'wrong_window', 'disabled', 'duplicate', 'missing',
                                    'unreadable', 'replaced', 'tab_missing', 'wrong_parent', 'wrong_subrole'])
def test_infobar_change_since_look_refuses_without_press(world, fw, monkeypatch, change):
    win, container, alert, close, tab, _tab_close, attempts = infobar_world(world, monkeypatch)
    assert fw('start', 'Dismiss', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0
    if change == 'wrong_pid': close['_pid'] = 88
    elif change == 'wrong_window': world.base['window_id'] = 999
    elif change == 'disabled': close['AXEnabled'] = False
    elif change == 'duplicate': alert['AXChildren'].append(dict(close))
    elif change == 'missing': container['AXChildren'] = []
    elif change == 'unreadable': alert['_errors'] = {'AXChildren': -25202}
    elif change == 'replaced': close['_hash'] = 900
    elif change == 'tab_missing': tab['AXParent']['AXChildren'] = []
    elif change == 'wrong_parent': close['AXParent'] = win
    elif change == 'wrong_subrole': close['AXSubrole'] = 'AXCloseButton'
    # A same-label SDK button must not inherit the vanished qualified selection.
    world.base['elements'].append({'element_index': 555, 'role': 'AXButton', 'label': 'Dismiss browser infobar',
                                    'enabled': True, 'actions': ['AXPress'], 'parent_index': 0})
    fw('do', 'click', 'Dismiss browser infobar')
    assert not attempts and not world.tool_calls


@pytest.mark.parametrize('error,admitted', [(-25205, True), (-25212, True), (-25202, False)])
def test_infobar_census_distinguishes_absence_from_read_error(world, fw, monkeypatch, error, admitted):
    *_, tab_close, attempts = infobar_world(world, monkeypatch)
    tab_close['_errors'] = {'AXSubrole': error}
    assert fw('start', 'Dismiss', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0
    assert any(c['id'] == -3 for c in _state(fw)['last_candidates']) is admitted
    fw('do', 'click', '-3')
    assert len(attempts) == int(admitted)


@pytest.mark.parametrize('change', ['tab_closed', 'tab_replaced', 'window_replaced', 'read_error', 'unacknowledged'])
def test_infobar_disappearance_alone_cannot_confirm(world, fw, monkeypatch, change):
    win, _container, _alert, _close, tab, _tab_close, attempts = infobar_world(world, monkeypatch)
    original = sys.modules['ApplicationServices'].AXUIElementPerformAction
    def press(el, action):
        original(el, action)
        if change == 'tab_closed': tab['AXParent']['AXChildren'] = []
        elif change == 'tab_replaced': tab['AXParent']['AXChildren'] = [dict(tab)]
        elif change == 'window_replaced': win['_hash'] = 888
        elif change == 'read_error': win['_errors'] = {'AXChildren': -25202}
        return -25202 if change == 'unacknowledged' else 0
    monkeypatch.setattr(sys.modules['ApplicationServices'], 'AXUIElementPerformAction', press)
    assert fw('start', 'Dismiss', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0
    fw('do', 'click', '-3')
    assert len(attempts) == 1 and receipt(fw)['effect'] == 'unverifiable'


@pytest.mark.parametrize('durable', [False, True])
@pytest.mark.parametrize('failure', ['census', 'preemption', 'replacement'])
def test_infobar_prepress_error_is_truthful_no_send(world, fw, monkeypatch, tmp_path, durable, failure):
    from jevdual import ax
    _win, _container, alert, close, _tab, _tab_close, attempts = infobar_world(world, monkeypatch)
    if durable:
        from jevdual.session import SessionState
        _durable_start(fw, monkeypatch, tmp_path)
        state = SessionState.load(fw.session); state.posture = 'exclusive_desktop'; state.save()
    else:
        assert fw('start', 'Dismiss', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0
    original = ax.press_infobar
    def press(*args, **kwargs):
        if failure == 'census': alert['_errors'] = {'AXSubrole': -25202}
        elif failure == 'replacement': alert['AXChildren'] = [dict(close)]
        else:
            raise RuntimeError('synthetic preemption before AX attempt')
        return original(*args, **kwargs)
    monkeypatch.setattr(ax, 'press_infobar', press)
    fw('do', 'click', '-3', *(['--token', 'refusal'] if durable else []))
    assert not attempts and all(name == 'bring_to_front' for name, _ in world.tool_calls)
    r = receipt(fw)
    assert r['effect'] == 'refused' and r['action']['dispatched'] is False
    assert not any(json.loads(line)['kind'] == 'stopped' for line in (fw.session/'session.jsonl').read_text().splitlines())


@pytest.mark.parametrize('words', [('click', 'Close'), ('click', '980'), ('click', '-3', 'extra'),
                                  ('scroll', '-3'), ('drag', '-3', 'to', '99')])
def test_infobar_does_not_relax_other_controls_or_operations(world, fw, monkeypatch, words):
    *_, attempts = infobar_world(world, monkeypatch)
    assert fw('start', 'Dismiss', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0
    fw('do', *words)
    assert not attempts and not world.tool_calls


@pytest.mark.asyncio
async def test_infobar_agent_bridge_never_offers_or_dispatches(world, monkeypatch):
    from jevdual.native import NativeBridge, NativeBridgeError
    *_, attempts = infobar_world(world, monkeypatch)
    agent = NativeBridge(world, 77, 40335)
    assert not any(c.native_infobar_control for c in (await agent.observe()).menu.candidates)
    operator = NativeBridge(world, 77, 40335, window_controls=True)
    menu = await operator.observe()
    with pytest.raises(NativeBridgeError):
        await operator.act(menu, 'click', -3)
    assert not attempts


def infobar_execution():
    import copy

    from tests.test_operator_evidence import make_execution
    op, record = make_execution()
    op.target = record['target'] = '-3'
    op.args = {'words': ['click', '-3']}
    control = {'pid': 77, 'window_id': 12, 'window_hash': 100, 'button_hash': 200, 'alert_hash': 201,
               'tab_hashes': [300], 'kind': 'native_infobar_close'}
    proof = {'schema_version': 1, 'producer': 'footwork.ax.infobar', 'predicate': 'native_infobar_disappearance',
             'before': control, 'after': {'pid': 77, 'window_id': 12, 'window_hash': 100, 'tab_hashes': [300],
                 'infobar_absent': True, 'window_retained': True, 'tabs_retained': True},
             'press_acknowledged': True, 'transition_observed': True}
    record['producer']['delivery_basis'] = 'ax_infobar_disappearance_readback'
    record['projection'].update(op='click', target_id=-3, target_label='Dismiss browser infobar', dispatched=True,
        target_identity={'role': 'button', 'label': 'Dismiss browser infobar', 'section': 'Native browser',
                         'native_infobar_control': copy.deepcopy(control)}, native_readback=proof)
    return op, record


def test_infobar_evidence_accepts_exact_disappearance():
    from tests.test_operator_evidence import BINDING, validate_execution
    op, record = infobar_execution()
    assert validate_execution(record, op, binding=BINDING) == record


@pytest.mark.parametrize('mutation', ['predicate', 'producer', 'schema', 'target', 'operation', 'selector',
                                    'pid', 'window', 'tab', 'identity', 'tab_bool', 'count', 'absent', 'ack',
                                    'window_retained', 'tabs_retained', 'unknown', 'basis', 'erase', 'dispatch'])
def test_infobar_evidence_rejects_contradictions_and_downgrade(mutation):
    from tests.test_operator_evidence import BINDING, EvidenceError, validate_execution
    op, record = infobar_execution()
    p = record['projection'];proof = p['native_readback']
    if mutation == 'predicate': proof['predicate'] = 'generic_close'
    elif mutation == 'producer': proof['producer'] = 'footwork.ax.fullscreen'
    elif mutation == 'schema': proof['schema_version'] = True
    elif mutation == 'target': op.target = record['target'] = '99'
    elif mutation == 'operation': op.move = record['move'] = 'drag'
    elif mutation == 'selector': op.args['words'] = ['click', 'Close']
    elif mutation == 'pid': proof['after']['pid'] = 88
    elif mutation == 'window': proof['after']['window_id'] = 55
    elif mutation == 'tab': proof['after']['tab_hashes'] = [301]
    elif mutation == 'identity': p['target_identity']['native_infobar_control']['button_hash'] = True
    elif mutation == 'tab_bool': proof['after']['tab_hashes'] = [True]
    elif mutation == 'count': record['producer']['delivered_count'] = 2
    elif mutation == 'absent': proof['after']['infobar_absent'] = False
    elif mutation == 'ack': proof['press_acknowledged'] = False
    elif mutation == 'window_retained': proof['after']['window_retained'] = False
    elif mutation == 'tabs_retained': proof['after']['tabs_retained'] = 1
    elif mutation == 'unknown': proof['additional'] = 'unsupported'
    elif mutation == 'basis': record['producer']['delivery_basis'] = 'sdk_delivery_count'
    elif mutation == 'erase':
        p.pop('target_identity');p.pop('native_readback');record['producer']['delivery_basis'] = 'sdk_delivery_count'
    elif mutation == 'dispatch': p['dispatched'] = False
    with pytest.raises(EvidenceError):
        validate_execution(record, op, binding=BINDING)


@pytest.mark.parametrize('count', [True, 2, None, 0])
def test_infobar_ordinary_receipt_requires_one_acknowledged_dispatch(count):
    from jevdual.receipts import Receipt
    from jevdual.session import _outside_receipt
    _op, record = infobar_execution()
    pending = record['projection']
    pending['native_delivery'] = {'delivery_basis': 'ax_infobar_disappearance_readback', 'delivered_count': count}
    # A generic visible diff must not confirm this fixed-purpose action.
    base = Receipt(1, ('click',), 'confirmed', 'generic visible diff')
    assert _outside_receipt(base, pending, pid=77, window_id=12).effect == 'unverifiable'


@pytest.mark.parametrize('durable', [False, True])
@pytest.mark.parametrize('selector', ['Dismiss browser infobar', 'button:Dismiss browser infobar',
                                      'label:Dismiss browser infobar', 'Dismiss browser',
                                      'button:Dismiss browser'])
def test_stale_infobar_selector_never_falls_through_to_sdk(world, fw, monkeypatch, tmp_path, selector, durable):
    from tests.fixtures.native_world import World
    _win, container, _alert, _close, _tab, _tab_close, attempts = infobar_world(world, monkeypatch)
    sdk_calls = []
    async def click(inp):
        sdk_calls.append(inp.position.element_token)
        return await World.click(world, inp)
    monkeypatch.setattr(world, 'click', click)
    if durable:
        from jevdual.session import SessionState
        _durable_start(fw, monkeypatch, tmp_path)
        state = SessionState.load(fw.session); state.posture = 'exclusive_desktop'; state.save()
    else:
        assert fw('start', 'Dismiss', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0
    assert any(c['id'] == -3 for c in _state(fw)['last_candidates'])
    container['AXChildren'] = []
    world.base['elements'].append({'element_index': 555, 'role': 'AXButton',
        'label': 'Dismiss browser infobar', 'enabled': True, 'actions': ['AXPress'], 'parent_index': 0})
    code, out, err = fw('do', 'click', selector, *(['--token', 'stale-alias'] if durable else []))
    assert not attempts
    assert not sdk_calls, json.dumps({'selector': selector, 'durable': durable, 'exit': code,
        'sdk_tokens': sdk_calls, 'presses': world.presses, 'stdout': out, 'stderr': err})


@pytest.mark.parametrize('drop', ['identity', 'identity_and_readback'])
def test_ordinary_reserved_target_cannot_downgrade_to_generic_receipt(drop):
    from jevdual.receipts import Receipt
    from jevdual.session import _outside_receipt
    _op, execution = infobar_execution()
    pending = copy.deepcopy(execution['projection'])
    pending['native_readback']['transition_observed'] = False
    pending['native_readback']['after']['infobar_absent'] = False
    pending.pop('target_identity')
    if drop == 'identity_and_readback':
        pending.pop('native_readback')
    pending['native_delivery'] = {'delivery_basis': 'sdk_delivery_count', 'delivered_count': 1}
    result = _outside_receipt(Receipt(1, ('click',), 'confirmed', 'generic visible diff'),
                              pending, pid=77, window_id=12)
    assert result.effect != 'confirmed', repr(result)




@pytest.mark.parametrize('phase', ['not_sent', 'ambiguous'])
def test_durable_positive_press_proof_cannot_be_relabelled_no_send_or_unknown(phase):
    from jevdual.operator_evidence import EvidenceError, validate_execution
    from tests.test_operator_evidence import BINDING
    op, record = infobar_execution()
    no_send = phase == 'not_sent'
    record.update(phase=phase, dispatched=False if no_send else None,
                  effect='refused' if no_send else 'unverifiable')
    record['projection'].update(dispatched=record['dispatched'], driver_effect=record['effect'])
    record['producer'].update(delivery_basis='qualified_gate' if no_send else 'unknown',
                              delivered_count=0 if no_send else None)
    with pytest.raises(EvidenceError):
        validate_execution(record, op, binding=BINDING)


@pytest.mark.parametrize('durable', [False, True])
def test_real_nsarray_children_offer_and_press_only_native_infobar(world, fw, monkeypatch, tmp_path, durable):
    Foundation = pytest.importorskip('Foundation')
    *_, attempts = infobar_world(world, monkeypatch)
    services = sys.modules['ApplicationServices']
    original = services.AXUIElementCopyAttributeValue
    def read(el, key, result):
        error, value = original(el, key, result)
        if key == 'AXChildren' and not error and value is not None:
            value = Foundation.NSArray.arrayWithArray_(value)
            assert not isinstance(value, (list, tuple))
        return error, value
    monkeypatch.setattr(services, 'AXUIElementCopyAttributeValue', read)
    if durable:
        from jevdual.session import SessionState
        _durable_start(fw, monkeypatch, tmp_path)
        state = SessionState.load(fw.session); state.posture = 'exclusive_desktop'; state.save()
    else:
        assert fw('start', 'Dismiss', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0
    assert any(c['id'] == -3 for c in _state(fw)['last_candidates'])
    assert fw('do', 'click', '-3', *(['--token', 'nsarray'] if durable else []))[0] == 0
    assert len(attempts) == 1 and receipt(fw)['effect'] == 'confirmed'


@pytest.mark.parametrize('collisions', [False, True])
def test_census_equality_work_is_bounded_without_trusting_hashes(world, monkeypatch, collisions):
    from jevdual import ax
    win, *_ = infobar_world(world, monkeypatch)
    win['AXChildren'] = [dict(AXRole='AXStaticText', AXParent=win, AXWindow=win,
                             _pid=77, _hash=10000 + (0 if collisions else i)) for i in range(2000)]
    comparisons = []
    original = ax.same_element
    def same(a, b):
        comparisons.append(1)
        return original(a, b)
    monkeypatch.setattr(ax, 'same_element', same)
    with pytest.raises(ax.AXError):
        ax.infobar_control(77, 40335)
    assert len(comparisons) < 10000


def test_infobar_observation_names_native_not_dom_identity(world, fw, monkeypatch):
    infobar_world(world, monkeypatch)
    assert fw('start', 'Dismiss', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0
    code, out, err = fw('look')
    assert code == 0, err
    line = next(line for line in out.splitlines() if 'Dismiss browser infobar' in line)
    assert 'native_infobar=' in line and 'dom_id=' not in line
