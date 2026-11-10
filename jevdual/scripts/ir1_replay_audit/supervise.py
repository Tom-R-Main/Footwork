"""Owned subprocess lifetime and finite whole-run bound; no global reaper."""
import ctypes
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import psutil


def descendants():
    rows=[]
    for p in psutil.Process().children(recursive=True):
        try:rows.append({'pid':p.pid,'start':p.create_time(),'status':p.status(),'name':p.name()})
        except (psutil.NoSuchProcess,ProcessLookupError):pass
    return rows


def send(row, sig):
    fd=None
    try:
        p=psutil.Process(row['pid'])
        if p.create_time()!=row['start']:return 'identity_changed'
        fd=os.pidfd_open(row['pid'])
        if p.create_time()!=row['start']:return 'identity_changed'
        signal.pidfd_send_signal(fd,sig);return 'sent'
    except (psutil.NoSuchProcess,ProcessLookupError):return 'exited'
    finally:
        if fd is not None:os.close(fd)


def main():
    package=Path(__file__).resolve().parent;task=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(mode=0o700)
    assert ctypes.CDLL(None,use_errno=True).prctl(36,1,0,0,0)==0
    env=dict(os.environ)
    for k in ['OPENAI_API_KEY','ANTHROPIC_API_KEY','TYPESAFE_API_KEY','DISPLAY','WAYLAND_DISPLAY','DBUS_SESSION_BUS_ADDRESS','AT_SPI_BUS_ADDRESS']:env.pop(k,None)
    cmd=[sys.executable,str(package/'run.py'),str(task),str(out/'first')]
    metadata={'argv':cmd,'cwd':str(package),'test_package_commit':subprocess.check_output(['git','-C',str(package),'rev-parse','HEAD'],text=True).strip(),'source_archive_sha256':'5588fa808559de5982f9195c1031696f51a67b057164fd42b60485ac6c30b401','package_files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in package.iterdir() if p.is_file()},'whole_run_bound_seconds':240,'python':sys.version}
    (out/'command.json').write_text(json.dumps(metadata,indent=2)+'\n')
    with (out/'stdout.txt').open('w') as stdout,(out/'stderr.txt').open('w') as stderr:
        child=subprocess.Popen(cmd,cwd=package,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
        deadline=time.monotonic()+240;history={};errors=[];signals=[]
        while child.poll() is None and time.monotonic()<deadline:
            try:
                for row in descendants():history[(row['pid'],row['start'])]=row
            except Exception as error:  # noqa: BLE001 - retain failures of the diagnostic process probe
                errors.append(type(error).__name__+': '+str(error))
            time.sleep(.05)
        timeout=child.poll() is None
        if timeout:
            for sig in [signal.SIGTERM,signal.SIGKILL]:
                for row in descendants():
                    if row['status']!='zombie':signals.append({**row,'signal':int(sig),'result':send(row,sig)})
                try:child.wait(timeout=3);break
                except subprocess.TimeoutExpired:pass
        code=child.wait()
    before=descendants();waits=[]
    def reap():
        while True:
            try:pid,status=os.waitpid(-1,os.WNOHANG)
            except ChildProcessError:return
            if not pid:return
            waits.append({'pid':pid,'raw_status':status,'returncode':os.waitstatus_to_exitcode(status)})
    for sig in [signal.SIGTERM,signal.SIGKILL]:
        for row in descendants():
            if row['status']!='zombie':signals.append({**row,'signal':int(sig),'result':send(row,sig)})
        deadline=time.monotonic()+3
        while descendants() and time.monotonic()<deadline:reap();time.sleep(.02)
        reap()
        if not descendants():break
    report={'command_returncode':code,'whole_run_timeout':timeout,'monitor_errors':errors,'pre_supervisor_cleanup':before,'signals':signals,'adopted_waits':waits,'final_owned_descendants':descendants(),'scope':'test-only subreaper, captured owned descendants; target/bus explicit stops separately journaled'}
    (out/'cleanup.json').write_text(json.dumps(report,indent=2)+'\n');(out/'process-history.json').write_text(json.dumps(list(history.values()),indent=2)+'\n')
    print(json.dumps(report));raise SystemExit(code if code else int(bool(timeout or errors or descendants())))


if __name__=='__main__':main()
