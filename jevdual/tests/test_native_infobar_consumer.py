"""Independent final infobar consumer controls; synthetic input only."""
import copy

import pytest
from jevdual.operator_evidence import EvidenceError, validate_execution

from tests import test_session_scenarios as scenarios
from tests.test_native_infobar import infobar_execution, infobar_world, ordinary_pending, outside, receipt
from tests.test_operator_evidence import BINDING
from tests.test_session_scenarios import _durable_start

fw = scenarios.fw
world = scenarios.world


def state_record(state):
    op, rec = infobar_execution()
    p = rec['projection']
    if state == 'no_send':
        rec.update(phase='not_sent', dispatched=False, effect='refused')
        rec['producer'].update(delivery_basis='qualified_gate', delivered_count=0)
        p.pop('native_readback')
        p.update(dispatched=False, driver_effect='not sent')
    elif state == 'unknown':
        rec.update(phase='ambiguous', dispatched=None, effect='unverifiable')
        rec['producer'].update(delivery_basis='unknown', delivered_count=None)
        p.pop('native_readback')
        p.update(dispatched=None, driver_effect='unverifiable')
    elif state == 'ack_only':
        rec['effect'] = p['driver_effect'] = 'unverifiable'
        p['native_readback']['after']['infobar_absent'] = False
        p['native_readback']['transition_observed'] = False
    elif state == 'unacknowledged':
        rec.update(phase='ambiguous', effect='unverifiable')
        rec['producer'].update(delivery_basis='unknown', delivered_count=None)
        p['driver_effect'] = 'unverifiable'
        p['native_readback']['press_acknowledged'] = False
    p['native_delivery'] = dict(dispatched=rec['dispatched'], **{k: rec['producer'][k] for k in ('delivery_basis', 'delivered_count')})
    return (op, rec)

@pytest.mark.parametrize('state', ['confirmed', 'ack_only', 'unacknowledged', 'no_send', 'unknown'])
def test_valid_states_keep_consumer_distinctions(state):
    op, rec = state_record(state)
    assert validate_execution(rec, op, binding=BINDING) == rec
    p = copy.deepcopy(rec['projection'])
    p['execution_receipt'] = copy.deepcopy(rec)
    assert outside(p).effect == {'confirmed': 'confirmed', 'no_send': 'refused'}.get(state, 'unverifiable')

@pytest.mark.parametrize('word', ['refused', 'not sent', 'not dispatched'])
def test_known_zero_send_words_require_consistent_facts(word):
    _op, rec = state_record('no_send')
    p = rec['projection']
    p['driver_effect'] = word
    assert outside(p).effect == 'refused'
    p['native_delivery']['delivered_count'] = 1
    assert outside(p).effect == 'unverifiable'
BAD = [('target_identity', None), ('target_identity', []), ('target_id', '-3'), ('target_id', -3.0), ('target_label', None), ('op', 'drag'), ('native_readback', None), ('native_readback', {}), ('native_delivery', None), ('native_delivery', []), ('target_identity.role', 'textbox'), ('target_identity.section', 'Web area'), ('target_identity.native_window_control', {}), ('target_identity.native_infobar_control.tab_hashes', [True]), ('target_identity.native_infobar_control.pid', True), ('native_readback.producer', 'footwork.ax.fullscreen'), ('native_readback.predicate', 'native_fullscreen_state_transition'), ('native_readback.schema_version', True), ('native_readback.extra', True), ('native_readback.press_acknowledged', 1), ('native_readback.transition_observed', 1), ('native_readback.before', None), ('native_readback.after', None), ('native_readback.after.tab_hashes', [True]), ('native_readback.after.infobar_absent', 1), ('native_readback.after.window_retained', False), ('native_readback.error', 'read error'), ('native_delivery.dispatched', None), ('native_delivery.dispatched', 1), ('native_delivery.delivered_count', True), ('native_delivery.delivered_count', 1.0), ('native_delivery.delivered_count', '1'), ('native_delivery.delivered_count', None), ('native_delivery.delivery_basis', 'sdk_delivery_count'), ('dispatched', 1), ('driver_effect', 'partial'), ('driver_effect', 'not sent')]

def put(p, path, value):
    parts = path.split('.')
    for k in parts[:-1]:
        p = p[k]
    p[parts[-1]] = value

