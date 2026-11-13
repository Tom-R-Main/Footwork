"""SN2: a browser start gives its URL to the browser once. Nothing here launches a browser."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("cua_driver")

from jevdual import browser_driver, session
from jevdual import browser_session_holder as bsh
from jevdual.browser_driver import BrowserEffect

URL = "http://127.0.0.1:1/order?token=single-use"


def _args(url, *, reserve=None, **filmed_options):
    """A start's arguments; filmed, under a claim whose registry reserves through ``reserve``, when given."""
    args = SimpleNamespace(mode=None, url=url, task="t", require="", authorize="", answer=None,
                           pointer_motion="off", text=0)
    if reserve is not None:
        args.mode, args.pointer_motion = "exclusive_desktop", "filmed"
        vars(args).update(filmed_options)
        args._coordination_claim = SimpleNamespace(resources=["desktop"], registry=SimpleNamespace(reserve=reserve))
    return args


def _a_start(monkeypatch, tmp_path, *, holder: bool, refused: bool = True):
    """A start whose browser is stood in for. Returns what the browser was handed, in order: the page
    its launch opens (``("launch", url)``) and each navigation (``("navigate", url)``). The navigation is
    refused, which ends the start there; with no URL, or a navigation that is not ``refused``, the first
    observation ends it. A filmed start's reading of the window is stood in for too and listed as
    ``("window read", None)``; a wait is listed as ``("wait", seconds)`` and not slept. ``handed.retired``
    counts the holders the start retired."""

    class Handed(list):
        retired = 0

    handed = Handed()

    def filmed_setup(state, args):
        handed.append(("window read", None))  # and refuses nothing

    async def no_wait(seconds):
        handed.append(("wait", seconds))

    monkeypatch.setattr(session, "_filmed_setup", filmed_setup)
    monkeypatch.setattr(session.asyncio, "sleep", no_wait)

    class Driver:
        async def shutdown(self):
            pass

    class Bridge:
        pid, window_id, tab_id, target_id, launch_identity = 77, 40335, "tab", "target", {}

        async def navigate(self, url):
            handed.append(("navigate", url))
            if refused is None:
                raise asyncio.CancelledError
            if not refused:
                return BrowserEffect("navigate", -1, url, "confirmed", summary="loaded")
            return BrowserEffect("navigate", -1, url, "refused", summary="ends the start here",
                                 error_code="stopped_for_the_test", dispatched=False)

        async def observe(self):
            raise RuntimeError("far enough")

    async def bind(url=None, *, policy=None, wrap_operations=None, page_accessibility=False):
        handed.append(("launch", url))
        return Driver(), Bridge()

    async def spawn_owned(*, url, page_accessibility=False):
        handed.append(("launch", url))
        return {"boot": "b", "pid": 4321, "start": "1.5", "runtime": str(tmp_path / "runtime"),
                "chrome_pid": 77, "window_id": 40335, "launch_identity": {}}

    async def attach(self, **_):
        self.target_id, self.tab_id = "target", "tab"
        return {}

    async def navigate(self, url):
        return await Bridge().navigate(url)

    async def observe(self):
        raise RuntimeError("far enough")

    async def retire_settled(runtime, *, expected):
        handed.retired += 1

    monkeypatch.setattr(bsh, "enabled", lambda: holder)
    monkeypatch.setattr(bsh, "spawn_owned", spawn_owned)
    monkeypatch.setattr(bsh, "retire_settled", retire_settled)
    monkeypatch.setattr(bsh.HeldDriver, "shutdown", Driver.shutdown, raising=False)
    monkeypatch.setattr(browser_driver, "bind_footwork_chrome", bind)
    monkeypatch.setattr(browser_driver.BrowserBridge, "attach", attach)
    monkeypatch.setattr(browser_driver.BrowserBridge, "navigate", navigate)
    monkeypatch.setattr(browser_driver.BrowserBridge, "observe", observe)
    return handed


@pytest.mark.parametrize("holder", [False, True])
async def test_a_start_with_a_url_gives_it_to_the_browser_once(monkeypatch, tmp_path, holder):
    """SN1: the URL was the last argument of the launch and then the target of a navigation, so a start
    that launched its browser loaded the page twice: both complete live runs of the filmed probe logged
    two documents. The launch now opens a blank page and the navigation is the one load."""
    handed = _a_start(monkeypatch, tmp_path, holder=holder)
    assert await session._start_browser(_args(URL), tmp_path) == 2  # the stand-in refuses the navigation
    assert handed == [("launch", "about:blank"), ("navigate", URL)]
    assert [what for what, url in handed if url == URL] == ["navigate"]
    assert session.START_LAUNCH_PAGE == "about:blank"


@pytest.mark.parametrize("holder", [False, True])
async def test_a_start_without_a_url_launches_as_before_and_navigates_nowhere(monkeypatch, tmp_path, holder):
    """SN2: only a start that will navigate replaces the launch's page. With no URL the launch is given
    none, as it always was, and nothing is navigated."""
    handed = _a_start(monkeypatch, tmp_path, holder=holder)
    with pytest.raises(RuntimeError, match="far enough"):
        await session._start_browser(_args(None), tmp_path)
    assert handed == [("launch", None)]


@pytest.mark.parametrize("holder", [False, True])
async def test_a_filmed_start_reads_the_window_after_its_navigation_and_reserves_after_that(monkeypatch, tmp_path, holder):
    """SN4: the filmed setup read the window between the bind and the navigation, and a window whose tab
    is on the launch's blank page showed no web area, so the one live filmed start was refused. The window
    is read when it shows the page that will be filmed: after the navigation, before the reservation."""
    handed = _a_start(monkeypatch, tmp_path, holder=holder, refused=False)

    def reserve(claim, resources):
        handed.append(("reserve", None))
        return "token"

    with pytest.raises(RuntimeError, match="far enough"):  # the first observation, after all of it
        await session._start_browser(_args(URL, reserve=reserve), tmp_path)
    # the wait is the two seconds a start gives its page to load, and the window is read after them
    assert handed == [("launch", "about:blank"), ("navigate", URL), ("wait", 2.0), ("window read", None),
                      ("reserve", None)]


