"""Owned, bounded X11 qualification session; never attaches to a user's desktop.

Probes run in killable subprocesses: cancelling an asyncio thread cannot bound an
Xlib/AT-SPI call. No global reaper is installed; container init owns orphan waits.
"""
from __future__ import annotations

import argparse
import asyncio
import ctypes
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

FIXTURE = "Footwork Linux fixture\n\tkeep trailing spaces  \n"


class SessionError(RuntimeError):
    pass


def process_table() -> dict[int, dict]:
    """Bounded selected /proc facts, without command lines or environments."""
    result = {}
    for index, entry in enumerate(Path('/proc').iterdir()):
        if index >= 16384:
            break
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
            result[int(entry.name)] = {'state': fields[0], 'parent': int(fields[1]),
                                      'group': int(fields[2]), 'session': int(fields[3]), 'start': fields[19]}
        except (OSError, ValueError, IndexError):
            continue
    return result


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
        self.identities: dict[int, str] = {}
        self.root_identities: dict[int, str] = {}
        self.cancelled = False
        self.created = False
        self.reservation: tuple[Path, int] | None = None
        self.report: dict = {'ready': False, 'phase': 'created', 'transitions': [], 'cleanup': None}
        self.env = os.environ.copy()

    def transition(self, phase: str, **details) -> None:
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
        candidates = [self.display_number] if self.display_number is not None else range(90, 190)
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
            raise SessionError('display_occupied')
        address = 'unix:path=' + str(self.state / 'runtime/bus')
        self.env['DBUS_SESSION_BUS_ADDRESS'] = address
        (self.state / 'session-bus').write_text(address)
        (self.state / 'document.txt').write_text(FIXTURE)

    def capture(self) -> dict[int, dict]:
        table = process_table()
        self.identities = {pid: start for pid, start in self.identities.items()
                           if pid in table and table[pid]['start'] == start}
        roots = {pid for pid, start in self.root_identities.items()
                 if pid in table and table[pid]['start'] == start}
        owned = roots | set(self.identities)
        sessions = roots | {table[pid]['session'] for pid in self.identities
                            if table[pid]['session'] in self.root_identities
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

    def spawn(self, name: str, command: list[str]) -> subprocess.Popen:
        if name in self.logs:
            self.logs[name].close()
        log = (self.state / (name + '.log')).open('w')
        self.logs[name] = log
        process = subprocess.Popen(self.commands.get(name, command), env=self.env, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        self.processes[name] = process
        row = process_table().get(process.pid)
        if row is not None:
            self.root_identities[process.pid] = row['start']
        self.capture()
        return process

    def check(self) -> None:
        self.capture()
        if self.cancelled:
            raise SessionError('cancelled')
        for name, process in self.processes.items():
            if not name.startswith('probe-') and process.poll() is not None:
                raise SessionError('component_exited:' + name)

    def probe_command(self, stage: str) -> list[str]:
        return [sys.executable, '-I', '-m', 'jevdual.linux_session', '--probe', stage,
                '--pid', str(self.processes.get('editor').pid if 'editor' in self.processes else 0),
                '--document', str(self.state / 'document.txt')]

    def signal_owned(self, names: list[str], sig: int) -> None:
        observed = self.capture()
        for name in names:
            process = self.processes[name]
            # A session ID remains reserved by the kernel while its members live.
            if any(r['session'] == process.pid for r in observed.values()):
                try:
                    os.killpg(process.pid, sig)
                except ProcessLookupError:
                    pass
        # Also cover observed descendants which established a new process group.
        for pid, record in observed.items():
            if names == list(self.processes) and record['state'] != 'Z':
                try:
                    os.kill(pid, sig)
                except ProcessLookupError:
                    pass

    def await_probe(self, stage: str, deadline: float) -> dict:
        last = 'not_ready'
        while time.monotonic() < deadline:
            self.check()
            name = 'probe-' + stage
            process = self.spawn(name, self.probe_command(stage))
            end = min(deadline, time.monotonic() + self.probe_timeout)
            try:
                while process.poll() is None and time.monotonic() < end:
                    self.check()
                    time.sleep(.03)
                if process.poll() is None:
                    last = 'probe_timeout'
                else:
                    text = (self.state / (name + '.log')).read_bytes()[:8192]
                    try:
                        value = json.loads(text)
                    except (ValueError, UnicodeError):
                        value = {'ready': False, 'reason': 'invalid_probe_reply'}
                    if process.returncode == 0 and value.get('ready') is True:
                        return value
                    last = value.get('reason', 'not_ready')
                    if last == 'recovery_modal':
                        raise SessionError('recovery_modal')
            finally:
                self.signal_owned([name], signal.SIGKILL)
                process.wait(timeout=1)
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
        remaining = self.capture()
        for log in self.logs.values():
            log.close()
        if self.reservation:
            path, inode = self.reservation
            if path.exists() and path.stat().st_ino == inode:
                path.unlink()
        (self.state / 'started').unlink(missing_ok=True)
        return {'forced_pids': forced,
                'survivors': [pid for pid, r in remaining.items() if r['state'] != 'Z'],
                'zombies': [pid for pid, r in remaining.items() if r['state'] == 'Z'],
                'scope': 'owned process groups and observed incarnation-bound descendants; container init reaps orphans'}

    def run(self) -> int:
        failure = None
        try:
            deadline = time.monotonic() + self.startup
            self.prepare()
            self.spawn('xvfb', ['Xvfb', self.env['DISPLAY'], '-screen', '0', '1280x900x24', '-nolisten', 'tcp'])
            self.transition('x11')
            self.await_probe('x11', deadline)
            self.spawn('bus', ['dbus-daemon', '--session', '--nofork', '--address=' + self.env['DBUS_SESSION_BUS_ADDRESS']])
            self.transition('session_bus')
            self.await_probe('bus', deadline)
            self.spawn('wm', ['openbox'])
            self.transition('wm')
            self.await_probe('wm', deadline)
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
                    self.await_probe('wm', time.monotonic() + self.probe_timeout)
                    health_at = time.monotonic() + 2
                time.sleep(.1)
        except (SessionError, OSError, subprocess.SubprocessError) as exc:
            failure = str(exc)
        finally:
            if self.created:
                self.transition('stopping', reason=failure or 'cancelled')
                self.report['cleanup'] = self.cleanup()
                failed = failure not in (None, 'cancelled') or bool(self.report['cleanup']['survivors'])
                self.transition('failed' if failed else 'stopped', reason=failure or 'cancelled')
        return 1 if failure not in (None, 'cancelled') or (self.report.get('cleanup') or {}).get('survivors') else 0


def _x_probe(wm: bool) -> dict:
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
            if not lib.XGetSelectionOwner(display, atom):
                return {'ready': False, 'reason': 'wm_unavailable'}
        return {'ready': True}
    finally:
        lib.XCloseDisplay(display)


async def _target_probe(pid: int, document: Path) -> dict:
    import cua_driver as cd

    from jevdual.linux_documents import bind
    from jevdual.native import NativeBridge

    driver = cd.CuaDriver.create(embedded=True)
    try:
        windows = (await driver.list_windows(cd.ListWindowsInput(pid=pid, on_screen_only=True))).windows
        if len(windows) != 1:
            return {'ready': False, 'reason': 'window_not_unique'}
        snapshot = await NativeBridge(driver, pid, windows[0].window_id).observe()
        if 'previous session did not end normally' in snapshot.menu.page_text.casefold():
            return {'ready': False, 'reason': 'recovery_modal'}
        fields = [c for c in snapshot.menu.candidates if 'append' in c.operations]
        if len(fields) != 1 or snapshot.values.get(fields[0].id) != FIXTURE:
            return {'ready': False, 'reason': 'exact_text_target_unavailable'}
        bind(pid, windows[0].window_id, document)
        return {'ready': True, 'pid': pid, 'window_id': windows[0].window_id,
                'document': str(document), 'exact_fixture_text': True}
    finally:
        await driver.shutdown()


def probe(stage: str, pid: int, document: Path) -> dict:
    if stage in ('x11', 'wm'):
        return _x_probe(stage == 'wm')
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
    return asyncio.run(_target_probe(pid, document))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('state', type=Path, nargs='?')
    parser.add_argument('--display', type=int)
    parser.add_argument('--rootless-prefix', type=Path)
    parser.add_argument('--startup-timeout', type=float, default=30)
    parser.add_argument('--probe-timeout', type=float, default=3)
    parser.add_argument('--cleanup-grace', type=float, default=2)
    parser.add_argument('--probe', choices=['x11', 'bus', 'wm', 'atspi', 'target'])
    parser.add_argument('--pid', type=int, default=0)
    parser.add_argument('--document', type=Path, default=Path('/nonexistent'))
    args = parser.parse_args()
    if args.probe:
        try:
            value = probe(args.probe, args.pid, args.document)
        except Exception as exc:  # noqa: BLE001 - isolated child preserves typed failure; no input
            value = {'ready': False, 'reason': type(exc).__name__}
        print(json.dumps(value))
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
