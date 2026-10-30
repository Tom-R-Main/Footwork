import asyncio,json,os,signal,subprocess,sys,time,urllib.request,resource
from pathlib import Path
import cua_driver as cd
import psutil
OUT=Path('/work');__import__('shutil').copyfile('/workspace/scratch/fw-reliability-diag-consumer/abort-capture.so',OUT/'abort-capture.so');PY=sys.executable;PREFIX='/workspace/.footwork-setup/sysroot'
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
# Diagnostic fixture: admit X11/bus/WM only, do not publish target readiness.
from jevdual.linux_session import Session
class Fixture:
 def poll(self):return None
 def terminate(self):pass
 def wait(self,**kw):return 0
session=Session(OUT/'session',prefix=Path(PREFIX));session.prepare();deadline=time.monotonic()+30
session.allocate_display(deadline);session.await_probe('x11',deadline)
session.spawn('bus',['dbus-daemon','--session','--nofork','--address='+session.env['DBUS_SESSION_BUS_ADDRESS']]);session.await_probe('bus',deadline)
session.spawn('wm',['openbox']);session.await_probe('wm',deadline)
state=session.state;p=Fixture();log=(OUT/'session.log').open('w')
rows=[];chrome=None
async def windows(pid):
 d=cd.CuaDriver.create(embedded=True)
 try:return [w.window_id for w in (await d.list_windows(cd.ListWindowsInput(pid=pid,on_screen_only=True))).windows]
 finally:await d.shutdown()
try:
 env=os.environ.copy();env.update(DISPLAY=(state/'display').read_text().strip(),DBUS_SESSION_BUS_ADDRESS=(state/'session-bus').read_text().strip(),XDG_RUNTIME_DIR=str(state/'runtime'),FOOTWORK_CHROME_EXECUTABLE='/usr/lib/chromium/chromium',FOOTWORK_CHROME_PROFILE='/work/profile',FOOTWORK_CHROME_PORT='9444')
 os.environ.update({k:env[k] for k in ['DISPLAY','DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR']})
 chrome_log=(OUT/'chrome.log').open('w');chrome=subprocess.Popen(['/usr/lib/chromium/chromium','--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--keep-alive-for-test','--user-data-dir=/work/profile','--remote-debugging-port=9444','--remote-debugging-address=127.0.0.1','--no-first-run','--no-default-browser-check','--force-renderer-accessibility','about:blank'],env=env,stdout=chrome_log,stderr=subprocess.STDOUT,start_new_session=True)
 incarnation=psutil.Process(chrome.pid).create_time();http=urllib.request.build_opener(urllib.request.ProxyHandler({}));end=time.monotonic()+20
 while True:
  try:
   tabs=json.loads(http.open('http://127.0.0.1:9444/json/list',timeout=1).read())
   if tabs and asyncio.run(windows(chrome.pid)):break
  except (OSError,ValueError):pass
  assert chrome.poll() is None and time.monotonic()<end
  time.sleep(.1)
 wrapper=OUT/'cli.py';wrapper.write_text('''import cua_driver as cd,runpy,sys,time,json,ctypes,resource
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
ctypes.CDLL(None).prctl(0x59616d61,ctypes.c_ulong(-1).value,0,0,0)
events=Path(sys.argv.pop(1))
def phase(p):
 with events.open('a') as f:f.write(json.dumps({'phase':p,'monotonic':time.monotonic()})+'\\n')
original=cd.CuaDriver.shutdown
async def shutdown(self):
 phase('shutdown');await original(self);phase('shutdown_returned')
cd.CuaDriver.shutdown=shutdown
phase('dispatch');runpy.run_module('jevdual.cli',run_name='__main__')
''')
 for i in range(10):
  tabs=json.loads(http.open('http://127.0.0.1:9444/json/list',timeout=1).read())
  for tab in tabs:
   if tab.get('type')=='page':http.open('http://127.0.0.1:9444/json/close/'+tab['id'],timeout=2).read()
  end=time.monotonic()+5
  while asyncio.run(windows(chrome.pid)) and time.monotonic()<end:time.sleep(.05)
  assert asyncio.run(windows(chrome.pid))==[]
  so=(OUT/f'recovery-{i:02}.stdout').open('w');se=(OUT/f'recovery-{i:02}.stderr').open('w')
  os.kill(chrome.pid,signal.SIGSTOP)
  child_env={**env,'LD_PRELOAD':'/work/abort-capture.so'}
  q=subprocess.Popen([PY,'-I',str(wrapper),str(OUT/f'recovery-{i:02}.events'),'--json','browser','start','Recover owned profile','--session',f'/work/recovered-{i:02}'],env=child_env,stdout=so,stderr=se)
  try:
   end=time.monotonic()+5;helper=None
   while q.poll() is None and time.monotonic()<end:
    for child in psutil.Process(q.pid).children():
     try:
      if child.exe()=='/usr/lib/chromium/chromium':helper=child.pid;break
     except psutil.Error:pass
    if helper:break
    time.sleep(.02)
   assert helper
   control=subprocess.run([PY,'-I','-c',"from jevdual.browser_driver import chrome_pid\ntry: print(chrome_pid())\nexcept RuntimeError: print('ambiguous')"],env=env,capture_output=True,text=True,timeout=2)
   assert control.stdout.strip()=='ambiguous'
  finally:os.kill(chrome.pid,signal.SIGCONT)
  try:
   end=time.monotonic()+30;captured=False
   while q.poll() is None and time.monotonic()<end:
    if psutil.Process(q.pid).status()==psutil.STATUS_STOPPED and not captured:
     captured=True
     g=subprocess.run([PREFIX+'/usr/bin/gdb','-q','-batch','-ex','set pagination off','-ex','set debuginfod enabled off','-ex','thread apply all bt','-ex','detach','-p',str(q.pid)],env=env,capture_output=True,text=True,timeout=10)
     (OUT/f'recovery-{i:02}.gdb').write_text(g.stdout+g.stderr)
     os.kill(q.pid,signal.SIGCONT)
    time.sleep(.01)
   code=q.wait(timeout=1)
  except subprocess.TimeoutExpired:
   g=subprocess.run([PREFIX+'/usr/bin/gdb','-q','-batch','-ex','set pagination off','-ex','thread apply all bt','-ex','detach','-p',str(q.pid)],env=env,capture_output=True,text=True,timeout=10)
   (OUT/f'recovery-{i:02}.gdb').write_text(g.stdout+g.stderr);q.kill();code=q.wait(timeout=3)
  so.close();se.close();row={'attempt':i,'returncode':code,'signal':-code if code<0 else None,'helper':helper,'same_root':psutil.Process(chrome.pid).create_time()==incarnation};rows.append(row);write(OUT/'attempts.json',rows);print(row,flush=True)
finally:
 if chrome is not None:
  os.killpg(chrome.pid,signal.SIGTERM)
  try:chrome.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(chrome.pid,signal.SIGKILL);chrome.wait()
 if p.poll() is None:p.terminate()
 try:p.wait(timeout=8)
 except subprocess.TimeoutExpired:p.kill();p.wait(timeout=3)
 log.close();write(OUT/'cleanup.json',session.cleanup())
