"""Owned, bounded X11 qualification session; never attaches to a user's desktop.

Probes run in killable subprocesses: cancelling an asyncio thread cannot bound an
Xlib/AT-SPI call. No global reaper is installed; container init owns orphan waits.
"""
from __future__ import annotations

import argparse
import asyncio
import ctypes
import errno
import json
import os
import select
import signal
import subprocess
import sys
import time
from pathlib import Path

from jevdual.linux_process import pin_signal, process_table, read_process

FIXTURE = "Footwork Linux fixture\n\tkeep trailing spaces  \n"


class SessionError(RuntimeError):
    pass


def _json(path: Path, value: dict) -> None:
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


class Session:
    def __init__(self, state: Path, *, display: int | None = None, prefix: Path | None = None,
                 startup: float = 30, probe_timeout: float = 3, grace: float = 2,
                 commands: dict | None = None):
        self.state = state.absolute()
        self.display_number = display
        self.prefix = prefix
        self.startup, self.probe_timeout, self.grace = startup, probe_timeout, grace
        self.commands = commands or {}
        self.processes: dict[str, subprocess.Popen] = {}
        self.logs: dict = {}
        self.probe_counts: dict[str, int] = {}
        self.probe_events: Path | None = None
        self.identities: dict[int, str] = {}
        self.root_identities: dict[int, str] = {}
        self.inventory_reasons: set[str] = set()
        self.unknown_identities: set[int] = set()
        self.signal_failures: dict[tuple, dict] = {}
        self.cancelled = False
        self.created = False
        self.reservation: tuple[Path, int] | None = None
        self.report: dict = {'ready': False, 'phase': 'created', 'transitions': [], 'cleanup': None}
        self.env = os.environ.copy()

    def transition(self, phase: str, **details) -> None:
        if phase != 'ready':
            (self.state / 'started').unlink(missing_ok=True)
        self.report.update(phase=phase, ready=phase == 'ready', **details)
        self.report['transitions'].append({'phase': phase, 'monotonic': time.monotonic(), **details})
        _json(self.state / 'session.json', self.report)

    def prepare(self) -> None:
        self.state.mkdir(mode=0o700)  # existing paths are never overwritten
        self.created = True
        for name in ['config', 'cache', 'data', 'state', 'runtime']:
            path = self.state / name
            path.mkdir(mode=0o700)
            self.env['XDG_' + ('RUNTIME_DIR' if name == 'runtime' else name.upper() + '_HOME')] = str(path)
        self.env.update(NO_AT_BRIDGE='0', GTK_MODULES='atk-bridge', GDK_BACKEND='x11')
        self.env.pop('WAYLAND_DISPLAY', None)
        data, config = ['/usr/local/share', '/usr/share'], ['/etc/xdg']
        if self.prefix is not None:
            prefix = self.prefix.resolve(strict=True)
            data.insert(0, str(prefix / 'usr/share'))
            config.insert(0, str(prefix / 'etc/xdg'))
            libraries = sorted((prefix / 'usr/lib').glob('*-linux-gnu'))
            self.env['LD_LIBRARY_PATH'] = ':'.join([*(str(p) for p in libraries),
                                                   self.env.get('LD_LIBRARY_PATH', '')]).rstrip(':')
        self.env['XDG_DATA_DIRS'], self.env['XDG_CONFIG_DIRS'] = ':'.join(data), ':'.join(config)
        self.report['rootless_prefix'] = str(self.prefix) if self.prefix else None
        self.report['resource_snapshot'] = __import__('jevdual.host_probe', fromlist=['probe']).probe()['resources']
        self.transition('reserving_display')
        self.env.pop('DISPLAY', None)
        candidates = [self.display_number] if self.display_number is not None else []
        for number in candidates:
            path = Path(f'/tmp/.footwork-X{number}.lock')
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                continue
            if Path(f'/tmp/.X{number}-lock').exists() or Path(f'/tmp/.X11-unix/X{number}').exists():
                os.close(fd)
                path.unlink()
                continue
            self.reservation = path, os.fstat(fd).st_ino
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            self.env['DISPLAY'] = f':{number}'
            (self.state / 'display').write_text(f':{number}\n')
            self.report['display'] = f':{number}'
            break
        else:
            if self.display_number is not None:
                raise SessionError('display_occupied')
        address = 'unix:path=' + str(self.state / 'runtime/bus')
        self.env['DBUS_SESSION_BUS_ADDRESS'] = address
        (self.state / 'session-bus').write_text(address)
        (self.state / 'document.txt').write_text(FIXTURE)

    def allocate_display(self, deadline: float) -> None:
        if self.display_number is not None:
            self.spawn('xvfb', ['Xvfb', self.env['DISPLAY'], '-screen', '0', '1280x900x24', '-nolisten', 'tcp'])
            return
        read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
        try:
            self.spawn('xvfb', ['Xvfb', '-displayfd', str(write_fd), '-screen', '0', '1280x900x24',
                                '-nolisten', 'tcp'], pass_fds=(write_fd,))
            os.close(write_fd)
            write_fd = None
            data = b''
            while b'\n' not in data:
                self.check()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise SessionError('display_allocation_timeout')
                if not select.select([read_fd], [], [], min(.05, remaining))[0]:
                    continue
                chunk = os.read(read_fd, 32)
                if not chunk or len(data) + len(chunk) > 16:
                    raise SessionError('display_allocation_invalid')
                data += chunk
            try:
                text = data.decode('ascii').strip()
            except UnicodeError as exc:
                raise SessionError('display_allocation_invalid') from exc
            if not text.isdecimal() or not 0 <= int(text) <= 65535:
                raise SessionError('display_allocation_invalid')
            self.env['DISPLAY'] = ':' + str(int(text))
            (self.state / 'display').write_text(self.env['DISPLAY'] + '\n')
            self.report['display'] = self.env['DISPLAY']
        finally:
            os.close(read_fd)
            if write_fd is not None:
                os.close(write_fd)

    def capture(self) -> dict[int, dict]:
        table = process_table()
        if not getattr(table, 'complete', True):
            self.inventory_reasons.update(getattr(table, 'reasons', {'inventory_incomplete'}))
        # A bounded inventory may omit a still-owned process. Re-read known
        # identities individually; never retire them merely because of omission.
        self.unknown_identities.clear()
        # Direct Popen custody is independent of the global census. An
        # unreaped child cannot be replaced by a recycled numeric PID while
        # this supervisor remains its only wait owner.
        for process in self.processes.values():
            if process.pid not in self.root_identities and getattr(process, 'returncode', None) is None:
                try:
                    row = read_process(process.pid)
                    self.root_identities[process.pid] = row['start']
                    self.identities[process.pid] = row['start']
                except (OSError, ValueError, IndexError):
                    self.unknown_identities.add(process.pid)
                    self.inventory_reasons.add('owned_child_identity_unavailable')
        for pid in self.identities:
            if pid not in table:
                try:
                    table[pid] = read_process(pid)
                except OSError as exc:
                    if exc.errno not in (errno.ENOENT, errno.ESRCH):
                        self.unknown_identities.add(pid)
                except (ValueError, IndexError):
                    self.unknown_identities.add(pid)
        self.identities = {pid: start for pid, start in self.identities.items()
                           if pid in self.unknown_identities or (pid in table and table[pid]['start'] == start)}
        roots = {pid for pid, start in self.root_identities.items()
                 if pid in table and table[pid]['start'] == start}
        owned = roots | (set(self.identities) & table.keys())
        sessions = roots | {table[pid]['session'] for pid in self.identities
                            if pid in table and table[pid]['session'] in self.root_identities
                            and (table[pid]['session'] not in table
                                 or table[table[pid]['session']]['start']
                                 == self.root_identities[table[pid]['session']])}
        for _ in range(32):
            children = {pid for pid, r in table.items()
                        if r['parent'] in owned or r['session'] in sessions}
            if children.issubset(owned):
                break
            owned |= children
        for pid in owned:
            if pid in table:
                self.identities.setdefault(pid, table[pid]['start'])
        current_roots = {p.pid for p in self.processes.values()}
        self.root_identities = {pid: start for pid, start in self.root_identities.items()
                                if pid in current_roots or pid in sessions}
        return {pid: table[pid] for pid, start in self.identities.items()
                if pid in table and table[pid]['start'] == start}

    def spawn(self, name: str, command: list[str], *, pass_fds: tuple = ()) -> subprocess.Popen:
        if name in self.logs:
            self.logs[name].close()
        log = (self.state / (name + '.log')).open('x')
        self.logs[name] = log
        stderr = subprocess.STDOUT
        if name.startswith('probe-'):
            stderr = (self.state / (name + '.stderr.log')).open('x')
            self.logs[name + '-stderr'] = stderr
        process = subprocess.Popen(self.commands.get(name, command), env=self.env, stdout=log,
                                   stderr=stderr, start_new_session=True, pass_fds=pass_fds)
        self.processes[name] = process
        try:
            row = read_process(process.pid)
            self.root_identities[process.pid] = row['start']
            self.identities[process.pid] = row['start']
        except (OSError, ValueError, IndexError):
            self.inventory_reasons.add('owned_child_identity_unavailable')
        self.capture()
        return process

    def check(self) -> None:
        self.capture()
        if self.cancelled:
            raise SessionError('cancelled')
        if self.inventory_reasons or self.unknown_identities:
            raise SessionError('process_inventory_incomplete')
        for name, process in self.processes.items():
            if not name.startswith('probe-') and process.poll() is not None:
                raise SessionError('component_exited:' + name)

    def probe_command(self, stage: str) -> list[str]:
        return [sys.executable, '-I', '-m', 'jevdual.linux_session', '--probe', stage,
                '--pid', str(self.processes.get('editor').pid if 'editor' in self.processes else 0),
                '--document', str(self.state / 'document.txt'),
                '--probe-events', str(self.probe_events)]

    def signal_owned(self, names: list[str], sig: int) -> None:
        observed = self.capture()
        selected = {self.processes[name].pid for name in names}
        recipients = set(observed) if names == list(self.processes) else {
            pid for pid, row in observed.items() if pid in selected or row['session'] in selected}
        # Group/ancestry observations establish scope; descriptors deliver to
        # individual members. No leader pidfd or numeric kill claims tree scope.
        for _ in range(32):
            children = {pid for pid, row in observed.items() if row.get('parent') in recipients}
            if children.issubset(recipients):
                break
            recipients |= children
        for pid, record in observed.items():
            if pid in recipients and record['state'] != 'Z':
                outcome = pin_signal(pid, record, sig)
                key = (pid, record['start'])
                if outcome['status'] in ('sent', 'exited', 'identity_changed'):
                    self.signal_failures.pop(key, None)
                else:
                    self.signal_failures[key] = outcome

    def await_probe(self, stage: str, deadline: float) -> dict:
        last = 'not_ready'
        while time.monotonic() < deadline:
            self.check()
            attempt = self.probe_counts.get(stage, 0) + 1
            self.probe_counts[stage] = attempt
            name = f'probe-{stage}-{attempt:04d}'
            self.probe_events = self.state / (name + '.events.jsonl')
            record = {'stage': stage, 'attempt': attempt, 'started': time.monotonic(),
                      'timeout': False, 'termination': [], 'result': None}
            process = self.spawn(name, self.probe_command(stage))
            record['pid'] = process.pid
            end = min(deadline, time.monotonic() + self.probe_timeout)
            try:
                while process.poll() is None and time.monotonic() < end:
                    self.check()
                    time.sleep(.03)
                if process.poll() is None:
                    last = 'probe_timeout'
                    record['timeout'] = True
                else:
                    with (self.state / (name + '.log')).open('rb') as stream:
                        text = stream.read(8193)
                    try:
                        if len(text) > 8192:
                            raise ValueError('oversized reply')
                        value = json.loads(text)
                        if not isinstance(value, dict):
                            raise TypeError('invalid reply')
                    except (ValueError, TypeError, UnicodeError):
                        value = {'ready': False, 'reason': 'invalid_probe_reply'}
                    record['result'] = value
                    if process.returncode == 0 and value.get('ready') is True:
                        last = 'ready'
                        return value
                    last = ('probe_abnormal_exit' if process.returncode != 0 and value.get('ready') is True
                            else value.get('reason', 'not_ready'))
                    if last == 'recovery_modal':
                        raise SessionError('recovery_modal')
            finally:
                try:
                    if process.poll() is None:
                        record['termination'].append({'signal': signal.SIGTERM.value,
                                                      'monotonic': time.monotonic()})
                        self.signal_owned([name], signal.SIGTERM)
                        try:
                            process.wait(timeout=min(.2, self.grace))
                        except subprocess.TimeoutExpired:
                            record['termination'].append({'signal': signal.SIGKILL.value,
                                                          'monotonic': time.monotonic()})
                            self.signal_owned([name], signal.SIGKILL)
                    code = process.wait(timeout=1)
                    record.update(returncode=code, exit_code=code if code >= 0 else None,
                                  signal=-code if code < 0 else None, wait_complete=True)
                except subprocess.TimeoutExpired:
                    record.update(returncode=None, wait_complete=False)
                    raise
                finally:
                    record['finished'] = time.monotonic()
                    record['events'] = _read_events(self.probe_events)
                    record['last_phase'] = (record['events'][-1]['phase'] if record['events'] else None)
                    record['reason'] = last
                    _json(self.state / (name + '.json'), record)
                    # Retain evidence on disk, but not open handles for every
                    # health probe over an arbitrarily long session.
                    for key in (name, name + '-stderr'):
                        self.logs.pop(key).close()
                    if process.returncode is not None:
                        self.processes.pop(name)
            time.sleep(min(.1, max(0, deadline - time.monotonic())))
        raise SessionError(stage + ':' + str(last))

    def cleanup(self) -> dict:
        self.signal_owned(list(self.processes), signal.SIGTERM)
        end = time.monotonic() + self.grace
        while time.monotonic() < end:
            for process in self.processes.values():
                process.poll()  # only reap direct children whose Popen handles we own
            if not any(r['state'] != 'Z' for r in self.capture().values()):
                break
            time.sleep(.03)
        alive = self.capture()
        forced = [pid for pid, r in alive.items() if r['state'] != 'Z']
        if forced:
            self.signal_owned(list(self.processes), signal.SIGKILL)
        end = time.monotonic() + self.grace
        while time.monotonic() < end:
            for process in self.processes.values():
                process.poll()
            if not any(r['state'] != 'Z' for r in self.capture().values()):
                break
            time.sleep(.03)
        before_reap = self.capture()
        direct_waits = {}
        for name, process in self.processes.items():
            code = process.poll()
            if code is None:
                # /proc can expose Z before waitpid reports the child. Join
                # through its sole Popen owner within the already-running
                # cleanup deadline; another nonblocking poll is insufficient.
                try:
                    code = process.wait(timeout=max(0, end - time.monotonic()))
                except subprocess.TimeoutExpired:
                    pass
            direct_waits[name] = {'pid': process.pid, 'returncode': code, 'wait_complete': code is not None,
                                  'exit_code': code if code is not None and code >= 0 else None,
                                  'signal': -code if code is not None and code < 0 else None}
        pending_waits = [name for name, row in direct_waits.items() if not row['wait_complete']]
        remaining = self.capture()
        failures = [r for (pid, start), r in self.signal_failures.items()
                    if pid in self.unknown_identities or (pid in remaining and remaining[pid]['start'] == start)]
        for log in self.logs.values():
            log.close()
        if self.reservation:
            path, inode = self.reservation
            if path.exists() and path.stat().st_ino == inode:
                path.unlink()
        (self.state / 'started').unlink(missing_ok=True)
        return {'forced_pids': forced,
                'pre_reap_zombies': [pid for pid, r in before_reap.items() if r['state'] == 'Z'],
                'direct_waits': direct_waits, 'pending_direct_waits': pending_waits,
                'survivors': [pid for pid, r in remaining.items() if r['state'] != 'Z'],
                'zombies': [pid for pid, r in remaining.items() if r['state'] == 'Z'],
                'inventory_complete': not self.inventory_reasons and not self.unknown_identities,
                'inventory_reasons': sorted(self.inventory_reasons),
                'unknown_identities': sorted(self.unknown_identities), 'signal_failures': failures,
                'uncertain': bool(self.inventory_reasons or self.unknown_identities or failures or pending_waits),
                'signal_policy': 'individual pidfd only; no numeric fallback',
                'scope': 'group/ancestry discovery and observed identities; pinned individual delivery; container init reaps orphans'}

    def run(self) -> int:
        failure = None
        try:
            deadline = time.monotonic() + self.startup
            self.prepare()
            capability = pin_signal(os.getpid(), read_process(os.getpid()), 0)
            self.report['signal_capability'] = capability
            if capability['status'] != 'sent':
                raise SessionError('pinned_signalling_unavailable:' + capability['status'])
            self.allocate_display(deadline)
            self.transition('x11')
            self.await_probe('x11', deadline)
            self.spawn('bus', ['dbus-daemon', '--session', '--nofork', '--address=' + self.env['DBUS_SESSION_BUS_ADDRESS']])
            self.transition('session_bus')
            self.await_probe('bus', deadline)
            self.spawn('wm', ['openbox'])
            self.transition('wm')
            wm = self.await_probe('wm', deadline)
            self.report['wm_identity'] = wm
            self.await_probe('wm_ready', deadline)
            editor = self.spawn('editor', ['mousepad', '--disable-server', str(self.state / 'document.txt')])
            (self.state / 'editor.pid').write_text(str(editor.pid))
            self.transition('accessibility')
            accessibility = self.await_probe('atspi', deadline)
            self.transition('target')
            target = self.await_probe('target', deadline)
            self.transition('ready', target=target)
            (self.state / 'started').touch(mode=0o600)
            health_at = time.monotonic() + 2
            while not self.cancelled:
                self.check()
                if time.monotonic() >= health_at:
                    health = self.await_probe('atspi', time.monotonic() + self.probe_timeout)
                    if health.get('bus_identity') != accessibility.get('bus_identity'):
                        raise SessionError('accessibility_bus_changed')
                    current_wm = self.await_probe('wm', time.monotonic() + self.probe_timeout)
                    if (current_wm.get('wm_window'), current_wm.get('selection_owner')) != (
                            wm.get('wm_window'), wm.get('selection_owner')):
                        raise SessionError('window_manager_changed')
                    health_at = time.monotonic() + 2
                time.sleep(.1)
        except (SessionError, OSError, subprocess.SubprocessError) as exc:
            failure = str(exc)
        finally:
            if self.created:
                self.transition('stopping', reason=failure or 'cancelled')
                self.report['cleanup'] = self.cleanup()
                failed = (failure not in (None, 'cancelled') or bool(self.report['cleanup']['survivors'])
                          or self.report['cleanup']['uncertain'])
                self.transition('failed' if failed else 'stopped', reason=failure or 'cancelled')
        cleanup = self.report.get('cleanup') or {}
        return 1 if failure not in (None, 'cancelled') or cleanup.get('survivors') or cleanup.get('uncertain') else 0


