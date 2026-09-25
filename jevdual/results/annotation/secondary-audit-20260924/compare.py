"""Compare frozen AI audit labels using repeat-safe identities; no human-validation claim."""
import csv,json
from pathlib import Path
from collections import Counter
OUT=Path(__file__).resolve().parent
BASE=OUT.parent

def key(row):
    return (row['run'],row.get('run_id') or row['task']+'|'+row['arm'],row['step'])

report={}
for tag,base,name in [('web',BASE,'q1-s1-decisions.csv'),('native',BASE/'q10','q10-s1-decisions.csv')]:
    audit=list(csv.DictReader((OUT/f'{tag}-audit.csv').open()))
    full=list(csv.DictReader((base/name).open()))
    lookup={key(r):r for r in full}
    assert len(lookup)==len(full), 'Ambiguous full-table identity'
    stats={'labels':dict(Counter(r['audit_label'] for r in audit)),'comparisons':{},'differences':[]}
    for col in ('label_a','label_b','model_label'):
        pairs=[(r['audit_label'],lookup[key(r)][col]) for r in audit if lookup[key(r)][col] in ('right','wrong','unclear')]
        n=len(pairs)
        if not n:
            stats['comparisons'][col]={'n':0,'agreement':None,'kappa':None}
            continue
        agreement=sum(a==b for a,b in pairs)/n
        ca,cb=Counter(a for a,b in pairs),Counter(b for a,b in pairs)
        pe=sum(ca[k]*cb[k] for k in ca)/(n*n)
        stats['comparisons'][col]={'n':n,'agreement':agreement,'kappa':(agreement-pe)/(1-pe) if pe!=1 else None}
    for i,r in enumerate(audit):
        m=lookup[key(r)]
        if m['model_label']!=r['audit_label']:
            stats['differences'].append({'row_index':i,'key':key(r),'audit':r['audit_label'],'model':m['model_label'],'reason_a':m['reason_a'],'audit_note':r['audit_note']})
    report[tag]=stats
(OUT/'agreement.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v['comparisons'] for k,v in report.items()},indent=2))
