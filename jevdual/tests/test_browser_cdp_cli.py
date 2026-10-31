"""Installed subprocess entrypoint, independent ingress, and lost client acknowledgement."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


def command(*args):
    configured = os.environ.get("FOOTWORK_EXECUTABLE")
    return [*(shlex.split(configured) if configured else [sys.executable, "-m", "jevdual.cli"]),
            "--json", *args]


def cli(*args, success=True):
    result = subprocess.run(command(*args), capture_output=True, text=True, timeout=55, check=False)
    envelope = json.loads(result.stdout)
    assert envelope["exit_code"] == result.returncode, result.stderr
    if success:
        assert result.returncode == 0, envelope
    return envelope["data"]


def test_cdp_discovery_and_disabled_typing():
    tools = cli("tools")
    assert tools["surfaces"]["browser"]["cdp"]["cua_required"] is False
    assert tools["surfaces"]["browser"]["cdp"]["typing"].startswith("disabled")
    doctor = cli("doctor")
    assert doctor["browser_profiles"]["cdp"]["runtime_qualification"] == "not_checked"
    assert doctor["browser_profiles"]["cdp"]["desktop_required"] is False
    schema = cli("schema", "browser", "cdp", "click")
    assert {a["name"] for a in schema["arguments"]} >= {"session", "ref", "token"}
    guide = cli("browser", "cdp", "guide")
    assert "metadata" in guide["install"]
    assert guide["completion"].startswith("unverified")
    refused = subprocess.run(command("browser", "cdp", "type", "--help"), capture_output=True, text=True, check=False)
    assert refused.returncode != 0


@pytest.fixture
def page():
    records = []
    arrived = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b'''<!doctype html><title>Durable fixture</title>
<button type="button" onclick="fetch('/ingress',{method:'POST',body:'intended'});let t=Date.now()+1200;while(Date.now()<t){}">Commit fixture</button>
<button type="button" onclick="fetch('/ingress',{method:'POST',body:'sentinel'})">Sentinel</button>''')

        def do_POST(self):
            records.append(self.rfile.read(int(self.headers["Content-Length"])).decode())
            arrived.set()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"retained independently")

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/", records, arrived
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture
def workspace():
    # Unix socket paths have a small platform limit; use a deliberately short test path.
    with tempfile.TemporaryDirectory(prefix="fw-cdp-", dir="/tmp") as directory:
        yield Path(directory)


def guard_file(root):
    adapter = root / "guard.py"
    adapter.write_text('''import json,sys
r=json.load(sys.stdin)
print(json.dumps({'producer':'footwork.browser.guard','version':1,'digest':r['digest'],'probabilities':[0.01]}))
''')
    config = root / "guard-argv.json"
    config.write_text(json.dumps([sys.executable, str(adapter)]))
    return config


def start(root, url, *, guard=True):
    args = ["browser", "cdp", "start", "Commit the fixture once", "--session", str(root / "session"),
            "--authority", str(root / "authority.db"), "--url", url]
    if guard:
        args += ["--guard-command", str(guard_file(root))]
    return cli(*args)


def refs(root):
    snapshot = cli("browser", "cdp", "look", "--session", str(root / "session"))["snapshot"]
    return {row["name"]: row["ref"] for row in snapshot["refs"]}


@pytest.mark.browser
def test_installed_cli_lost_client_ack_replays_without_redispatch(workspace, page):
    root, (url, records, arrived) = workspace, page
    start(root, url)
    session = str(root / "session")
    try:
        selected = refs(root)["Commit fixture"]
        invocation = ("browser", "cdp", "click", "--session", session, "--ref", selected, "--token", "intent-1")
        client = subprocess.Popen(command(*invocation), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            assert arrived.wait(15), client.communicate(timeout=5)
            # The fixture effect exists while its handler is still executing and before CDP's reply.
            assert client.poll() is None, "probe failed to intercept the acknowledgement window"
            client.kill()
            client.communicate(timeout=5)
        finally:
            if client.poll() is None:
                client.kill()
                client.communicate(timeout=5)
        time.sleep(1.5)
        retained = cli("browser", "cdp", "status", "--session", session, "--token", "intent-1")["operations"][0]
        assert retained["state"] == "unknown" and retained["completion"] == "unverified"
        replay = cli(*invocation)
        assert replay["replayed"] is True and replay["operation"]["id"] == retained["id"]
        assert records == ["intended"]
        conflict = cli(*invocation[:-1], "intent-2", success=False)
        assert conflict["ok"] is False
        assert records == ["intended"]
        cli("browser", "cdp", "stop", "--session", session)
        time.sleep(0.3)
        recovered = cli("browser", "cdp", "recover", "--session", session, "--token", "intent-1")
        assert recovered["operations"][0]["state"] == "unknown"
        assert records == ["intended"]
        after_stop = cli(*invocation)
        assert after_stop["replayed"] is True and after_stop["operation"]["id"] == retained["id"]
    finally:
        cli("browser", "cdp", "stop", "--session", session, success=False)


@pytest.mark.browser
def test_missing_guard_refuses_before_admission(workspace, page, monkeypatch):
    root, (url, records, _) = workspace, page
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    start(root, url, guard=False)
    session = str(root / "session")
    try:
        selected = refs(root)["Commit fixture"]
        result = cli("browser", "cdp", "click", "--session", session, "--ref", selected,
                     "--token", "missing-guard", success=False)
        assert result["ok"] is False and result["dispatched"] is False
        assert cli("browser", "cdp", "status", "--session", session)["operations"] == []
        assert records == []
    finally:
        cli("browser", "cdp", "stop", "--session", session, success=False)
