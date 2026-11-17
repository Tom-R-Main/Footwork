"""One fault matrix across every infobar evidence consumer; no OS input."""
import copy
import hashlib
import sys

import pytest

from tests import test_session_scenarios as scenarios
from tests.test_native_infobar import infobar_world, receipt
from tests.test_native_infobar_delivery import start

fw = scenarios.fw
world = scenarios.world
STATES = ['confirmed', 'no_send', 'ack_only', 'unacknowledged']
FAULTS = ['session_wrong', 'session_bool', 'error_wrong', 'error_list',
          'boot_wrong', 'pid_float', 'operation_wrong', 'observation_wrong',
          'dispatch', 'count', 'basis', 'delivery', 'driver_delivery', 'route']


def natural(world, fw, monkeypatch, tmp_path, scenario):
    from jevdual import ax
    _, _, alert, _, _, _, attempts = infobar_world(world, monkeypatch, disappear=scenario != 'ack_only')
    if scenario == 'unacknowledged':
        press = sys.modules['ApplicationServices'].AXUIElementPerformAction
        def unack(el, action):
            press(el, action)
            return -25202
        monkeypatch.setattr(sys.modules['ApplicationServices'], 'AXUIElementPerformAction', unack)
    authority = start(fw, monkeypatch, tmp_path, True)
    if scenario == 'no_send':
        press = ax.press_infobar
        def refuse(*args, **kwargs):
            alert['_errors'] = {'AXSubrole': -25202}
            return press(*args, **kwargs)
        monkeypatch.setattr(ax, 'press_infobar', refuse)
    return authority, attempts


def corrupt(projection, fault):
    if fault == 'session_wrong': projection['session_id'] = 'another-session'
    elif fault == 'session_bool': projection['session_id'] = False
    elif fault == 'error_wrong': projection['error'] = 'another-error'
    elif fault == 'error_list': projection['error'] = []
    elif fault == 'boot_wrong': projection['binding']['boot'] = 'another-boot'
    elif fault == 'pid_float': projection['binding']['pid'] = float(projection['binding']['pid'])
    elif fault == 'operation_wrong': projection['operation_id'] = 'another-operation'
    elif fault == 'observation_wrong': projection['observation'] = 'another-observation'
    else:
        d = projection['native_delivery']
        if fault == 'dispatch': d['dispatched'] = not d['dispatched']
        elif fault == 'count': d['delivered_count'] = 1 if d['delivered_count'] != 1 else 0
        elif fault == 'basis': d['delivery_basis'] = 'sdk_delivery_count'
        elif fault == 'delivery': d['delivery'] = 'background'
        elif fault == 'driver_delivery': d['driver_delivery'] = 'background'
        elif fault == 'route': d['route'] = 'mouse'
        else: raise AssertionError(fault)


@pytest.mark.parametrize('boundary', ['producer', 'retention', 'retained', 'presentation'])
@pytest.mark.parametrize('scenario', STATES)
@pytest.mark.parametrize('fault', FAULTS)
def test_same_fault_matrix_at_every_consumer(world, fw, monkeypatch, tmp_path, boundary, scenario, fault):
    from jevdual import operator_evidence, session
    from jevdual.operator_evidence import EvidenceError, canonical
    from jevdual.session_operations import SessionOperations
    authority, attempts = natural(world, fw, monkeypatch, tmp_path, scenario)
    originals = []
    if boundary in ('producer', 'retention'):
        original = operator_evidence.execution_record
        def inject(*args, **kwargs):
            if boundary == 'producer':
                kwargs['projection'] = copy.deepcopy(kwargs['projection'])
                corrupt(kwargs['projection'], fault)
                return original(*args, **kwargs)
            rec = copy.deepcopy(original(*args, **kwargs))
            # Separate binding aliases: change only the projection copy.
            rec['projection'] = copy.deepcopy(rec['projection'])
            corrupt(rec['projection'], fault)
            return rec
        monkeypatch.setattr(operator_evidence, 'execution_record', inject)
    elif boundary == 'retained':
        original = SessionOperations.record_execution
        def inject(self, op_id, capsule):
            original(self, op_id, capsule)
            changed = copy.deepcopy(capsule)
            changed['projection'] = copy.deepcopy(changed['projection'])
            corrupt(changed['projection'], fault)
            body = canonical(changed)
            # Fixture-only storage fault with a matching digest: the semantic
            # read/settlement guard, not a checksum mismatch, must decide.
            self._db.execute('UPDATE operator_execution_receipts SET body=?,digest=? WHERE operation=?',
                             (body, hashlib.sha256(body.encode()).hexdigest(), op_id))
        monkeypatch.setattr(SessionOperations, 'record_execution', inject)
    else:
        original = session._outside_receipt
        def inject(r, pending, **kwargs):
            originals.append(copy.deepcopy(pending['execution_receipt']))
            pending['execution_receipt'] = copy.deepcopy(pending['execution_receipt'])
            inner = pending['execution_receipt']['projection']
            inner['binding'] = copy.deepcopy(inner['binding'])
            corrupt(inner, fault)
            return original(r, pending, **kwargs)
        monkeypatch.setattr(session, '_outside_receipt', inject)
    code, _, _ = fw('do', 'click', '-3', '--token', 'matrix')
    assert len(attempts) == (0 if scenario == 'no_send' else 1)
    assert all(name == 'bring_to_front' for name, _ in world.tool_calls)
    with SessionOperations(authority) as ops:
        op = ops.status()[-1]
        status = ops.receipt(op)
        if boundary == 'retained':
            with pytest.raises(EvidenceError): ops._retained_execution(op)
            with pytest.raises(EvidenceError): ops.finish_from_execution(op.id)
            reconciled = ops._reconcile_execution(op.id)
            assert reconciled.state == 'unknown' and reconciled.disposition == 'unknown'
        elif boundary in ('producer', 'retention'):
            assert ops._retained_execution(op) is None
        else:
            assert ops._retained_execution(op) == originals[0]
    if boundary == 'presentation':
        assert code == 0 and receipt(fw)['effect'] == 'unverifiable'
        expected = {'confirmed': ('final', 'applied', 'sent'), 'no_send': ('final', 'not_sent', 'not_sent'),
                    'ack_only': ('unknown', 'unknown', 'sent'), 'unacknowledged': ('unknown', 'unknown', 'ambiguous')}
        assert (status['state'], status['disposition'], status['phase']) == expected[scenario]
    else:
        assert code != 0
        assert (status['state'], status['disposition'], status['phase']) == ('unknown', 'unknown', 'ambiguous')
    before = len(attempts)
    fw('do', 'click', '-3', '--token', 'matrix')
    assert len(attempts) == before
    if boundary != 'presentation' or scenario in ('ack_only', 'unacknowledged'):
        fresh = fw('do', 'click', '-3', '--token', 'fresh-matrix')
        assert fresh[0] != 0 and 'unresolved' in fresh[2] and len(attempts) == before


