"""Export each attempt without overwriting evidence or copying environment data."""
import json,shutil
from pathlib import Path
ROOT=Path('/workspace/Footwork/jevdual/results/linux-native-reliability-20261030')
labels=['initial','minimal','callback','recovery','recovery-isolated','recovery-gdb','recovery-gdb20','recovery-capture','admissions','windows','windows10','windowattrs10','wm10','editor10','wm-ack10','final','controls','qualified','qualified-controls','qualified-controls2','release','release-controls']
for label in labels:
 source=Path('/workspace/scratch/fw-reliability-'+label)
 if not source.exists():continue
 dest=ROOT/label;dest.mkdir(exist_ok=True)
 for name in ['attempts.json','identity.json','counters.json','cleanup-followup.json','container-config.json','container.txt','refusal.json','refusal-sdk.json','faults.json']:
  p=source/name
  if p.exists():shutil.copyfile(p,dest/name)
 sessions=[];probes=[];receipts=[];captures=[]
 for p in sorted(source.rglob('*')):
  if not p.is_file():continue
  relative=p.relative_to(source).as_posix()
  if p.name=='session.json' and 'recovered' not in relative and 'installed' not in relative:
   try:sessions.append({'path':relative,'record':json.loads(p.read_text())})
   except (ValueError,UnicodeError):pass
  elif p.name.startswith('probe-') and p.suffix=='.json':
   row={'path':relative,'record':json.loads(p.read_text())}
   for suffix,key in [('.log','stdout'),('.stderr.log','stderr')]:
    log=p.with_suffix(suffix)
    if log.exists():
     data=log.read_bytes();row[key]=data[:32768].decode(errors='replace');row[key+'_truncated']=len(data)>32768
   probes.append(row)
  elif p.name in ['driver.events','driver.stdout','driver.stderr','journey.stdout','journey.stderr','recovery.stdout','recovery.stderr','mcp-first.jsonl','mcp-restart.jsonl'] or (relative.startswith(('journey-','lifecycle-')) and p.suffix in ['.stdout','.stderr']) or p.suffix=='.gdb' or p.name.startswith(('minimal-','recovery-')) and p.suffix in ['.stdout','.stderr','.events'] or p.name in ['native-view.txt','x11-view.txt','x11-attributes.txt','wm-properties.txt','editor-properties.txt','failure.txt']:
   captures.append({'path':relative,'text':p.read_text(errors='replace')})
  elif p.suffix=='.json' and (p.name.endswith('.exit.json') or p.name in ['supervisor-exit.json','recovery-exit.json','receipt.json','driver-save.json','restarted-status.json']):
   receipts.append({'path':relative,'record':json.loads(p.read_text())})
 for name,rows in [('sessions',sessions),('probes',probes),('receipts',receipts),('captures',captures)]:
  (dest/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows))
