"""Own a disposable X11 fixture with bounded startup and shutdown.

Requires dbus-run-session and container init for orphan reaping. No global
reaper or shared desktop is managed by this script.
"""

import argparse
import json
import os
import re
import select
import signal
import subprocess
import sys
import time
from pathlib import Path

FIXTURE = "Footwork Linux fixture\n\tkeep trailing spaces  \n"
HERE = Path(__file__).resolve().parent


class Cancelled(Exception):
    pass


def incarnation(pid):
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
    except (OSError, IndexError):
        return None


class Session:
    def __init__(self, state, *, timeout=30, grace=3, probe=None):
        self.state = state.resolve()
        self.deadline = time.monotonic() + timeout
        self.grace = grace
        self.probe = probe or [sys.executable, "-I", str(HERE / "desktop_probe.py")]
        self.children = []
        self.environment = dict(os.environ)
        self.record = {"schema_version": 1, "state": "starting", "stages": [], "cleanup": None,
                       "supervisor": {"pid": os.getpid(), "start": incarnation(os.getpid())}, "processes": []}

    def write(self):
        temporary = self.state / "session.json.tmp"
        temporary.write_text(json.dumps(self.record, indent=2) + "\n")
        temporary.replace(self.state / "session.json")

    def prepare(self):
        if not self.environment.get("DBUS_SESSION_BUS_ADDRESS"):
            raise RuntimeError("dbus-run-session required")
        self.state.mkdir(mode=0o700)
        self.environment.update(NO_AT_BRIDGE="0", GTK_MODULES="atk-bridge", JEVDUAL_PURE_PY="1")
        for variable, name in [("XDG_RUNTIME_DIR", "runtime"), ("XDG_CONFIG_HOME", "config"),
                               ("XDG_CACHE_HOME", "cache"), ("XDG_DATA_HOME", "data"), ("XDG_STATE_HOME", "state")]:
            path = self.state / name
            path.mkdir(mode=0o700)
            self.environment[variable] = str(path)
        for variable, relative, fallback in [("XDG_DATA_DIRS", "usr/share", "/usr/local/share:/usr/share"),
                                              ("XDG_CONFIG_DIRS", "etc/xdg", "/etc/xdg")]:
            prefix = self.environment.get("FOOTWORK_DESKTOP_SYSROOT")
            self.environment[variable] = (str(Path(prefix).resolve() / relative) + ":" if prefix else "") + fallback
        self.record["environment"] = {key: self.environment[key] for key in
                                      ["XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME",
                                       "XDG_STATE_HOME", "XDG_DATA_DIRS", "XDG_CONFIG_DIRS"]}
        bus = self.state / "session-bus"
        bus.write_text(self.environment["DBUS_SESSION_BUS_ADDRESS"])
        bus.chmod(0o600)
        (self.state / "document.txt").write_text(FIXTURE)
        self.write()

    def spawn(self, name, argv, *, pass_fds=()):
        with (self.state / f"{name}.log").open("wb") as log:
            process = subprocess.Popen(argv, env=self.environment, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True, pass_fds=pass_fds)
        start = incarnation(process.pid)
        self.children.append((name, process, start))
        self.record["processes"].append({"name": name, "pid": process.pid, "start": start})
        self.write()
        return process

    def alive(self):
        for name, process, _ in self.children:
            if process.poll() is not None:
                raise RuntimeError(f"critical component exited: {name} ({process.returncode})")

    def remaining(self):
        self.alive()
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError("desktop readiness deadline expired")
        return remaining

    def display(self):
        read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
        try:
            self.spawn("xvfb", ["Xvfb", "-displayfd", str(write_fd), "-screen", "0", "1280x900x24",
                                "-nolisten", "tcp"], pass_fds=(write_fd,))
            os.close(write_fd)
            write_fd = None
            data = b""
            while b"\n" not in data:
                if not select.select([read_fd], [], [], min(.1, self.remaining()))[0]:
                    continue
                chunk = os.read(read_fd, 32)
                if not chunk or len(data) + len(chunk) > 16:
                    raise RuntimeError("Xvfb did not reserve a display")
                data += chunk
            value = data.decode().strip()
            if not re.fullmatch(r"[0-9]{1,5}", value):
                raise RuntimeError("invalid reserved display")
            self.environment["DISPLAY"] = ":" + value
            self.record["display"] = self.environment["DISPLAY"]
        finally:
            os.close(read_fd)
            if write_fd is not None:
                os.close(write_fd)

    def stage(self, name, *args):
        self.record["pending_stage"] = name
        self.write()
        while True:
            remaining = self.remaining()
            try:
                process = subprocess.Popen([*self.probe, name, *map(str, args)], env=self.environment,
                                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, text=True, start_new_session=True)
                try:
                    stdout, _ = process.communicate(timeout=min(5, remaining))
                except BaseException:
                    # Cancellation must not wait indefinitely in Popen.__exit__.
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.communicate(timeout=1)
                    raise
                data = json.loads(stdout) if process.returncode == 0 and len(stdout) <= 4096 else None
            except (subprocess.TimeoutExpired, ValueError):
                data = None
            self.remaining()
            expected = {"x11": "x11_connected", "wm": "wm_ready", "bus": "bus_accessible",
                        "editor": "editor_exact_target_ready"}[name]
            if isinstance(data, dict) and data.get(expected) is True:
                self.record["stages"].append({"stage": name, "proof": data})
                self.write()
                return
            time.sleep(min(.1, self.remaining()))

    def start(self):
        self.display()
        self.stage("x11")
        self.spawn("openbox", ["openbox"])
        self.stage("wm")
        self.stage("bus")
        editor = self.spawn("editor", ["mousepad", "--disable-server", str(self.state / "document.txt")])
        (self.state / "editor.pid").write_text(str(editor.pid) + "\n")
        self.stage("editor", editor.pid, self.state / "document.txt")
        self.record.update(state="ready", pending_stage=None)
        self.write()
        (self.state / "started").touch()

    def cleanup(self):
        forced, unresolved = [], []
        retained = []
        # Snapshot group members before TERM so a leader exit cannot hide a
        # TERM-ignoring grandchild. Every later signal rechecks its incarnation.
        from itertools import islice

        entries = list(islice(Path("/proc").iterdir(), 4097))
        if len(entries) > 4096:
            unresolved.append("process_inventory_truncated")
        groups = {p.pid: (name, start) for name, p, start in self.children}
        for entry in entries[:4096]:
            if not entry.name.isdigit():
                continue
            try:
                fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
                group, session = int(fields[2]), int(fields[3])
                if group in groups and group == session:
                    name, leader_start = groups[group]
                    if leader_start is not None and incarnation(group) == leader_start:
                        retained.append((name, int(entry.name), fields[19]))
            except (OSError, IndexError, ValueError):
                continue
        for name, process, start in reversed(self.children):
            if start is not None and incarnation(process.pid) == start:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            else:
                unresolved.append(name + "_leader_identity_lost")
        deadline = time.monotonic() + self.grace
        for name, process, start in reversed(self.children):
            try:
                process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                if start is not None and incarnation(process.pid) == start:
                    forced.append(name)
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    unresolved.append(name)
        for name, pid, start in retained:
            if incarnation(pid) == start:
                # A zombie has finished; its parent/init owns reaping.
                try:
                    state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
                    if state != "Z":
                        os.kill(pid, signal.SIGKILL)
                        forced.append(name + "_member")
                except (ProcessLookupError, FileNotFoundError):
                    pass
        (self.state / "started").unlink(missing_ok=True)
        self.record.update(state="stopped", cleanup={"forced": forced, "unresolved": unresolved,
                           "orphan_reaping": "container init required; not established by leader exit"})
        self.write()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", type=Path)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--grace", type=float, default=3)
    args = parser.parse_args()
    if not 0 < args.timeout <= 300 or not 0 < args.grace <= 30:
        parser.error("timeout/grace must be positive and bounded")
    session = Session(args.state, timeout=args.timeout, grace=args.grace)
    session.prepare()

    def cancel(_signal, _frame):
        raise Cancelled()

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, cancel)
    code = 0
    try:
        session.start()
        print(json.dumps({"ready": True, "display": session.record["display"]}), flush=True)
        while True:
            session.alive()
            time.sleep(.1)
    except Cancelled:
        session.record["stop_reason"] = "cancelled"
    except Exception as exc:  # noqa: BLE001 - retain startup failure then cleanup
        session.record["stop_reason"] = str(exc)[:200]
        code = 2
    finally:
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, signal.SIG_IGN)
        session.cleanup()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
