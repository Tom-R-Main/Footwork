"""FP88: Footwork launches its Chrome so that the window shows the page's web area, and the diagnostic
that tests that apart from the probe keeps its books right. Neither test launches anything."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("cua_driver")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import diag_chrome_web_area as diag
from jevdual import browser_driver


def test_only_a_launch_asked_to_force_page_accessibility_carries_the_switch():
    """FP90: the switch is for a filmed start's launch. A launch not asked for it is argument for
    argument what it was before the switch existed, and one asked for it differs by that one argument."""
    url = "http://127.0.0.1:1/"
    switch = browser_driver.ACCESSIBILITY_SWITCH
    assert switch == "--force-renderer-accessibility"
    before = [browser_driver.chrome_executable(), f"--user-data-dir={browser_driver.PROFILE_DIR}",
              f"--remote-debugging-port={browser_driver.PORT}", "--remote-debugging-address=127.0.0.1",
              "--no-first-run", "--no-default-browser-check", "--window-size=1200,900"]
    assert browser_driver._chrome_args(url) == [*before, url]
    assert browser_driver._chrome_args(url, new_window=True) == [*before, "--new-window", url]
    assert browser_driver._chrome_args() == before
    for kw in ({}, {"new_window": True}):
        plain = browser_driver._chrome_args(url, **kw)
        forced = browser_driver._chrome_args(url, page_accessibility=True, **kw)
        assert switch not in plain and forced.count(switch) == 1
        assert [arg for arg in forced if arg != switch] == plain
        assert forced[-1] == url and forced.index(switch) < forced.index(url)


@pytest.mark.parametrize("asked", [False, True])
def test_the_launch_of_chrome_passes_the_switch_only_when_asked(monkeypatch, tmp_path, asked):
    """FP90: what reaches the process is what the caller chose; the default is no switch."""
    from jevdual import coordination

    launched: list[list[str]] = []

    def popen(args, **_):
        launched.append(list(args))
        return SimpleNamespace(pid=4243, poll=lambda: None)

    monkeypatch.setattr(browser_driver, "chrome_pid", lambda: None)
    monkeypatch.setattr(browser_driver, "PROFILE_DIR", tmp_path / "profile")
    monkeypatch.setattr(coordination, "checkpoint", lambda: None)
    monkeypatch.setattr(browser_driver.subprocess, "Popen", popen)
    monkeypatch.setattr(browser_driver, "_CHROME_LAUNCHES", {})
    url = "http://127.0.0.1:1/"
    pid, process = browser_driver._begin_chrome(url, page_accessibility=True) if asked else browser_driver._begin_chrome(url)
    assert pid == 4243 and process is not None
    assert launched == [browser_driver._chrome_args(url, page_accessibility=asked)]
    assert (browser_driver.ACCESSIBILITY_SWITCH in launched[0]) is asked


@pytest.mark.parametrize("asked", [False, True])
def test_the_holder_carries_the_choice_to_its_own_launch(monkeypatch, tmp_path, asked):
    """FP90: a session's browser is usually launched by its holder, a separate process, so the choice
    crosses a command line: spawn adds one argument, the holder's entry reads it, its bind receives it."""
    import subprocess

    from jevdual import browser_session_holder as bsh

    commands: list[list[str]] = []

    def popen(command, **_):
        commands.append(list(command))
        return SimpleNamespace(pid=4244, poll=lambda: 1, terminate=lambda: None, wait=lambda **_: 1)

    runtime = tmp_path / "runtime"
    runtime.mkdir()
    monkeypatch.setattr(bsh, "new_runtime", lambda: runtime)
    monkeypatch.setattr(subprocess, "Popen", popen)
    with pytest.raises(bsh.HolderUnavailable):
        bsh.spawn(url="http://127.0.0.1:1/", page_accessibility=True) if asked else bsh.spawn(url="http://127.0.0.1:1/")
    command, = commands
    tail = command[command.index("jevdual.browser_session_holder") + 1:]
    assert tail == ["--runtime", str(runtime), "--url", "http://127.0.0.1:1/", *(["--page-accessibility"] if asked else [])]

    bound: list[dict] = []

    async def bind(url, **kw):
        bound.append({"url": url, **kw})
        raise RuntimeError("far enough")

    monkeypatch.setattr(browser_driver, "bind_footwork_chrome", bind)
    with pytest.raises(RuntimeError, match="far enough"):
        bsh.main(tail)
    said, = bound
    assert said["url"] == "http://127.0.0.1:1/" and said["page_accessibility"] is asked


