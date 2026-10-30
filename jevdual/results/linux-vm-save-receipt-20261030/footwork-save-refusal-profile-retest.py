"""Repeat the installed Debian foreground refusal and working-desktop control."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path('/workspace/Footwork/jevdual')
OUT = ROOT / 'results/linux-vm-save-receipt-20261030'
PYTHON = Path('/workspace/scratch/footwork-debian-consumer-045fc5d/bin/python')
FIXTURE = b'Footwork Linux fixture\n\tkeep trailing spaces  \n'


def case(label, working):
    profile = Path('/workspace/scratch/footwork-save-profile-' + label)
    profile.mkdir()
    state = Path('/workspace/scratch/footwork-save-' + label)
    runtime = Path('/workspace/scratch/footwork-save-' + label + '-runtime')
    if state.exists() or runtime.exists() or Path('/tmp/.X99-lock').exists():
        raise RuntimeError('Fresh state/output and unused display :99 required')
    env = dict(os.environ)
    env['LD_LIBRARY_PATH'] = '/workspace/.footwork-setup/sysroot/usr/lib/x86_64-linux-gnu'
    env['XDG_CONFIG_HOME'] = str(profile / 'config')
    env['XDG_CACHE_HOME'] = str(profile / 'cache')
    env['XDG_DATA_HOME'] = str(profile / 'data')
    env['XDG_STATE_HOME'] = str(profile / 'state')
    env['FOOTWORK_SAVE_DIAGNOSTIC_PATH'] = str(OUT / (label + '-sdk.json'))
    env['XDG_DATA_DIRS'] = '/usr/local/share:/usr/share'
    env['XDG_CONFIG_DIRS'] = '/etc/xdg'
    if working:
        env['XDG_DATA_DIRS'] = '/workspace/.footwork-setup/sysroot/usr/share:' + env['XDG_DATA_DIRS']
        env['XDG_CONFIG_DIRS'] = '/workspace/.footwork-setup/sysroot/etc/xdg:' + env['XDG_CONFIG_DIRS']
    record = {'implementation_commit': '045fc5d', 'state': str(state), 'runtime': str(runtime),
              'working_desktop': working, 'identity_checks': 'unchanged'}
    log = (OUT / (label + '-desktop.txt')).open('w')
    desktop = subprocess.Popen(
        ['dbus-run-session', '--', 'bash', str(ROOT / 'scripts/linux/desktop-session.sh'), str(state)],
        env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    try:
        for _ in range(150):
            if (state / 'started').exists():
                break
            if desktop.poll() is not None:
                raise RuntimeError(f'desktop exited {desktop.returncode}')
            time.sleep(.1)
        else:
            raise RuntimeError('desktop readiness timed out')
        time.sleep(3)
        before = (state / 'document.txt').read_bytes()
        assert before == FIXTURE
        with (OUT / (label + '-qualification.txt')).open('w') as qlog:
            result = subprocess.run(
                [str(PYTHON), '-I', '/workspace/scratch/record-footwork-sdk.py', str(ROOT / 'scripts/linux/qualify.py'), '--state', str(state),
                 '--output', str(runtime), '--chrome', '/usr/lib/chromium/chromium'],
                env=env, stdout=qlog, stderr=subprocess.STDOUT, timeout=180,
            )
        record['qualification_exit_code'] = result.returncode
        effect = json.loads((runtime / 'driver-save.json').read_text())
        after = (state / 'document.txt').read_bytes()
        record['save_effect'] = effect
        record['before_disk_sha256'] = hashlib.sha256(before).hexdigest()
        record['after_disk_sha256'] = hashlib.sha256(after).hexdigest()
        record['disk_unchanged'] = before == after
        if working:
            assert result.returncode == 0
            receipt = json.loads((runtime / 'receipt.json').read_text())
            record['receipt'] = receipt
            assert receipt['saved_file_exact'] and receipt['duplicate_not_repeated'] and receipt['restart_not_repeated']
            assert effect['dispatched'] is True and effect['error_code'] is None
            assert after == (runtime / 'expected.txt').read_bytes()
        else:
            assert result.returncode != 0
            assert 'scoped driver save was not sent' in (OUT / (label + '-qualification.txt')).read_text()
            assert effect['error_code'] == 'foreground_unavailable'
            assert effect['effect'] == 'refused'
            assert effect['dispatched'] is False
            assert effect['delivered_count'] == 0
            assert effect['delivery_basis'] == 'qualified_gate'
            assert effect['readback'] is None
            assert before == after
            assert not (runtime / 'receipt.json').exists()
        record['passed'] = True
    except Exception as exc:
        record['passed'] = False
        record['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        try:
            os.killpg(desktop.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            desktop.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(desktop.pid, signal.SIGKILL)
            desktop.wait()
        log.close()
        (OUT / (label + '.json')).write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps({'case': label, 'passed': record.get('passed'),
                          'save_effect': record.get('save_effect'), 'error': record.get('error')}), flush=True)
    return record['passed']


if __name__ == '__main__':
    refused = case('045fc5d-refused-profile', False)
    working = case('045fc5d-working-profile', True)
    raise SystemExit(0 if refused and working else 1)
