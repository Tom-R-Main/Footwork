"""Fixture lifecycle tests: Linux subprocesses without host display/input."""
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts/linux/desktop_session.py"
spec = importlib.util.spec_from_file_location("desktop_session", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_private_profiles_and_explicit_rootless_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "private-test-address")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/ambient/config")
    monkeypatch.setenv("FOOTWORK_DESKTOP_SYSROOT", str(tmp_path / "sysroot"))
    session = module.Session(tmp_path / "fresh")
    session.prepare()
    assert session.environment["XDG_CONFIG_HOME"] == str(tmp_path / "fresh/config")
    assert session.environment["XDG_DATA_DIRS"].startswith(str(tmp_path / "sysroot/usr/share") + ":")
    assert "private-test-address" not in (session.state / "session.json").read_text()
    assert (session.state / "session-bus").stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        session.prepare()


@pytest.mark.parametrize("program", ["import time; time.sleep(30)", "print('{}')"])
def test_stalled_or_malformed_probe_never_ready(tmp_path, monkeypatch, program):
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "fixture")
    session = module.Session(tmp_path / "failed", timeout=.25, probe=[sys.executable, "-c", program])
    session.prepare()
    start = time.monotonic()
    with pytest.raises(RuntimeError, match="deadline"):
        session.stage("wm")
    assert time.monotonic() - start < 2
    assert not (session.state / "started").exists()


@pytest.fixture
def fake_desktop(tmp_path, monkeypatch):
    if sys.platform != "linux":
        pytest.skip("Linux process identity and process-group lifecycle")
    binaries = tmp_path / "bin"
    binaries.mkdir()
    for name, body in {"Xvfb": "os.write(int(sys.argv[sys.argv.index('-displayfd')+1]), b'42\\n')",
                       "openbox": "pass", "mousepad": "pass"}.items():
        p = binaries / name
        p.write_text(f"#!{sys.executable}\nimport os,sys,time\n{body}\ntime.sleep(60)\n")
        p.chmod(0o700)
    probe = tmp_path / "desktop_probe.py"
    probe.write_text("import json,sys\nn={'x11':'x11_connected','wm':'wm_ready','bus':'bus_accessible',"
                     "'editor':'editor_exact_target_ready'}\nprint(json.dumps({n[sys.argv[1]]:True}))\n")
    monkeypatch.setenv("PATH", str(binaries) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "fixture")
    return tmp_path, probe


def test_ready_stages_and_bounded_cleanup(fake_desktop):
    root, probe = fake_desktop
    session = module.Session(root / "ready", timeout=3, grace=.2, probe=[sys.executable, str(probe)])
    session.prepare()
    try:
        session.start()
        assert session.record["display"] == ":42"
        assert [p["stage"] for p in session.record["stages"]] == ["x11", "wm", "bus", "editor"]
        assert (session.state / "started").exists()
    finally:
        session.cleanup()
    assert not (session.state / "started").exists()
    assert all(p.poll() is not None for _, p, _ in session.children)
    assert session.record["cleanup"]["unresolved"] == []


def test_term_ignoring_child_is_forced(fake_desktop):
    root, _ = fake_desktop
    session = module.Session(root / "cleanup", grace=.1)
    session.prepare()
    child = session.spawn("stubborn", [sys.executable, "-c",
        "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); print('ready',flush=True); time.sleep(60)"])
    deadline = time.monotonic() + 2
    while "ready" not in (session.state / "stubborn.log").read_text():
        assert time.monotonic() < deadline
        time.sleep(.01)
    start = time.monotonic()
    session.cleanup()
    assert time.monotonic() - start < 2
    assert child.poll() is not None
    assert "stubborn" in session.record["cleanup"]["forced"]


def test_cancellation_kills_stalled_probe(fake_desktop):
    root, probe = fake_desktop
    state = root / "cancelled"
    runner = root / "cancel.py"
    runner.write_text(f"import importlib.util\ns=importlib.util.spec_from_file_location('ds',{str(SCRIPT)!r})\n"
                      "m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n"
                      "m.HERE=__import__('pathlib').Path(__file__).parent\nraise SystemExit(m.main())\n")
    probe.write_text("import time; time.sleep(60)\n")
    process = subprocess.Popen([sys.executable, str(runner), str(state)], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 3
        while not (state / "session.json").exists() or json.loads((state / "session.json").read_text()).get("pending_stage") != "x11":
            assert time.monotonic() < deadline
            time.sleep(.02)
        process.send_signal(signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=4)
        assert process.returncode == 0, (stdout, stderr)
        record = json.loads((state / "session.json").read_text())
        assert record["state"] == "stopped" and record["stop_reason"] == "cancelled"
        assert not (state / "started").exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=2)


def test_partial_editor_readiness_never_publishes_ready(fake_desktop):
    root, probe = fake_desktop
    probe.write_text("import json,sys\nn={'x11':'x11_connected','wm':'wm_ready','bus':'bus_accessible',"
                     "'editor':'editor_exact_target_ready'}\nprint(json.dumps({n[sys.argv[1]]:sys.argv[1]!='editor'}))\n")
    session = module.Session(root / "partial", timeout=.8, grace=.1, probe=[sys.executable, str(probe)])
    session.prepare()
    try:
        with pytest.raises(RuntimeError, match="deadline"):
            session.start()
        assert session.record["pending_stage"] == "editor"
        assert not (session.state / "started").exists()
    finally:
        session.cleanup()
    assert all(p.poll() is not None for _, p, _ in session.children)


def test_critical_component_death_stops_monitor(fake_desktop):
    root, probe = fake_desktop
    session = module.Session(root / "death", timeout=3, grace=.1, probe=[sys.executable, str(probe)])
    session.prepare()
    try:
        session.start()
        _, child, _ = session.children[0]
        child.kill()
        child.wait(timeout=1)
        with pytest.raises(RuntimeError, match="critical component exited: xvfb"):
            session.alive()
    finally:
        session.cleanup()
    assert not (session.state / "started").exists()


def test_term_ignoring_grandchild_is_retained_for_cleanup(fake_desktop):
    root, _ = fake_desktop
    session = module.Session(root / "grandchild", grace=.1)
    session.prepare()
    child_code = "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); print('ready',flush=True); time.sleep(60)"
    pidfile = session.state / "grandchild.pid"
    parent_code = (f"import subprocess,sys,time,pathlib; p=subprocess.Popen([sys.executable,'-c',{child_code!r}]); "
                   f"pathlib.Path({str(pidfile)!r}).write_text(str(p.pid)); time.sleep(60)")
    session.spawn("parent", [sys.executable, "-c", parent_code])
    deadline = time.monotonic() + 2
    while not pidfile.exists() or "ready" not in (session.state / "parent.log").read_text():
        assert time.monotonic() < deadline
        time.sleep(.01)
    pid = int(pidfile.read_text())
    session.cleanup()
    deadline = time.monotonic() + 1
    while Path(f"/proc/{pid}/stat").exists():
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
        if state == "Z":
            break  # init owns orphan reaping
        assert time.monotonic() < deadline
        time.sleep(.01)
    assert "parent_member" in session.record["cleanup"]["forced"]
