"""Fresh conformance probes. All input is the existing public CLI synthetic Mac."""
import copy

import pytest
from jevdual.operator_evidence import EvidenceError, validate_execution

from tests import test_session_scenarios as scenarios
from tests.test_native_infobar import infobar_world, outside, receipt
from tests.test_native_infobar_consumer import state_record
from tests.test_operator_evidence import BINDING
from tests.test_session_scenarios import _durable_start

fw = scenarios.fw
world = scenarios.world
FIELDS = [('delivery', 'background'), ('driver_delivery', 'background'), ('route', 'mouse')]

def start(fw, monkeypatch, tmp_path, durable):
    if durable:
        from jevdual.session import SessionState
        authority = _durable_start(fw, monkeypatch, tmp_path)
        st = SessionState.load(fw.session)
        st.posture = 'exclusive_desktop'
        st.save()
        return authority
    assert fw('start', 'Dismiss', '--app', 'Calculator', '--mode', 'exclusive_desktop')[0] == 0

@pytest.mark.parametrize('state', ['confirmed', 'no_send', 'unknown', 'ack_only', 'unacknowledged'])
def test_complete_valid_delivery_controls(state):
    op, rec = copy.deepcopy(state_record(state))
    p = rec['projection']
    p['native_delivery'].update(delivery='foreground', driver_delivery=None, route='accessibility' if state in ('confirmed', 'ack_only') else None)
    assert validate_execution(rec, op, binding=BINDING) == rec
    p['execution_receipt'] = copy.deepcopy(rec)
    assert outside(p).effect == {'confirmed': 'confirmed', 'no_send': 'refused'}.get(state, 'unverifiable')

@pytest.mark.parametrize('field', ['delivery', 'driver_delivery', 'route'])
@pytest.mark.parametrize('value', [False, 1, [], {}])
@pytest.mark.parametrize('consumer', ['ordinary', 'durable'])
def test_retained_delivery_requires_declared_types(field, value, consumer):
    op, rec = copy.deepcopy(state_record('confirmed'))
    rec['projection']['native_delivery'][field] = value
    if consumer == 'ordinary':
        assert outside(rec['projection']).effect == 'unverifiable'
    else:
        with pytest.raises(EvidenceError):
            validate_execution(rec, op, binding=BINDING)

@pytest.mark.parametrize('field,value', FIELDS)
@pytest.mark.parametrize('consumer', ['ordinary', 'ordinary_attached', 'durable'])
def test_public_cli_retained_delivery_agreement(world, fw, monkeypatch, tmp_path, consumer, field, value):
    from jevdual import operator_evidence, session
    from jevdual.session_operations import SessionOperations
    *_, attempts = infobar_world(world, monkeypatch)
    authority = start(fw, monkeypatch, tmp_path, consumer == 'durable')
    tag = consumer + '-' + field
    if consumer == 'durable':
        original = operator_evidence.execution_record

        def corrupt(*args, **kwargs):
            rec = original(*args, **kwargs)
            if rec['target'] == '-3':
                nd = rec['projection']['native_delivery']
                assert nd['delivery'] == 'foreground' and nd['driver_delivery'] is None
                assert nd['route'] == 'accessibility' and nd['delivered_count'] == 1
                nd[field] = value
            return rec
        monkeypatch.setattr(operator_evidence, 'execution_record', corrupt)
    else:
        original = session._outside_receipt

        def consume(r, pending, **kwargs):
            if pending.get('target_id') == -3:
                nd = pending['native_delivery']
                assert nd['delivery'] == 'foreground' and nd['driver_delivery'] is None
                assert nd['route'] == 'accessibility' and nd['delivered_count'] == 1
                if consumer == 'ordinary_attached':
                    _, rec = copy.deepcopy(state_record('confirmed'))
                    rec['producer'].update(**{k: nd[k] for k in ('delivery_basis', 'delivered_count')})
                    rec['binding']['window_id'] = kwargs['window_id']
                    rec['projection'] = copy.deepcopy(pending)
                    rec['projection']['native_delivery'][field] = value
                    pending['execution_receipt'] = rec
                else:
                    nd[field] = value
            return original(r, pending, **kwargs)
        monkeypatch.setattr(session, '_outside_receipt', consume)
    code, _stdout, _stderr = fw('do', 'click', '-3', *(['--token', tag] if consumer == 'durable' else []))
    assert len(attempts) == 1
    assert all((name == 'bring_to_front' for name, _ in world.tool_calls))
    if consumer == 'durable':
        with SessionOperations(authority) as ops:
            op = ops.status()[-1]
            retained = ops._retained_execution(op)
            result = ops.receipt(op)
        assert retained is None
        assert code != 0
        assert result['state'] == 'unknown' and result['disposition'] == 'unknown'
        assert result['phase'] == 'ambiguous'
    else:
        result = receipt(fw)
        assert code == 0
        assert result['effect'] == 'unverifiable'

