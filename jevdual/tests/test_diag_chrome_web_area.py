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


def test_footworks_own_launch_of_chrome_forces_page_accessibility():
    """FP87: four of five live filmed starts on a Chrome launched without the switch found no web area
    in eight seconds, and the request to show one was refused each time."""
    url = "http://127.0.0.1:1/"
    for args in (browser_driver._chrome_args(url), browser_driver._chrome_args(new_window=True)):
        assert args.count("--force-renderer-accessibility") == 1 == args.count(browser_driver.ACCESSIBILITY_SWITCH)
    with_url = browser_driver._chrome_args(url)
    assert with_url[-1] == url and with_url.index(browser_driver.ACCESSIBILITY_SWITCH) < with_url.index(url)


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
