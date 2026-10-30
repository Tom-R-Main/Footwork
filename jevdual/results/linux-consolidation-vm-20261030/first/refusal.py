"""Intentionally omit WM readiness to challenge the installed SDK no-input gate."""
import asyncio,dataclasses,json,os,subprocess,sys,time
from pathlib import Path
import cua_driver as cd
from jevdual.linux_session import Session
from jevdual.native import NativeBridge
from jevdual.posture import ExecutionPolicy

OUT=Path('/work');state=OUT/'negative-no-wm';owner=Session(state,prefix=Path('/workspace/.footwork-setup/sysroot'))
record={'implementation_commit':'f16cc54','fixture':'intentional no-WM gate challenge; no readiness marker or authority claim'}
original=cd.CuaDriver.call_tool
async def capture(self,name,args):
 result=await original(self,name,args)
 if name=='hotkey':
  raw={k:getattr(result,k,None) for k in ['text','structured_json','is_error','error_code','raw_json']}
  raw['action_present']=result.action is not None
  (OUT/'refusal-sdk.json').write_text(json.dumps(raw,indent=2)+'\n')
 return result
cd.CuaDriver.call_tool=capture
async def save(pid,wid):
 driver=cd.CuaDriver.create(embedded=True)
 try:
  bridge=NativeBridge(driver,pid,wid,policy=ExecutionPolicy('exclusive_desktop'))
  snapshot=await bridge.observe()
  values=list(snapshot.values.values())
  assert any('Refused save remains unsaved' in value for value in values)
  effect=await bridge.hotkey(snapshot,['ctrl','s'])
  return dataclasses.asdict(effect)
 finally:await asyncio.wait_for(driver.shutdown(),timeout=3)
try:
 owner.prepare();deadline=time.monotonic()+30
 owner.allocate_display(deadline);owner.await_probe('x11',deadline)
 owner.spawn('bus',['dbus-daemon','--session','--nofork','--address='+owner.env['DBUS_SESSION_BUS_ADDRESS']]);owner.await_probe('bus',deadline)
 editor=owner.spawn('editor',['mousepad','--disable-server',str(state/'document.txt')]);owner.await_probe('atspi',deadline)
 target=owner.await_probe('target',deadline)
 owner.transition('negative_fixture',target=target)
 before=(state/'document.txt').read_bytes()
 for label,args in [('start',['start','Exercise only the owned refusal fixture','--app','Mousepad','--pid',str(editor.pid),'--session','/work/refusal-session']),('append',['do','append','text area','Refused save remains unsaved 🧪  ','--session','/work/refusal-session'])]:
  r=subprocess.run([sys.executable,'-I','-m','jevdual.cli',*args],env=owner.env,capture_output=True,text=True,timeout=30)
  (OUT/('refusal-'+label+'.txt')).write_text(r.stdout+r.stderr)
  assert r.returncode==0,r.stdout+r.stderr
 for key in ['DISPLAY','DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR']:os.environ[key]=owner.env[key]
 effect=asyncio.run(asyncio.wait_for(save(editor.pid,target['window_id']),timeout=20))
 record['save_effect']=effect
 record['disk_unchanged']=(state/'document.txt').read_bytes()==before
 assert effect['effect']=='refused' and effect['dispatched'] is False
 assert effect['delivered_count']==0 and effect['readback'] is None and record['disk_unchanged']
 assert effect['error_code']=='foreground_unavailable' and not (state/'started').exists()
 record['passed']=True
finally:
 owner.transition('stopping')
 owner.report['cleanup']=owner.cleanup()
 owner.transition('stopped' if not owner.report['cleanup']['survivors'] and not owner.report['cleanup']['uncertain'] else 'failed')
 record['cleanup']=owner.report['cleanup']
 (OUT/'refusal.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
