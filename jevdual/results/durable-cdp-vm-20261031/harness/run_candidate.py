"""Run unchanged installed-wheel candidate tests; never import checkout product code."""
import ctypes
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import resource
import shutil
import signal
import subprocess
import sys
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import psutil

SOURCE = Path('/workspace/footwork-durable-cdp-cad7508')
ROOT = Path('/workspace/scratch/footwork-durable-cdp-cad7508')
BASE = 'cad7508f8f4375735c0651c5e0aa5929f3b57700'
CHROME = '/usr/lib/chromium/chromium'
TESTS = ['test_cdp_effector.py', 'test_cdp_transport_deadline.py', 'test_cdp_launch_custody.py', 'test_cdp_click.py', 'test_cdp_click_contract.py', 'test_browser_durable_authority.py', 'test_browser_holder.py', 'test_browser_guard.py', 'test_browser_cdp_cli.py', 'test_browser_restart_cli.py']


def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError as error:
        return {'unavailable': type(error).__name__}


def save(name, data):
    (ROOT / name).write_text(json.dumps(data, indent=2) + '\n')


def identity(process):
    return {'pid': process.pid, 'start': process.create_time(), 'parent': process.ppid(),
            'name': process.name(), 'status': process.status(),
            'session': os.getsid(process.pid), 'group': os.getpgid(process.pid)}


def descendants():
    rows = []
    for process in psutil.Process().children(recursive=True):
        try:
            rows.append(identity(process))
        except psutil.NoSuchProcess:
            pass
    return rows


def pinned_signal(row, sig):
    fd = None
    try:
        process = psutil.Process(row['pid'])
        if process.create_time() != row['start']:
            return 'identity_changed'
        fd = os.pidfd_open(process.pid)
        if process.create_time() != row['start']:
            return 'identity_changed'
        signal.pidfd_send_signal(fd, sig)
        return 'sent'
    except (ProcessLookupError, psutil.NoSuchProcess):
        return 'exited'
    except (OSError, psutil.Error) as error:
        return type(error).__name__
    finally:
        if fd is not None:
            os.close(fd)


