"""Acquisition custody, pinned delivery and bounded-inventory failure contracts."""
import errno
import os
import signal
from types import SimpleNamespace

import pytest
from jevdual import linux_process as process
from jevdual import linux_session as session


@pytest.fixture
def primitive(monkeypatch):
    state = SimpleNamespace(start='owned-A', closed=[], delivered=[], opened=[])
    monkeypatch.setattr(process.os, 'getuid', lambda: 1000)
    monkeypatch.setattr(process, 'read_process', lambda pid: {'start': state.start, 'uid': 1000})

    def acquire(pid, flags):
        state.opened.append((pid, flags))
        state.pinned = state.start
        return 91

    def deliver(fd, sig, info, flags):
        assert fd == 91 and info is None and flags == 0
        state.start = 'replacement-B'
        state.delivered.append((state.pinned, sig))

    monkeypatch.setattr(process.os, 'pidfd_open', acquire, raising=False)
    monkeypatch.setattr(process.signal, 'pidfd_send_signal', deliver, raising=False)
    monkeypatch.setattr(process.os, 'close', state.closed.append)
    monkeypatch.setattr(process.os, 'kill', lambda *_: pytest.fail('numeric signal fallback'))
    monkeypatch.setattr(process.os, 'killpg', lambda *_: pytest.fail('numeric group fallback'))
    return state


def test_delivery_remains_pinned_after_acquisition_and_closes_descriptor(primitive):
    r = process.pin_signal(42, {'start': 'owned-A'}, signal.SIGTERM)
    assert r['status'] == 'sent' and r['delivery'] == 'pidfd'
    assert primitive.delivered == [('owned-A', signal.SIGTERM)]
    assert primitive.opened == [(42, 0)] and primitive.closed == [91]


def test_replacement_at_handle_acquisition_is_not_adopted(monkeypatch, primitive):
    def replace(pid, flags):
        primitive.start = 'replacement-B'
        return 91
    monkeypatch.setattr(process.os, 'pidfd_open', replace)
    r = process.pin_signal(42, {'start': 'owned-A'}, signal.SIGTERM)
    assert r['status'] == 'identity_changed' and r['delivery'] is None
    assert not primitive.delivered and primitive.closed == [91]


def test_stale_observation_cannot_gain_custody_by_opening_a_new_fd(primitive):
    primitive.start = 'replacement-B'
    r = process.pin_signal(42, {'start': 'owned-A'}, signal.SIGTERM)
    assert r['status'] == 'identity_changed'
    assert not primitive.opened and not primitive.delivered


@pytest.mark.parametrize('code,status', [(errno.EPERM, 'denied'), (errno.EACCES, 'denied'),
                                        (errno.ENOSYS, 'unsupported'), (errno.EINVAL, 'unsupported'),
                                        (errno.EMFILE, 'resource_exhausted'), (errno.ENFILE, 'resource_exhausted'),
                                        (errno.ESRCH, 'exited')])
def test_fd_acquisition_failure_never_downgrades_delivery(monkeypatch, primitive, code, status):
    def fail(*_):
        raise OSError(code, 'controlled acquisition failure')
    monkeypatch.setattr(process.os, 'pidfd_open', fail)
    r = process.pin_signal(42, {'start': 'owned-A'}, signal.SIGTERM)
    assert r['status'] == status and r['delivery'] is None
    assert not primitive.delivered and not primitive.closed


def test_denied_delivery_closes_fd_without_a_pinned_delivery_claim(monkeypatch, primitive):
    def denied(*_):
        raise PermissionError(errno.EPERM, 'denied')
    monkeypatch.setattr(process.signal, 'pidfd_send_signal', denied)
    r = process.pin_signal(42, {'start': 'owned-A'}, signal.SIGTERM)
    assert r['status'] == 'denied' and r['delivery'] is None
    assert primitive.closed == [91] and not primitive.delivered


def test_unavailable_api_is_explicit_and_does_not_open_or_signal(monkeypatch, primitive):
    monkeypatch.setattr(process.os, 'pidfd_open', None)
    r = process.pin_signal(42, {'start': 'owned-A'}, signal.SIGTERM)
    assert r['status'] == 'unsupported' and r['delivery'] is None
    assert not primitive.delivered and not primitive.opened


