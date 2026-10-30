"""Fixed 30 lifecycle + 10 public journey attempts; no replacement runs."""
import asyncio,hashlib,json,os,signal,subprocess,sys,time,urllib.request,traceback
from pathlib import Path
import psutil
import cua_driver as cd
OUT=Path('/work');PY=sys.executable;PREFIX='/workspace/.footwork-setup/sysroot';ROOT=Path('/workspace/Footwork/jevdual')
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def read(p):return json.loads(p.read_text())
def run(cmd,env,out,timeout=120):
 start=time.monotonic();term=[];p=subprocess.Popen(cmd,env=env,stdout=(out.with_suffix('.stdout')).open('w'),stderr=(out.with_suffix('.stderr')).open('w'))
 try:code=p.wait(timeout=timeout)
 except subprocess.TimeoutExpired:
  term.append('TERM');p.terminate()
  try:code=p.wait(timeout=2)
  except subprocess.TimeoutExpired:term.append('KILL');p.kill();code=p.wait(timeout=3)
 row={'started':start,'finished':time.monotonic(),'returncode':code,'signal':-code if code<0 else None,'termination':term,'wait_complete':True};write(out.with_suffix('.exit.json'),row)
 return row

def start(case):
 state=case/'session';log=(case/'supervisor.log').open('w');p=subprocess.Popen([PY,'-I','-m','jevdual.linux_session',str(state),'--rootless-prefix',PREFIX],stdout=log,stderr=subprocess.STDOUT)
 end=time.monotonic()+36;ready=False
 while p.poll() is None and time.monotonic()<end:
  if (state/'started').exists():ready=True;break
  time.sleep(.03)
 return p,state,log,ready

def stop(p,state,log):
 if p.poll() is None:p.terminate()
 try:code=p.wait(timeout=8)
 except subprocess.TimeoutExpired:p.kill();code=p.wait(timeout=3)
 log.close();report=read(state/'session.json');write(state.parent/'supervisor-exit.json',{'returncode':code,'wait_complete':True})
 return code,report

def environment(state):
 env=os.environ.copy();env.update(DISPLAY=(state/'display').read_text().strip(),DBUS_SESSION_BUS_ADDRESS=(state/'session-bus').read_text().strip(),XDG_RUNTIME_DIR=str(state/'runtime'))
 for kind in ['config','cache','data','state']:env['XDG_'+kind.upper()+'_HOME']=str(state/kind)
 return env

async def windows(pid):
 d=cd.CuaDriver.create(embedded=True)
 try:return [w.window_id for w in (await d.list_windows(cd.ListWindowsInput(pid=pid,on_screen_only=True))).windows]
 finally:await d.shutdown()

