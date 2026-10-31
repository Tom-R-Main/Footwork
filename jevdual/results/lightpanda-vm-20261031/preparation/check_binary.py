"""Pinned prebuilt metadata only; no Footwork route, socket or browser target is exercised."""
import ctypes
import hashlib
import json
import os
import platform
import resource
import signal
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import psutil

ROOT = Path('/workspace/scratch/footwork-lightpanda-preparation-20261031')
EXPECTED = '19f3fee25fb14bb75a1e0c1e0f8ab9cce842950544e4a144fbad3884c94b98a3'


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')


def read(path):
    return Path(path).read_text().strip()


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def children():
    result = []
    for process in psutil.Process().children(recursive=True):
        try:
            result.append({'pid': process.pid, 'start': process.create_time(),
                           'status': process.status(), 'name': process.name()})
        except psutil.NoSuchProcess:
            pass
    return result


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    downloaded = ROOT / 'lightpanda-x86_64-linux.download'
    # All verification precedes chmod, rename and either executable invocation.
    assert downloaded.stat().st_size == 77129032
    assert digest(downloaded) == EXPECTED
    with downloaded.open('rb') as stream:
        header = stream.read(20)
    assert header[:4] == b'\x7fELF' and header[4:6] == b'\x02\x01'
    assert int.from_bytes(header[18:20], 'little') == 62  # ELF x86-64
    verified = {'utc_verified': datetime.now(UTC).isoformat(), 'asset_id': 694146173,
                'bytes': downloaded.stat().st_size, 'sha256': digest(downloaded), 'elf_machine': 'x86_64',
                'execution_permitted_only_after_verification': True}
    save('verified-before-execution.json', verified)
    binary = ROOT / 'lightpanda-x86_64-linux'
    downloaded.rename(binary)
    binary.chmod(0o500)
    assert ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) == 0
    cpu_lines = Path('/proc/cpuinfo').read_text().splitlines()
    flags = next((line.split(':', 1)[1].split() for line in cpu_lines if line.startswith('flags')), [])
    environment = {
        'utc_observed': datetime.now(UTC).isoformat(), 'python': platform.python_version(),
        'psutil': psutil.__version__, 'kernel': platform.release(), 'architecture': platform.machine(),
        'os_release': read('/etc/os-release'), 'uid': os.getuid(), 'pid1': psutil.Process(1).name(),
        'cpu_model': next((s.split(':', 1)[1].strip() for s in cpu_lines if s.startswith('model name')), None),
        'logical_cpu_count': os.cpu_count(), 'affinity': sorted(os.sched_getaffinity(0)),
        'selected_cpu_flags': [f for f in ['sse4_2', 'avx', 'avx2', 'bmi1', 'bmi2', 'avx512f'] if f in flags],
        'cgroup_membership': read('/proc/self/cgroup'),
        'cgroup': {name: read('/sys/fs/cgroup/' + name) for name in
                   ['cpu.max', 'cpuset.cpus.effective', 'memory.max', 'memory.current', 'memory.swap.max',
                    'pids.max', 'pids.current', 'memory.events', 'pids.events']},
        'swap': [s for s in Path('/proc/meminfo').read_text().splitlines()
                 if s.startswith(('SwapTotal:', 'SwapFree:'))],
        'metadata_child_rlimit_core': [0, 0], 'test_only_subreaper': True,
        'child_environment_overrides': {'LIGHTPANDA_DISABLE_TELEMETRY': 'true', 'LIGHTPANDA_DISABLE_CORE_DUMP': '1'},
        'tag_provenance': 'nightly tag target is not asserted as source; record actual binary version and digest',
    }
    save('environment.json', environment)
    env = dict(os.environ)
    for key in ['TYPESAFE_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY']:
        env.pop(key, None)
    env.update(LIGHTPANDA_DISABLE_TELEMETRY='true', LIGHTPANDA_DISABLE_CORE_DUMP='1')
    records = []
    for label, option in [('version', '--version'), ('help', '--help')]:
        assert digest(binary) == EXPECTED
        before = time.monotonic()
        process = subprocess.Popen([str(binary), option], cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                                   preexec_fn=no_core)
        timed_out = False
        try:
            out, err = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()  # sole-owner direct Popen handle; metadata watchdog only
            out, err = process.communicate(timeout=3)
        (ROOT / f'{label}.stdout.txt').write_bytes(out)
        (ROOT / f'{label}.stderr.txt').write_bytes(err)
        records.append({'command': [str(binary), option], 'pid': process.pid, 'returncode': process.returncode,
                        'signal': -process.returncode if process.returncode < 0 else None,
                        'timeout': timed_out, 'wait_complete': True, 'elapsed_seconds': time.monotonic() - before,
                        'stdout_sha256': hashlib.sha256(out).hexdigest(),
                        'stderr_sha256': hashlib.sha256(err).hexdigest()})
        save('commands.json', records)
    before_reap = children()
    waits = []
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        if pid == 0:
            break
        waits.append({'pid': pid, 'raw_wait_status': status, 'returncode': os.waitstatus_to_exitcode(status)})
    final = children()
    receipt = {'before_test_reap': before_reap, 'adopted_waits': waits, 'final_owned_descendants': final,
               'binary_sha256_after_commands': digest(binary),
               'qualification': 'metadata preparation only; no candidate/read route/socket/target tested'}
    save('cleanup.json', receipt)
    return 1 if final or any(r['returncode'] or r['timeout'] for r in records) else 0


if __name__ == '__main__':
    raise SystemExit(main())
