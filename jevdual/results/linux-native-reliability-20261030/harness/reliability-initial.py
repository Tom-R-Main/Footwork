import subprocess,sys,time,json,os,signal
from pathlib import Path
PY=sys.executable;OUT=Path('/work');PREFIX='/workspace/.footwork-setup/sysroot'
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
write(OUT/'identity.json',{'source':'5324f6f','product_sha256':'db820e3ee44d3f8051d5a2a6cebe5a158bb5a48e430e93a41e6d84f5f403fb85','native_sha256':'0595b6042a98538b3c79ddef07301dd9481e477a5fbf64278b6cc63c2ed474c9','policy':{'startup':30,'probe':3,'grace':2},'limits':{n:Path('/sys/fs/cgroup/'+n).read_text().strip() for n in ['pids.max','memory.max','memory.swap.max','cpu.max']}})
# 10 fresh session attempts, no rerun replacement.
rows=[]
for i in range(10):
 state=OUT/f'session-{i:02}'; log=(OUT/f'session-{i:02}.log').open('w')
 p=subprocess.Popen([PY,'-I','-m','jevdual.linux_session',str(state),'--rootless-prefix',PREFIX],stdout=log,stderr=subprocess.STDOUT)
 end=time.monotonic()+36;ready=False
 while p.poll() is None and time.monotonic()<end:
  if (state/'started').exists():ready=True;break
  time.sleep(.05)
 if p.poll() is None:p.terminate()
 try:code=p.wait(timeout=8)
 except subprocess.TimeoutExpired:p.kill();code=p.wait(timeout=3)
 log.close();row={'attempt':i,'ready':ready,'returncode':code,'state':str(state)};rows.append(row);write(OUT/'attempts.json',rows);print(row,flush=True)
