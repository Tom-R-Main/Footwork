"""Hold run-owned browser/TextEdit fixtures; Ctrl-C performs bounded owned cleanup.

Accessibility must already be granted. Closing the exact document uses AX only;
this helper never requests an Automation or Screen Recording grant.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import signal
import stat
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import ProxyHandler, build_opener

VALUE = "17.25 USD"
PREFIX = "Invoice report\n"
HTML = f"<!doctype html><title>Footwork invoice fixture</title><h1>Invoice</h1><p>Invoice total: {VALUE}</p>"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BROWSER_STARTUP_SECONDS = 180
IDENTITY_SECONDS = 30
CLEANUP_SECONDS = 10
MAX_DOCUMENT_BYTES = 1024 * 1024


class FixtureFailure(Exception):
    def __init__(self, phase: str, reason: str, exit_code: int):
        super().__init__(reason)
        self.phase, self.reason, self.exit_code = phase, reason, exit_code


class Page(BaseHTTPRequestHandler):
    def do_GET(self):
        payload = HTML.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


def normalized_document(value) -> str | None:
    if not value:
        return None
    parts = urlsplit(str(value))
    if parts.scheme != "file" or parts.netloc not in ("", "localhost") or parts.query or parts.fragment:
        return None
    return str(Path(unquote(parts.path)).resolve())


def ax_deadline(element, deadline: float | None):
    from ApplicationServices import AXUIElementSetMessagingTimeout

    if deadline is None:
        return
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise FixtureFailure("document_cleanup", "cleanup_deadline", 6)
    error = AXUIElementSetMessagingTimeout(element, min(1.0, remaining))
    if error:
        raise FixtureFailure("document_cleanup", f"ax_timeout_refused:{error}", 6)


def ax_attribute(element, name: str, *, optional: bool = False, deadline: float | None = None):
    from ApplicationServices import AXUIElementCopyAttributeValue

    ax_deadline(element, deadline)
    error, value = AXUIElementCopyAttributeValue(element, name, None)
    # AXErrorAttributeUnsupported / AXErrorNoValue are absence only for optional attributes.
    if error in (-25205, -25212) and optional:
        return None
    if error:
        raise FixtureFailure("document_cleanup", f"ax_attribute_refused:{name}:{error}", 6)
    return value


def owned_window(app, document: Path, deadline: float | None = None):
    expected = str(document.resolve())
    matches = [
        window
        for window in ax_attribute(app, "AXWindows", deadline=deadline) or ()
        if normalized_document(ax_attribute(window, "AXDocument", optional=True, deadline=deadline))
        == expected
    ]
    if len(matches) > 1:
        raise FixtureFailure("document_cleanup", "document_ambiguous", 6)
    return matches[0] if matches else None


def press(element, deadline: float | None = None):
    from ApplicationServices import AXUIElementPerformAction

    ax_deadline(element, deadline)
    error = AXUIElementPerformAction(element, "AXPress")
    if error:
        raise FixtureFailure("document_cleanup", f"ax_press_refused:{error}", 6)


def discard_button(window, deadline: float | None = None):
    sheets = list(ax_attribute(window, "AXSheets", optional=True, deadline=deadline) or ())
    # Some TextEdit versions expose attached sheets through AXChildren instead.
    if not sheets:
        sheets = [
            child
            for child in ax_attribute(window, "AXChildren", optional=True, deadline=deadline) or ()
            if ax_attribute(child, "AXRole", optional=True, deadline=deadline) == "AXSheet"
        ]
    if not sheets:
        return None
    if len(sheets) != 1 or ax_attribute(sheets[0], "AXRole", deadline=deadline) != "AXSheet":
        raise FixtureFailure("document_cleanup", "sheet_ambiguous", 6)
    sheet = sheets[0]
    # The sheet must be attached to this exact window, never app-global.
    if ax_attribute(sheet, "AXParent", deadline=deadline) != window:
        raise FixtureFailure("document_cleanup", "sheet_not_attached", 6)
    stack, seen, matches, titles = [sheet], 0, [], set()
    while stack:
        node = stack.pop()
        seen += 1
        if seen > 400:
            raise FixtureFailure("document_cleanup", "sheet_tree_limit", 6)
        if ax_attribute(node, "AXRole", optional=True, deadline=deadline) == "AXButton":
            title = str(ax_attribute(node, "AXTitle", optional=True, deadline=deadline) or "")
            titles.add(title)
            if title in ("Don't Save", "Don’t Save", "Delete"):
                matches.append(node)
        stack.extend(ax_attribute(node, "AXChildren", optional=True, deadline=deadline) or ())
    if not {"Save", "Cancel"} <= titles:
        raise FixtureFailure("document_cleanup", "sheet_not_save_prompt", 6)
    if len(matches) != 1:
        raise FixtureFailure("document_cleanup", "discard_button_ambiguous", 6)
    return sheet, matches[0]


def close_owned_document(pid: int, document: Path) -> dict:
    from ApplicationServices import AXUIElementCreateApplication

    try:
        deadline = time.monotonic() + CLEANUP_SECONDS
        app = AXUIElementCreateApplication(pid)
        window = owned_window(app, document, deadline)
        if window is None:
            return {"status": "unknown", "reason": "document_not_observed", "pid": pid}
        close = ax_attribute(window, "AXCloseButton", optional=True, deadline=deadline)
        if close is None:
            raise FixtureFailure("document_cleanup", "close_button_missing", 6)
        if owned_window(app, document, deadline) != window:
            raise FixtureFailure("document_cleanup", "document_identity_changed", 6)
        if ax_attribute(window, "AXCloseButton", deadline=deadline) != close:
            raise FixtureFailure("document_cleanup", "close_button_changed", 6)
        press(close, deadline)
        discarded = False
        last_invalid = None
        while time.monotonic() < deadline:
            try:
                current = owned_window(app, document, deadline)
                if current is None:
                    # Do not mistake a renamed/reused window for observed disappearance.
                    if window in (ax_attribute(app, "AXWindows", deadline=deadline) or ()):
                        raise FixtureFailure("document_cleanup", "document_identity_changed", 6)
                    return {"status": "confirmed", "reason": "window_disappeared", "pid": pid}
                if current != window:
                    raise FixtureFailure("document_cleanup", "document_identity_changed", 6)
                discard = discard_button(window, deadline)
                if discard is not None and not discarded:
                    if (
                        owned_window(app, document, deadline) != window
                        or discard_button(window, deadline) != discard
                    ):
                        raise FixtureFailure("document_cleanup", "sheet_identity_changed", 6)
                    press(discard[1], deadline)
                    discarded = True
                last_invalid = None
            except FixtureFailure as exc:
                # A successful close can invalidate a previously observed child or
                # window between reads. Only that observation error is retryable,
                # only after the close press; it is never evidence of disappearance.
                # Restart from fresh AXWindows and exact identity, never repeat AXPress.
                if not (exc.reason.startswith("ax_attribute_refused:") and exc.reason.endswith(":-25202")):
                    raise
                last_invalid = exc.reason
            time.sleep(0.1)
        return {
            "status": "unknown",
            "reason": "invalid_element_unresolved" if last_invalid else "window_still_present",
            "pid": pid,
        }
    except Exception as exc:  # noqa: BLE001 - receipt boundary; independent cleanup must continue
        return {"status": "error", "reason": getattr(exc, "reason", type(exc).__name__), "pid": pid}


def wait_browser_ready(browser, profile: Path) -> dict:
    deadline = time.monotonic() + BROWSER_STARTUP_SECONDS
    opener = build_opener(ProxyHandler({}))
    while time.monotonic() < deadline:
        if browser.poll() is not None:
            raise FixtureFailure("browser_startup", "browser_exited", 3)
        try:
            lines = (profile / "DevToolsActivePort").read_text().splitlines()
            port = int(lines[0])
            if not 1 <= port <= 65535 or len(lines) != 2 or not lines[1].startswith("/devtools/browser/"):
                raise ValueError("invalid private-profile endpoint")
            with opener.open(f"http://127.0.0.1:{port}/json/version", timeout=1) as response:
                version = json.loads(response.read(65536))
            if version.get("webSocketDebuggerUrl") != f"ws://127.0.0.1:{port}{lines[1]}":
                raise ValueError("endpoint mismatch")
            if browser.poll() is not None:
                raise FixtureFailure("browser_startup", "browser_exited", 3)
            return {"status": "ready", "pid": browser.pid, "port": port}
        except (OSError, ValueError, IndexError):
            time.sleep(0.25)
    raise FixtureFailure("browser_startup", "startup_timeout", 3)


async def bounded_call(awaitable, deadline: float, phase: str):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        awaitable.close()
        raise FixtureFailure(phase, "sdk_deadline", 4 if phase == "identity" else 6)
    try:
        return await asyncio.wait_for(awaitable, timeout=remaining)
    except TimeoutError as exc:
        raise FixtureFailure(phase, "sdk_timeout", 4 if phase == "identity" else 6) from exc


async def shutdown_driver(driver, phase: str, deadline: float):
    await bounded_call(driver.shutdown(), deadline, phase)


async def textedit_pid() -> int | None:
    from cua_driver import CuaDriver, ListAppsInput

    driver = CuaDriver.create()
    deadline = time.monotonic() + 3
    try:
        apps = (await bounded_call(driver.list_apps(ListAppsInput()), deadline - 1, "document_cleanup")).apps
        pids = {a.pid for a in apps if a.name == "TextEdit" and a.pid}
        if len(pids) > 1:
            raise FixtureFailure("document_cleanup", "textedit_process_ambiguous", 6)
        return next(iter(pids), None)
    finally:
        await shutdown_driver(driver, "document_cleanup", deadline)


async def scope_for(chrome_pid: int, url: str, document: Path, browser=None) -> dict:
    from ApplicationServices import AXUIElementCreateSystemWide, AXUIElementSetMessagingTimeout
    from cua_driver import CuaDriver, ListAppsInput, ListWindowsInput
    from jevdual import ax

    driver = CuaDriver.create()
    global_ax = AXUIElementCreateSystemWide()
    try:
        deadline = time.monotonic() + IDENTITY_SECONDS
        while time.monotonic() < deadline:
            if browser is not None and browser.poll() is not None:
                raise FixtureFailure("identity", "browser_exited", 4)
            apps = (await bounded_call(driver.list_apps(ListAppsInput()), deadline, "identity")).apps
            textedit_pids = {a.pid for a in apps if a.name == "TextEdit" and a.pid}
            if len(textedit_pids) > 1:
                raise FixtureFailure("identity", "textedit_process_ambiguous", 4)
            textedit = next(iter(textedit_pids), None)
            browser_windows = (
                await bounded_call(
                    driver.list_windows(ListWindowsInput(pid=chrome_pid, on_screen_only=True)),
                    deadline,
                    "identity",
                )
            ).windows
            native_windows = (
                (
                    await bounded_call(
                        driver.list_windows(ListWindowsInput(pid=textedit, on_screen_only=True)),
                        deadline,
                        "identity",
                    )
                ).windows
                if textedit
                else []
            )
            matching = []
            for window in native_windows:
                # System-wide element timeout sets this helper process's global AX
                # default, including references created inside the product lookup.
                # Recheck the phase budget for each window and refuse late results.
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise FixtureFailure("identity", "identity_deadline", 4)
                error = AXUIElementSetMessagingTimeout(global_ax, min(1.0, remaining))
                if error:
                    raise FixtureFailure("identity", f"ax_timeout_refused:{error}", 4)
                try:
                    path = ax.document_path(textedit, window.window_id)
                    if path and str(Path(path).resolve()) == str(document.resolve()):
                        matching.append(window)
                except ax.AXError as exc:
                    if exc.reason != "window_missing":
                        raise
            if len(browser_windows) == 1 and len(matching) == 1:
                if time.monotonic() >= deadline:
                    raise FixtureFailure("identity", "identity_deadline", 4)
                if browser is not None and browser.poll() is not None:
                    raise FixtureFailure("identity", "browser_exited", 4)
                return {
                    "task": document.parent.name,
                    "source": {"pid": chrome_pid, "window_id": browser_windows[0].window_id, "url": url},
                    "destination": {
                        "pid": textedit,
                        "window_id": matching[0].window_id,
                        "document": str(document),
                    },
                }
            await asyncio.sleep(0.25)
        raise FixtureFailure("identity", "windows_not_unique", 4)
    finally:
        try:
            await shutdown_driver(driver, "identity", time.monotonic() + 2)
        finally:
            # This standalone helper owns the process default. Zero resets the
            # global default; it does not restore an unknown previous timeout.
            error = AXUIElementSetMessagingTimeout(global_ax, 0)
            if error:
                raise FixtureFailure("identity", f"ax_timeout_reset_refused:{error}", 4)


def document_snapshot(document: Path) -> dict:
    """Hash bounded actual file bytes; this says nothing about unsaved AX text."""
    directory_fd = file_fd = None
    try:
        directory_fd = os.open(document.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        file_fd = os.open(document.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode):
            return {"status": "refused", "reason": "not_regular"}
        if before.st_size > MAX_DOCUMENT_BYTES:
            return {"status": "refused", "reason": "file_too_large"}
        payload = bytearray()
        while len(payload) <= MAX_DOCUMENT_BYTES:
            chunk = os.read(file_fd, min(65536, MAX_DOCUMENT_BYTES + 1 - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) > MAX_DOCUMENT_BYTES:
            return {"status": "refused", "reason": "file_too_large"}
        after = os.fstat(file_fd)
        current = os.stat(document.name, dir_fd=directory_fd, follow_symlinks=False)
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
        if (
            identity(before) != identity(after)
            or identity(after) != identity(current)
            or len(payload) != after.st_size
        ):
            return {"status": "refused", "reason": "file_changed"}
        return {
            "status": "observed",
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    except FileNotFoundError:
        return {"status": "absent", "reason": "file_missing"}
    except OSError as exc:
        return {"status": "error", "reason": type(exc).__name__, "errno": exc.errno}
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if directory_fd is not None:
            os.close(directory_fd)


def cleanup(browser, http, thread, logfile, document: Path, *, opened: bool, pid: int | None) -> dict:
    result = {
        "document": {"status": "not_started"},
        "browser": {"status": "not_started"},
        "listener": {"status": "not_started"},
    }
    before = document_snapshot(document)
    if opened:
        try:
            observed_pid = asyncio.run(textedit_pid())
            if pid is not None and observed_pid != pid:
                raise FixtureFailure("document_cleanup", "textedit_process_changed", 6)
            pid = observed_pid
            result["document"] = (
                close_owned_document(pid, document)
                if pid
                else {"status": "unknown", "reason": "textedit_not_observed"}
            )
        except Exception as exc:  # noqa: BLE001 - receipt boundary; independent cleanup must continue
            result["document"] = {"status": "error", "reason": getattr(exc, "reason", type(exc).__name__)}
    result["document"]["file_before"] = before
    result["document"]["file_after"] = document_snapshot(document)
    if browser is not None:
        try:
            if browser.poll() is None:
                browser.terminate()
            try:
                browser.wait(timeout=10)
            except subprocess.TimeoutExpired:
                browser.kill()
                browser.wait(timeout=10)
            result["browser"] = {"status": "confirmed", "pid": browser.pid, "returncode": browser.returncode}
        except Exception as exc:  # noqa: BLE001 - receipt boundary; independent cleanup must continue
            result["browser"] = {"status": "error", "reason": type(exc).__name__, "pid": browser.pid}
    if http is not None:
        try:
            if thread is not None and thread.is_alive():
                http.shutdown()
            http.server_close()
            if thread is not None:
                thread.join(timeout=2)
                if thread.is_alive():
                    raise RuntimeError("listener_thread_alive")
            result["listener"] = {"status": "confirmed"}
        except Exception as exc:  # noqa: BLE001 - receipt boundary; independent cleanup must continue
            result["listener"] = {"status": "error", "reason": type(exc).__name__}
    if logfile is not None:
        logfile.close()
    return result


def record(root: Path, name: str, value: dict):
    (root / name).write_text(json.dumps(value, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    from ApplicationServices import AXIsProcessTrusted
    from jevdual.posture import screen_locked

    if screen_locked():
        parser.error("fixture requires an unlocked desktop; no resources created")
    if not AXIsProcessTrusted():
        parser.error("fixture requires existing Accessibility permission; no resources created")
    root = args.run_dir.resolve()
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    document = root / f"{root.name}-invoice.txt"
    browser = http = thread = logfile = pid = None
    opened, exit_code, phase = False, 0, "setup"
    try:
        document.write_text(PREFIX)
        (root / "fixture.html").write_text(HTML)
        http = ThreadingHTTPServer(("127.0.0.1", 0), Page)
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{http.server_port}/"
        logfile = (root / "chrome.log").open("w")
        phase = "browser_startup"
        browser = subprocess.Popen(
            [
                CHROME,
                f"--user-data-dir={root / 'chrome-profile'}",
                "--remote-debugging-port=0",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-networking",
                "--disable-sync",
                "--disable-component-update",
                "--new-window",
                url,
            ],
            stdout=logfile,
            stderr=logfile,
            start_new_session=True,
        )
        startup = wait_browser_ready(browser, root / "chrome-profile")
        record(root, "startup.json", startup)
        phase = "document_open"
        # Mark attempted ownership before launch, so partial opens still get cleanup.
        opened = True
        subprocess.run(["open", "-a", "TextEdit", str(document)], check=True, timeout=10)
        phase = "identity"
        scope = asyncio.run(scope_for(browser.pid, url, document, browser))
        pid = scope["destination"]["pid"]
        record(root, "scope.json", scope)
        record(
            root,
            "fixture.json",
            {
                "url": url,
                "document": str(document),
                "value": VALUE,
                "prefix": PREFIX,
                "browser_pid": browser.pid,
            },
        )
        ready = {"ready": True, "phase": "hold", "scope": str(root / "scope.json")}
        record(root, "fixture-status.json", ready)
        print(json.dumps(ready), flush=True)
        phase = "hold"
        while browser.poll() is None:
            time.sleep(1)
        raise FixtureFailure("hold", "browser_exited", 3)
    except KeyboardInterrupt:
        if phase != "hold":
            exit_code = 130
            failure = {"ready": False, "phase": phase, "reason": "interrupted", "exit_code": exit_code}
            record(root, "fixture-status.json", failure)
            print(json.dumps(failure), flush=True)
    except Exception as exc:  # noqa: BLE001 - receipt boundary; independent cleanup must continue
        exit_code = getattr(
            exc, "exit_code", 3 if phase == "browser_startup" else 4 if phase == "identity" else 5
        )
        failure = {
            "ready": False,
            "phase": getattr(exc, "phase", phase),
            "reason": getattr(exc, "reason", type(exc).__name__),
            "exit_code": exit_code,
        }
        record(root, "fixture-status.json", failure)
        print(json.dumps(failure), flush=True)
    finally:
        previous_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            shutdown = cleanup(browser, http, thread, logfile, document, opened=opened, pid=pid)
            record(root, "cleanup.json", shutdown)
            print(json.dumps({"shutdown": shutdown}), flush=True)
            if (
                any(item["status"] not in ("confirmed", "not_started") for item in shutdown.values())
                and not exit_code
            ):
                exit_code = 6
        finally:
            signal.signal(signal.SIGINT, previous_sigint)
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
