"""Launch and verify a Chrome that Footwork owns, reached only through its own DevTools endpoint.

Chrome starts with ``--remote-debugging-port=0`` and writes the chosen port and browser path to
``DevToolsActivePort`` in its profile directory. That file is deleted before launch, so only the
launched process can write the one that names the endpoint. After connecting, the endpoint must
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

    profile_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    port_file = profile_dir / "DevToolsActivePort"
    port_file.unlink(missing_ok=True)  # a stale file must never name the endpoint
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
    except BaseException:
        _terminate(process)
        raise


def _terminate(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        process.wait(timeout=3)


def stop(chrome: OwnedChrome) -> None:
    """Stop a browser this module launched. Never called for a discovered process."""
    _terminate(chrome.process)


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
