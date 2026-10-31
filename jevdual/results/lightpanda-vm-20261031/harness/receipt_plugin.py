"""Test-only passive receipts; never change a subprocess command/result or product state."""
import functools
import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent  # copied into the new owned run before execution
CURRENT = None
LOCK = threading.Lock()
COUNTER = 0


def digest(value):
    return hashlib.sha256(value).hexdigest()


def clean(value):
    if isinstance(value, dict):
        return {k: {'redacted_nonce_sha256': digest(str(v).encode())} if k == 'nonce' else clean(v)
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, bytes):
        return value.decode(errors='replace')
    if isinstance(value, Path):
        return str(value)
    return value


def emit(kind, **fields):
    with LOCK, (ROOT / 'observer.jsonl').open('a') as stream:
        stream.write(json.dumps(clean({'kind': kind, 'monotonic': time.monotonic(),
                                      'nodeid': CURRENT, **fields})) + '\n')


def observer_error(stage, error):
    with LOCK, (ROOT / 'observer-errors.jsonl').open('a') as stream:
        stream.write(json.dumps({'stage': stage, 'nodeid': CURRENT,
                                 'type': type(error).__name__, 'message': str(error)}) + '\n')


def output(value):
    if value is None:
        return None
    raw = value if isinstance(value, bytes) else value.encode()
    text = raw.decode(errors='replace')
    try:
        parsed = json.loads(text)
    except ValueError:
        parsed = None
    return {'sha256': digest(raw), 'bytes': len(raw),
            'json': clean(parsed), 'text': json.dumps(clean(parsed)) if parsed is not None else text}


def selected(argv):
    if not isinstance(argv, (tuple, list)):
        return None
    if str(argv[0]) == os.environ.get('FOOTWORK_EXECUTABLE'):
        return 'public_cli'
    if '-c' in argv and any('test-boundary.json' in str(x) and 'os._exit(86)' in str(x) for x in argv):
        return 'test_only_holder_shim'
    if '-c' in argv and any('zombies_before_test_reap' in str(x) and 'live_before_test_cleanup' in str(x) for x in argv):
        return 'test_only_startup_supervisor'
    return None


def arguments(argv):
    values = list(map(str, argv))
    if '-c' in values:
        index = values.index('-c') + 1
        values[index] = {'test_script_sha256': digest(values[index].encode()), 'characters': len(values[index])}
    return values


def pytest_configure(config):
    global ORIGINAL_INIT, ORIGINAL_WAIT, ORIGINAL_COMMUNICATE
    ORIGINAL_INIT = subprocess.Popen.__init__
    ORIGINAL_WAIT = subprocess.Popen.wait
    ORIGINAL_COMMUNICATE = subprocess.Popen.communicate

    def initialize(self, args, *positional, **kwargs):
        global COUNTER
        ORIGINAL_INIT(self, args, *positional, **kwargs)
        kind = selected(args)
        if kind:
            with LOCK:
                COUNTER += 1
                number = COUNTER
            self._vm_receipt = {'process_number': number, 'process_kind': kind, 'owner_nodeid': CURRENT,
                                'pid': self.pid, 'argv': arguments(args), 'cwd': str(kwargs.get('cwd') or os.getcwd())}
            emit('spawn', **self._vm_receipt)

    def wait(self, *args, **kwargs):
        result = ORIGINAL_WAIT(self, *args, **kwargs)
        record = getattr(self, '_vm_receipt', None)
        if record:
            emit('wait', **record, returncode=result, signal=-result if result < 0 else None)
        return result

    def communicate(self, *args, **kwargs):
        result = ORIGINAL_COMMUNICATE(self, *args, **kwargs)
        record = getattr(self, '_vm_receipt', None)
        if record:
            emit('communicate', **record, returncode=self.returncode,
                 signal=-self.returncode if self.returncode is not None and self.returncode < 0 else None,
                 stdout=output(result[0]), stderr=output(result[1]))
            if record['process_kind'] == 'test_only_startup_supervisor':
                safe_snapshot(record['cwd'], 'startup_supervisor_return')
        return result

    subprocess.Popen.__init__ = initialize
    subprocess.Popen.wait = wait
    subprocess.Popen.communicate = communicate


def snapshots(root, stage):
    root = Path(root)
    files = []
    for directory in [root, root / 'session', root / 'next']:
        for name in ['browser.json', 'holder.json', 'test-boundary.json', 'startup-boundary.json', 'holder.stderr.log', 'holder.stdout.log']:
            path = directory / name
            try:
                raw = path.read_bytes()
                info = path.stat()
            except FileNotFoundError:
                continue
            item = {'path': str(path), 'sha256': digest(raw), 'mtime_ns': info.st_mtime_ns,
                    'mode': oct(info.st_mode & 0o777)}
            try:
                item['json'] = clean(json.loads(raw))
            except ValueError:
                item['text'] = raw.decode(errors='replace')
            files.append(item)
    if files:
        emit('session_snapshot', stage=stage, root=root, files=files)


def safe_snapshot(root, stage):
    try:
        snapshots(root, stage)
    except Exception as error:  # noqa: BLE001 - diagnostics must not bypass fixture cleanup
        observer_error(stage, error)


def wrap_helper(module, name):
    original = getattr(module, name, None)
    if original is None or getattr(original, '_vm_observed', False):
        return

    @functools.wraps(original)
    def observed(*args, **kwargs):
        root = None
        if module.__name__ == 'test_browser_restart_cli' and name in ('_cli', '_setup') and args:
            root = args[0]
        elif '--session' in args:
            root = Path(args[args.index('--session') + 1]).parent
        if root is not None:
            safe_snapshot(root, 'before_' + name)
        try:
            result = original(*args, **kwargs)
            if name in ('_cli', 'cli'):
                emit('helper_return', helper=name, arguments=list(map(str, args)), result=result)
            return result
        finally:
            if root is not None:
                safe_snapshot(root, 'after_' + name)

    observed._vm_observed = True
    setattr(module, name, observed)


def pytest_runtest_setup(item):
    global CURRENT
    CURRENT = item.nodeid
    if item.module.__name__ in ('test_browser_restart_cli', 'test_browser_cdp_cli'):
        for name in ('_cli', 'cli', '_setup', '_test_cleanup'):
            wrap_helper(item.module, name)


def fixture_records(item):
    for name in ('ingress', 'page', 'fixture_site'):
        fixture = item.funcargs.get(name)
        if not isinstance(fixture, tuple) or len(fixture) < 2:
            continue
        records = fixture[1]() if callable(fixture[1]) else fixture[1]
        if isinstance(records, list):
            emit('independent_fixture_records', fixture=name, url=fixture[0], records=list(records),
                 request_paths=list(getattr(fixture[2], 'requests', [])) if name == 'fixture_site' and len(fixture) > 2 else None)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    emit('pytest_report', phase=report.when, outcome=report.outcome,
         duration=report.duration, longrepr=str(report.longrepr) if report.failed else None)
    if report.when == 'call':
        try:
            fixture_records(item)
        except Exception as error:  # noqa: BLE001 - preserve collector gaps separately from product results
            observer_error('fixture_records', error)


def pytest_unconfigure(config):
    subprocess.Popen.__init__ = ORIGINAL_INIT
    subprocess.Popen.wait = ORIGINAL_WAIT
    subprocess.Popen.communicate = ORIGINAL_COMMUNICATE