def _x_probe(wm: bool, *, service: bool = False, phase=lambda _: None) -> dict:
    lib = ctypes.CDLL('libX11.so.6')
    lib.XOpenDisplay.argtypes, lib.XOpenDisplay.restype = [ctypes.c_char_p], ctypes.c_void_p
    lib.XCloseDisplay.argtypes = [ctypes.c_void_p]
    display = lib.XOpenDisplay(None)
    if not display:
        return {'ready': False, 'reason': 'x11_unavailable'}
    try:
        if wm:
            lib.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
            lib.XInternAtom.restype = ctypes.c_ulong
            lib.XGetSelectionOwner.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            lib.XGetSelectionOwner.restype = ctypes.c_ulong
            atom = lib.XInternAtom(display, b'WM_S0', 0)
            owner = lib.XGetSelectionOwner(display, atom)
            if not owner:
                return {'ready': False, 'reason': 'wm_unavailable'}
            ptr, ulong, integer = ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int
            lib.XDefaultRootWindow.argtypes, lib.XDefaultRootWindow.restype = [ptr], ulong
            lib.XGetWindowProperty.argtypes = [ptr, ulong, ulong, ctypes.c_long, ctypes.c_long,
                                              integer, ulong, ctypes.POINTER(ulong), ctypes.POINTER(integer),
                                              ctypes.POINTER(ulong), ctypes.POINTER(ulong), ctypes.POINTER(ptr)]
            lib.XFree.argtypes = [ptr]
            check_atom = lib.XInternAtom(display, b'_NET_SUPPORTING_WM_CHECK', 1)
            if not check_atom:
                return {'ready': False, 'reason': 'wm_ewmh_unavailable'}

            def supporting(window):
                actual, kind, count, remaining, data = ulong(), integer(), ulong(), ulong(), ptr()
                result = lib.XGetWindowProperty(display, window, check_atom, 0, 1, 0, 33,
                                                ctypes.byref(actual), ctypes.byref(kind), ctypes.byref(count),
                                                ctypes.byref(remaining), ctypes.byref(data))
                try:
                    if result or actual.value != 33 or kind.value != 32 or count.value != 1 or remaining.value or not data:
                        return None
                    return ctypes.cast(data, ctypes.POINTER(ulong))[0]
                finally:
                    if data:
                        lib.XFree(data)

            child = supporting(lib.XDefaultRootWindow(display))
            if not child or supporting(child) != child:
                return {'ready': False, 'reason': 'wm_ewmh_unavailable'}
            if service:
                # Selection/EWMH publication can precede the event loop. An
                # initial admission also needs an acknowledged MapRequest.
                # Health checks use the pure identity probe, never this window.
                phase('wm_map')
                if not _wm_servicing(lib, display):
                    return {'ready': False, 'reason': 'wm_not_servicing'}
                if lib.XGetSelectionOwner(display, atom) != owner or supporting(child) != child:
                    return {'ready': False, 'reason': 'wm_identity_changed'}
                phase('wm_map_acknowledged')
            return {'ready': True, 'wm_window': child, 'selection_owner': owner}
        return {'ready': True}
    finally:
        lib.XCloseDisplay(display)


