"""Real subprocess ownership/deadlines, with deterministic readiness replies."""
import asyncio
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from jevdual import linux_session as session

pytestmark = pytest.mark.skipif(sys.platform != 'linux', reason='Linux /proc process ownership')
SLEEP = [sys.executable, '-c', 'import time; time.sleep(60)']


class FixtureSession(session.Session):
    blocked = None
    reason = None

    def __init__(self, state, **kw):
        kw.setdefault('display', next(n for n in range(30000, 31000)
                                     if not Path(f'/tmp/.X{n}-lock').exists()
                                     and not Path(f'/tmp/.footwork-X{n}.lock').exists()))
        super().__init__(state, startup=1.5, probe_timeout=.15, grace=.15,
                         commands={n: SLEEP for n in ['xvfb', 'bus', 'wm', 'editor']}, **kw)

    def probe_command(self, stage):
        if stage == self.blocked:
            if self.reason:
                return [sys.executable, '-c', 'print(' + repr(json.dumps({'ready': False, 'reason': self.reason})) + ')']
            return SLEEP
        return [sys.executable, '-c', 'print(\'{"ready": true}\')']


def stop_on_ready(target):
    end = time.monotonic() + 5
    while time.monotonic() < end:
        if target.report['phase'] == 'ready':
            target.cancelled = True
            return
        time.sleep(.01)


def test_fresh_profiles_ready_then_cancellation_reaps_owned_children(tmp_path):
    target = FixtureSession(tmp_path / 'fresh')
    timer = threading.Thread(target=stop_on_ready, args=(target,))
    timer.start()
    assert target.run() == 0
    timer.join(timeout=5)
    assert [r['phase'] for r in target.report['transitions']][-3:] == ['ready', 'stopping', 'stopped']
    assert not (target.state / 'started').exists()
    assert not target.report['cleanup']['survivors']
    assert all(p.poll() is not None for p in target.processes.values())
    for key in ['CONFIG_HOME', 'CACHE_HOME', 'DATA_HOME', 'STATE_HOME', 'RUNTIME_DIR']:
        path = Path(target.env['XDG_' + key])
        assert path.parent == target.state and path.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize('stage,reason', [('x11', None), ('wm', 'wm_unavailable'),
                                        ('bus', 'bus_missing'), ('atspi', 'bus_missing'),
                                        ('target', 'exact_text_target_unavailable'), ('target', 'recovery_modal')])
def test_partial_start_never_ready_and_probes_are_bounded(tmp_path, stage, reason):
    target = FixtureSession(tmp_path / 'failed')
    target.blocked, target.reason = stage, reason
    before = time.monotonic()
    assert target.run() == 1
    assert time.monotonic() - before < 4
    assert 'ready' not in [r['phase'] for r in target.report['transitions']]
    assert not target.report['cleanup']['survivors']
    assert target.report['phase'] == 'failed'


def test_occupied_display_is_not_touched_and_cleans_reservation(tmp_path):
    number = next(n for n in range(30000, 31000) if not Path(f'/tmp/.X{n}-lock').exists())
    occupied = Path(f'/tmp/.X{number}-lock')
    occupied.write_text('unrelated display sentinel')
    try:
        target = FixtureSession(tmp_path / 'occupied', display=number)
        assert target.run() == 1
        assert target.report['reason'] == 'display_occupied'
        assert occupied.read_text() == 'unrelated display sentinel'
        assert not target.processes
    finally:
        occupied.unlink()


def test_cancellation_during_stalled_probe_is_bounded(tmp_path):
    target = FixtureSession(tmp_path / 'cancel')
    target.blocked = 'x11'
    timer = threading.Timer(.1, lambda: setattr(target, 'cancelled', True))
    timer.start()
    before = time.monotonic()
    assert target.run() == 0
    timer.join()
    assert time.monotonic() - before < 2
    assert not target.report['cleanup']['survivors']
    assert not any(r['phase'] == 'ready' for r in target.report['transitions'])


