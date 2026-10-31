"""Signals before holder readiness retain real launch custody until bounded owned cleanup.

The real-browser cells run under a dedicated test supervisor. On Linux that supervisor is a child
subreaper solely to collect test-owned orphan zombies after assertions. Product cleanup is assessed
first from live process identities; test reaping is recorded separately and is not product evidence.
No production fault flags or test-only cleanup behavior are added to the holder.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace

import psutil
import pytest
from jevdual import browser_holder as broker

_SHIM = r'''
import asyncio,json,os,sys,time
from pathlib import Path
import psutil
from jevdual import browser_holder as broker
from jevdual.effectors.cdp import operations

directory,phase=Path(sys.argv[1]),sys.argv[2]
def mark(chrome):
    root=psutil.Process(chrome.pid)
    identities={str(root.pid):root.create_time()}
    for child in root.children(recursive=True):
        try: identities[str(child.pid)]=child.create_time()
        except psutil.NoSuchProcess: pass
    with (directory/'startup-boundary.json').open('w') as stream:
        json.dump({'phase':phase,'pid':chrome.pid,'start':chrome.incarnation,'captured':identities},stream)
        stream.flush()
        os.fsync(stream.fileno())

original_launch=broker.launch.launch
def launch(*args,**kwargs):
    chrome=original_launch(*args,**kwargs)
    if phase=='launch':
        mark(chrome)
        time.sleep(1.5)  # handle exists in the real worker thread, not yet in run()
    return chrome
broker.launch.launch=launch
if phase=='connect':
    original_verify=operations.verify_endpoint
    async def verify(conn,chrome):
        await original_verify(conn,chrome)
        mark(chrome)
        await asyncio.sleep(60)  # cancellable verification with a real acquired connection
    operations.verify_endpoint=verify
elif phase=='navigate':
    original_connect=operations.CdpBrowserOperations.connect.__func__
    async def connect(cls,chrome):
        ops=await original_connect(cls,chrome)
        original_send=ops.conn.send
        async def send(method,*args,**kwargs):
            result=await original_send(method,*args,**kwargs)
            if method=='Page.navigate':
                mark(chrome)
                await asyncio.sleep(60)  # cancellable initial navigation, before holder readiness
            return result
        ops.conn.send=send
        return ops
    operations.CdpBrowserOperations.connect=classmethod(connect)
asyncio.run(broker.run(directory))
'''

_SUPERVISOR = r'''
import ctypes,json,os,signal,subprocess,sys,time
from pathlib import Path
import psutil

directory,phase,signal_number=Path(sys.argv[1]),sys.argv[2],int(sys.argv[3])
subreaper=False
if sys.platform=='linux':
    if ctypes.CDLL(None,use_errno=True).prctl(36,1,0,0,0):
        raise OSError(ctypes.get_errno(),'test subreaper unavailable')
    subreaper=True
process=subprocess.Popen([sys.executable,str(directory/'child.py'),str(directory/'session'),phase],
                         stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
identities={process.pid:psutil.Process(process.pid).create_time()}
def inventory():
    # Only descendants of this dedicated test supervisor confer test cleanup custody.
    for child in psutil.Process().children(recursive=True):
        try: identities[child.pid]=child.create_time()
        except psutil.NoSuchProcess: pass
def live():
    result=[]
    for pid,start in identities.items():
        try:
            child=psutil.Process(pid)
            if child.create_time()==start and child.status()!=psutil.STATUS_ZOMBIE:
                result.append(pid)
        except psutil.NoSuchProcess: pass
    return result
report={'phase':phase,'test_subreaper':subreaper}
failed=False
try:
    deadline=time.monotonic()+25
    marker=directory/'session'/'startup-boundary.json'
    while not marker.exists():
        inventory()
        if process.poll() is not None:
            raise AssertionError('holder exited before startup boundary: '+str(process.communicate(timeout=2)))
        if time.monotonic()>deadline: raise AssertionError('startup boundary timeout')
        time.sleep(.02)
    observed=json.loads(marker.read_text())
    inventory()
    assert identities.get(observed['pid'])==observed['start'],'marker did not name an owned live descendant'
    assert not (directory/'session'/'holder.json').exists(),'holder was published before test boundary'
    process.send_signal(signal_number)  # actual child handle, never a PID-file signal
    report['holder_exit']=process.wait(timeout=25)
    assert report['holder_exit']==0,str(process.communicate(timeout=2))
    deadline=time.monotonic()+5
    while live() and time.monotonic()<deadline:
        inventory()
        time.sleep(.02)
    report['live_before_test_cleanup']=live()
    report['holder_published']=(directory/'session'/'holder.json').exists()
    report['chrome_pid']=observed['pid']
    report['captured_count']=len(identities)
    report['zombies_before_test_reap']=[]
    for pid,start in identities.items():
        try:
            child=psutil.Process(pid)
            if child.create_time()==start and child.status()==psutil.STATUS_ZOMBIE:
                report['zombies_before_test_reap'].append(pid)
        except psutil.NoSuchProcess: pass
    assert not report['live_before_test_cleanup'],'product left captured live processes'
    assert not report['holder_published'],'stopped startup must not publish readiness'
except BaseException as exc:
    failed=True
    report['error']=str(exc)
finally:
    inventory()
    # Failure hygiene is deliberately after the product liveness assertion.
    for pid in reversed(live()):
        try:
            child=psutil.Process(pid)
            if child.create_time()==identities[pid]: child.terminate()
        except psutil.NoSuchProcess: pass
    deadline=time.monotonic()+3
    while live() and time.monotonic()<deadline: time.sleep(.02)
    for pid in live():
        try:
            child=psutil.Process(pid)
            if child.create_time()==identities[pid]: child.kill()
        except psutil.NoSuchProcess: pass
    process.wait(timeout=5)
    report['test_reaped']=0
    if subreaper:
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            try: pid,_=os.waitpid(-1,os.WNOHANG)
            except ChildProcessError: break
            if pid: report['test_reaped']+=1
            else: time.sleep(.02)
    report['live_after_test_cleanup']=live()
print(json.dumps(report))
sys.exit(1 if failed else 0)
'''


def _environment():
    environment = dict(os.environ)
    if environment.get("FOOTWORK_EXECUTABLE"):
        environment.pop("PYTHONPATH", None)
    elif environment.get("PYTHONPATH"):
        environment["PYTHONPATH"] = os.pathsep.join(
            str(Path(item or ".").resolve()) for item in environment["PYTHONPATH"].split(os.pathsep)
        )
    return environment


def _configuration(root):
    from jevdual.browser_driver import chrome_executable

    session = root / "session"
    session.mkdir(mode=0o700)
    config = {"version": 1, "session_id": "startup-fixture", "task": "Observe the fixture",
              "chrome": chrome_executable(), "initial_url": "http://127.0.0.1:1/",
              "authority": str(root / "authority.db"), "guard_command": None}
    broker._write_private(session / broker.CONFIG_FILE, config)
    return session


@pytest.mark.browser
@pytest.mark.parametrize("phase,selected_signal", [
    ("launch", signal.SIGTERM), ("launch", signal.SIGINT),
    ("connect", signal.SIGTERM), ("navigate", signal.SIGTERM),
])
def test_real_chrome_startup_signal_releases_owned_live_processes(phase, selected_signal):
    with tempfile.TemporaryDirectory(prefix="fw-start-", dir="/tmp") as raw:
        root = Path(raw)
        _configuration(root)
        (root / "child.py").write_text(_SHIM)
        supervisor = subprocess.Popen([sys.executable, "-c", _SUPERVISOR, str(root), phase, str(int(selected_signal))],
                                      cwd=root, env=_environment(), stdin=subprocess.DEVNULL,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            output, error = supervisor.communicate(timeout=65)
            assert supervisor.returncode == 0, (output, error)
            result = json.loads(output)
            assert result["holder_exit"] == 0 and result["holder_published"] is False
            assert result["live_before_test_cleanup"] == result["live_after_test_cleanup"] == []
            assert result["captured_count"] >= 2
            assert result["test_subreaper"] is (sys.platform == "linux")
        finally:
            if supervisor.poll() is None:
                # Only a failed test harness reaches this fallback. Capture descendants while its
                # actual Popen identity is still known; never acquire cleanup authority from marker data.
                owned = psutil.Process(supervisor.pid)
                descendants = [(child, child.create_time()) for child in owned.children(recursive=True)]
                for child, start in reversed(descendants):
                    try:
                        if child.create_time() == start:
                            child.kill()
                    except psutil.NoSuchProcess:
                        pass
                supervisor.kill()
                supervisor.wait(timeout=5)


def _unit_configuration(directory):
    config = {"version": 1, "session_id": "startup-unit", "task": "Observe the fixture",
              "chrome": "/fixture/chrome", "initial_url": "http://127.0.0.1:1/",
              "authority": str(directory / "authority.db"), "guard_command": None}
    broker._write_private(directory / broker.CONFIG_FILE, config)


def test_task_cancellation_during_launch_waits_for_actual_handle_then_cleans_it(monkeypatch):
    entered, release = threading.Event(), threading.Event()
    chrome = SimpleNamespace(pid=123, incarnation=1.0)
    stopped = []

    def launch(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        return chrome

    monkeypatch.setattr(broker.launch, "launch", launch)
    monkeypatch.setattr(broker.launch, "stop", stopped.append)

    async def run(directory):
        previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
        task = asyncio.create_task(broker.run(directory))
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            task.cancel()
            await asyncio.sleep(0)
            assert not task.done() and stopped == []
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert stopped == [chrome]
            assert not (directory / broker.HOLDER_FILE).exists()
            assert {sig: signal.getsignal(sig) for sig in previous} == previous
        finally:
            release.set()

    with tempfile.TemporaryDirectory(prefix="fw-start-unit-", dir="/tmp") as raw:
        directory = Path(raw)
        _unit_configuration(directory)
        asyncio.run(run(directory))


def test_readiness_failure_still_attempts_cleanup_and_reports_cleanup_uncertainty(monkeypatch):
    chrome = SimpleNamespace(pid=123, incarnation=1.0)
    stopped = []
    monkeypatch.setattr(broker.launch, "launch", lambda *a, **k: chrome)

    async def unavailable(*args):
        raise RuntimeError("readiness unavailable")

    def cleanup(handle):
        stopped.append(handle)
        raise broker.launch.CleanupUnverified("test inventory unavailable")

    monkeypatch.setattr(broker.CdpBrowserOperations, "connect", unavailable)
    monkeypatch.setattr(broker.launch, "stop", cleanup)
    with tempfile.TemporaryDirectory(prefix="fw-start-unit-", dir="/tmp") as raw:
        directory = Path(raw)
        _unit_configuration(directory)
        with pytest.raises(broker.launch.CleanupUnverified, match="inventory unavailable"):
            asyncio.run(broker.run(directory))
        assert stopped == [chrome]
        assert not (directory / broker.HOLDER_FILE).exists()
