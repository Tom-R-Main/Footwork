import subprocess,sys,json
from pathlib import Path
ROOT=Path('/workspace/Footwork/jevdual');OUT=Path('/work')
# Historical control harnesses; exact source copies are supplied in the final
# evidence with only version, default timeout and probe-log adaptations.
program=Path('/workspace/Footwork/jevdual/results/linux-consolidation-vm-20261030/first/refusal.py')
# Files are mounted through the consumer for this standalone task harness.
for name in ['refusal','faults']:
 p=subprocess.run([sys.executable,'-I',f'/workspace/scratch/fw-reliability-final-consumer/{name}-control.py'],capture_output=True,text=True,timeout=160)
 (OUT/(name+'-control.stdout')).write_text(p.stdout);(OUT/(name+'-control.stderr')).write_text(p.stderr)
 (OUT/(name+'-control.exit.json')).write_text(json.dumps({'returncode':p.returncode}))
 print(name,p.returncode,flush=True)
 assert p.returncode==0,p.stdout[-3000:]+p.stderr[-3000:]
