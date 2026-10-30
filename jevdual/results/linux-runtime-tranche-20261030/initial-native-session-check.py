import json,os,signal,subprocess,time
from pathlib import Path
root=Path('/workspace/Footwork/jevdual');out=root/'results/linux-runtime-tranche-20261030'
state=Path('/workspace/scratch/fw-bounded-dev');python=root/'.venv/bin/python'
with (out/'lifecycle-native-dev.txt').open('w') as log:
 p=subprocess.Popen([str(python),'-I','-m','jevdual.linux_session',str(state),'--rootless-prefix','/workspace/.footwork-setup/sysroot'],stdout=log,stderr=subprocess.STDOUT)
 r={'source_commit':'f31f7bd'}
 try:
  end=time.monotonic()+40
  while not (state/'started').exists():
   if p.poll() is not None:raise RuntimeError(f'supervisor exited {p.returncode}: '+(state/'session.json').read_text())
   if time.monotonic()>end:raise TimeoutError('readiness')
   time.sleep(.1)
  r['ready']=json.loads((state/'session.json').read_text())
  q=subprocess.run([str(python),str(root/'scripts/linux/qualify.py'),'--state',str(state),'--output','/workspace/scratch/fw-bounded-dev-run','--chrome','/usr/lib/chromium/chromium'],stdout=log,stderr=subprocess.STDOUT,timeout=150)
  r['qualification_exit_code']=q.returncode
 except Exception as e:r['error']=str(e)
 finally:
  p.terminate()
  try:p.wait(timeout=8)
  except subprocess.TimeoutExpired:p.kill();p.wait()
  r['session']=json.loads((state/'session.json').read_text())
  (out/'lifecycle-native-dev.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(r))
raise SystemExit(0 if r.get('qualification_exit_code')==0 else 1)
