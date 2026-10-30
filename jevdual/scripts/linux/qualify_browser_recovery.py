"""Installed public startup from an owned Linux Chrome with zero windows.

The no-sandbox option is explicit and confined to this disposable container
harness. Product launch arguments remain unchanged.
"""

import argparse
import asyncio
import http.server
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--state", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--chrome", type=Path, required=True)
parser.add_argument("--container-no-sandbox", action="store_true")
args = parser.parse_args()
out = args.output.resolve()
out.mkdir(mode=0o700)
manifest = json.loads((args.state / "session.json").read_text())
assert manifest["state"] == "ready"
os.environ["DISPLAY"] = manifest["display"]
os.environ["DBUS_SESSION_BUS_ADDRESS"] = (args.state / "session-bus").read_text()
os.environ.update(manifest["environment"])
os.environ["FOOTWORK_CHROME_EXECUTABLE"] = str(args.chrome.resolve())
os.environ["FOOTWORK_CHROME_PROFILE"] = str(out / "profile")
os.environ["FOOTWORK_CHROME_PORT"] = "9334"
os.environ["JEVDUAL_PURE_PY"] = "1"
os.environ["ANONYMIZED_TELEMETRY"] = "false"
os.environ["BROWSER_USE_CLOUD_SYNC"] = "false"

from jevdual import browser_driver as browser


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<title>Recovery fixture</title><h1>Owned zero-window recovery</h1>")

    def log_message(self, *_):
        pass


async def windows(pid):
    from cua_driver import CuaDriver, ListWindowsInput
    driver = CuaDriver.create(embedded=True)
    try:
        return (await driver.list_windows(ListWindowsInput(pid=pid, on_screen_only=True))).windows
    finally:
        await driver.shutdown()


server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
command = [*browser._chrome_args(str(args.chrome.resolve())), "--no-startup-window"]
if args.container_no_sandbox:
    command += ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
with (out / "chrome.log").open("w") as log:
    root = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
try:
    import psutil
    deadline = time.monotonic() + 10
    while browser.chrome_pid() != root.pid:
        assert root.poll() is None and time.monotonic() < deadline
        time.sleep(.1)
    start = psutil.Process(root.pid).create_time()
    before = asyncio.run(windows(root.pid))
    assert before == [], "fixture must begin with no visible browser window"
    result = subprocess.run([sys.executable, "-I", "-m", "jevdual.cli", "start", "Read the owned fixture",
                             "--browser", "--url", f"http://127.0.0.1:{server.server_port}/",
                             "--session", str(out / "session")], capture_output=True, text=True,
                            timeout=30, check=False)
    (out / "start.stdout").write_text(result.stdout)
    (out / "start.stderr").write_text(result.stderr)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "Owned zero-window recovery" in result.stdout
    after = asyncio.run(windows(root.pid))
    assert after and all(w.pid == root.pid for w in after)
    assert root.poll() is None and browser.chrome_pid() == root.pid
    assert psutil.Process(root.pid).create_time() == start
    receipt = {"public_start_passed": True, "initial_visible_windows": 0,
               "recovered_windows": len(after), "same_process_incarnation": True,
               "persistent_browser_survived": True, "pid": root.pid}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))
finally:
    # Only the harness-owned browser group is stopped after checking it survived startup.
    if root.poll() is None:
        os.killpg(root.pid, signal.SIGTERM)
    try:
        root.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(root.pid, signal.SIGKILL)
        root.wait(timeout=2)
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
