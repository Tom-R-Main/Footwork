import subprocess,sys,json
from pathlib import Path
ROOT=Path('/workspace/Footwork/jevdual');OUT=Path('/work')
# Historical control harnesses; exact source copies are supplied in the final
# evidence with only version, default timeout and probe-log adaptations.
program=Path('/workspace/Footwork/jevdual/results/linux-consolidation-vm-20261030/first/refusal.py')
# Files are mounted through the consumer for this standalone task harness.
for name in ['refusal','faults']:
 p=subprocess.run([sys.executable,'-I',f'/workspace/scratch/fw-reliability-release-consumer/{name}-control.py'],capture_output=True,text=True,timeout=160)
 (OUT/(name+'-control.stdout')).write_text(p.stdout);(OUT/(name+'-control.stderr')).write_text(p.stderr)
 (OUT/(name+'-control.exit.json')).write_text(json.dumps({'returncode':p.returncode}))
 print(name,p.returncode,flush=True)
 assert p.returncode==0,p.stdout[-3000:]+p.stderr[-3000:]

for kind in ['xvfb','bus','editor','wm','atspi']:
 p=subprocess.run([sys.executable,'-I','/workspace/scratch/fw-reliability-release-consumer/critical-control.py',kind],capture_output=True,text=True,timeout=50)
 (OUT/('critical-'+kind+'.stdout')).write_text(p.stdout);(OUT/('critical-'+kind+'.stderr')).write_text(p.stderr)
 (OUT/('critical-'+kind+'.exit.json')).write_text(json.dumps({'returncode':p.returncode}))
 print(kind,p.returncode,flush=True)
 assert p.returncode==0,p.stdout[-2000:]+p.stderr[-2000:]
# Cancellation before readiness, separate from primary30/10 attempts.
import time
state=OUT/'cancel-early';log=(OUT/'cancel-early.log').open('w')
p=subprocess.Popen([sys.executable,'-I','-m','jevdual.linux_session',str(state),'--rootless-prefix','/workspace/.footwork-setup/sysroot'],stdout=log,stderr=subprocess.STDOUT)
end=time.monotonic()+5
while not (state/'session.json').exists() and p.poll() is None and time.monotonic()<end:time.sleep(.005)
assert p.poll() is None;p.terminate();code=p.wait(timeout=8);log.close()
r=json.loads((state/'session.json').read_text());assert code==0 and not (state/'started').exists() and r['phase']=='stopped' and not r['cleanup']['survivors'] and not r['cleanup']['uncertain']
(OUT/'cancel-early.exit.json').write_text(json.dumps({'returncode':code,'session':r}));print('cancel-early',code,flush=True)
