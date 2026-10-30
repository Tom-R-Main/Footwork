import asyncio,hashlib,json,os,signal,subprocess,sys,time,urllib.request
from pathlib import Path
import cua_driver as cd
import psutil
ROOT=Path('/workspace/Footwork/jevdual');OUT=Path('/work');PY=sys.executable
PREFIX='/workspace/.footwork-setup/sysroot'

def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def start(label,extra=()):
 state=OUT/label
 log=(OUT/(label+'.log')).open('w')
 p=subprocess.Popen([PY,'-I','-m','jevdual.linux_session',str(state),'--rootless-prefix',PREFIX,'--probe-timeout','10',*extra],stdout=log,stderr=subprocess.STDOUT)
 end=time.monotonic()+40
 while not (state/'started').exists():
  if p.poll() is not None:raise RuntimeError('session startup failed: '+str(read(state/'session.json')))
  if time.monotonic()>end:raise TimeoutError('session readiness')
  time.sleep(.1)
 return p,state,log

def stop(p,state,log):
 p.terminate()
 p.wait(timeout=8)
 log.close()
 return read(state/'session.json')

async def windows(pid):
 d=cd.CuaDriver.create(embedded=True)
 try:return [w.window_id for w in (await d.list_windows(cd.ListWindowsInput(pid=pid,on_screen_only=True))).windows]
 finally:await d.shutdown()

result={'source_commit':'f16cc54','pid1':Path('/proc/1/comm').read_text().strip(),
        'limits':{n:Path('/sys/fs/cgroup/'+n).read_text().strip() for n in ['pids.max','memory.max','memory.swap.max','cpu.max']}}
import atexit
occupied_log=(OUT/'occupied.log').open('w')
occupied=subprocess.Popen(['Xvfb',':0','-screen','0','640x480x24','-nolisten','tcp'],stdout=occupied_log,stderr=subprocess.STDOUT)
def stop_occupied():
 if occupied.poll() is None:
  occupied.terminate();occupied.wait(timeout=3)
 occupied_log.close()
atexit.register(stop_occupied)
end=time.monotonic()+5
while not Path('/tmp/.X11-unix/X0').exists():
 assert occupied.poll() is None and time.monotonic()<end
 time.sleep(.02)
