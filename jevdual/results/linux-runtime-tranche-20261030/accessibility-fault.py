import json,os,subprocess,sys,time
from pathlib import Path
from jevdual.linux_ax import _Bus, _DBUS
OUT=Path('/work');state=OUT/'fault-accessibility-qualified'
log=(OUT/'accessibility-fault.log').open('w')
p=subprocess.Popen([sys.executable,'-I','-m','jevdual.linux_session',str(state),'--rootless-prefix','/workspace/.footwork-setup/sysroot'],stdout=log,stderr=subprocess.STDOUT)
try:
 end=time.monotonic()+35
 while not (state/'started').exists():
  assert p.poll() is None and time.monotonic()<end
  time.sleep(.05)
 os.environ['DBUS_SESSION_BUS_ADDRESS']=(state/'session-bus').read_text()
 os.environ['DISPLAY']=(state/'display').read_text().strip()
 os.environ['XDG_RUNTIME_DIR']=str(state/'runtime')
 with _Bus() as bus:
  server=bus.call(_DBUS,'org.freedesktop.DBus','GetConnectionUnixProcessID','s',('org.freedesktop.DBus',))[0]
  identity=bus.identity
 os.kill(server,15)
 p.wait(timeout=12)
 r=json.loads((state/'session.json').read_text())
 r['fault_injection']={'accessibility_bus_pid':server,'accessibility_bus_identity':identity,'selection':'exact private accessibility bus GetConnectionUnixProcessID'}
 (OUT/'accessibility-fault.json').write_text(json.dumps(r,indent=2)+'\n')
 assert r['phase']=='failed' and not r['cleanup']['survivors']
 print(json.dumps({'passed':True,'reason':r['reason'],'cleanup':r['cleanup']}))
finally:
 if p.poll() is None:p.terminate();p.wait(timeout=8)
 log.close()