def test_foreign_uid_is_not_signal_authority(monkeypatch, primitive):
    monkeypatch.setattr(process, 'read_process', lambda pid: {'start': 'owned-A', 'uid': 2000})
    assert process.pin_signal(42, {'start': 'owned-A'}, 15)['status'] == 'identity_changed'
    assert not primitive.opened


def test_inventory_bound_carries_incomplete_coverage(tmp_path):
    for pid in [101, 102]:
        path = tmp_path / str(pid)
        path.mkdir()
        fields = ['S', '1', '50', '50', *(['0'] * 15), str(pid)]
        (path / 'stat').write_text(f'{pid} (fixture) ' + ' '.join(fields))
    r = process.process_table(limit=1, proc=tmp_path)
    assert not r.complete and r.reasons == {'entry_limit'} and len(r) <= 1


def test_permission_failure_is_unknown_not_an_empty_complete_inventory(monkeypatch, tmp_path):
    (tmp_path / '42').mkdir()
    def denied(*_, **__):
        raise PermissionError(errno.EACCES, 'denied')
    monkeypatch.setattr(process, 'read_process', denied)
    r = process.process_table(proc=tmp_path)
    assert not r and not r.complete and 'process_read_unavailable' in r.reasons


def test_omitted_known_identity_is_retained_and_coverage_stays_unknown(monkeypatch, tmp_path):
    target = session.Session(tmp_path / 'known')
    target.identities[43] = 'owned-A'
    table = process.ProcessInventory()
    table.incomplete('entry_limit')
    monkeypatch.setattr(session, 'process_table', lambda: table)
    monkeypatch.setattr(session, 'read_process', lambda pid: {
        'start': 'owned-A', 'uid': os.getuid(), 'parent': 1, 'session': 43, 'group': 43, 'state': 'S'})
    assert 43 in target.capture() and target.identities[43] == 'owned-A'
    with pytest.raises(session.SessionError, match='inventory_incomplete'):
        target.check()


def test_empty_partial_inventory_cannot_claim_complete_cleanup(monkeypatch, tmp_path):
    table = process.ProcessInventory()
    table.incomplete('entry_limit')
    monkeypatch.setattr(session, 'process_table', lambda: table)
    target = session.Session(tmp_path / 'unknown', grace=.01)
    r = target.cleanup()
    assert not r['survivors'] and r['uncertain'] and not r['inventory_complete']
    assert r['inventory_reasons'] == ['entry_limit']


def test_marker_is_invalidated_at_stopping_before_cleanup(tmp_path):
    target = session.Session(tmp_path / 'marker')
    target.state.mkdir()
    target.transition('ready')
    (target.state / 'started').touch()
    target.transition('stopping')
    assert not (target.state / 'started').exists()


def test_unreadable_omitted_identity_is_not_retired(monkeypatch, tmp_path):
    target = session.Session(tmp_path / 'unknown-owner', grace=.01)
    target.identities[43] = 'owned-A'
    def partial():
        value = process.ProcessInventory()
        value.incomplete('entry_limit')
        return value
    def denied(pid):
        raise PermissionError(errno.EACCES, 'denied')
    monkeypatch.setattr(session, 'process_table', partial)
    monkeypatch.setattr(session, 'read_process', denied)
    r = target.cleanup()
    assert target.identities[43] == 'owned-A'
    assert r['uncertain'] and r['unknown_identities'] == [43]


def test_denied_signal_is_an_explicit_unresolved_cleanup(monkeypatch, tmp_path):
    target = session.Session(tmp_path / 'denied', grace=.01)
    target.processes = {'root': SimpleNamespace(pid=42, poll=lambda: None)}
    observed = {42: {'state': 'S', 'start': 'owned-A', 'session': 42, 'parent': 1}}
    monkeypatch.setattr(target, 'capture', lambda: observed)
    monkeypatch.setattr(session, 'pin_signal', lambda *_: {'pid': 42, 'status': 'denied', 'delivery': None})
    r = target.cleanup()
    assert r['survivors'] == [42] and r['uncertain']
    assert r['signal_failures'] == [{'pid': 42, 'status': 'denied', 'delivery': None}]
