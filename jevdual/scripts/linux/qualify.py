"""Qualify an installed Footwork on an owned X11 desktop, with no model calls.

Run under the installed environment's Python. The desktop-session.sh fixture
must already be running. Chrome uses --no-sandbox only inside this isolated
container harness, never as a product default. Results distinguish public CLI,
public MCP, direct driver save, and independent file evidence.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path


def cli(out: Path, name: str, *args: str) -> str:
    started = time.monotonic()
    process = subprocess.Popen([sys.executable, "-I", "-m", "jevdual.cli", *args],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    timed_out, termination = False, []
    try:
        stdout, stderr = process.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        timed_out = True
        termination.append("TERM")
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            termination.append("KILL")
            process.kill()
            stdout, stderr = process.communicate(timeout=3)
    (out / f"{name}.stdout").write_text(stdout)
    (out / f"{name}.stderr").write_text(stderr)
    (out / f"{name}.exit.json").write_text(json.dumps({
        "started": started, "finished": time.monotonic(), "returncode": process.returncode,
        "signal": -process.returncode if process.returncode < 0 else None,
        "wait_complete": True, "timeout": timed_out, "termination": termination}))
    if timed_out or process.returncode:
        raise RuntimeError(f"{name} exited {process.returncode}; timeout={timed_out}; see retained output")
    return stdout


class MCP:
    def __init__(self, scope: Path, journal: Path, out: Path, name: str):
        self.out, self.name, self.closed = out, name, False
        self.stderr = (out / f"{name}.stderr").open("w")
        self.transcript = (out / f"{name}.jsonl").open("w")
        self.process = subprocess.Popen(
            [sys.executable, "-I", "-m", "jevdual.capability.cli", "server",
             "--scope", str(scope), "--journal", str(journal)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr, text=True,
        )
        self.sequence = 0
        self.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                    "clientInfo": {"name": "linux-qualification", "version": "1"}})
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self.process.stdin.flush()

    def request(self, method: str, params: dict) -> dict:
        self.sequence += 1
        request = {"jsonrpc": "2.0", "id": self.sequence, "method": method, "params": params}
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        if not select.select([self.process.stdout], [], [], 90)[0]:
            raise TimeoutError("MCP response timed out")
        response = json.loads(self.process.stdout.readline())
        self.transcript.write(json.dumps({"request": request, "response": response}) + "\n")
        self.transcript.flush()
        if response.get("id") != self.sequence or "error" in response:
            raise RuntimeError("MCP protocol response failed")
        return response["result"]

    def tool(self, tool_name: str, **arguments) -> dict:
        result = self.request("tools/call", {"name": tool_name, "arguments": arguments})
        if result.get("isError"):
            raise RuntimeError(f"MCP {tool_name}: {result.get('structuredContent')}")
        return result["structuredContent"]

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.process.stdin.close()
        except BrokenPipeError:
            pass
        termination = []
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            termination.append("TERM")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                termination.append("KILL")
                self.process.kill()
                self.process.wait(timeout=3)
        self.stderr.close()
        self.transcript.close()
        code = self.process.returncode
        (self.out / f"{self.name}.exit.json").write_text(json.dumps({
            "returncode": code, "signal": -code if code < 0 else None,
            "termination": termination, "wait_complete": True}))
        if code != 0 or termination:
            raise RuntimeError(f"MCP {self.name} exited {code}; see retained output")


async def identities(pid: int) -> int:
    from cua_driver import CuaDriver, ListWindowsInput
    driver = CuaDriver.create(embedded=True)
    try:
        windows = (await driver.list_windows(ListWindowsInput(pid=pid, on_screen_only=True))).windows
        if len(windows) != 1:
            raise RuntimeError(f"expected one fixture window, got {len(windows)}")
        return windows[0].window_id
    finally:
        await driver.shutdown()


async def exact_text(pid: int, wid: int) -> str:
    from cua_driver import CuaDriver
    from jevdual.native import NativeBridge
    driver = CuaDriver.create(embedded=True)
    try:
        snapshot = await NativeBridge(driver, pid, wid).observe()
        fields = [c for c in snapshot.menu.candidates if "append" in c.operations]
        if len(fields) != 1:
            raise RuntimeError("expected one qualified fixture text field")
        return snapshot.values[fields[0].id]
    finally:
        await driver.shutdown()


async def save(pid: int, wid: int, out: Path):
    import dataclasses

    from cua_driver import CuaDriver
    from jevdual.native import NativeBridge
    from jevdual.posture import ExecutionPolicy
    driver = CuaDriver.create(embedded=True)
    try:
        bridge = NativeBridge(driver, pid, wid, policy=ExecutionPolicy("exclusive_desktop"))
        snapshot = await bridge.observe()
        effect = await bridge.hotkey(snapshot, ["ctrl", "s"])
        (out / "driver-save.json").write_text(json.dumps(dataclasses.asdict(effect), indent=2))
        if not effect.dispatched:
            raise RuntimeError("scoped driver save was not sent")
    finally:
        await driver.shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chrome", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(mode=0o700)  # fresh evidence only
    state = args.state.resolve()
    display = state / "display"
    os.environ["DISPLAY"] = display.read_text().strip() if display.exists() else ":99"
    os.environ["XDG_RUNTIME_DIR"] = str(state / "runtime")
    os.environ["DBUS_SESSION_BUS_ADDRESS"] = (state / "session-bus").read_text()
    os.environ["ANONYMIZED_TELEMETRY"] = "false"
    os.environ["BROWSER_USE_CLOUD_SYNC"] = "false"
    os.environ["JEVDUAL_PURE_PY"] = "1"
    os.environ["FOOTWORK_CHROME_EXECUTABLE"] = str(args.chrome.resolve())
    os.environ["FOOTWORK_CHROME_PROFILE"] = str(out / "chrome-profile")
    os.environ["FOOTWORK_CHROME_PORT"] = "9333"
    pid = int((state / "editor.pid").read_text())
    wid = asyncio.run(identities(pid))
    document = state / "document.txt"
    initial = document.read_text()
    session = str(out / "native-session")
    cli(out, "native-start", "start", "Append the owned Linux fixture", "--app", "Mousepad",
        "--pid", str(pid), "--session", session)
    appended = "CLI Unicode 🧪 café with trailing spaces  "
    cli(out, "native-append", "do", "append", "text area", appended, "--session", session)
    after_cli = initial + ("" if not initial or initial.endswith("\n") else "\n") + appended
    assert asyncio.run(exact_text(pid, wid)) == after_cli
    web = out / "web"
    web.mkdir()
    source_text = "Linux source: café 🧪"
    (web / "index.html").write_text(f'<!doctype html><meta charset="utf-8"><title>Linux qualification</title>'
                                  f'<h1>Owned fixture</h1><p>{source_text}</p>')
    handles = []
    processes = []
    mcp = None
    try:
        for name, command in (
            ("http", [sys.executable, "-I", "-m", "http.server", "8765", "--bind", "127.0.0.1", "--directory", str(web)]),
            ("chrome", [str(args.chrome.resolve()), "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
                        f"--user-data-dir={out / 'chrome-profile'}", "--remote-debugging-port=9333",
                        "--remote-debugging-address=127.0.0.1", "--no-first-run", "--no-default-browser-check",
                        "--force-renderer-accessibility", "http://127.0.0.1:8765/"]),
        ):
            log = (out / f"{name}.log").open("w")
            handles.append(log)
            processes.append(subprocess.Popen(command, stdout=log, stderr=log))
        browser_pid = processes[-1].pid
        deadline = time.monotonic() + 20
        while True:
            try:
                browser_window = asyncio.run(identities(browser_pid))
                break
            except RuntimeError:
                if time.monotonic() >= deadline or processes[-1].poll() is not None:
                    raise
                time.sleep(.2)
        browser_output = cli(out, "browser-start", "start", "Read the owned fixture", "--browser",
                             "--url", "http://127.0.0.1:8765/", "--session", str(out / "browser-session"))
        assert source_text in browser_output
        scope = {"task": "linux-qualification", "source": {"pid": browser_pid, "window_id": browser_window,
                  "url": "http://127.0.0.1:8765/"}, "destination": {"pid": pid, "window_id": wid,
                  "document": str(document)}}
        scope_path, journal = out / "scope.json", out / "operations.sqlite"
        scope_path.write_text(json.dumps(scope))
        scope_path.chmod(0o600)
        mcp = MCP(scope_path, journal, out, "mcp-first")
        source = mcp.tool("bind", name="source")
        assert source_text in source["text"]
        destination = mcp.tool("bind", name="destination")
        targets = [r["target"] for r in destination["elements"] if "append" in r["moves"]]
        assert len(targets) == 1
        request = {"target": targets[0], "text": source_text, "client_token": "linux-once"}
        first = mcp.tool("act", **request)
        assert first["state"] == "final" and first["disposition"] == "applied", first
        repeat = mcp.tool("act", **request)
        assert repeat["operation_id"] == first["operation_id"] and repeat["repeat"]
        expected = after_cli + "\n" + source_text
        assert asyncio.run(exact_text(pid, wid)) == expected
        mcp.close()
        mcp = MCP(scope_path, journal, out, "mcp-restart")
        status = mcp.tool("status", client_token="linux-once", reconcile=True)
        assert status["state"] == "final" and status["disposition"] == "applied", status
        assert status.get("current", {}).get("agreement") == "yes", status
        repeated_after_restart = mcp.tool("act", **request)
        assert repeated_after_restart["operation_id"] == first["operation_id"]
        assert repeated_after_restart["repeat"]
        assert asyncio.run(exact_text(pid, wid)) == expected
        (out / "restarted-status.json").write_text(json.dumps(status, indent=2))
        mcp.close()
        mcp = None
        asyncio.run(save(pid, wid, out))
        deadline = time.monotonic() + 5
        while document.read_text() != expected and time.monotonic() < deadline:
            time.sleep(.1)
        assert document.read_text() == expected
        (out / "expected.txt").write_text(expected)
        cli(out, "saved-artifact", "check-artifact", str(document), "--expected-file", str(out / "expected.txt"),
            "--expected-sha256", hashlib.sha256(expected.encode()).hexdigest())
        result = {"platform": sys.platform, "python": sys.version.split()[0], "public_cli_append": True,
                  "public_browser_read": True, "public_mcp_append": True, "duplicate_not_repeated": True,
                  "restart_not_repeated": True, "saved_file_exact": True,
                  "save_route": "direct NativeBridge exclusive desktop; no public model guard bypass",
                  "characters": len(expected), "sha256": hashlib.sha256(document.read_bytes()).hexdigest(),
                  "operation": first}
        (out / "receipt.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result))
    finally:
        try:
            if mcp is not None:
                mcp.close()
        finally:
            for process in reversed(processes):
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            for handle in handles:
                handle.close()


if __name__ == "__main__":
    main()
