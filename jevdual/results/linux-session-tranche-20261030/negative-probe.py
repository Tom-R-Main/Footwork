"""Negative-only owned no-WM session; never presented as a ready desktop."""
import asyncio
import dataclasses
import json
import os
import signal
import subprocess
import time
from pathlib import Path

root = Path('/artifacts/refused-save')
root.mkdir(mode=0o700)
os.environ.update(DISPLAY=':99', NO_AT_BRIDGE='0', GTK_MODULES='atk-bridge', JEVDUAL_PURE_PY='1')
for key, name in [('XDG_RUNTIME_DIR','runtime'),('XDG_CONFIG_HOME','config'),('XDG_CACHE_HOME','cache'),
                  ('XDG_DATA_HOME','data'),('XDG_STATE_HOME','state')]:
    path=root/name
    path.mkdir(mode=0o700)
    os.environ[key]=str(path)
document=root/'document.txt'
document.write_text('Original owned text\n')
children=[]
handles=[]

def start(name, command):
    log=(root/(name+'.log')).open('w'); handles.append(log)
    p=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    children.append(p)
    return p

async def check(pid):
    from cua_driver import CuaDriver,ListWindowsInput
    from jevdual.native import NativeBridge
    from jevdual.posture import ExecutionPolicy
    driver=CuaDriver.create(embedded=True)
    try:
        deadline=time.monotonic()+15
        bridge=None
        while time.monotonic()<deadline:
            windows=(await driver.list_windows(ListWindowsInput(pid=pid,on_screen_only=True))).windows
            if len(windows)==1:
                bridge=NativeBridge(driver,pid,windows[0].window_id,policy=ExecutionPolicy('exclusive_desktop'))
                menu=await bridge.observe()
                fields=[c for c in menu.menu.candidates if 'append' in c.operations]
                if len(fields)==1:break
            await asyncio.sleep(.2)
        else:raise RuntimeError('no exact fixture field')
        effect=await bridge.act(menu,'append',fields[0].id,'Unsaved negative fixture')
        assert effect.effect=='confirmed',effect
        menu=await bridge.observe()
        result=await bridge.hotkey(menu,['ctrl','s'])
        receipt=dataclasses.asdict(result)
        (root/'driver-save.json').write_text(json.dumps(receipt,indent=2)+'\n')
        assert result.effect=='refused' and not result.dispatched and result.delivered_count==0,receipt
        assert result.readback is None and result.error_code=='foreground_unavailable',receipt
        assert document.read_text()=='Original owned text\n'
        (root/'receipt.json').write_text(json.dumps({'qualified_no_input':True,'disk_unchanged':True,
                                                   'direct_bridge_negative_only':True},indent=2)+'\n')
        print(json.dumps(receipt))
    finally:await driver.shutdown()

try:
    start('xvfb',['Xvfb',':99','-screen','0','1280x900x24','-nolisten','tcp'])
    deadline=time.monotonic()+5
    while not Path('/tmp/.X11-unix/X99').exists():
        assert time.monotonic()<deadline and children[0].poll() is None
        time.sleep(.05)
    editor=start('editor',['mousepad','--disable-server',str(document)])
    asyncio.run(check(editor.pid))
finally:
    for p in reversed(children):
        if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
        try:p.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=2)
    for h in handles:h.close()
