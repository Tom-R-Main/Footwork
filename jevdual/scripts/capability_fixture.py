"""Prepare and hold run-owned browser/TextEdit fixtures for capability trials.

Run in a terminal; Ctrl-C closes only this process's browser and named fixture
document. Scope and fixture files remain in the explicitly supplied directory.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VALUE = "17.25 USD"
PREFIX = "Invoice report\n"
HTML = f"<!doctype html><title>Footwork invoice fixture</title><h1>Invoice</h1><p>Invoice total: {VALUE}</p>"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


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


def script(source: str, *args: str) -> str:
    return subprocess.run(
        ["osascript", "-e", source, *args], check=True, capture_output=True, text=True
    ).stdout.strip()


async def scope_for(chrome_pid: int, url: str, document: Path) -> dict:
    from cua_driver import CuaDriver, ListAppsInput, ListWindowsInput
    from jevdual import ax

    driver = CuaDriver.create()
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            apps = (await driver.list_apps(ListAppsInput())).apps
            textedit = next((a for a in apps if a.name == "TextEdit" and a.pid), None)
            browser_windows = (await driver.list_windows(ListWindowsInput(pid=chrome_pid))).windows
            native_windows = (
                (await driver.list_windows(ListWindowsInput(pid=textedit.pid))).windows if textedit else []
            )
            matching = [
                w for w in native_windows if ax.document_path(textedit.pid, w.window_id) == str(document)
            ]
            if len(browser_windows) == 1 and len(matching) == 1:
                return {
                    "task": document.parent.name,
                    "source": {"pid": chrome_pid, "window_id": browser_windows[0].window_id, "url": url},
                    "destination": {
                        "pid": textedit.pid,
                        "window_id": matching[0].window_id,
                        "document": str(document),
                    },
                }
            await asyncio.sleep(0.25)
        raise RuntimeError("Owned browser/document windows could not be identified uniquely")
    finally:
        await driver.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.run_dir.resolve()
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    document = root / "footwork-invoice-fixture.txt"
    document.write_text(PREFIX)
    (root / "fixture.html").write_text(HTML)
    http = ThreadingHTTPServer(("127.0.0.1", 0), Page)
    threading.Thread(target=http.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{http.server_port}/"
    logfile = (root / "chrome.log").open("w")
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
    try:
        subprocess.run(["open", "-a", "TextEdit", str(document)], check=True)
        scope = asyncio.run(scope_for(browser.pid, url, document))
        (root / "scope.json").write_text(json.dumps(scope, indent=2) + "\n")
        (root / "fixture.json").write_text(
            json.dumps(
                {
                    "url": url,
                    "document": str(document),
                    "value": VALUE,
                    "prefix": PREFIX,
                    "browser_pid": browser.pid,
                },
                indent=2,
            )
            + "\n"
        )
        print(json.dumps({"ready": True, "scope": str(root / "scope.json")}), flush=True)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        # This exact file was created and opened by this fixture owner.
        script(
            'on run argv\ntell application "TextEdit"\n'
            "repeat with d in documents\nif path of d is (item 1 of argv) then close d saving no\n"
            "end repeat\nend tell\nend run",
            str(document),
        )
        browser.terminate()
        try:
            browser.wait(timeout=10)
        except subprocess.TimeoutExpired:
            browser.kill()
            browser.wait(timeout=10)
        http.shutdown()
        logfile.close()


if __name__ == "__main__":
    main()