def recovery(case,state):
 env=environment(state);profile=str(case/'recovery-profile');env.update(FOOTWORK_CHROME_EXECUTABLE='/usr/lib/chromium/chromium',FOOTWORK_CHROME_PROFILE=profile,FOOTWORK_CHROME_PORT='9444')
 os.environ.update({k:env[k] for k in ['DISPLAY','DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR']})
 log=(case/'recovery-chrome.log').open('w');chrome=subprocess.Popen(['/usr/lib/chromium/chromium','--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--keep-alive-for-test','--user-data-dir='+profile,'--remote-debugging-port=9444','--remote-debugging-address=127.0.0.1','--no-first-run','--no-default-browser-check','--force-renderer-accessibility','about:blank'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 paused=False;caller=None;result={};http=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 try:
  incarnation=psutil.Process(chrome.pid).create_time();end=time.monotonic()+20
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
  while asyncio.run(windows(chrome.pid)) and time.monotonic()<end:time.sleep(.05)
  assert asyncio.run(windows(chrome.pid))==[]
  so=(case/'recovery.stdout').open('w');se=(case/'recovery.stderr').open('w');os.kill(chrome.pid,signal.SIGSTOP);paused=True
  started=time.monotonic();caller=subprocess.Popen([PY,'-I','-m','jevdual.cli','--json','browser','start','Recover owned profile','--session',str(case/'recovered')],env=env,stdout=so,stderr=se)
  end=time.monotonic()+5;helper=None
  while caller.poll() is None and time.monotonic()<end:
   for child in psutil.Process(caller.pid).children():
    try:
     args=child.cmdline()
     if child.exe()=='/usr/lib/chromium/chromium' and '--user-data-dir='+profile in args and '--remote-debugging-port=9444' in args:helper=child.pid;break
    except psutil.Error:pass
   if helper:break
   time.sleep(.01)
  assert helper,'owned helper not observed'
  probe=subprocess.run([PY,'-I','-c',"from jevdual.browser_driver import chrome_pid\ntry: print(chrome_pid())\nexcept RuntimeError: print('ambiguous')"],env=env,capture_output=True,text=True,timeout=2)
  assert probe.returncode==0 and probe.stdout.strip()=='ambiguous'
  os.kill(chrome.pid,signal.SIGCONT);paused=False
  code=caller.wait(timeout=30);so.close();se.close()
  result.update(returncode=code,signal=-code if code<0 else None,started=started,finished=time.monotonic(),helper=helper,ambiguous_control=True)
  write(case/'recovery-exit.json',result)
  assert code==0,'public recovery process exit'
  saved=read(case/'recovered/session.json');assert saved['pid']==chrome.pid and psutil.Process(chrome.pid).create_time()==incarnation
  assert asyncio.run(windows(chrome.pid))
  result.update(same_root=True,root_pid=chrome.pid,incarnation=incarnation,profile=profile);write(case/'recovery-exit.json',result)
 finally:
  if paused:os.kill(chrome.pid,signal.SIGCONT)
  if caller is not None and caller.poll() is None:caller.terminate();caller.wait(timeout=5)
  os.killpg(chrome.pid,signal.SIGTERM)
  try:chrome.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(chrome.pid,signal.SIGKILL);chrome.wait()
  log.close()

write(OUT/'identity.json',{'product_source':'51ee6e2f57c3959ce30e19f168baa864d9d38a6b','product_sha256':'c8fdc3644f3e109377a819dc327f5f7621aab71a136e5ca3c214665e8b312e4b','native_sha256':'3d63eff31c16bcbeffe4acdea9a2291d10a26b4110bbbfa652906d8ed8a69a20','policy':{'startup':30,'probe':3,'grace':2,'wm_service_per_attempt':1},'pid1':Path('/proc/1/comm').read_text().strip(),'limits':{n:Path('/sys/fs/cgroup/'+n).read_text().strip() for n in ['pids.max','memory.max','memory.swap.max','cpu.max']}})
# Fresh worker processes, three create/observe/shutdown cycles in each.
worker=OUT/'native-cycle.py';worker.write_text('''import asyncio,json,sys,time
from pathlib import Path
from jevdual.linux_session import _target_probe
pid=int(sys.argv[1]);document=Path(sys.argv[2]);events=Path(sys.argv[3])
def phase(p):
 with events.open('a') as f:f.write(json.dumps({'phase':p,'monotonic':time.monotonic()})+'\\n')
async def main():
 for i in range(3):
  phase('cycle_start');r=await _target_probe(pid,document,phase);assert r['ready'];phase('cycle_complete')
asyncio.run(main());print('{"ready":true}',flush=True)
''')
rows=[]
for kind,count in [('lifecycle',30),('journey',10)]:
 for i in range(count):
  case=OUT/f'{kind}-{i:02}';case.mkdir();p,state,log,ready=start(case);row={'kind':kind,'attempt':i,'ready':ready,'passed':False}
  try:
   assert ready,'target readiness failed'
   if kind=='lifecycle':
    r=run([PY,'-I',str(worker),(state/'editor.pid').read_text().strip(),str(state/'document.txt'),str(case/'driver.events')],environment(state),case/'driver',timeout=12);assert r['returncode']==0 and not r['termination']
   else:
    r=run([PY,'-I',str(ROOT/'scripts/linux/qualify.py'),'--state',str(state),'--output',str(case/'installed'),'--chrome','/usr/lib/chromium/chromium'],environment(state),case/'journey',timeout=120);assert r['returncode']==0 and not r['termination'],'installed journey process'
    assert read(case/'installed/receipt.json')['saved_file_exact'];recovery(case,state)
   row['passed']=True
  except Exception as e:
   row['error']=str(e);(case/'failure.txt').write_text(traceback.format_exc())
  finally:
   code,report=stop(p,state,log);row['supervisor_returncode']=code;row['cleanup']=report.get('cleanup');row['passed']=row['passed'] and code==0 and not any(report['cleanup'][k] for k in ['survivors','uncertain','zombies'])
   rows.append(row);write(OUT/'attempts.json',rows);print(row,flush=True)
write(OUT/'counters.json',{n:Path('/sys/fs/cgroup/'+n).read_text().strip() for n in ['pids.current','pids.events','memory.events']})
assert len(rows)==40 and all(r['passed'] for r in rows), 'finite acceptance failed; every attempt retained'
