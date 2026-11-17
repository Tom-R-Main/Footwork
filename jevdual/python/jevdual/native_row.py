"""Closed SDK-owned row predicates and delivery receipts; no AX or input endpoint."""
from __future__ import annotations

import json
from typing import Any

FIELDS = ('version', 'pid', 'window_id', 'document_url', 'table_headers', 'row_values', 'key_column', 'key_value', 'role', 'name', 'action')
RECEIPT_FIELDS = ('version', 'predicate', 'dispatched', 'acknowledged', 'delivered_count', 'effect', 'error')


def get(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, dict) else getattr(value, key, None)


def record(value: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    if isinstance(value, dict):
        if set(value) != set(fields):
            raise ValueError('unsupported row record fields')
        return dict(value)
    if value is None or any(not hasattr(value, key) for key in fields):
        raise ValueError('missing typed row record')
    return {key: getattr(value, key) for key in fields}


def predicate(value: Any) -> dict[str, Any]:
    row = record(value, FIELDS)
    headers = row['table_headers']
    values = row['row_values']
    if (type(row['version']) is not int or row['version'] != 2
            or any(type(row[k]) is not int or row[k] <= 0 for k in ('pid', 'window_id'))
            or any(not isinstance(row[k], str) or not row[k] or len(row[k].encode()) > 2048
                   for k in ('document_url', 'key_column', 'key_value', 'name'))
            or row['role'] not in ('AXButton', 'AXPopUpButton') or row['action'] != 'AXPress'
            or not isinstance(headers, list) or not 1 <= len(headers) <= 64
            or any(not isinstance(h, str) or len(h.encode()) > 2048 for h in headers)
            or headers.count(row['key_column']) != 1
            or not isinstance(values, list) or len(values) != len(headers)
            or any(not isinstance(v, str) or len(v.encode()) > 2048 for v in values)
            or values[headers.index(row['key_column'])] != row['key_value']):
        raise ValueError('invalid SDK row predicate')
    return row


def identity(value: Any) -> tuple[Any, ...] | None:
    try:
        row = predicate(value)
    except (ValueError, TypeError):
        return None
    return ('sdk_row', *(tuple(row[key]) if key in ('table_headers', 'row_values') else row[key] for key in FIELDS))


def section(row: dict[str, Any]) -> str:
    return row['key_column'] + '=' + row['key_value']


def same(a: Any, b: Any) -> bool:
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def receipt(value: Any, expected: Any) -> dict[str, Any]:
    proof = record(value, RECEIPT_FIELDS)
    row = predicate(proof['predicate'])
    if not same(row, predicate(expected)):
        raise ValueError('row delivery belongs to another recipient')
    proof['predicate'] = row
    if (type(proof['version']) is not int or proof['version'] != 1
            or type(proof['dispatched']) is not bool or type(proof['acknowledged']) is not bool
            or type(proof['delivered_count']) is not int
            or proof['delivered_count'] != int(proof['acknowledged'])
            or proof['effect'] != ('unverifiable' if proof['dispatched'] else 'refused')
            or (proof['acknowledged'] and (not proof['dispatched'] or proof['error'] is not None))
            or (not proof['acknowledged'] and (not isinstance(proof['error'], str) or not proof['error']))):
        raise ValueError('contradictory SDK row delivery')
    return proof


def action_receipt(action: Any, expected: Any) -> dict[str, Any]:
    def word(value: Any) -> Any:
        return value.name.lower() if hasattr(value, 'name') else value
    proof = receipt(get(action, 'row_receipt'), expected)
    delivery = get(action, 'delivery')
    if (word(get(action, 'effect')) != proof['effect'] or word(get(action, 'route')) != 'accessibility'
            or get(action, 'evidence') is not None or get(action, 'escalation') is not None
            or (proof['dispatched'] and (word(get(delivery, 'mode')) != 'foreground'
                or type(get(delivery, 'delivered_count')) is not int
                or get(delivery, 'delivered_count') != proof['delivered_count']))
            or (not proof['dispatched'] and delivery is not None)):
        raise ValueError('SDK row receipt contradicts public action')
    return proof


def intent(candidate: Any, *, operation: str = 'click') -> dict[str, Any]:
    """Preserve selected semantic intent before a replaceable producer reply."""
    from jevdual.menu import qualified_control_identity
    if qualified_control_identity(candidate) is None or get(candidate, 'native_row_control') is None:
        raise ValueError('missing admitted row identity')
    if operation != 'click' or type(get(candidate, 'id')) is not int:
        raise ValueError('unsupported row operation')
    return {'op': operation, 'target_id': get(candidate, 'id'), 'target_label': get(candidate, 'label'),
            'predicate': predicate(get(candidate, 'native_row_control'))}


def admission(projection: Any) -> dict[str, Any] | None:
    if not isinstance(projection, dict):
        return None
    identity = projection.get('target_identity')
    if not isinstance(identity, dict) or identity.get('native_row_control') is None:
        return None
    admitted = intent({**identity, 'id': projection.get('target_id')}, operation=projection.get('op'))
    if not same(projection.get('target_label'), admitted['target_label']):
        raise ValueError('row target label differs from admitted identity')
    return admitted


def has_row(projection: Any) -> bool:
    if not isinstance(projection, dict):
        return False
    identity = projection.get('target_identity')
    proof = projection.get('native_readback')
    delivery = projection.get('native_delivery')
    return ((isinstance(identity, dict) and identity.get('native_row_control') is not None)
            or (isinstance(proof, dict) and proof.get('producer') == 'cua.sdk.row')
            or (isinstance(delivery, dict) and delivery.get('delivery_basis') == 'sdk_row_press_ack'))


def projection_effect(projection: Any, admitted: Any, pid: int, window_id: int,
                      *, execution: Any = None, attached: bool = True) -> str:
    """One strict row consumer. No page diff or acknowledgement proves application effect."""
    from jevdual.operator_evidence import validate_binding
    if (not isinstance(projection, dict) or not isinstance(admitted, dict)
            or set(admitted) != {'op', 'target_id', 'target_label', 'predicate'}
            or admitted['op'] != 'click' or type(admitted['target_id']) is not int):
        raise ValueError('missing row admission')
    expected = predicate(admitted['predicate'])
    if (type(pid) is not int or type(window_id) is not int
            or expected['pid'] != pid or expected['window_id'] != window_id
            or admitted['target_label'] != expected['name']):
        raise ValueError('row admission binding differs')
    selected = admission(projection)
    if not same(selected, admitted):
        raise ValueError('row projection differs from admitted click')
    identity = projection['target_identity']
    if identity.get('native_window_control') is not None or identity.get('native_infobar_control') is not None:
        raise ValueError('row projection mixes control families')
    delivery = projection.get('native_delivery')
    if (not isinstance(delivery, dict) or set(delivery) != {
            'dispatched', 'delivery_basis', 'delivered_count', 'delivery', 'driver_delivery', 'route'}
            or delivery['driver_delivery'] is not None or delivery['delivery'] not in (None, 'foreground')):
        raise ValueError('invalid row delivery shape')
    dispatched = projection.get('dispatched')
    effect = projection.get('driver_effect')
    effect = 'refused' if effect in ('not sent', 'not dispatched') else effect
    if type(dispatched) not in (bool, type(None)) or not same(delivery['dispatched'], dispatched):
        raise ValueError('contradictory row dispatch')
    proof = projection.get('native_readback')
    if proof is not None:
        if (not isinstance(proof, dict) or set(proof) != {'schema_version', 'producer', 'predicate', 'receipt'}
                or type(proof['schema_version']) is not int or proof['schema_version'] != 1
                or proof['producer'] != 'cua.sdk.row' or proof['predicate'] != 'sdk_row_recipient'):
            raise ValueError('unsupported row readback')
        facts = receipt(proof['receipt'], expected)
        basis = 'sdk_row_press_ack' if facts['acknowledged'] else ('unknown' if facts['dispatched'] else 'qualified_gate')
        count = 1 if facts['acknowledged'] else (None if facts['dispatched'] else 0)
        route = 'accessibility'
        if not same(dispatched, facts['dispatched']) or effect != facts['effect']:
            raise ValueError('row receipt contradicts dispatch/effect')
    elif dispatched is False and effect == 'refused':
        basis, count, route = 'qualified_gate', 0, None
    elif dispatched in (True, None) and effect == 'unverifiable':
        basis, count, route = 'unknown', None, None
    else:
        raise ValueError('row outcome lacks exact evidence')
    if (not same(delivery['delivered_count'], count) or delivery['delivery_basis'] != basis
            or delivery['route'] != route or (proof is not None and delivery['delivery'] != 'foreground')):
        raise ValueError('row delivery contradicts SDK evidence')
    envelope = projection.get('execution_receipt') if execution is None else execution
    if envelope is not None:
        if not attached or not isinstance(envelope, dict):
            raise ValueError('nested row execution unsupported')
        fixed = {'schema_version': '1', 'kind': 'execution', 'protocol': 1, 'custody': 'returned',
                 'move': 'click', 'target': str(admitted['target_id']), 'effect': effect,
                 'dispatched': dispatched,
                 'phase': 'not_sent' if dispatched is False else 'sent' if count == 1 else 'ambiguous',
                 'producer': {'name': 'footwork.native', 'version': 1,
                              'delivery_basis': basis, 'delivered_count': count}}
        if any(not same(envelope.get(k), v) for k, v in fixed.items()):
            raise ValueError('row execution contradicts projection')
        inner = envelope.get('projection')
        projection_effect(inner, admitted, pid, window_id, attached=False)
        for key in ('target_label', 'target_identity', 'native_readback', 'native_delivery', 'dispatched', 'driver_effect'):
            if not same(inner.get(key), projection.get(key)):
                raise ValueError('row retained projection copies disagree')
        copies = [projection, envelope, inner]
    else:
        copies = [projection]
    for key in ('binding', 'operation_id', 'session_id', 'observation', 'error'):
        values = []
        for copy in copies:
            if key not in copy:
                continue
            value = copy[key]
            if key == 'binding':
                bound = validate_binding(value)
                if bound['pid'] != pid or bound['window_id'] != window_id:
                    raise ValueError('row execution binding differs')
            elif key == 'error':
                if value is not None and not isinstance(value, str):
                    raise ValueError('invalid row error')
            elif not isinstance(value, str) or not value:
                raise ValueError('invalid row provenance')
            values.append(value)
        if any(not same(v, values[0]) for v in values[1:]):
            raise ValueError('row retained provenance differs')
    return effect