@pytest.mark.parametrize("holder", [False, True])
async def test_a_filmed_start_whose_navigation_is_refused_reads_no_window_and_reserves_nothing(monkeypatch, tmp_path, holder):
    """SN5: the navigation's refusal ends a start before anything is recorded of a page it is not on."""
    handed = _a_start(monkeypatch, tmp_path, holder=holder)
    reserved: list = []
    args = _args(URL, reserve=lambda claim, resources: reserved.append(resources) or "token")
    assert await session._start_browser(args, tmp_path) == 2
    assert handed == [("launch", "about:blank"), ("navigate", URL)] and reserved == []
    assert not getattr(args, "_created_reservation", "") and handed.retired == (1 if holder else 0)


@pytest.mark.parametrize("holder", [False, True])
async def test_a_filmed_start_cancelled_at_its_navigation_reserves_nothing_and_retires_its_holder(monkeypatch, tmp_path, holder):
    """SN8: the cancellation the older test made at the navigation, which no longer follows the reservation."""
    handed = _a_start(monkeypatch, tmp_path, holder=holder, refused=None)
    reserved: list = []
    args = _args(URL, reserve=lambda claim, resources: reserved.append(resources) or "token")
    with pytest.raises(asyncio.CancelledError):
        await session._start_browser(args, tmp_path)
    assert handed == [("launch", "about:blank"), ("navigate", URL)] and reserved == []
    assert handed.retired == (1 if holder else 0) and not (tmp_path / "session.json").exists()


@pytest.mark.parametrize("holder", [False, True])
@pytest.mark.parametrize(("options", "says"), [
    ({"mode": "background_only"}, "it needs --mode exclusive_desktop"),
    ({"rest": "20"}, "--rest needs 2 numbers, got '20'"),
    ({"keep_out": "0,0,100"}, "--keep-out needs 4 numbers, got '0,0,100'"),
    ({"rest": "20,40", "keep_out": "0,0,100,100"}, "the rest position is inside the keep-out"),
])
async def test_a_filmed_start_its_own_options_refuse_hands_the_browser_nothing(monkeypatch, tmp_path, capsys, holder,
                                                                              options, says):
    """SN8: with the navigation ahead of the filmed setup, a filmed start that its own options refuse
    navigated first and was refused after, replacing the page of a browser that was already running. What
    can be refused from the arguments alone is refused before a browser is launched, bound or navigated."""
    handed = _a_start(monkeypatch, tmp_path, holder=holder, refused=False)
    reserved: list = []
    args = _args(URL, reserve=lambda claim, resources: reserved.append(resources) or "token", **options)
    assert await session._start_browser(args, tmp_path) == 2
    assert handed == [] and reserved == [] and handed.retired == 0
    said = capsys.readouterr().err
    assert said.startswith("not starting: ") and says in said, said
    assert not (tmp_path / "session.json").exists()


async def test_a_filmed_start_with_no_url_reads_the_window_the_launch_opened(monkeypatch, tmp_path):
    """SN5: with nowhere to navigate, a filmed start reads the window as it always has."""
    handed = _a_start(monkeypatch, tmp_path, holder=False)
    with pytest.raises(RuntimeError, match="far enough"):
        await session._start_browser(_args(None, reserve=lambda claim, resources: "token"), tmp_path)
    assert handed == [("launch", None), ("window read", None)]


def test_the_blank_page_reaches_the_holders_own_launch_and_a_bind_with_a_url_still_launches_on_it(monkeypatch, tmp_path):
    """SN2: the holder is a separate process, so what its launch opens crosses its command line; and the
    callers that bind with a URL and never navigate (the probes) still get a launch on that URL."""
    import subprocess

    commands: list[list[str]] = []

    def popen(command, **_):
        commands.append(list(command))
        return SimpleNamespace(pid=4244, poll=lambda: 1, terminate=lambda: None, wait=lambda **_: 1)

    runtime = tmp_path / "runtime"
    runtime.mkdir()
    monkeypatch.setattr(bsh, "new_runtime", lambda: runtime)
    monkeypatch.setattr(subprocess, "Popen", popen)
    with pytest.raises(bsh.HolderUnavailable):
        bsh.spawn(url=session.START_LAUNCH_PAGE)
    tail = commands[0][commands[0].index("jevdual.browser_session_holder") + 1:]
    assert tail == ["--runtime", str(runtime), "--url", "about:blank"]

    bound: list = []

    async def bind(url, **kw):
        bound.append(url)
        raise RuntimeError("far enough")

    monkeypatch.setattr(browser_driver, "bind_footwork_chrome", bind)
    with pytest.raises(RuntimeError, match="far enough"):
        bsh.main(tail)
    assert bound == ["about:blank"]
    assert browser_driver._chrome_args("about:blank")[-1] == "about:blank"
    assert browser_driver._chrome_args(URL)[-1] == URL and URL not in browser_driver._chrome_args()


def test_the_script_that_counts_requests_is_importable_and_launches_nothing_on_import():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import probe_start_single_navigation as probe

    assert [name for name, _ in probe.ARMS] == ["launched on the URL", "launched on a blank page"]
    assert probe.ARMS[1][1] == session.START_LAUNCH_PAGE and probe.ARMS[0][1] is None
