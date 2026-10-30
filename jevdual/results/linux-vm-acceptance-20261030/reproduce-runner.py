import json, os, signal, subprocess, time
from pathlib import Path
root=Path('/workspace/Footwork/jevdual')
out=root/'results/linux-vm-acceptance-20261030'
state=Path('/workspace/scratch/footwork-debian-desktop-ready')
consumer=Path('/workspace/scratch/footwork-debian-consumer/bin/python')
env=dict(os.environ)
env['LD_LIBRARY_PATH']='/workspace/.footwork-setup/sysroot/usr/lib/x86_64-linux-gnu'+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
env['XDG_DATA_DIRS']='/workspace/.footwork-setup/sysroot/usr/share:/usr/local/share:/usr/share'
env['XDG_CONFIG_DIRS']='/workspace/.footwork-setup/sysroot/etc/xdg:/etc/xdg'
log=(out/'desktop-ready.txt').open('w')
p=subprocess.Popen(['dbus-run-session','--','bash',str(root/'scripts/linux/desktop-session.sh'),str(state)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
result={'source_commit':'0b1e82c','state':str(state),'chrome':'/usr/lib/chromium/chromium'}
try:
 for _ in range(150):
  if (state/'started').exists():break
  if p.poll() is not None:raise RuntimeError(f'desktop exited {p.returncode}')
  time.sleep(.1)
 else:raise RuntimeError('desktop readiness timed out')
 time.sleep(3)
 with (out/'qualification-ready.txt').open('w') as qlog:
  q=subprocess.run([str(consumer),str(root/'scripts/linux/qualify.py'),'--state',str(state),'--output','/workspace/scratch/footwork-debian-qualified-ready','--chrome',result['chrome']],env=env,stdout=qlog,stderr=subprocess.STDOUT,timeout=300)
 result['qualification_exit_code']=q.returncode
except Exception as exc:result['error']=f'{type(exc).__name__}: {exc}'
finally:
 try:os.killpg(p.pid,signal.SIGTERM)
 except ProcessLookupError:pass
 try:p.wait(timeout=10)
 except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
 log.close()
 (out/'qualification-ready-run.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result))
 print((out/'qualification-ready.txt').read_text()[-6000:] if (out/'qualification-ready.txt').exists() else '')
raise SystemExit(result.get('qualification_exit_code',1))
