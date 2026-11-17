"""Recipient labels agree at every consumer; real Rust guard, simulated AX/input."""
import copy
import hashlib

import pytest
from jevdual import native_row, operator_evidence, session
from jevdual.operator_evidence import EvidenceError, canonical
from jevdual.session_operations import SessionOperations

from tests import test_native_row_sdk_cli as cli
from tests.test_native_row_sdk import node

fw, world = cli.fw, cli.world
pytestmark = cli.pytestmark
SELECTOR = 'section:Task ID=TASK-0::combobox:Open menu'
STATES = ['ack', 'sdk_refusal', 'preinput_error', 'rpc_error']
FAULTS = ['different', 'missing', 'null', 'bool']


def setup(world, fw, monkeypatch, tmp_path, state, durable):
    from jevdual.native import NativeBridge, NativeBridgeError
    graph, sent = cli.sdk_row_world(world, monkeypatch, 'complete')
    authority = cli.start_row(fw, monkeypatch, tmp_path, durable)
    original = world.click
    if state == 'sdk_refusal':
        async def refuse(inp):
            node(graph, 940)['enabled'] = False
            try:
                return await original(inp)
            finally:
                node(graph, 940)['enabled'] = True
        monkeypatch.setattr(world, 'click', refuse)
    elif state == 'rpc_error':
        async def lose_reply(inp):
            await original(inp)
            raise RuntimeError('synthetic lost reply')
        monkeypatch.setattr(world, 'click', lose_reply)
    elif state == 'preinput_error':
        async def refuse(*args, **kwargs):
            raise NativeBridgeError('census_failed', 'synthetic unreadable recipient')
        monkeypatch.setattr(NativeBridge, '_live', refuse)
    return authority, sent


def corrupt(projection, fault):
    if fault == 'missing':
        projection.pop('target_label')
    else:
        projection['target_label'] = {'different': 'OTHER RECIPIENT', 'null': None, 'bool': True}[fault]


def assert_presses(sent, state):
    assert sent == ([] if state in ('sdk_refusal', 'preinput_error') else [940])


@pytest.mark.parametrize('state', STATES)
@pytest.mark.parametrize('fault', FAULTS)
@pytest.mark.parametrize('boundary', ['producer', 'retained', 'presentation', 'attached'])
def test_label_agreement_at_durable_boundaries(world, fw, monkeypatch, tmp_path, state, fault, boundary):
    authority, sent = setup(world, fw, monkeypatch, tmp_path, state, True)
    originals, rejections = [], []
    if boundary == 'producer':
        original = operator_evidence.execution_record
        def inject(*args, **kwargs):
            corrupt(kwargs['projection'], fault)
            return original(*args, **kwargs)
        monkeypatch.setattr(operator_evidence, 'execution_record', inject)
    elif boundary == 'retained':
        original = SessionOperations.record_execution
        def inject(self, op_id, capsule):
            original(self, op_id, capsule)
            changed = copy.deepcopy(capsule)
            corrupt(changed['projection'], fault)
            body = canonical(changed)
            # Recomputed digest isolates semantic validation from integrity checks.
            self._db.execute('UPDATE operator_execution_receipts SET body=?,digest=? WHERE operation=?',
                             (body, hashlib.sha256(body.encode()).hexdigest(), op_id))
        monkeypatch.setattr(SessionOperations, 'record_execution', inject)
    else:
        original = session._outside_receipt
        def inject(r, pending, **kwargs):
            originals.append(copy.deepcopy(pending['execution_receipt']))
            pending['execution_receipt'] = copy.deepcopy(pending['execution_receipt'])
            corrupt(pending if boundary == 'presentation' else pending['execution_receipt']['projection'], fault)
            # Ack-only was already unverifiable: prove rejection, not just that same output.
            with pytest.raises(ValueError, match='row.*label'):
                native_row.projection_effect(pending, kwargs['row_intent'], 77, 40335)
            rejections.append(True)
            return original(r, pending, **kwargs)
        monkeypatch.setattr(session, '_outside_receipt', inject)
    result = fw('do', 'click', SELECTOR, '--token', 'labels')
    assert_presses(sent, state)
    with SessionOperations(authority) as ops:
        op = ops.status()[-1]
        status = ops.receipt(op)
        if boundary == 'producer':
            assert ops._retained_execution(op) is None
        elif boundary == 'retained':
            for read in (lambda: ops._retained_execution(op), lambda: ops.qualified_receipt(op),
                         lambda: ops.finish_from_execution(op.id)):
                with pytest.raises(EvidenceError, match='row.*label'):
                    read()
            reconciled = ops._reconcile_execution(op.id)
            assert (reconciled.state, reconciled.disposition) == ('unknown', 'unknown')
        else:
            assert rejections == [True]
            assert ops._retained_execution(op) == originals[0]
    if boundary in ('producer', 'retained'):
        assert result[0] == 7, result
        assert (status['state'], status['disposition']) == ('unknown', 'unknown')
    else:
        assert result[0] == 0, result
        assert cli.last_receipt(fw)['effect'] == 'unverifiable'
        assert status['state'] == ('final' if state in ('sdk_refusal', 'preinput_error') else 'unknown')
    fw('do', 'click', SELECTOR, '--token', 'labels')
    assert_presses(sent, state)


@pytest.mark.parametrize('state', STATES)
@pytest.mark.parametrize('fault', FAULTS)
def test_ordinary_label_contradiction_is_rejected(world, fw, monkeypatch, tmp_path, state, fault):
    _, sent = setup(world, fw, monkeypatch, tmp_path, state, False)
    original = session._outside_receipt
    rejected = []
    def inject(r, pending, **kwargs):
        corrupt(pending, fault)
        with pytest.raises(ValueError, match='row.*label'):
            native_row.projection_effect(pending, kwargs['row_intent'], 77, 40335)
        rejected.append(True)
        return original(r, pending, **kwargs)
    monkeypatch.setattr(session, '_outside_receipt', inject)
    assert fw('do', 'click', SELECTOR)[0] == 0
    assert rejected == [True]
    assert cli.last_receipt(fw)['effect'] == 'unverifiable'
    assert_presses(sent, state)


@pytest.mark.parametrize('state', STATES)
def test_valid_label_admission_and_retention_controls(world, fw, monkeypatch, tmp_path, state):
    authority, sent = setup(world, fw, monkeypatch, tmp_path, state, True)
    assert fw('do', 'click', SELECTOR, '--token', 'labels')[0] == 0
    with SessionOperations(authority) as ops:
        op = ops.status()[-1]
        rec = ops.qualified_receipt(op)
        prepared = ops._execution_preparation(op.id)
        admitted = native_row.admission(prepared)
        assert admitted['target_label'] == admitted['predicate']['name'] == 'Open menu'
        operator_evidence.validate_execution(rec, op, binding=ops._execution_binding(op.id), admitted_projection=prepared)
        for fault in FAULTS:
            damaged = copy.deepcopy(prepared)
            corrupt(damaged, fault)
            with pytest.raises(ValueError, match='row.*label'):
                native_row.admission(damaged)
        assert ops.qualified_receipt(op) == rec
    assert cli.last_receipt(fw)['effect'] == ('refused' if state in ('sdk_refusal', 'preinput_error') else 'unverifiable')
    assert fw('do', 'click', SELECTOR, '--token', 'labels')[0] == 0
    assert_presses(sent, state)