@pytest.mark.parametrize('field', ['target_id', 'proof_schema', 'control_window'])
def test_public_ordinary_attached_inner_types(world, fw, monkeypatch, tmp_path, field):
    from jevdual import session
    *_, attempts = infobar_world(world, monkeypatch)
    start(fw, monkeypatch, tmp_path, False)
    original = session._outside_receipt

    def consume(r, pending, **kwargs):
        if pending.get('target_id') == -3:
            _, rec = copy.deepcopy(state_record('confirmed'))
            rec['binding']['window_id'] = kwargs['window_id']
            rec['projection'] = copy.deepcopy(pending)
            inner = rec['projection']
            if field == 'target_id':
                inner['target_id'] = -3.0
            elif field == 'proof_schema':
                inner['native_readback']['schema_version'] = True
            else:
                c = inner['target_identity']['native_infobar_control']
                c['window_id'] = float(c['window_id'])
            pending['execution_receipt'] = rec
        return original(r, pending, **kwargs)
    monkeypatch.setattr(session, '_outside_receipt', consume)
    code, _stdout, _stderr = fw('do', 'click', '-3')
    result = receipt(fw)
    assert len(attempts) == 1 and code == 0
    assert result['effect'] == 'unverifiable'

@pytest.mark.parametrize('durable', [False, True])
def test_default_bridge_error_after_fixed_marker_cannot_claim_no_attempt(world, fw, monkeypatch, tmp_path, durable):
    from jevdual.native import NativeBridge, NativeBridgeError
    from jevdual.session_operations import SessionOperations
    *_, attempts = infobar_world(world, monkeypatch)
    authority = start(fw, monkeypatch, tmp_path, durable)
    original = NativeBridge.act
    async def fail_after(self, *args, **kwargs):
        await original(self, *args, **kwargs)
        raise NativeBridgeError('synthetic_after_press', 'default error flag after actual fixed marker')
    monkeypatch.setattr(NativeBridge, 'act', fail_after)
    fw('do', 'click', '-3', *(['--token', 'marker-error'] if durable else []))
    assert len(attempts) == 1
    assert receipt(fw)['effect'] == 'unverifiable'
    if durable:
        with SessionOperations(authority) as ops:
            op = ops.status()[-1]
            assert ops._retained_execution(op) is None
            result = ops.receipt(op)
        assert result['state'] == 'unknown' and result['disposition'] == 'unknown'
        assert result['phase'] == 'ambiguous'


@pytest.mark.parametrize('path,value', [
    ('producer.name', 'sdk'), ('producer.version', True), ('producer.version', 2),
    ('move', 'drag'), ('target', '99'), ('target', -3),
    ('schema_version', '2'), ('protocol', True), ('kind', 'observation'), ('custody', 'held'),
    ('binding.pid', 88), ('binding.window_id', 12.0),
])
def test_attached_execution_provenance_and_binding_types(path, value):
    _op, rec = copy.deepcopy(state_record('confirmed'))
    p = copy.deepcopy(rec['projection']); p['execution_receipt'] = rec
    obj = rec
    keys = path.split('.')
    for key in keys[:-1]: obj = obj[key]
    obj[keys[-1]] = value
    assert outside(p).effect == 'unverifiable'
