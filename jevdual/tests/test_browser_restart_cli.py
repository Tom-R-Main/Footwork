"""Real CLI recovery after abrupt holder death at committed journal boundaries.

Only holder startup is a test shim: it wraps the real journal methods and exits
the process after their transactions commit. Look/click/status/recover and offline
replay use the actual subprocess entrypoint. This is test-owned fault injection,
not a product fault flag or evidence of graceful product cleanup.
"""

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

import psutil
import pytest

_SHIM = r"""
import asyncio,json,os,sys,time
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import urlopen
from jevdual.browser_authority import BrowserAuthority
from jevdual.browser_holder import run

directory,boundary=Path(sys.argv[1]),sys.argv[2]
method={'prepared':'admit_click','started':'start','retained':'record_execution'}[boundary]
original=getattr(BrowserAuthority,method)
def interrupted(self,*args,**kwargs):
    result=original(self,*args,**kwargs)
    operation_id=result.id if method=='admit_click' else args[0]
    ingress_before_exit=None
    if boundary=='retained':
        # Test-only barrier: the independent effect must predate holder death.
        # This read-only fixture endpoint is never consulted by product recovery.
        config=json.loads((directory/'browser.json').read_text())
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            with urlopen(urljoin(config['initial_url'],'count'),timeout=1) as response:
                ingress_before_exit=json.load(response)['count']
            if ingress_before_exit:
                break
            time.sleep(0.02)
    marker={'boundary':boundary,'operation_id':operation_id,
            'ingress_before_exit':ingress_before_exit,
            'heavy_imports':[name for name in sys.modules
                             if name=='cua_driver' or name.startswith('cua_driver.')
                             or name=='browser_use' or name.startswith('browser_use.')]}
    with (directory/'test-boundary.json').open('w') as stream:
        json.dump(marker,stream)
        stream.flush()
        os.fsync(stream.fileno())
    os._exit(86)
setattr(BrowserAuthority,method,interrupted)
asyncio.run(run(directory))
"""


def _environment():
    environment = dict(os.environ)
    if environment.get("FOOTWORK_EXECUTABLE"):
        # Installed acceptance must not fall back to this checkout from an empty cwd.
        environment.pop("PYTHONPATH", None)
    elif environment.get("PYTHONPATH"):
        # Source qualification also changes cwd; preserve explicit source roots.
        environment["PYTHONPATH"] = os.pathsep.join(
            str(Path(item or ".").resolve()) for item in environment["PYTHONPATH"].split(os.pathsep)
        )
    return environment


def _command(*args):
    configured = os.environ.get("FOOTWORK_EXECUTABLE")
    entry = shlex.split(configured) if configured else [sys.executable, "-m", "jevdual.cli"]
    return [*entry, "--json", "browser", "cdp", *args]


def _cli(root, *args, success=True):
    completed = subprocess.run(_command(*args), cwd=root, env=_environment(),
                               capture_output=True, text=True, timeout=45, check=False)
    envelope = json.loads(completed.stdout)
    assert envelope["exit_code"] == completed.returncode, completed.stderr
    if success:
        assert completed.returncode == 0, envelope
    return envelope["data"]


def _inventory(process, identities):
    """Capture descendants of our live Popen holder, before intentional abandonment."""
    try:
        root = psutil.Process(process.pid)
        if root.create_time() != identities[process.pid]:
            return
        for child in root.children(recursive=True):
            try:
                identities[child.pid] = child.create_time()
            except psutil.NoSuchProcess:
                pass
    except psutil.NoSuchProcess:
        pass


def _test_cleanup(process, identities):
    """Bounded test cleanup, using only identities captured from our actual child.

    The abrupt-exit holder cannot perform product cleanup. A live captured browser
    can have spawned more descendants since the first inventory; capture those
    only after rechecking its incarnation. A PID read from a file never grants
    cleanup authority here.
    """
    for pid, incarnation in list(identities.items()):
        try:
            owned = psutil.Process(pid)
            if owned.create_time() != incarnation or owned.status() == psutil.STATUS_ZOMBIE:
                continue
            for child in owned.children(recursive=True):
                try:
                    identities[child.pid] = child.create_time()
                except psutil.NoSuchProcess:
                    pass
        except psutil.NoSuchProcess:
            pass
    remaining = []
    for pid, incarnation in reversed(list(identities.items())):
        try:
            owned = psutil.Process(pid)
            if owned.create_time() == incarnation and owned.status() != psutil.STATUS_ZOMBIE:
                owned.terminate()
                remaining.append((owned, incarnation))
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs([owned for owned, _ in remaining], timeout=3)
    for owned in alive:
        try:
            if owned.create_time() == identities[owned.pid] and owned.status() != psutil.STATUS_ZOMBIE:
                owned.kill()
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(alive, timeout=3)
    process.wait(timeout=5)  # reap our actual child; orphan descendants are outside our waitpid custody


