"""Launch and verify a Chrome that Footwork owns, reached only through its own DevTools endpoint.

Chrome starts with ``--remote-debugging-port=0`` and writes the chosen port and browser path to
``DevToolsActivePort`` in a fresh, private profile directory created exclusively for this launch.
Existing paths, including symlinks, are refused before any file is changed. After connecting, the endpoint must
report the launched pid as its browser process and that pid must still have its launch start time.
Only a handle created here grants cleanup authority; a discovered process never does.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


class LaunchRefused(RuntimeError):
    """The browser could not be launched or verified; nothing was sent to any page."""

    dispatched = False

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class CleanupUnverified(RuntimeError):
    """Owned cleanup could not establish the bounded known-process postcondition."""

    code = "browser_cleanup_unverified"


@dataclass(frozen=True)
class OwnedChrome:
    pid: int
    #: process start time, the incarnation that pins this pid
    incarnation: float
    executable: str
    profile_dir: Path
    headless: bool
    #: ``ws://127.0.0.1:<port><path>`` from this launch's DevToolsActivePort
    browser_url: str
    process: subprocess.Popen = field(compare=False, repr=False)

    def alive(self) -> bool:
        import psutil

        try:
            return self.process.poll() is None and psutil.Process(self.pid).create_time() == self.incarnation
        except psutil.Error:
            return False


def chrome_args(executable: str, profile_dir: Path, *, headless: bool) -> list[str]:
    args = [
        executable, f"--user-data-dir={profile_dir}", "--remote-debugging-port=0",
        "--remote-debugging-address=127.0.0.1", "--no-first-run", "--no-default-browser-check",
        "--window-size=1200,900",
    ]
    if headless:
        args.append("--headless=new")
    return [*args, "about:blank"]


def _read_port_file(path: Path, *, not_before: float) -> tuple[int, str] | None:
    try:
        if path.stat().st_mtime < not_before:
            return None
        lines = path.read_text().splitlines()
    except OSError:
        return None
    if len(lines) < 2 or not lines[0].isdigit() or not lines[1].startswith("/devtools/browser/"):
        return None
    return int(lines[0]), lines[1]


def launch(executable: str, profile_dir: Path, *, headless: bool = True, timeout: float = 15.0) -> OwnedChrome:
    import psutil

    try:
        profile_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    except OSError as exc:
        raise LaunchRefused(
            "browser_profile_unavailable", "Chrome requires a fresh private profile directory"
        ) from exc
    port_file = profile_dir / "DevToolsActivePort"
    started = time.time() - 1.0  # filesystem timestamps can be coarser than time.time()
    process = subprocess.Popen(
        chrome_args(executable, profile_dir, headless=headless),
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    try:
        incarnation = psutil.Process(process.pid).create_time()
        deadline = time.monotonic() + timeout
        while True:
            if process.poll() is not None:
                # e.g. the profile belongs to a running Chrome, which took the launch over and exited us
                raise LaunchRefused("browser_launch_failed", f"Chrome exited ({process.returncode}) before readiness")
            found = _read_port_file(port_file, not_before=started)
            if found is not None:
                break
            if time.monotonic() >= deadline:
                raise LaunchRefused("browser_launch_failed", "Chrome wrote no DevToolsActivePort in time")
            time.sleep(0.05)
        port, path = found
        return OwnedChrome(
            pid=process.pid, incarnation=incarnation, executable=executable, profile_dir=profile_dir,
            headless=headless, browser_url=f"ws://127.0.0.1:{port}{path}", process=process,
        )
    except BaseException as exc:
        try:
            _terminate(process)
        except CleanupUnverified as cleanup:
            exc.add_note(str(cleanup))
        raise


def _terminate(process: subprocess.Popen, *, incarnation: float | None = None) -> None:
    """Stop the root and descendants inventoried while its custody can still be checked.

    A process group is signaled only before this Popen root is reaped. Captured descendants are
    subsequently addressed individually, with a fresh start-time check and psutil's reuse guard.
    This bounded inventory cannot prove absence of a concurrently forked or escaped descendant.
    """
    import psutil

    if process.poll() is not None:
        raise CleanupUnverified("the browser root exited before descendants could be inventoried")
    try:
        root = psutil.Process(process.pid)
        if incarnation is not None and root.create_time() != incarnation:
            raise CleanupUnverified("the browser root changed incarnation before cleanup")
        descendants = []
        for child in root.children(recursive=True):
            try:
                descendants.append((child.pid, child.create_time()))
            except psutil.NoSuchProcess:
                pass  # an ordinary child exit during inventory requires no signal
    except psutil.Error as exc:
        raise CleanupUnverified("the browser descendant inventory was unavailable") from exc

    def live(identity: tuple[int, float]):
        try:
            child = psutil.Process(identity[0])
            if child.create_time() != identity[1] or child.status() == psutil.STATUS_ZOMBIE:
                return None
            return child
        except psutil.NoSuchProcess:
            return None
        except psutil.Error as exc:
            raise CleanupUnverified("a captured descendant could not be revalidated") from exc

    def signal_children(sig: int) -> None:
        for identity in descendants:
            child = live(identity)
            if child is not None:
                try:
                    child.send_signal(sig)
                except psutil.NoSuchProcess:
                    pass
                except psutil.Error as exc:
                    raise CleanupUnverified("a captured descendant could not be stopped") from exc

    def wait_children(timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while any(live(identity) is not None for identity in descendants):
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.02)
        return True

    # poll can reap a newly exited root: never signal its numeric group after that point.
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        # Popen keeps its unreaped direct child's identity; do not signal the group here.
        process.kill()
        process.wait(timeout=3)
    signal_children(signal.SIGTERM)
    if not wait_children(3):
        signal_children(signal.SIGKILL)
        if not wait_children(3):
            raise CleanupUnverified("captured browser descendants survived bounded cleanup")


def stop(chrome: OwnedChrome) -> None:
    """Stop this launched root and its captured descendants, or report cleanup uncertainty.

    This is not an atomic process-tree inventory or proof against daemon escape. The caller owns
    removal of the fresh profile directory after cleanup; no external profile is removed here.
    """
    _terminate(chrome.process, incarnation=chrome.incarnation)


async def verify_endpoint(conn, chrome: OwnedChrome) -> None:
    """Refuse unless the endpoint's browser process is the launched pid at its launch incarnation."""
    from .transport import CdpError

    try:
        info = await conn.send("SystemInfo.getProcessInfo", timeout=5.0)
    except CdpError as exc:
        raise LaunchRefused("browser_identity_unverified", f"the endpoint cannot report its process: {exc}") from exc
    browsers = [p.get("id") for p in info.get("processInfo") or [] if p.get("type") == "browser"]
    if browsers != [chrome.pid]:
        raise LaunchRefused(
            "browser_identity_mismatch", f"the endpoint's browser process {browsers} is not the launched pid"
        )
    if not chrome.alive():
        raise LaunchRefused("browser_identity_mismatch", "the launched browser exited or changed incarnation")