@pytest.mark.parametrize('path,value', BAD)
def test_ordinary_malformed_evidence_never_confirms(path, value):
    p = ordinary_pending()
    put(p, path, value)
    assert outside(p).effect == 'unverifiable'

@pytest.mark.parametrize('key', ['op', 'target_id', 'target_label', 'target_identity', 'native_readback', 'native_delivery', 'dispatched', 'driver_effect'])
def test_ordinary_missing_fields_never_confirm(key):
    p = ordinary_pending()
    p.pop(key)
    assert outside(p).effect == 'unverifiable'

@pytest.mark.parametrize('state', ['confirmed', 'no_send', 'unknown'])
@pytest.mark.parametrize('field,value', [('dispatched', True), ('delivered_count', 1), ('delivery_basis', 'ax_infobar_disappearance_readback')])
def test_durable_rejects_nested_delivery_contradiction(state, field, value):
    op, rec = state_record(state)
    if state == 'confirmed':
        value = {'dispatched': False, 'delivered_count': 0, 'delivery_basis': 'qualified_gate'}[field]
    rec['projection']['native_delivery'][field] = value
    with pytest.raises(EvidenceError):
        validate_execution(rec, op, binding=BINDING)

@pytest.mark.parametrize('state', ['confirmed', 'no_send'])
@pytest.mark.parametrize('field', ['dispatched', 'delivered_count', 'delivery_basis'])
def test_ordinary_checks_delivery_inside_execution_projection(state, field):
    _op, rec = state_record(state)
    p = copy.deepcopy(rec['projection'])
    p['execution_receipt'] = copy.deepcopy(rec)
    bad = {'dispatched': False, 'delivered_count': 0, 'delivery_basis': 'qualified_gate'} if state == 'confirmed' else {'dispatched': True, 'delivered_count': 1, 'delivery_basis': 'ax_infobar_disappearance_readback'}
    p['execution_receipt']['projection']['native_delivery'][field] = bad[field]
    assert outside(p).effect == 'unverifiable'

@pytest.mark.parametrize('state', ['no_send', 'unknown', 'confirmed'])
def test_public_durable_cannot_settle_against_retained_nested_delivery(world, fw, monkeypatch, tmp_path, state):
    from jevdual import operator_evidence
    from jevdual.session import SessionState
    from jevdual.session_operations import SessionOperations
    *_, attempts = infobar_world(world, monkeypatch)
    authority = _durable_start(fw, monkeypatch, tmp_path)
    session = SessionState.load(fw.session)
    session.posture = 'exclusive_desktop'
    session.save()
    original = operator_evidence.execution_record

    def corrupt(*args, **kwargs):
        rec = original(*args, **kwargs)
        if rec['target'] == '-3':
            p = rec['projection']
            assert p['native_delivery']['dispatched'] is True
            assert p['native_readback']['press_acknowledged'] is True
            if state in ('no_send', 'unknown'):
                p.pop('native_readback')
                rec.update(phase='not_sent' if state == 'no_send' else 'ambiguous', dispatched=False if state == 'no_send' else None, effect='refused' if state == 'no_send' else 'unverifiable')
                rec['producer'].update(delivery_basis='qualified_gate' if state == 'no_send' else 'unknown', delivered_count=0 if state == 'no_send' else None)
                p.update(dispatched=rec['dispatched'], driver_effect='not sent' if state == 'no_send' else 'unverifiable')
            else:
                p['native_delivery'].update(dispatched=False, delivery_basis='qualified_gate', delivered_count=0)
        return rec
    monkeypatch.setattr(operator_evidence, 'execution_record', corrupt)
    try:
        code, _out, err = fw('do', 'click', '-3', '--token', 'contract-' + state)
    except EvidenceError:
        assert len(attempts) == 1
        return
    with SessionOperations(authority) as ops:
        rows = ops.status()
        result = ops.receipt(rows[-1])
        assert ops._retained_execution(rows[-1]) is None
    assert len(attempts) == 1
    assert code != 0 and 'infobar nested delivery contradicts execution' in err
    assert result['state'] == 'unknown' and result['disposition'] == 'unknown'
    assert result['phase'] == 'ambiguous'

