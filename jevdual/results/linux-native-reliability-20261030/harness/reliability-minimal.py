import subprocess,sys,time,json,os,signal
from pathlib import Path
PY=sys.executable;OUT=Path('/work');PREFIX='/workspace/.footwork-setup/sysroot'
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
state=OUT/'session';log=(OUT/'session.log').open('w')
p=subprocess.Popen([PY,'-I','-m','jevdual.linux_session',str(state),'--rootless-prefix',PREFIX],stdout=log,stderr=subprocess.STDOUT)
rows=[]
try:
 end=time.monotonic()+36
 while not (state/'started').exists():
  if p.poll() is not None:raise RuntimeError('session startup failed')
  if time.monotonic()>end:raise TimeoutError('session startup')
  time.sleep(.05)
 env=os.environ.copy();env.update(DISPLAY=(state/'display').read_text().strip(),DBUS_SESSION_BUS_ADDRESS=(state/'session-bus').read_text().strip(),XDG_RUNTIME_DIR=str(state/'runtime'))
 child=OUT/'minimal.py'
 child.write_text('''import asyncio,sys,json,time,ctypes,os
from pathlib import Path
ctypes.CDLL(None).prctl(0x59616d61,ctypes.c_ulong(-1).value,0,0,0)
import cua_driver as cd
from jevdual.native import NativeBridge
out=Path(sys.argv[1]);pid=int(sys.argv[2])
def phase(name):
 with out.open('a') as f:f.write(json.dumps({'phase':name,'monotonic':time.monotonic()})+'\\n')
async def main():
 for n in range(3):
  phase('create');d=cd.CuaDriver.create(embedded=True)
  try:
   phase('list');ws=(await d.list_windows(cd.ListWindowsInput(pid=pid,on_screen_only=True))).windows
   phase('observe');await NativeBridge(d,pid,ws[0].window_id).observe();phase('observe_returned')
  finally:phase('shutdown');await d.shutdown();phase('shutdown_returned')
asyncio.run(main());phase('asyncio_returned');print('{"ready":true}',flush=True);phase('result_emitted')
''')
 for i in range(40):
  events=OUT/f'minimal-{i:02}.events';stderr=OUT/f'minimal-{i:02}.stderr';stdout=OUT/f'minimal-{i:02}.stdout'
  with stdout.open('w') as so,stderr.open('w') as se:
   q=subprocess.Popen([PY,'-I',str(child),str(events),(state/'editor.pid').read_text().strip()],env=env,stdout=so,stderr=se)
   try:code=q.wait(timeout=12)
   except subprocess.TimeoutExpired:
    # Target explicitly permits this task-owned debugger. Never ptrace another process.
    g=subprocess.run([PREFIX+'/usr/bin/gdb','-q','-batch','-ex','set pagination off','-ex','thread apply all bt','-ex','detach','-p',str(q.pid)],env=env,capture_output=True,text=True,timeout=10)
    (OUT/f'minimal-{i:02}.gdb').write_text(g.stdout+g.stderr);q.kill();code=q.wait(timeout=3)
  row={'attempt':i,'returncode':code,'signal':-code if code<0 else None};rows.append(row);write(OUT/'attempts.json',rows);print(row,flush=True)
finally:
 if p.poll() is None:p.terminate()
 try:p.wait(timeout=8)
 except subprocess.TimeoutExpired:p.kill();p.wait(timeout=3)
 log.close()