@pytest.mark.parametrize('component', ['xvfb', 'bus', 'editor'])
def test_component_death_after_readiness_is_failure(tmp_path, component):
    target = FixtureSession(tmp_path / component)

    def kill():
        while target.report['phase'] not in ('ready', 'failed'):
            time.sleep(.01)
        os.kill(target.processes[component].pid, signal.SIGTERM)

    thread = threading.Thread(target=kill)
    thread.start()
    assert target.run() == 1
    thread.join(timeout=3)
    assert target.report['reason'] == 'component_exited:' + component
    assert not target.report['cleanup']['survivors']


def test_term_ignoring_component_is_killed_after_grace(tmp_path):
    target = FixtureSession(tmp_path / 'ignore')
    target.commands['wm'] = [sys.executable, '-c',
                             'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)']
    thread = threading.Thread(target=stop_on_ready, args=(target,))
    thread.start()
    assert target.run() == 0
    thread.join(timeout=3)
    assert target.processes['wm'].pid in target.report['cleanup']['forced_pids']
    assert not target.report['cleanup']['survivors']


def test_orphan_grandchild_in_owned_group_is_terminated_without_global_reaper(tmp_path):
    target = FixtureSession(tmp_path / 'orphan')
    childfile = tmp_path / 'child'
    target.commands['wm'] = [sys.executable, '-c',
        ('import subprocess,sys,time; from pathlib import Path; '
         f'p=subprocess.Popen({SLEEP!r}); Path({str(childfile)!r}).write_text(str(p.pid)); time.sleep(.3)')]
    assert target.run() == 1
    child = int(childfile.read_text())
    row = session.process_table().get(child)
    assert row is None or row['state'] == 'Z'
    assert not target.report['cleanup']['survivors']


def test_existing_profile_is_never_modified(tmp_path):
    path = tmp_path / 'existing'
    path.mkdir()
    (path / 'sentinel').write_text('ambient user data')
    target = FixtureSession(path)
    assert target.run() == 1
    assert (path / 'sentinel').read_text() == 'ambient user data'
    assert not (path / 'session.json').exists()


def test_reused_root_pid_does_not_grant_descendant_cleanup_authority(monkeypatch, tmp_path):
    target = FixtureSession(tmp_path / 'reuse')
    target.processes['wm'] = SimpleNamespace(pid=42)
    target.identities = {42: 'old'}
    target.root_identities = {42: 'old'}
    foreign = {'state': 'S', 'parent': 1, 'group': 42, 'session': 42, 'start': 'new'}
    monkeypatch.setattr(session, 'process_table', lambda: {42: foreign})
    assert target.capture() == {}


def test_cleanup_never_addresses_a_replacement_after_its_inventory_snapshot(monkeypatch, tmp_path):
    target = FixtureSession(tmp_path / 'stale-signal')
    target.processes = {'root': SimpleNamespace(pid=42)}
    live = {42: {'start': 'root-A', 'session': 42, 'state': 'S'},
            43: {'start': 'member-A', 'session': 42, 'state': 'S'}}
    snapshot = {pid: dict(row) for pid, row in live.items()}
    monkeypatch.setattr(target, 'capture', lambda: snapshot)
    delivered = []

    def group(*_):
        live[43]['start'] = 'replacement-B'

    def numeric(pid, _):
        delivered.append(live[pid]['start'])

    def pinned(pid, row, _):
        # A retained handle addresses the referent acquired before replacement.
        live[43]['start'] = 'replacement-B'
        delivered.append(row['start'])
        return {'pid': pid, 'status': 'sent', 'delivery': 'pidfd'}

    monkeypatch.setattr(session.os, 'killpg', group)
    monkeypatch.setattr(session.os, 'kill', numeric)
    monkeypatch.setattr(session, 'pin_signal', pinned, raising=False)
    target.signal_owned(['root'], signal.SIGTERM)
    assert 'replacement-B' not in delivered
    assert 'root-A' in delivered