def main():
    assert sys.prefix == str(ROOT / 'consumer')
    assert not importlib.util.find_spec('cua_driver')
    assert not importlib.util.find_spec('browser_use')
    import jevdual
    from jevdual.effectors.cdp import operations

    wheel = next((ROOT / 'wheel').glob('*.whl'))
    package_root = Path(jevdual.__file__).parent.parent
    assert package_root.is_relative_to(ROOT / 'consumer')
    verified = []
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.startswith('jevdual/'):
                installed = package_root / name
                assert installed.read_bytes() == archive.read(name), name
                verified.append(name)
    for helper in ('receipt_plugin.py', 'pytest_main.py'):
        shutil.copyfile(Path(__file__).with_name(helper), ROOT / helper)
    testdir = ROOT / 'tests'
    testdir.mkdir(mode=0o700)
    hashes = {}
    for name in TESTS:
        original = SOURCE / 'jevdual/tests' / name
        copied = testdir / name
        shutil.copyfile(original, copied)
        assert copied.read_bytes() == original.read_bytes()
        hashes[name] = sha(copied)
    libc = ctypes.CDLL(None, use_errno=True)
    assert libc.prctl(36, 1, 0, 0, 0) == 0, ctypes.get_errno()  # task-only child subreaper
    state = ctypes.c_int()
    assert libc.prctl(37, ctypes.byref(state), 0, 0, 0) == 0 and state.value == 1
    metadata = {
        'utc_started': datetime.now(UTC).isoformat(), 'baseline_source': BASE,
        'measurement_commit': subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip(),
        'evidence_commit': subprocess.check_output(['git', '-C', '/workspace/footwork-durable-cdp-vm-evidence', 'rev-parse', 'HEAD'], text=True).strip(),
        'harness_sha256': sha(Path(__file__)), 'wheel': {'name': wheel.name, 'sha256': sha(wheel)},
        'test_sha256': hashes, 'verified_installed_package_files': len(verified),
        'origins': {'jevdual': jevdual.__file__, 'operations': operations.__file__,
                    'python': sys.executable, 'prefix': sys.prefix, 'sys_path': sys.path},
        'packages': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()},
        'optional_backends': {'cua_driver': False, 'browser_use': False},
        'python': sys.version, 'os_release': read('/etc/os-release'),
        'kernel': {'system': platform.system(), 'release': platform.release(), 'machine': platform.machine()},
        'chrome': {'executable': CHROME, 'sha256': sha(Path(CHROME)),
                   'version': subprocess.check_output([CHROME, '--version'], text=True).strip(),
                   'sandbox_override': False},
        'cgroup_membership': read('/proc/self/cgroup'),
        'cgroup': {n: read('/sys/fs/cgroup/' + n) for n in
                   ['cpu.max', 'cpuset.cpus.effective', 'memory.max', 'memory.swap.max', 'pids.max',
                    'memory.events', 'pids.events']},
        'affinity': sorted(os.sched_getaffinity(0)), 'uid': os.getuid(),
        'rlimits': {n: resource.getrlimit(getattr(resource, n)) for n in
                    ['RLIMIT_CORE', 'RLIMIT_NPROC', 'RLIMIT_NOFILE', 'RLIMIT_AS']},
        'kernel_policy': {p: read(p) for p in ['/proc/sys/kernel/unprivileged_userns_clone',
                           '/proc/sys/user/max_user_namespaces', '/proc/sys/kernel/core_pattern']},
        'pid1': psutil.Process(1).name(), 'test_wrapper_subreaper': True,
        'watchdog_seconds': 600, 'cleanup_grace_seconds': 3,
        'scope': 'explicit durable CDP CLI and holder; typing/completion oracle/light metadata split remain off',
    }
    save('environment.json', metadata)
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env.pop('TYPESAFE_API_KEY', None)  # fixture guards only; no provider-backed calls
    env['FOOTWORK_EXECUTABLE'] = str(ROOT / 'consumer/bin/footwork')
    env.update(FOOTWORK_CHROME_EXECUTABLE=CHROME, JEVDUAL_PURE_PY='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    command = [sys.executable, '-I', str(ROOT / 'pytest_main.py'), '-q', '-rA', '-o', 'markers=browser: launches a real owned browser', '--confcutdir=' + str(testdir),
               '--basetemp=' + str(ROOT / 'pytest-tmp'), '--junitxml=' + str(ROOT / 'junit.xml'), str(testdir)]
    save('command.json', {'argv': command, 'cwd': str(testdir), 'PYTHONPATH': 'unset',
                         'FOOTWORK_CHROME_EXECUTABLE': CHROME, 'JEVDUAL_PURE_PY': '1',
                         'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'FOOTWORK_EXECUTABLE': env['FOOTWORK_EXECUTABLE'], 'provider_key_forwarded': False})
    save('pre-owned-processes.json', descendants())
    with (ROOT / 'pytest.stdout.txt').open('w') as out, (ROOT / 'pytest.stderr.txt').open('w') as err:
        process = subprocess.Popen(command, cwd=testdir, env=env, stdout=out, stderr=err, start_new_session=True)
        observed = {}
        deadline = time.monotonic() + 600
        while process.poll() is None and time.monotonic() < deadline:
            for row in descendants():
                observed[(row['pid'], row['start'])] = row
            time.sleep(.05)
        timed_out = process.poll() is None
        if timed_out:
            process.terminate()  # sole direct-child Popen identity; watchdog only
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
        code = process.wait(timeout=3)
    pre_cleanup = descendants()
    save('owned-process-history.json', list(observed.values()))
    save('post-pytest-before-wrapper-reaping.json', pre_cleanup)
    signals, waits = [], []

    def reap():
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                break
            if pid == 0:
                break
            waits.append({'pid': pid, 'raw_wait_status': status,
                          'returncode': os.waitstatus_to_exitcode(status)})

    for sig in (signal.SIGTERM, signal.SIGKILL):
        for row in descendants():
            if row['status'] != psutil.STATUS_ZOMBIE:
                signals.append({**row, 'signal': sig.value, 'delivery': pinned_signal(row, sig)})
        deadline = time.monotonic() + 3
        while descendants() and time.monotonic() < deadline:
            reap()
            time.sleep(.02)
        reap()
        if not descendants():
            break
    final = descendants()
    save('cleanup.json', {'pytest_returncode': code, 'pytest_timeout': timed_out,
                         'pre_wrapper_cleanup': pre_cleanup, 'signals': signals,
                         'adopted_waits': waits, 'final_owned_descendants': final,
                         'utc_finished': datetime.now(UTC).isoformat(),
                         'limits': 'bounded known descendants; no atomic inventory/daemon-escape/global no-zombie claim'})
    observer_gap = (ROOT / 'observer-errors.jsonl').exists() and (ROOT / 'observer-errors.jsonl').stat().st_size > 0
    wrapper_code = 1 if timed_out or final or observer_gap else (code if code >= 0 else 128 - code)
    receipt = json.loads((ROOT / 'cleanup.json').read_text())
    receipt.update(observer_gap=observer_gap, wrapper_returncode=wrapper_code)
    save('cleanup.json', receipt)
    return wrapper_code


if __name__ == '__main__':
    raise SystemExit(main())
