"""Owned-child Linux syscall plumbing check, not a product integration test."""
import errno
import json
import os
import platform
import signal
import subprocess
import sys
from pathlib import Path

record={'level':'isolated_linux_mechanism','kernel':platform.release(),'python':platform.python_version(),
        'architecture':platform.machine(),'product_revision':'bd6f185 not modified or exercised',
        'numeric_signal_fallback':False}
fd=None
child=sentinel=None
try:
    if not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal'):
        raise NotImplementedError('Python pidfd APIs unavailable')
    child=subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(30)'])
    sentinel=subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(30)'])
    fd=os.pidfd_open(child.pid)
    signal.pidfd_send_signal(fd,signal.SIGTERM)
    child.wait(timeout=3)
    assert child.returncode==-signal.SIGTERM
    try:
        signal.pidfd_send_signal(fd,0)
    except OSError as exc:
        assert exc.errno==errno.ESRCH,exc
        record['after_exit_errno']='ESRCH'
    else:
        raise AssertionError('retained fd unexpectedly addressed an exited process')
    assert sentinel.poll() is None
    record.update(status='passed',child_terminated_through_fd=True,sentinel_survived=True)
except (NotImplementedError,PermissionError) as exc:
    record.update(status='unavailable',reason=type(exc).__name__)
finally:
    if fd is not None:os.close(fd)
    for process in [child,sentinel]:
        if process is not None:
            if process.poll() is None:process.terminate()
            process.wait(timeout=3)
    record['owned_children_joined']=True
    record['pidfd_closed']=fd is not None
Path('/artifacts/pidfd-learning.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