def test_recovery_modal_is_a_readiness_refusal_not_an_action(monkeypatch, tmp_path):
    import cua_driver as cd
    from jevdual import native

    class Driver:
        async def list_windows(self, _):
            return SimpleNamespace(windows=[SimpleNamespace(window_id=3)])

        async def shutdown(self):
            pass

    class Bridge:
        def __init__(self, *_):
            pass

        async def observe(self):
            return SimpleNamespace(menu=SimpleNamespace(page_text='The previous session did not end normally'))

    monkeypatch.setattr(cd.CuaDriver, 'create', lambda **_: Driver())
    monkeypatch.setattr(native, 'NativeBridge', Bridge)
    assert asyncio.run(session._target_probe(2, tmp_path / 'document')) == {'ready': False, 'reason': 'recovery_modal'}


def test_actual_xlib_handshake_on_a_stalled_socket_is_killably_bounded(tmp_path):
    class StalledX(FixtureSession):
        def probe_command(self, stage):
            if stage == 'x11':
                return [sys.executable, '-I', '-m', 'jevdual.linux_session', '--probe', 'x11']
            return super().probe_command(stage)

    target = StalledX(tmp_path / 'stalled-x')
    target.commands['xvfb'] = [sys.executable, '-c',
        ('import socket,os,time; s=socket.socket(socket.AF_UNIX); '
         's.bind("/tmp/.X11-unix/X"+os.environ["DISPLAY"][1:]); '
         's.listen(10); c=s.accept()[0]; time.sleep(60)')]
    before = time.monotonic()
    try:
        assert target.run() == 1
        assert time.monotonic() - before < 4
        assert target.report['reason'] == 'x11:probe_timeout'
        assert not target.report['cleanup']['survivors']
        assert not any(t['phase'] == 'ready' for t in target.report['transitions'])
    finally:
        # The test's fake server cannot run Xvfb's normal socket cleanup.
        Path('/tmp/.X11-unix/X' + target.report['display'][1:]).unlink(missing_ok=True)


def test_root_only_accessibility_snapshot_cannot_publish_readiness(monkeypatch, tmp_path):
    import cua_driver as cd
    from jevdual import native

    class Driver:
        async def list_windows(self, _):
            return SimpleNamespace(windows=[SimpleNamespace(window_id=3)])

        async def shutdown(self):
            pass

    class Bridge:
        def __init__(self, *_):
            pass

        async def observe(self):
            return SimpleNamespace(menu=SimpleNamespace(page_text='', candidates=[]), values={})

    monkeypatch.setattr(cd.CuaDriver, 'create', lambda **_: Driver())
    monkeypatch.setattr(native, 'NativeBridge', Bridge)
    assert asyncio.run(session._target_probe(2, tmp_path / 'document')) == {
        'ready': False, 'reason': 'exact_text_target_unavailable'}


def test_wm_selection_without_ewmh_cannot_publish_readiness(monkeypatch):
    class Function:
        def __init__(self, fn):
            self.fn = fn

        def __call__(self, *args):
            return self.fn(*args)

    lib = SimpleNamespace(
        XOpenDisplay=Function(lambda _: 1), XCloseDisplay=Function(lambda _: 0),
        XInternAtom=Function(lambda _, name, __: 11 if name == b'WM_S0' else 0),
        XGetSelectionOwner=Function(lambda *_: 99),
        XDefaultRootWindow=Function(lambda _: 1),
        XGetWindowProperty=Function(lambda *_: 0), XFree=Function(lambda _: 0))
    monkeypatch.setattr(session.ctypes, 'CDLL', lambda _: lib)
    assert session._x_probe(True)['ready'] is False


def test_stalled_native_display_allocation_is_bounded(tmp_path):
    target = session.Session(tmp_path / 'display-stall', startup=.3, grace=.1,
                             commands={'xvfb': SLEEP})
    before = time.monotonic()
    assert target.run() == 1
    assert time.monotonic() - before < 3
    assert target.report['reason'] == 'display_allocation_timeout'
    assert not (target.state / 'started').exists()
    assert not target.report['cleanup']['survivors']