def test_a_browser_already_running_without_the_switch_is_still_footworks(monkeypatch):
    """FP88: the switch is an argument of the launch and not part of what a running browser is recognised
    by; a browser started before this change must not become one Footwork cannot find."""
    import os

    import psutil

    executable = browser_driver.chrome_executable()
    old = [executable, f"--user-data-dir={browser_driver.PROFILE_DIR}", f"--remote-debugging-port={browser_driver.PORT}",
           "--remote-debugging-address=127.0.0.1", "--no-first-run", "--no-default-browser-check",
           "--window-size=1200,900"]
    assert browser_driver.ACCESSIBILITY_SWITCH not in old
    running = SimpleNamespace(info={"pid": 4242, "cmdline": old, "exe": executable,
                                    "uids": SimpleNamespace(real=os.getuid())})
    monkeypatch.setattr(psutil, "process_iter", lambda attrs: [running])
    assert browser_driver.chrome_pid() == 4242


def test_the_diagnostics_forced_launch_uses_the_switch_footwork_launches_with():
    names = [name for name, _, _ in diag.arms()]
    assert names == ["bare", "bare_asked", "forced"]
    by_name = {name: (switches, ask) for name, switches, ask in diag.arms()}
    assert by_name == {"bare": ((), False), "bare_asked": ((), True),
                       "forced": ((browser_driver.ACCESSIBILITY_SWITCH,), False)}


def test_the_diagnostic_says_when_a_window_first_showed_a_web_area():
    none = [{"t": 0.0, "windows": 0}, {"t": 0.2, "windows": 1, "web_area": None}, {"t": 0.4, "error": "AXError: gone"}]
    later = [*none, {"t": 0.6, "windows": 1, "web_area": [22.0, 142.0, 1200.0, 813.0]}, {"t": 0.8, "web_area": None}]
    assert diag.first_seen(none) is None and diag.first_seen([]) is None and diag.first_seen(later) == 0.6
    closed = {"closed": True}
    said = diag.summary({"bare": closed | {"readings": none}, "bare_asked": closed | {"readings": none},
                         "forced": closed | {"readings": later}})
    assert said == {"first_seen_s": {"bare": None, "bare_asked": None, "forced": 0.6},
                    "forced_shows_a_web_area": True, "bare_shows_none": True, "every_browser_closed": True}
    # the second live run's kind of launch: a bare Chrome that shows one anyway is said, not hidden
    said = diag.summary({"bare": closed | {"readings": later}, "bare_asked": closed | {"readings": none},
                         "forced": {"closed": False, "readings": none}})
    assert (said["forced_shows_a_web_area"], said["bare_shows_none"], said["every_browser_closed"]) == (False, False, False)


def test_a_launch_reads_asks_and_closes_what_it_started(monkeypatch, tmp_path):
    """The diagnostic's own cleanup: the Chrome it launched is terminated and its profile removed
    whatever the readings did, and a reading that raises is recorded as one that failed."""
    did: list = []
    clock = {"t": 100.0}

    class Chrome:
        pid = 777

        def __init__(self, command, **kwargs):
            did.append(("launch", [a for a in command if a.startswith(("--force", "data:"))]))
            self.profile = next(a.split("=", 1)[1] for a in command if a.startswith("--user-data-dir="))
            assert Path(self.profile).is_dir() and "--remote-debugging-port" not in " ".join(command)
            self.gone = False

        def terminate(self):
            did.append("terminate")
            self.gone = True

        def wait(self, timeout=None):
            return 0

        def poll(self):
            return 0 if self.gone else None

    readings = iter([{"windows": 0}, RuntimeError("the window went away"), {"windows": 1, "web_area": [1.0, 2.0, 3.0, 4.0]}])

    def read(pid):
        value = next(readings, {"windows": 1, "web_area": [1.0, 2.0, 3.0, 4.0]})
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(diag.subprocess, "Popen", Chrome)
    monkeypatch.setattr(diag.time, "time", lambda: clock["t"])
    monkeypatch.setattr(diag.time, "sleep", lambda seconds: clock.update(t=clock["t"] + 1.0))
    monkeypatch.setattr(diag, "_read", read)
    monkeypatch.setattr(diag, "_ask", lambda pid: [{"attribute": "AXManualAccessibility", "set_error": -25205}])
    from jevdual import ax

    monkeypatch.setattr(ax, "_attr", lambda el, name: [])
    found = diag.launch("forced", (browser_driver.ACCESSIBILITY_SWITCH,), True)
    assert did == [("launch", [browser_driver.ACCESSIBILITY_SWITCH, diag.PAGE]), "terminate"]
    assert found["closed"] is True and found["profile_removed"] is True and found["pid"] == 777
    assert [r["t"] for r in found["readings"]] == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    assert found["readings"][1]["error"] == "RuntimeError: the window went away" and found["first_seen_s"] == 2.0
    assert len(found["asks"]) == 6 and found["asks"][0]["answers"][0]["set_error"] == -25205
    assert found["window_at_the_end"] == "no window"