@pytest.mark.parametrize('state', ['confirmed', 'no_send'])
def test_public_ordinary_checks_retained_inner_delivery(world, fw, monkeypatch, state):
    from jevdual import session
    *_, attempts = infobar_world(world, monkeypatch)
    assert fw('start', 'Dismiss', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0
    original = session._outside_receipt

    def consume(r, pending, **kwargs):
        if pending.get('target_id') == -3:
            assert pending['native_readback']['press_acknowledged'] is True
            assert pending['native_delivery']['delivered_count'] == 1
            positive = copy.deepcopy(pending['native_delivery'])
            if state == 'no_send':
                pending.pop('native_readback')
                pending.update(dispatched=False, driver_effect='not sent')
                pending['native_delivery'].update(dispatched=False, delivery_basis='qualified_gate', delivered_count=0)
            _op, execution = copy.deepcopy(infobar_execution())
            execution.update(dispatched=pending['dispatched'], effect='confirmed' if state == 'confirmed' else 'refused', phase='sent' if state == 'confirmed' else 'not_sent')
            execution['binding']['window_id'] = kwargs['window_id']
            execution['producer'].update(**{k: pending['native_delivery'][k] for k in ('delivery_basis', 'delivered_count')})
            execution['projection'] = copy.deepcopy(pending)
            execution['projection']['native_delivery'] = positive if state == 'no_send' else {'dispatched': False, 'delivery_basis': 'qualified_gate', 'delivered_count': 0}
            pending['execution_receipt'] = execution
        return original(r, pending, **kwargs)
    monkeypatch.setattr(session, '_outside_receipt', consume)
    assert fw('do', 'click', '-3')[0] == 0
    result = receipt(fw)
    assert len(attempts) == 1
    assert result['effect'] == 'unverifiable', result

@pytest.mark.parametrize('durable', [False, True])
@pytest.mark.parametrize('selector', ['Dismiss browser infobar', 'button:Dismiss browser infobar', 'label:Dismiss browser', 'section:Native browser::Dismiss'])
def test_previous_ambiguity_cannot_silently_acquire_fixed_authority(world, fw, monkeypatch, tmp_path, durable, selector):
    from jevdual.session import SessionState
    *_, attempts = infobar_world(world, monkeypatch)
    other = {'element_index': 555, 'role': 'AXButton', 'label': 'Dismiss browser infobar', 'enabled': True, 'actions': ['AXPress'], 'parent_index': 0, 'section': 'Native browser'}
    world.base['elements'].append(other)
    if durable:
        _durable_start(fw, monkeypatch, tmp_path)
        st = SessionState.load(fw.session)
        st.posture = 'exclusive_desktop'
        st.save()
    else:
        assert fw('start', 'Dismiss', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0
    world.base['elements'].remove(other)
    fw('do', 'click', selector, *(['--token', 'ambiguous-fixed'] if durable else []))
    assert not attempts and (not world.tool_calls)

@pytest.mark.parametrize('durable', [False, True])
@pytest.mark.parametrize('site', ['click_infobar_entry', 'act_require_fresh'])
def test_exception_path_genuine_no_send(world, fw, monkeypatch, tmp_path, durable, site):
    from jevdual.native import NativeBridge, NativeBridgeError
    *_, attempts = infobar_world(world, monkeypatch)
    if durable:
        from jevdual.session import SessionState
        _durable_start(fw, monkeypatch, tmp_path)
        state = SessionState.load(fw.session)
        state.posture = 'exclusive_desktop'
        state.save()
    else:
        assert fw('start', 'Dismiss', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0
    if site == 'click_infobar_entry':

        async def refuse(self, nm, id, cand):
            raise NativeBridgeError('target_changed', 'infobar identity does not match the bound native window')
        monkeypatch.setattr(NativeBridge, '_click_infobar', refuse)
    else:
        original = NativeBridge._require_fresh

        def fresh(self, nm, id, *a, **k):
            if id == -3:
                raise NativeBridgeError('target_changed', 'synthetic stale observation for -3')
            return original(self, nm, id, *a, **k)
        monkeypatch.setattr(NativeBridge, '_require_fresh', fresh)
    fw('do', 'click', '-3', *(['--token', 'exc'] if durable else []))
    r = receipt(fw)
    assert not attempts
    assert r['effect'] == 'refused'
