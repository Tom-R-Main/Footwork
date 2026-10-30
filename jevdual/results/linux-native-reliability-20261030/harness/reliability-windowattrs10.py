import subprocess,sys,time,json,os,signal
from pathlib import Path
out=Path('/work');py=sys.executable
base=out
for attempt in range(10):
 out=base/f'case-{attempt:02}';out.mkdir()
 state=out/'session';p=subprocess.Popen([py,'-I','-m','jevdual.linux_session',str(state),'--rootless-prefix','/workspace/.footwork-setup/sysroot'],stdout=(out/'session.log').open('w'),stderr=subprocess.STDOUT)
 try:
  end=time.monotonic()+35;inspected=False
  while p.poll() is None and time.monotonic()<end:
   attempts=list(state.glob('probe-target-*.json')) if state.exists() else []
   if attempts and not inspected and time.monotonic()>end-32:
    inspected=True
    env=os.environ.copy();env.update(DISPLAY=(state/'display').read_text().strip(),DBUS_SESSION_BUS_ADDRESS=(state/'session-bus').read_text().strip(),XDG_RUNTIME_DIR=str(state/'runtime'))
    script='''import cua_driver as cd,asyncio,json,sys
 async def main():
  d=cd.CuaDriver.create(embedded=True)
  try:
   for pid in [int(sys.argv[1]),None]:
    ws=(await d.list_windows(cd.ListWindowsInput(pid=pid,on_screen_only=True))).windows
    print(json.dumps({'requested_pid':pid,'windows':[{'pid':w.pid,'id':w.window_id,'title':w.title} for w in ws]}),flush=True)
  finally:await d.shutdown()
 asyncio.run(main())'''
    q=subprocess.run([py,'-I','-c',script.splitlines()[0]+'\n'+__import__('textwrap').dedent('\n'.join(script.splitlines()[1:])),(state/'editor.pid').read_text().strip()],env=env,capture_output=True,text=True,timeout=10);(out/'native-view.txt').write_text(q.stdout+q.stderr)
    q=subprocess.run(['xwininfo','-root','-tree'],env=env,capture_output=True,text=True,timeout=3);(out/'x11-view.txt').write_text(q.stdout+q.stderr)
    q=subprocess.run(['xwininfo','-id','0x400003'],env=env,capture_output=True,text=True,timeout=3);(out/'x11-attributes.txt').write_text(q.stdout+q.stderr)
    q=subprocess.run(['xprop','-root','_NET_CLIENT_LIST','_NET_CLIENT_LIST_STACKING','_NET_SUPPORTING_WM_CHECK'],env=env,capture_output=True,text=True,timeout=3);(out/'wm-properties.txt').write_text(q.stdout+q.stderr)
    q=subprocess.run(['xprop','-id','0x400003','WM_STATE','_NET_WM_PID','WM_CLASS'],env=env,capture_output=True,text=True,timeout=3);(out/'editor-properties.txt').write_text(q.stdout+q.stderr)
    print('inspected',flush=True)
   if (state/'started').exists():print('ready',flush=True);break
   time.sleep(.1)
 finally:
  if p.poll() is None:p.terminate()
  p.wait(timeout=8)
