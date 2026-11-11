"""Invocation-owned real Chrome probe; no existing browser/profile or user page."""
import asyncio
import json
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

from jevdual import browser_driver, browser_target
from jevdual.coordination import CoordinationError
from jevdual.effectors.cdp.transport import CdpConnection


async def probe():
    with tempfile.TemporaryDirectory(prefix="fw-catalogue-") as directory:
        profile = Path(directory) / "profile"
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        browser_driver.PROFILE_DIR, browser_driver.PORT = profile, port
        executable = browser_driver.chrome_executable()
        with (Path(directory) / "chrome.log").open("w+") as log:
            process = subprocess.Popen([
                executable, f"--user-data-dir={profile}", f"--remote-debugging-port={port}",
                "--remote-debugging-address=127.0.0.1", "--headless=new", "--no-first-run",
                "--no-default-browser-check", "about:blank",
            ], stdout=log, stderr=log, start_new_session=True)
            connection = None
            try:
                deadline = time.monotonic() + 10
                while True:
                    if process.poll() is not None:
                        log.seek(0)
                        raise RuntimeError("owned Chrome exited: " + log.read()[-1200:])
                    try:
                        with urlopen(f"http://127.0.0.1:{port}/json/version", timeout=.5) as response:
                            endpoint = json.load(response)["webSocketDebuggerUrl"]
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise
                        await asyncio.sleep(.05)
                pin, url = await browser_target.resolve(process.pid, url="about:blank")
                assert pin["pid"] == process.pid and pin["target"] and url == "about:blank"
                connection = await CdpConnection.open(endpoint)
                replacement = (await connection.send("Target.createTarget", {"url": "about:blank"}))["targetId"]
                assert replacement != pin["target"]
                assert (await connection.send("Target.closeTarget", {"targetId": pin["target"]}))["success"]
                try:
                    await browser_target.resolve(process.pid, expected=pin)
                except CoordinationError as error:
                    assert "original browser page is no longer open" in str(error)
                    return {"passed": True, "real_owned_chrome": True,
                            "initial_page_pinned": True, "same_url_replacement_refused": True,
                            "scope": "headless catalogue identity; no CUA/native/filmed qualification"}
                raise AssertionError("same-URL replacement adopted")
            finally:
                if connection is not None:
                    await connection.close()
                # Only this invocation's direct child is signaled/reaped.
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    print(json.dumps(asyncio.run(probe()), indent=2))