@pytest.fixture
def ingress():
    records = []
    arrived = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            if self.path == "/count":
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"count": len(records)}).encode())
                return
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b'''<!doctype html><title>Restart boundary</title>
<button type="button" onclick="fetch('/ingress',{method:'POST',body:'intended'})">Commit fixture</button>''')

        def do_POST(self):
            records.append(self.rfile.read(int(self.headers["Content-Length"])).decode())
            arrived.set()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"independently retained")

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/", records, arrived
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _private_json(path, value):
    with path.open("x") as stream:
        os.chmod(path, 0o600)
        json.dump(value, stream)


def _setup(root, url, boundary):
    from jevdual.browser_driver import chrome_executable

    session = root / "session"
    session.mkdir(mode=0o700)
    adapter = root / "guard.py"
    adapter.write_text("import json,sys\nr=json.load(sys.stdin)\n"
                       "print(json.dumps({'producer':'footwork.browser.guard','version':1,"
                       "'digest':r['digest'],'probabilities':[0.01]}))\n")
    _private_json(session / "browser.json", {
        "version": 1, "session_id": "restart-fixture", "task": "Commit the fixture once",
        "chrome": chrome_executable(), "initial_url": url, "authority": str(root / "authority.db"),
        "guard_command": [sys.executable, str(adapter)],
    })
    process = subprocess.Popen([sys.executable, "-c", _SHIM, str(session), boundary], cwd=root,
                               env=_environment(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, start_new_session=True)
    identities = {process.pid: psutil.Process(process.pid).create_time()}
    try:
        deadline = time.monotonic() + 25
        while not (session / "holder.json").exists():
            _inventory(process, identities)
            if process.poll() is not None:
                pytest.fail(f"test holder failed before readiness: {process.communicate(timeout=2)}")
            assert time.monotonic() < deadline, "test holder readiness timed out"
            time.sleep(0.03)
        _inventory(process, identities)
    except BaseException:
        _test_cleanup(process, identities)
        raise
    return session, process, identities


@pytest.mark.browser
@pytest.mark.parametrize("boundary", ["prepared", "started", "retained"])
def test_cli_recovers_abrupt_holder_death_without_redispatch(boundary, ingress):
    url, records, arrived = ingress
    with tempfile.TemporaryDirectory(prefix="fw-crash-", dir="/tmp") as directory:
        root = Path(directory)
        session, holder, identities = _setup(root, url, boundary)
        try:
            snapshot = _cli(root, "look", "--session", str(session))["snapshot"]
            ref = next(row["ref"] for row in snapshot["refs"] if row["name"] == "Commit fixture")
            _inventory(holder, identities)
            invocation = ("click", "--session", str(session), "--ref", ref, "--token", "intent-1")
            interrupted = _cli(root, *invocation, success=False)
            assert holder.wait(timeout=10) == 86
            assert interrupted["ok"] is False
            assert interrupted["dispatched"] is None  # transport loss itself proves no no-send predicate
            marker = json.loads((session / "test-boundary.json").read_text())
            assert marker["boundary"] == boundary
            assert marker["heavy_imports"] == []
            if boundary == "retained":
                assert arrived.wait(10), "activation did not reach the independent fixture ingress"
                assert marker["ingress_before_exit"] == 1
            recovered = _cli(root, "recover", "--session", str(session), "--token", "intent-1")
            op = recovered["operations"][0]
            assert op["id"] == marker["operation_id"]
            assert op["completion"] == "unverified" and op["retryable"] is False
            assert op["state"] == ("final" if boundary == "prepared" else "unknown")
            assert op["disposition"] == ("not_sent" if boundary == "prepared" else "unknown")
            assert op["phase"] == ("not_sent" if boundary == "prepared" else "sent" if boundary == "retained" else "ambiguous")
            if boundary == "retained":
                assert op["evidence"]["execution_receipt"]["basis"] == "activation_ack"
            else:
                assert "execution_receipt" not in op["evidence"]
            status = _cli(root, "status", "--session", str(session), "--token", "intent-1")
            assert status["operations"] == recovered["operations"]
            for _ in range(2):
                replay = _cli(root, *invocation)
                assert replay["replayed"] is True and replay["operation"]["id"] == op["id"]
                assert replay["operation"]["disposition"] == op["disposition"]
            new_intent = _cli(root, *invocation[:-1], "intent-2", success=False)
            assert new_intent["ok"] is False  # offline recovery cannot grant a fresh mutation
            assert records == (["intended"] if boundary == "retained" else [])
            if boundary != "prepared":
                # Remove abandoned test-owned custodians before starting another browser.
                # The public start route must reject this domain before launching Chrome.
                _test_cleanup(holder, identities)
                fresh_session = root / "next"
                blocked = _cli(root, "start", "Try a new intent", "--session", str(fresh_session),
                               "--authority", str(root / "authority.db"), "--url", url, success=False)
                assert blocked["ok"] is False
                assert not list(fresh_session.glob("profile-*"))
                assert not (fresh_session / "holder.json").exists()
                assert records == (["intended"] if boundary == "retained" else [])
        finally:
            _test_cleanup(holder, identities)
