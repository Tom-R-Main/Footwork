import json,os,subprocess,sys,time
from pathlib import Path
import psutil
from jevdual.linux_ax import _Bus,_DBUS
kind=sys.argv[1];OUT=Path('/work');state=OUT/('critical-'+kind)
log=(OUT/('critical-'+kind+'.log')).open('w')
p=subprocess.Popen([sys.executable,'-I','-m','jevdual.linux_session',str(state),'--rootless-prefix','/workspace/.footwork-setup/sysroot','--probe-timeout','10'],stdout=log,stderr=subprocess.STDOUT)
r={'kind':kind,'implementation_commit':'f16cc54'}
try:
 end=time.monotonic()+35
 while not (state/'started').exists():
  if p.poll() is not None:raise RuntimeError('readiness failed: '+(state/'session.json').read_text())
  assert time.monotonic()<end
  time.sleep(.05)
 if kind=='atspi':
  os.environ['DBUS_SESSION_BUS_ADDRESS']=(state/'session-bus').read_text()
  os.environ['DISPLAY']=(state/'display').read_text().strip()
  os.environ['XDG_RUNTIME_DIR']=str(state/'runtime')
  with _Bus() as bus:
   pid=bus.call(_DBUS,'org.freedesktop.DBus','GetConnectionUnixProcessID','s',('org.freedesktop.DBus',))[0]
   r['previous_accessibility_identity']=bus.identity
  os.kill(pid,15)
 else:
  name={'xvfb':'Xvfb','bus':'dbus-daemon','editor':'mousepad'}[kind]
  candidates=[c for c in psutil.Process(p.pid).children() if c.name()==name]
  assert len(candidates)==1
  candidates[0].terminate()
 p.wait(timeout=15)
 r['session']=json.loads((state/'session.json').read_text())
 assert r['session']['phase']=='failed' and not (state/'started').exists()
 if kind=='atspi':assert r['session']['reason']=='accessibility_bus_changed' or r['session']['reason'].startswith('atspi:')
 else:assert r['session']['reason']=='component_exited:'+kind
 assert not r['session']['cleanup']['survivors'] and not r['session']['cleanup']['uncertain']
 r['passed']=True
finally:
 if p.poll() is None:p.terminate();p.wait(timeout=8)
 log.close()
 if (state/'session.json').exists():r['session']=json.loads((state/'session.json').read_text())
 r['counters']={n:Path('/sys/fs/cgroup/'+n).read_text().strip() for n in ['pids.current','pids.events','memory.events']}
 (OUT/('critical-'+kind+'.json')).write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'passed':r['passed'],'kind':kind,'reason':r['session']['reason'],'cleanup':r['session']['cleanup']}))