def test_invalid_native_display_reply_does_not_publish_ready(tmp_path):
    class CorruptDisplay(session.Session):
        def spawn(self, name, command, **kwargs):
            if name == 'xvfb':
                self.commands[name] = [sys.executable, '-c',
                    'import os,sys,time;os.write(int(sys.argv[1]),bytes([255,10]));time.sleep(60)', command[2]]
            return super().spawn(name, command, **kwargs)

    target = CorruptDisplay(tmp_path / 'display-corrupt', startup=1, grace=.1)
    assert target.run() == 1
    assert target.report['reason'] == 'display_allocation_invalid'
    assert not target.report['cleanup']['survivors']


def test_unavailable_pinned_signalling_refuses_before_starting_components(monkeypatch, tmp_path):
    target = session.Session(tmp_path / 'unsupported')
    monkeypatch.setattr(session, 'pin_signal', lambda *_: {'status': 'unsupported', 'delivery': None})
    assert target.run() == 1
    assert not target.processes
    assert target.report['reason'] == 'pinned_signalling_unavailable:unsupported'
    assert not (target.state / 'started').exists()


def test_probe_attempts_preserve_results_stderr_phases_and_signal_exit(tmp_path):
    target = FixtureSession(tmp_path / 'attempts')
    target.prepare()
    def command(stage):
        path = str(target.probe_events)
        return [sys.executable, '-c',
                ('import os,signal,time,json; from pathlib import Path; '
                 f'Path({path!r}).write_text(json.dumps({{"phase":"shutdown_returned","monotonic":time.monotonic()}})+"\\n"); '
                 'print("diagnostic",file=__import__("sys").stderr,flush=True); '
                 'print(\'{"ready":true}\',flush=True); os.kill(os.getpid(),signal.SIGABRT)')]
    target.probe_command = command
    with pytest.raises(session.SessionError, match='probe_abnormal_exit'):
        target.await_probe('target', time.monotonic() + .3)
    records = sorted(target.state.glob('probe-target-*.json'))
    assert records
    for path in records:
        row = json.loads(path.read_text())
        assert row['signal'] == signal.SIGABRT and row['returncode'] == -signal.SIGABRT
        assert row['wait_complete'] and row['last_phase'] == 'shutdown_returned'
        assert row['result']['ready'] is True
        assert path.with_suffix('.stderr.log').read_text().strip() == 'diagnostic'
        assert json.loads(path.with_suffix('.log').read_text()) == {'ready': True}
    target.cleanup()


def test_probe_timeout_retains_phase_escalation_and_final_wait(tmp_path):
    target = FixtureSession(tmp_path / 'phase-timeout')
    target.prepare()
    def command(stage):
        return [sys.executable, '-c',
                ('import signal,time,json; from pathlib import Path; '
                 'signal.signal(signal.SIGTERM,signal.SIG_IGN); '
                 f'Path({str(target.probe_events)!r}).write_text(json.dumps({{"phase":"shutdown","monotonic":time.monotonic()}})+"\\n"); '
                 'time.sleep(60)')]
    target.probe_command = command
    with pytest.raises(session.SessionError, match='probe_timeout'):
        target.await_probe('target', time.monotonic() + .25)
    rows = [json.loads(p.read_text()) for p in target.state.glob('probe-target-*.json')]
    assert rows
    for row in rows:
        assert row['timeout'] and row['last_phase'] == 'shutdown'
        assert [r['signal'] for r in row['termination']] == [signal.SIGTERM, signal.SIGKILL]
        assert row['signal'] == signal.SIGKILL and row['wait_complete']
    target.cleanup()


def test_editor_waits_for_window_manager_mapping_acknowledgement(tmp_path):
    target = FixtureSession(tmp_path / 'not-servicing')
    target.blocked, target.reason = 'wm_ready', 'wm_not_servicing'
    assert target.run() == 1
    assert 'editor' not in target.processes
    assert not (target.state / 'started').exists()
    assert target.report['reason'] == 'wm_ready:wm_not_servicing'
    assert not target.report['cleanup']['survivors']