def _wm_servicing(lib, display) -> bool:
    """One disposable client, before the editor exists; no user input."""
    ptr, ulong, integer = ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int
    root = lib.XDefaultRootWindow(display)
    lib.XCreateSimpleWindow.argtypes = [ptr, ulong, integer, integer, ctypes.c_uint,
                                        ctypes.c_uint, ctypes.c_uint, ulong, ulong]
    lib.XCreateSimpleWindow.restype = ulong
    lib.XMapWindow.argtypes = lib.XDestroyWindow.argtypes = [ptr, ulong]
    lib.XStoreName.argtypes = [ptr, ulong, ctypes.c_char_p]
    lib.XSync.argtypes = [ptr, integer]
    window = lib.XCreateSimpleWindow(display, root, 0, 0, 32, 32, 0, 0, 0)
    if not window:
        return False

    def values(target, atom, expected):
        actual, kind, count, remaining, data = ulong(), integer(), ulong(), ulong(), ptr()
        status = lib.XGetWindowProperty(display, target, atom, 0, 1024, 0, expected,
                                        ctypes.byref(actual), ctypes.byref(kind), ctypes.byref(count),
                                        ctypes.byref(remaining), ctypes.byref(data))
        try:
            if status or actual.value != expected or kind.value != 32 or remaining.value or not data:
                return []
            return list(ctypes.cast(data, ctypes.POINTER(ulong))[:count.value])
        finally:
            if data:
                lib.XFree(data)

    try:
        state = lib.XInternAtom(display, b'WM_STATE', 0)
        clients = lib.XInternAtom(display, b'_NET_CLIENT_LIST', 0)
        lib.XStoreName(display, window, b'Footwork readiness probe')
        lib.XMapWindow(display, window)
        lib.XSync(display, 0)
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            if values(window, state, state)[:1] == [1] and window in values(root, clients, 33):
                return True
            time.sleep(.02)
        return False
    finally:
        lib.XDestroyWindow(display, window)
        lib.XSync(display, 0)


