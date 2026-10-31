"""One installed public HTTPS read, never an automatic retry or reconnect probe."""
import ctypes
import hashlib
import json
import os
import resource
import signal
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import psutil

ROOT = Path('/workspace/scratch/footwork-lightpanda-2b5325e')
OUT = ROOT / 'https-example'
ENGINE = ROOT / 'lightpanda-x86_64-linux'
EXPECTED = '19f3fee25fb14bb75a1e0c1e0f8ab9cce842950544e4a144fbad3884c94b98a3'


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def descendants():
    rows = []
    for process in psutil.Process().children(recursive=True):
        try:
            rows.append({'pid': process.pid, 'start': process.create_time(),
                         'status': process.status(), 'name': process.name()})
        except psutil.NoSuchProcess:
            pass
    return rows


def pinned(row, sig):
    fd = None
    try:
        process = psutil.Process(row['pid'])
        if process.create_time() != row['start']:
            return 'identity_changed'
        fd = os.pidfd_open(row['pid'])
        if process.create_time() != row['start']:
            return 'identity_changed'
        signal.pidfd_send_signal(fd, sig)
        return 'sent'
    except (psutil.NoSuchProcess, ProcessLookupError):
        return 'exited'
    finally:
        if fd is not None:
            os.close(fd)


def main():
    assert hashlib.sha256(ENGINE.read_bytes()).hexdigest() == EXPECTED
    OUT.mkdir(mode=0o700)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    assert ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) == 0
    parent = Path(tempfile.mkdtemp(prefix='lp-https-', dir='/tmp'))
    work = parent / 'engine'
    env = dict(os.environ)
    for key in ['PYTHONPATH', 'TYPESAFE_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY']:
        env.pop(key, None)
    env.update(JEVDUAL_PURE_PY='1', LIGHTPANDA_DISABLE_TELEMETRY='true', LIGHTPANDA_DISABLE_CORE_DUMP='1',
               FOOTWORK_LIGHTPANDA_EXECUTABLE=str(ENGINE))
    command = [str(ROOT / 'consumer/bin/footwork'), '--json', 'browser', 'lightpanda', 'read',
               'https://example.org/', '--executable', str(ENGINE), '--work-dir', str(work), '--timeout', '30']
    save('command.json', {'argv': command, 'cwd': str(OUT), 'attempts': 1, 'capture_timeout': 30,
                          'outer_watchdog': 70, 'provider_key_forwarded': False, 'PYTHONPATH': 'unset',
                          'proxy_ca_policy': 'inherited unchanged; no TLS bypass', 'private_parent': str(parent)})
    process = subprocess.Popen(command, cwd=OUT, env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    observed = {}
    end = time.monotonic() + 70
    while process.poll() is None and time.monotonic() < end:
        for row in descendants():
            observed[(row['pid'], row['start'])] = row
        time.sleep(.02)
    timed_out = process.poll() is None
    if timed_out:
        process.kill()  # sole-owner Popen watchdog; no read retry follows
    out, err = process.communicate(timeout=3)
    (OUT / 'stdout.txt').write_bytes(out)
    (OUT / 'stderr.txt').write_bytes(err)
    save('owned-process-history.json', list(observed.values()))
    before = descendants()
    waits, signals = [], []

    def reap():
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                break
            if pid == 0:
                break
            waits.append({'pid': pid, 'raw_wait_status': status, 'returncode': os.waitstatus_to_exitcode(status)})

    for sig in (signal.SIGTERM, signal.SIGKILL):
        for row in descendants():
            if row['status'] != psutil.STATUS_ZOMBIE:
                signals.append({**row, 'signal': sig.value, 'delivery': pinned(row, sig)})
        end = time.monotonic() + 3
        while descendants() and time.monotonic() < end:
            reap()
            time.sleep(.02)
        reap()
        if not descendants():
            break
    try:
        envelope = json.loads(out)
    except ValueError:
        envelope = None
    receipt = {'utc_finished': datetime.now(UTC).isoformat(), 'returncode': process.returncode,
               'signal': -process.returncode if process.returncode < 0 else None, 'timeout': timed_out,
               'attempts': 1, 'retry_performed': False, 'envelope': envelope, 'before_wrapper_cleanup': before,
               'signals': signals, 'adopted_waits': waits, 'final_owned_descendants': descendants(),
               'retained_work_dir': str(work), 'work_parent_mode': oct(parent.stat().st_mode & 0o777)}
    save('receipt.json', receipt)
    # A captured network/read refusal remains a recorded result, never an automatic retry.
    return 1 if timed_out or receipt['final_owned_descendants'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
