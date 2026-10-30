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