def _read_events(path: Path) -> list[dict]:
    try:
        with path.open('rb') as stream:
            data = stream.read(16385)
        if len(data) > 16384:
            return []
        events = [json.loads(line) for line in data.splitlines()]
        if len(events) > 64 or any(set(e) != {'phase', 'monotonic'}
                                   or not isinstance(e['phase'], str) or len(e['phase']) > 64
                                   or not isinstance(e['monotonic'], (int, float)) for e in events):
            return []
        return events
    except (OSError, ValueError, TypeError):
        return []


class ProbeEvents:
    """Fixed, text-free phases on a separate bounded diagnostic channel."""
    def __init__(self, path: Path | None):
        self.path, self.count = path, 0

    def __call__(self, phase: str) -> None:
        if self.path is not None and self.count < 64:
            with self.path.open('a') as stream:
                stream.write(json.dumps({'phase': phase, 'monotonic': time.monotonic()}) + '\n')
            self.count += 1


async def _target_probe(pid: int, document: Path, phase=lambda _: None) -> dict:
    phase('import')
    import cua_driver as cd

    from jevdual.linux_documents import bind
    from jevdual.native import NativeBridge

    phase('create')
    driver = cd.CuaDriver.create(embedded=True)
    try:
        phase('list_windows')
        windows = (await driver.list_windows(cd.ListWindowsInput(pid=pid, on_screen_only=True))).windows
        if len(windows) != 1:
            return {'ready': False, 'reason': 'window_not_unique', 'window_count': len(windows)}
        phase('observe')
        snapshot = await NativeBridge(driver, pid, windows[0].window_id).observe()
        phase('fixture_check')
        if 'previous session did not end normally' in snapshot.menu.page_text.casefold():
            return {'ready': False, 'reason': 'recovery_modal'}
        fields = [c for c in snapshot.menu.candidates if 'append' in c.operations]
        if len(fields) != 1 or snapshot.values.get(fields[0].id) != FIXTURE:
            return {'ready': False, 'reason': 'exact_text_target_unavailable'}
        phase('document_bind')
        bind(pid, windows[0].window_id, document)
        return {'ready': True, 'pid': pid, 'window_id': windows[0].window_id,
                'document': str(document), 'exact_fixture_text': True}
    finally:
        phase('shutdown')
        await driver.shutdown()
        phase('shutdown_returned')