@pytest.mark.parametrize('scenario', STATES)
def test_omitting_durable_shared_check_reproduces_bad_retention(world, fw, monkeypatch, tmp_path, scenario):
    from jevdual import operator_evidence
    from jevdual.session_operations import SessionOperations
    authority, attempts = natural(world, fw, monkeypatch, tmp_path, scenario)
    original_check = operator_evidence._infobar_provenance_agreement
    skipped = []
    def omit_durable(copies, pid, window_id):
        if len(copies) == 2 and copies[0].get('kind') == 'execution':
            skipped.append(True)
            return
        return original_check(copies, pid, window_id)
    monkeypatch.setattr(operator_evidence, '_infobar_provenance_agreement', omit_durable)
    original = operator_evidence.execution_record
    def corrupt_return(*args, **kwargs):
        rec = copy.deepcopy(original(*args, **kwargs))
        rec['projection']['session_id'] = False
        return rec
    monkeypatch.setattr(operator_evidence, 'execution_record', corrupt_return)
    assert fw('do', 'click', '-3', '--token', 'omit-check')[0] == 0
    with SessionOperations(authority) as ops:
        op = ops.status()[-1]
        retained = ops._retained_execution(op)
        assert retained['projection']['session_id'] is False
    assert skipped and len(attempts) == (0 if scenario == 'no_send' else 1)


@pytest.mark.parametrize('scenario', STATES)
@pytest.mark.parametrize('omitted', ['none', 'session_id', 'error', 'binding'])
def test_historical_omissions_remain_retained_with_placeholder_limit(world, fw, monkeypatch, tmp_path, scenario, omitted):
    from jevdual import operator_evidence
    from jevdual.session_operations import SessionOperations
    authority, attempts = natural(world, fw, monkeypatch, tmp_path, scenario)
    original = operator_evidence.execution_record
    def omit(*args, **kwargs):
        rec = copy.deepcopy(original(*args, **kwargs))
        rec['projection']['session_id'] = rec['session_id']
        if omitted != 'none': rec['projection'].pop(omitted, None)
        return rec
    monkeypatch.setattr(operator_evidence, 'execution_record', omit)
    assert fw('do', 'click', '-3', '--token', 'historical')[0] == 0
    with SessionOperations(authority) as ops:
        op = ops.status()[-1]
        assert ops._retained_execution(op) is not None
        status = ops.receipt(op)
    assert len(attempts) == (0 if scenario == 'no_send' else 1)
    expected = {'confirmed': ('final', 'applied'), 'no_send': ('final', 'not_sent')}.get(scenario, ('unknown', 'unknown'))
    assert (status['state'], status['disposition']) == expected
    # Existing admission-placeholder merge causes a conservative false negative
    # when the successful returned projection omits error. Explicitly deferred.
    effect = {'confirmed': 'confirmed', 'no_send': 'refused'}.get(scenario, 'unverifiable')
    if scenario == 'confirmed' and omitted == 'error': effect = 'unverifiable'
    assert receipt(fw)['effect'] == effect
