"""Native consolidated readiness/cleanup gates plus explicit capability injections."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path('/workspace/Footwork/jevdual');OUT=Path('/work');PY=sys.executable
cases={}
wm = '''import ctypes,time
p=ctypes.c_void_p;u=ctypes.c_ulong;i=ctypes.c_int
x=ctypes.CDLL('libX11.so.6');x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=p
x.XDefaultRootWindow.argtypes=[p];x.XDefaultRootWindow.restype=u
x.XCreateSimpleWindow.argtypes=[p,u,i,i,ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,u,u];x.XCreateSimpleWindow.restype=u
x.XInternAtom.argtypes=[p,ctypes.c_char_p,i];x.XInternAtom.restype=u
x.XSetSelectionOwner.argtypes=[p,u,u,u];x.XFlush.argtypes=[p]
d=x.XOpenDisplay(None);w=x.XCreateSimpleWindow(d,x.XDefaultRootWindow(d),0,0,1,1,0,0,0)
x.XSetSelectionOwner(d,x.XInternAtom(d,b'WM_S0',0),w,0);x.XFlush(d)
time.sleep(60)
'''
programs={
 'selection-only': f"""import sys
from pathlib import Path
from jevdual.linux_session import Session
s=Session(Path('/work/fault-selection-only'),prefix=Path('/workspace/.footwork-setup/sysroot'),startup=5,commands={{'wm':[sys.executable,'-c',{wm!r}]}})
raise SystemExit(s.run())
""",
 'partial-inventory': """from pathlib import Path
from jevdual import linux_session as m
original=m.process_table
class Cut(m.Session):
 def transition(self,phase,**kw):
  super().transition(phase,**kw)
  if phase=='ready':m.process_table=lambda:original(limit=1)
s=Cut(Path('/work/fault-partial-inventory'),prefix=Path('/workspace/.footwork-setup/sysroot'),startup=30,probe_timeout=10)
raise SystemExit(s.run())
""",
}
for status in ['unsupported','denied','resource_exhausted']:
 programs[status]=f"""from pathlib import Path
from jevdual import linux_session as m
m.pin_signal=lambda *_:{{'status':{status!r},'delivery':None}}
s=m.Session(Path('/work/fault-{status}'),prefix=Path('/workspace/.footwork-setup/sysroot'))
raise SystemExit(s.run())
"""
for label,program in programs.items():
 p=subprocess.run([PY,'-I','-c',program],capture_output=True,text=True,timeout=45)
 (OUT/(label+'.txt')).write_text(p.stdout+p.stderr)
 r=json.loads((OUT/('fault-'+label)/'session.json').read_text())
 assert p.returncode==1 and r['phase']=='failed'
 assert not (OUT/('fault-'+label)/'started').exists()
 assert not r['cleanup']['survivors'],r
 if label=='partial-inventory':
  assert r['reason']=='process_inventory_incomplete' and r['cleanup']['uncertain']
  assert not r['cleanup']['inventory_complete'] and 'entry_limit' in r['cleanup']['inventory_reasons']
 elif label=='selection-only':assert r['reason']=='wm:wm_ewmh_unavailable'
 else:assert r['reason']=='pinned_signalling_unavailable:'+label and r['signal_capability']['delivery'] is None
 cases[label]=r
# Existing process ownership, cancellation, pin failure and root identity tests,
# all executed within the same init/512-PID boundary.
p=subprocess.run([str(ROOT/'.venv/bin/python'),'-I','-m','pytest','-q','-p','no:cacheprovider',str(ROOT/'tests/test_linux_process.py'),str(ROOT/'tests/test_linux_session.py'),str(ROOT/'tests/test_host_probe.py')],cwd=ROOT,capture_output=True,text=True,timeout=60)
(OUT/'process-fault-tests.txt').write_text(p.stdout+p.stderr)
assert p.returncode==0,p.stdout+p.stderr
(OUT/'faults.json').write_text(json.dumps(cases,indent=2)+'\n')
print(json.dumps({'passed':True,'cases':{k:{'phase':v['phase'],'reason':v['reason'],'cleanup':v['cleanup']} for k,v in cases.items()}}))
