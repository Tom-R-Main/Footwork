import errno,json,os,platform,signal,subprocess,sys
from pathlib import Path
out=Path('/workspace/Footwork/jevdual/results/linux-consolidation-vm-20261030/pidfd-kernel.json')
children=[];fd=None
r={'kernel':platform.release(),'python':platform.python_version(),'pidfd_open':hasattr(os,'pidfd_open'),'pidfd_send_signal':hasattr(signal,'pidfd_send_signal'),'numeric_delivery_fallback':False}
try:
 for _ in range(2):children.append(subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']))
 target,sentinel=children
 fd=os.pidfd_open(target.pid,0)
 signal.pidfd_send_signal(fd,signal.SIGTERM,None,0)
 r['target_exit']=target.wait(timeout=3)
 try:signal.pidfd_send_signal(fd,0,None,0);r['exited_fd_errno']=None
 except OSError as e:r['exited_fd_errno']=e.errno
 r['sentinel_alive']=sentinel.poll() is None
 r['passed']=r['target_exit']==-signal.SIGTERM and r['exited_fd_errno']==errno.ESRCH and r['sentinel_alive']
except (OSError,AttributeError) as e:r.update(passed=False,error=type(e).__name__,errno=getattr(e,'errno',None))
finally:
 if fd is not None:os.close(fd)
 for p in children:
  if p.poll() is None:p.terminate()
  p.wait(timeout=3)
 r['test_fixture_children_joined']=True
 out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
raise SystemExit(0 if r.get('passed') else 1)
