import json,os,subprocess,sys,time
from pathlib import Path
import psutil
OUT=Path('/work');PY=sys.executable;PREFIX='/workspace/.footwork-setup/sysroot'
results={}
def result(label,state):
 r=json.loads((state/'session.json').read_text());results[label]=r
 assert not r['cleanup']['survivors']
 return r

def launch(label,extra=(),prefix=True):
 state=OUT/label;log=(OUT/(label+'.log')).open('w')
 args=[PY,'-I','-m','jevdual.linux_session',str(state),'--startup-timeout','8']
 if prefix:args+=['--rootless-prefix',PREFIX]
 p=subprocess.Popen([*args,*extra],stdout=log,stderr=subprocess.STDOUT)
 return p,state,log

def ready(p,state):
 end=time.monotonic()+12
 while not (state/'started').exists():
  assert p.poll() is None
  assert time.monotonic()<end
  time.sleep(.03)

# Cancellation during startup must publish no readiness.
p,state,log=launch('fault-cancel-start')
end=time.monotonic()+5
while not (state/'session.json').exists():
 assert time.monotonic()<end;time.sleep(.005)
p.terminate();p.wait(timeout=8);log.close();r=result('cancel_before_ready',state)
assert not any(t['phase']=='ready' for t in r['transitions'])
# Missing rootless dependencies do not masquerade as ready.
p,state,log=launch('fault-missing-wm',prefix=False)
p.wait(timeout=12);log.close();r=result('missing_rootless_wm',state)
assert r['phase']=='failed' and not any(t['phase']=='ready' for t in r['transitions'])
# Existing actual X socket/server belongs to a different owner and survives refusal.
xlog=(OUT/'occupied-x.log').open('w')
x=subprocess.Popen(['Xvfb',':120','-screen','0','640x480x24','-nolisten','tcp'],stdout=xlog,stderr=subprocess.STDOUT)
try:
 end=time.monotonic()+5
 while not Path('/tmp/.X11-unix/X120').exists():assert x.poll() is None and time.monotonic()<end;time.sleep(.01)
 p,state,log=launch('fault-occupied',extra=['--display','120'])
 p.wait(timeout=5);log.close();r=result('occupied_display',state)
 assert r['reason']=='display_occupied' and x.poll() is None and Path('/tmp/.X11-unix/X120').exists()
finally:x.terminate();x.wait(timeout=3);xlog.close()
# Accessibility-service replacement cannot silently preserve readiness.
p,state,log=launch('fault-accessibility')
try:
 ready(p,state)
 children=psutil.Process(p.pid).children(recursive=True)
 candidates=[c for c in children if c.name()=='dbus-daemon' and c.ppid()!=p.pid]
 assert len(candidates)==1,[c.pid for c in candidates]
 candidates[0].terminate();p.wait(timeout=12)
 r=result('accessibility_bus_death',state)
 assert r['phase']=='failed' and (r['reason'].startswith('atspi:') or r['reason']=='accessibility_bus_changed')
finally:
 if p.poll() is None:p.terminate();p.wait(timeout=8)
 log.close()
(OUT/'fault-acceptance.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({'passed':True,'cases':{k:{'phase':v['phase'],'reason':v['reason'],'cleanup':v['cleanup']} for k,v in results.items()}}))