def probe(stage: str, pid: int, document: Path, phase=lambda _: None) -> dict:
    if stage in ('x11', 'wm', 'wm_ready'):
        return _x_probe(stage != 'x11', service=stage == 'wm_ready', phase=phase)
    if stage == 'bus':
        from jeepney import DBusAddress, new_method_call
        from jeepney.io.blocking import open_dbus_connection
        connection = open_dbus_connection(bus=os.environ['DBUS_SESSION_BUS_ADDRESS'])
        try:
            reply = connection.send_and_get_reply(new_method_call(
                DBusAddress('/org/freedesktop/DBus', bus_name='org.freedesktop.DBus',
                            interface='org.freedesktop.DBus'), 'GetId'), timeout=1)
            return {'ready': bool(reply.body)}
        finally:
            connection.close()
    if stage == 'atspi':
        from jevdual.linux_ax import _Bus
        with _Bus() as bus:
            return {'ready': bool(bus.identity), 'bus_identity': bus.identity}
    return asyncio.run(_target_probe(pid, document, phase))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('state', type=Path, nargs='?')
    parser.add_argument('--display', type=int)
    parser.add_argument('--rootless-prefix', type=Path)
    parser.add_argument('--startup-timeout', type=float, default=30)
    parser.add_argument('--probe-timeout', type=float, default=3)
    parser.add_argument('--cleanup-grace', type=float, default=2)
    parser.add_argument('--probe', choices=['x11', 'bus', 'wm', 'wm_ready', 'atspi', 'target'])
    parser.add_argument('--pid', type=int, default=0)
    parser.add_argument('--document', type=Path, default=Path('/nonexistent'))
    parser.add_argument('--probe-events', type=Path)
    args = parser.parse_args()
    if args.probe:
        phase = ProbeEvents(args.probe_events)
        phase('probe_enter')
        try:
            value = probe(args.probe, args.pid, args.document, phase)
        except Exception as exc:  # noqa: BLE001 - isolated child preserves typed failure; no input
            value = {'ready': False, 'reason': type(exc).__name__}
            from jevdual.ax import AXError
            if isinstance(exc, AXError):
                # AXError.reason is a fixed adapter code, never its message,
                # which can contain target text. Bound even this diagnostic.
                code = exc.reason
                if isinstance(code, str) and len(code) <= 64 and code.replace('_', '').isascii() and code.replace('_', '').isalpha():
                    value['error_code'] = code
        phase('probe_returned')
        print(json.dumps(value), flush=True)
        phase('result_emitted')
        return 0 if value.get('ready') else 1
    if (sys.platform != 'linux' or args.state is None or args.state.exists()
            or any(not 0 < n <= 120 for n in [args.startup_timeout, args.probe_timeout, args.cleanup_grace])
            or (args.display is not None and not 0 <= args.display <= 65535)):
        parser.error('Linux, fresh state, bounded positive deadlines and a valid display are required')
    session = Session(args.state, display=args.display, prefix=args.rootless_prefix,
                      startup=args.startup_timeout, probe_timeout=args.probe_timeout, grace=args.cleanup_grace)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: setattr(session, 'cancelled', True))
    return session.run()


if __name__ == '__main__':
    raise SystemExit(main())
