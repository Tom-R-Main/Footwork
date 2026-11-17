"""Infobar retained provenance agreement through the public CLI and consumer."""
import copy

import pytest

from tests import test_session_scenarios as scenarios
from tests.test_native_infobar import infobar_world, outside, receipt
from tests.test_native_infobar_consumer import state_record
from tests.test_native_infobar_delivery import start

fw = scenarios.fw
world = scenarios.world


PUBLIC_CASES = [
    ('binding.boot', 'different-boot'), ('binding.start', 'different-start'),
    ('projection.binding.boot', 'different-boot'), ('projection.binding.start', 'different-start'),
    ('operation_id', 'different-operation'), ('projection.operation_id', 'different-operation'),
    ('observation', 'different-observation'), ('projection.observation', 'different-observation'),
    ('projection.binding.pid', 77.0), ('projection.binding.window_id', 40335.0),
    ('projection.binding.pid', 78), ('projection.binding.window_id', 40336),
    ('unchanged', None), ('no_optional_binding', None),
]


@pytest.mark.parametrize('path,value', PUBLIC_CASES)
def test_public_attached_provenance_agrees(world, fw, monkeypatch, tmp_path, path, value):
    from jevdual import session
    from jevdual.session_operations import SessionOperations

    *_, attempts = infobar_world(world, monkeypatch)
    authority = start(fw, monkeypatch, tmp_path, True)
    original = session._outside_receipt
    originals = []

    def consume(r, pending, **kwargs):
        if pending.get('target_id') == -3:
            originals.append(copy.deepcopy(pending['execution_receipt']))
            pending['execution_receipt'] = copy.deepcopy(pending['execution_receipt'])
            rec = pending['execution_receipt']
            rec['projection']['binding'] = copy.deepcopy(rec['projection']['binding'])
            if path == 'no_optional_binding':
                rec.pop('binding')
                rec['projection'].pop('binding')
            elif path != 'unchanged':
                obj = rec
                bits = path.split('.')
                for bit in bits[:-1]:
                    obj = obj[bit]
                obj[bits[-1]] = value
        return original(r, pending, **kwargs)

    monkeypatch.setattr(session, '_outside_receipt', consume)
    code, _, _ = fw('do', 'click', '-3', '--token', 'attached-provenance')
    assert code == 0 and len(attempts) == 1 and len(originals) == 1
    assert all(name == 'bring_to_front' for name, _ in world.tool_calls)
    with SessionOperations(authority) as ops:
        op = ops.status()[-1]
        assert ops._retained_execution(op) == originals[0]
        result = ops.receipt(op)
    assert result['state'] == 'final' and result['disposition'] == 'applied'
    expected = 'confirmed' if path in ('unchanged', 'no_optional_binding') else 'unverifiable'
    assert receipt(fw)['effect'] == expected


def copies(state='confirmed'):
    _, rec = copy.deepcopy(state_record(state))
    inner = rec['projection']
    # Add only consistent optional facts; natural public CLI coverage above
    # checks the real producer independently of this schema matrix.
    for key in ('binding', 'operation_id', 'observation', 'session_id', 'error'):
        inner[key] = copy.deepcopy(rec[key])
    outer = copy.deepcopy(inner)
    outer['execution_receipt'] = rec
    return outer, rec, inner


@pytest.mark.parametrize('which', [0, 1, 2])
@pytest.mark.parametrize('key,value', [
    ('binding', None), ('binding', {}),
    ('operation_id', None), ('operation_id', 1), ('operation_id', ''),
    ('observation', []), ('observation', ''),
    ('session_id', False), ('session_id', ''), ('error', {}),
    ('operation_id', 'other-operation'), ('observation', 'other-observation'),
    ('session_id', 'other-session'), ('error', 'other-error'),
])
def test_every_present_provenance_copy_is_typed_and_agrees(which, key, value):
    values = copies()
    values[which][key] = value
    assert outside(values[0]).effect == 'unverifiable'


@pytest.mark.parametrize('state', ['confirmed', 'no_send', 'unknown', 'ack_only', 'unacknowledged'])
@pytest.mark.parametrize('mask', range(8))
def test_consistent_optional_provenance_subsets_keep_effect(state, mask):
    values = copies(state)
    for i, value in enumerate(values):
        if not mask & (1 << i):
            for key in ('binding', 'operation_id', 'observation', 'session_id', 'error'):
                value.pop(key)
    expected = {'confirmed': 'confirmed', 'no_send': 'refused'}.get(state, 'unverifiable')
    assert outside(values[0]).effect == expected
