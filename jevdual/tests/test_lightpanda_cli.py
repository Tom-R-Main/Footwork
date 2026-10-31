"""Public entrypoint and the no-input boundary of the Lightpanda read-only lane."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shlex
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from jevdual import lightpanda_cli


def command(*args):
    configured = os.environ.get("FOOTWORK_EXECUTABLE")
    entry = shlex.split(configured) if configured else [sys.executable, "-m", "jevdual.cli"]
    return [*entry, "--json", *args]


def cli(*args, expected=0):
    result = subprocess.run(command(*args), capture_output=True, text=True, timeout=65, check=False)
    envelope = json.loads(result.stdout)
    assert result.returncode == envelope["exit_code"] == expected, envelope
    assert envelope["effect_verification"] == "not_asserted"
    return envelope["data"]


def test_installed_lightpanda_discovery_is_an_explicit_readonly_profile():
    profile = cli("tools")["surfaces"]["browser"]["lightpanda"]
    assert profile["commands"] == ["read", "guide", "artifact"]
    assert profile["typing"] == "disabled" and profile["cua_required"] is False
    assert profile["model_required"] is False and profile["desktop_required"] is False
    schema = cli("schema", "browser", "lightpanda", "read")
    assert schema["command"] == ["browser", "lightpanda", "read"]
    assert {a["name"] for a in schema["arguments"]} >= {"url", "executable", "work_dir", "timeout"}
    guide = cli("browser", "lightpanda", "guide")
    assert guide["completion"] == "not_asserted; observation is not task completion"
    assert "pending" in guide["install"]
    doctor = cli("doctor")["browser_profiles"]["lightpanda"]
    assert doctor["runtime_qualification"] == "not_checked"
    assert doctor["typing"] == "disabled"


def test_artifact_lookup_never_downloads_or_builds():
    pin = cli("browser", "lightpanda", "artifact", "--platform", "linux-x86_64")
    assert pin["asset_id"] == 694146173
    assert pin["sha256"] == "19f3fee25fb14bb75a1e0c1e0f8ab9cce842950544e4a144fbad3884c94b98a3"
    assert pin["available"] is True


@pytest.mark.parametrize("method", ["click", "type", "navigate", "evaluate", "connect"])
def test_input_and_raw_protocol_routes_are_absent(method):
    cli("browser", "lightpanda", method, expected=2)


@pytest.mark.parametrize("url", ["file:///private/input", "javascript:alert(1)", "https://u:p@example.test/"])
def test_invalid_url_refuses_before_engine_start(url):
    result = cli("browser", "lightpanda", "read", url, expected=3)
    assert result["code"] == "lightpanda_url_invalid"
    assert result["capture_completed"] is False
    assert result["input"] == {"supported": False, "dispatched": False}


def test_unpinned_binary_cannot_execute(tmp_path, monkeypatch):
    from jevdual.effectors.lightpanda import artifacts

    marker = tmp_path / "executed"
    binary = tmp_path / "unqualified"
    binary.write_text(f"#!/bin/sh\ntouch {marker}\n")
    binary.chmod(0o700)
    monkeypatch.setattr(artifacts, "host_key", lambda: "linux-x86_64")
    args = argparse.Namespace(url="http://127.0.0.1/", executable=str(binary), work_dir=None, timeout=1)
    result, code = asyncio.run(lightpanda_cli._run(args))
    assert code == 3 and result["code"] == "lightpanda_digest_mismatch"
    assert not marker.exists()


def test_unqualified_platform_refuses_before_signal_or_engine_setup(monkeypatch, capsys):
    from jevdual.effectors.lightpanda import artifacts

    monkeypatch.setattr(artifacts, "host_key", lambda: "unqualified-platform")
    monkeypatch.setattr(asyncio, "run", lambda *args: pytest.fail("unsupported platform started runtime setup"))
    assert lightpanda_cli.main(["read", "http://127.0.0.1/"]) == 3
    result = json.loads(capsys.readouterr().out)
    assert result["code"] == "lightpanda_platform_unqualified"
    assert result["cleanup"]["status"] == "not_started"


@pytest.mark.parametrize("status", ["bounded_owned_processes_stopped", "unverified"])
def test_startup_cleanup_receipt_survives_without_returned_handle(tmp_path, monkeypatch, status):
    from jevdual.effectors.lightpanda import artifacts, launch

    binary = tmp_path / "engine"
    binary.write_text("fixture")
    pin = {"available": True, "sha256": "a" * 64, "bytes": binary.stat().st_size}
    monkeypatch.setattr(artifacts, "artifact", lambda: pin)
    failure = RuntimeError("injected post-spawn identity failure")
    failure.process_started = True
    failure.owned_cleanup = {"status": status}

    def failed_start(*args, **kwargs):
        raise failure

    monkeypatch.setattr(launch, "start", failed_start)
    args = argparse.Namespace(url="http://127.0.0.1/", executable=str(binary),
                              work_dir=tmp_path / "fresh", timeout=1)
    result, code = asyncio.run(lightpanda_cli._run(args))
    assert code == 3 and result["capture_completed"] is False
    assert result["process_started"] is True
    assert result["cleanup"]["status"] == status


@pytest.mark.parametrize("timeout", ["nan", "inf", "0", "61", "-1"])
def test_capture_deadline_is_finite_and_bounded(timeout):
    cli("browser", "lightpanda", "read", "http://127.0.0.1/", "--timeout", timeout, expected=2)


@pytest.fixture
def engine():
    value = os.environ.get("FOOTWORK_LIGHTPANDA_EXECUTABLE")
    if not value or not Path(value).is_file():
        pytest.skip("requires the explicitly pinned external Lightpanda executable")
    return str(Path(value).resolve())


@pytest.fixture
def fixture_site():
    posts = []
    loading = threading.Event()
    loading.requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            loading.requests.append(self.path)
            loading.set()
            if self.path == "/slow":
                time.sleep(3)
            password = "LP_PRIVATE_SHORT" if self.path == "/short" else "LP_PRIVATE_MUCH_LONGER_SECRET"
            html = f'''<!doctype html><title>Read-only fixture</title>
<h1>Public heading</h1><p id="ready">Waiting</p><a href="/next">Next item</a>
<button type="button" onclick="fetch('/input-effect',{{method:'POST'}})">Commit fixture</button>
<label for="pw">Password</label><input id="pw" type="password" value="{password}">
<input value="LP_PRIVATE_TEXT"><textarea>LP_PRIVATE_TEXTAREA</textarea>
<select><option>LP_PRIVATE_OPTION</option></select>
<div contenteditable="true">LP_PRIVATE_EDITABLE</div>
<p hidden>LP_PRIVATE_HIDDEN</p><script>document.getElementById('ready').textContent='Script content ready';</script>'''
            if self.path == "/base":
                html = '<!doctype html><head><base href="https://cdn.example/reports/"></head><body><h1>Public heading</h1><a href="report">Read report</a></body>'
            elif self.path == "/frames":
                html = '<!doctype html><h1>Public heading</h1><iframe srcdoc="<p>LP_PRIVATE_CHILD</p>"></iframe><iframe src="data:text/html,LP_PRIVATE_DATA_CHILD"></iframe>'
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            try:
                self.wfile.write(html.encode())
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            posts.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", posts, loading
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


@pytest.mark.browser
def test_real_installed_read_is_semantic_and_withholds_sensitive_fields(engine, fixture_site):
    url, posts, _ = fixture_site
    results = [cli("browser", "lightpanda", "read", url + path, "--executable", engine)
               for path in ("/short", "/long")]
    for result in results:
        assert result["ok"] is True and result["capture_completed"] is True
        assert result["cleanup"]["status"] == "bounded_owned_processes_stopped"
        assert result["input"] == {"supported": False, "dispatched": False}
        assert result["completion"] == "not_asserted"
        assert set(result["protocol_methods"]) <= {
            "Target.createTarget", "Target.attachToTarget", "Target.getTargets", "Page.enable",
            "Page.navigate", "Page.getFrameTree", "DOM.getDocument",
        }
        assert result["protocol_methods"].count("Page.navigate") == 1
        observation = result["observation"]
        raw = json.dumps(observation)
        assert "Public heading" in raw and "Script content ready" in raw and "Next item" in raw
        assert "LP_PRIVATE_" not in raw
        assert observation["actions"] == [] and observation["mutation_authority"] is False
        assert observation["capture"]["atomic"] is False
    assert results[0]["observation"]["content"] == results[1]["observation"]["content"]
    assert posts == []


@pytest.mark.browser
def test_real_initial_load_timeout_closes_engine(engine, fixture_site):
    url, posts, _ = fixture_site
    result = cli("browser", "lightpanda", "read", url + "/slow", "--executable", engine,
                 "--timeout", "1", expected=3)
    assert result["code"] == "lightpanda_timeout"
    assert result["capture_completed"] is False
    assert result["cleanup"]["status"] == "bounded_owned_processes_stopped"
    assert posts == []


def _live_captured(identities):
    import psutil

    live = []
    for pid, start in identities:
        try:
            process = psutil.Process(pid)
            if process.create_time() == start and process.status() != psutil.STATUS_ZOMBIE:
                live.append(process)
        except psutil.NoSuchProcess:
            pass
    return live


@pytest.mark.browser
@pytest.mark.parametrize("fault", ["terminate_cli", "kill_engine"])
def test_real_interruption_retains_cleanup_scope_without_reconnect(engine, fixture_site, fault):
    import psutil

    url, posts, loading = fixture_site
    client = subprocess.Popen(command("browser", "lightpanda", "read", url + "/slow", "--executable", engine,
                                      "--timeout", "15"), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    identities = []
    try:
        assert loading.wait(10), "probe did not reach the real initial network load"
        root = psutil.Process(client.pid)
        children = root.children(recursive=True)
        identities = [(child.pid, child.create_time()) for child in children]
        engines = [child for child in children if child.exe() == engine]
        assert len(engines) == 1
        if fault == "terminate_cli":
            client.send_signal(signal.SIGTERM)
        else:
            engines[0].kill()  # captured actual descendant object; not a PID-file adoption
        output, error = client.communicate(timeout=20)
        envelope = json.loads(output)
        result = envelope["data"]
        assert result["capture_completed"] is False and result["input"]["dispatched"] is False
        if fault == "terminate_cli":
            assert client.returncode == 143
            assert result["code"] == "lightpanda_interrupted"
            assert result["cleanup"]["status"] == "bounded_owned_processes_stopped"
        else:
            assert client.returncode == 3
            assert result["cleanup"]["status"] == "unverified"
        assert not _live_captured(identities), "product left a captured live engine before test cleanup"
        assert loading.requests == ["/slow"] and posts == [], error
    finally:
        if client.poll() is None:
            client.kill()
            client.communicate(timeout=5)
        # Failure hygiene is after the product liveness assertion and uses only captured identities.
        for process in _live_captured(identities):
            try:
                process.kill()
            except psutil.NoSuchProcess:
                pass


@pytest.mark.browser
@pytest.mark.parametrize("path", ["/base", "/frames"])
def test_real_base_links_and_omitted_non_http_frames(engine, fixture_site, path):
    url, posts, _ = fixture_site
    result = cli("browser", "lightpanda", "read", url + path, "--executable", engine)
    assert result["ok"] is True
    observation = result["observation"]
    assert "Public heading" in observation["text"]
    assert "LP_PRIVATE_" not in json.dumps(observation)
    if path == "/base":
        link = next(row for row in observation["content"] if row["kind"] == "link")
        assert link["text"] == "Read report" and "destination" not in link
        assert observation["omitted"]["link_destinations"] == 1
    else:
        assert observation["omitted"]["excluded_subtrees"] >= 3
        # This pin reports no child frames for srcdoc/data. Their metadata
        # validation is modeled separately; DOM omission is the runtime claim.
    assert result["cleanup"]["status"] == "bounded_owned_processes_stopped"
    assert posts == []