p,state,log=start('session')
assert (state/'display').read_text().strip()!=':0' and occupied.poll() is None
result['native_display_reservation']={'occupied_display':':0','selected_display':(state/'display').read_text().strip(),'unrelated_server_alive':True}
chrome=None
try:
 result['readiness']=read(state/'session.json')
 q=subprocess.run([PY,str(ROOT/'scripts/linux/qualify.py'),'--state',str(state),'--output','/work/installed','--chrome','/usr/lib/chromium/chromium'],capture_output=True,text=True,timeout=120)
 (OUT/'installed.txt').write_text(q.stdout+q.stderr)
 assert q.returncode==0,q.stderr
 result['installed']=read(OUT/'installed/receipt.json')
 env=os.environ.copy();env['PYTHONFAULTHANDLER']='1';env.update(DISPLAY=(state/'display').read_text().strip(),DBUS_SESSION_BUS_ADDRESS=(state/'session-bus').read_text(),XDG_RUNTIME_DIR=str(state/'runtime'),FOOTWORK_CHROME_EXECUTABLE='/usr/lib/chromium/chromium',FOOTWORK_CHROME_PROFILE='/work/recovery-profile',FOOTWORK_CHROME_PORT='9444')
 for kind in ['config','cache','data','state']:env['XDG_'+kind.upper()+'_HOME']=str(state/kind)
 os.environ.update({k:v for k,v in env.items() if k in ['DISPLAY','DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR']})
 chrome_log=(OUT/'recovery-chrome.txt').open('w')
 chrome=subprocess.Popen(['/usr/lib/chromium/chromium','--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--keep-alive-for-test','--user-data-dir=/work/recovery-profile','--remote-debugging-port=9444','--remote-debugging-address=127.0.0.1','--no-first-run','--no-default-browser-check','--force-renderer-accessibility','about:blank'],env=env,stdout=chrome_log,stderr=subprocess.STDOUT,start_new_session=True)
 incarnation=psutil.Process(chrome.pid).create_time()
 http=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 end=time.monotonic()+20
 while True:
  try:
   tabs=json.loads(http.open('http://127.0.0.1:9444/json/list',timeout=1).read())
   if tabs and asyncio.run(windows(chrome.pid)):break
  except (OSError,ValueError):pass
  assert chrome.poll() is None and time.monotonic()<end,'Chrome startup'
  time.sleep(.1)
 for tab in tabs:
  if tab.get('type')=='page':http.open('http://127.0.0.1:9444/json/close/'+tab['id'],timeout=2).read()
 end=time.monotonic()+5
 while asyncio.run(windows(chrome.pid)) and time.monotonic()<end:time.sleep(.1)
 assert asyncio.run(windows(chrome.pid))==[] and chrome.poll() is None
 before={'pid':chrome.pid,'incarnation':incarnation,'visible_windows':[],'profile':env['FOOTWORK_CHROME_PROFILE']}
 paused=False
 try:
  os.kill(chrome.pid,signal.SIGSTOP);paused=True
  helper_log=(OUT/'browser-recovery.txt').open('w')
  caller=subprocess.Popen([PY,'-X','faulthandler','-I','-m','jevdual.cli','--json','browser','start','Recover the same owned profile','--session','/work/recovered-session'],env=env,stdout=helper_log,stderr=subprocess.STDOUT)
  deadline=time.monotonic()+5;observed_helper=None
  while time.monotonic()<deadline:
   if caller.poll() is not None:break
   for child in psutil.Process(caller.pid).children():
    try:
     args=child.cmdline()
     if child.exe()=='/usr/lib/chromium/chromium' and '--user-data-dir=/work/recovery-profile' in args and '--remote-debugging-port=9444' in args:
      observed_helper={'pid':child.pid,'incarnation':child.create_time(),'matches_root_predicate':True}
      break
    except psutil.Error:pass
   if observed_helper:break
   time.sleep(.02)
  assert observed_helper,'owned forwarding helper not observed'
  probe=subprocess.run([PY,'-I','-c',"from jevdual.browser_driver import chrome_pid;\ntry: print(chrome_pid())\nexcept RuntimeError: print('ambiguous')"],env=env,capture_output=True,text=True,timeout=2)
  assert probe.stdout.strip()=='ambiguous',probe.stdout+probe.stderr
  result['delayed_owned_helper']={**observed_helper,'raw_unique_discovery_while_helper_alive':'ambiguous'}
 finally:
  if paused:os.kill(chrome.pid,signal.SIGCONT)
 code=caller.wait(timeout=30);helper_log.close()
 result['recovery_process_exit_code']=code
 assert code==0,(OUT/'browser-recovery.txt').read_text()
 q=type('Exit',(),{'returncode':code})()
 saved=read(OUT/'recovered-session/session.json')
 assert saved['pid']==chrome.pid and psutil.Process(chrome.pid).create_time()==incarnation
 after=asyncio.run(windows(chrome.pid));assert after
 result['browser_recovery']={'before':before,'after_window_ids':after,'same_pid_and_incarnation':True,'public_cli_exit_code':q.returncode}
finally:
 if chrome is not None:
  os.killpg(chrome.pid,signal.SIGTERM)
  try:chrome.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(chrome.pid,signal.SIGKILL);chrome.wait()
 result['cleanup']=stop(p,state,log)
 write(OUT/'acceptance.json',result)
assert not result['cleanup']['cleanup']['survivors']
# Kill each critical component on a separately ready real desktop.
for label,component in [('death-xvfb','xvfb'),('death-bus','bus'),('death-editor','editor')]:
 p,state,log=start(label)
 # Selected process names are in the session leader's descendants, never system-wide.
 candidates=[c for c in psutil.Process(p.pid).children() if c.name() in {'Xvfb','dbus-daemon','mousepad'}]
 selected=next(c for c in candidates if c.name()=={'xvfb':'Xvfb','bus':'dbus-daemon','editor':'mousepad'}[component])
 selected.terminate();p.wait(timeout=8);log.close()
 final=read(state/'session.json')
 assert final['phase']=='failed' and final['reason']=='component_exited:'+component
 assert not final['cleanup']['survivors']
 result[label]=final
# Deterministic process failure/cancellation tests under the same hard PID cap.
r=subprocess.run([str(ROOT/'.venv/bin/python'),'-I','-m','pytest','-q',str(ROOT/'tests/test_linux_session.py'),str(ROOT/'tests/test_host_probe.py'),str(ROOT/'tests/test_linux_process.py')],cwd=ROOT,capture_output=True,text=True,timeout=60)
(OUT/'lifecycle-tests.txt').write_text(r.stdout+r.stderr)
assert r.returncode==0,r.stdout+r.stderr
result['lifecycle_tests_passed']=True
result['final_counters']={n:Path('/sys/fs/cgroup/'+n).read_text().strip() for n in ['pids.current','pids.events','memory.events']}
assert occupied.poll() is None
stop_occupied()
write(OUT/'acceptance.json',result)
print(json.dumps({'passed':True,'browser_recovery':result['browser_recovery'],'limits':result['limits'],'cleanup':result['cleanup']['cleanup'],'lifecycle_tests_passed':True,'final_counters':result['final_counters']}))
