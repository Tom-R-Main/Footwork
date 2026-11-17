"""Fixed-purpose native infobar action through the real public operator CLI."""
import json
import sys

import pytest

from tests.test_session_scenarios import _fullscreen_actions, _state, fw, world  # noqa: F401


def infobar_world(world, monkeypatch, *, disappear=True):
    win, buttons, _ = _fullscreen_actions(world, monkeypatch)
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
        world.base['elements'].append(dict(element_index=idx, role='AXButton', label='Close',
                                          enabled=True, actions=['AXPress'], parent_index=0))
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
    win, container, alert, close, tab, tab_close, attempts = infobar_world(world, monkeypatch)
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
