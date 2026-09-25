"""Offline sensitivity analysis; source labels remain unchanged. Run from jevdual."""
import csv,json,random
from pathlib import Path
from collections import Counter,defaultdict
from evals.metrics import auroc
from evals.calibration import pairs_for

OUT=Path(__file__).resolve().parent
rows=list(csv.DictReader(open('results/annotation/q10/q10-s1-decisions.csv')))
labeled=[r for r in rows if r['model_label'] in ('right','wrong')]
results={}
for name,sub in [('all',labeled),('clicks',[r for r in labeled if r['s1_operation']=='click']),('without_percent',[r for r in labeled if r['task']!='calc-percent']),('percent_only',[r for r in labeled if r['task']=='calc-percent'])]:
 results[name]={'n':len(sub),'labels':dict(Counter(r['model_label'] for r in sub)),'target_n':len(pairs_for(sub,'s1_target_conf')),'target_auc':auroc(pairs_for(sub,'s1_target_conf')),'operation_auc':auroc(pairs_for(sub,'s1_op_conf'))}
# Task-cluster bootstrap; resample entire tasks to avoid treating repeated clicks as independent.
groups=defaultdict(list)
for r in labeled:groups[r['task']].append(r)
rng=random.Random(20260924);names=sorted(groups);vals=[]
for _ in range(4000):
 sample=[r for _ in names for r in groups[rng.choice(names)]]
 x=auroc(pairs_for(sample,'s1_target_conf'))
 if x is not None:vals.append(x)
vals.sort();results['task_cluster_bootstrap']={'draws':4000,'valid_draws':len(vals),'ci95':[vals[int(.025*len(vals))],vals[int(.975*len(vals))-1]],'warning':'Seven task types only; pooled AUC remains composition-sensitive; labels not independently validated.'}
results['wrong_by_task']=dict(Counter(r['task'] for r in labeled if r['model_label']=='wrong'))
results['disagreements_by_task']=dict(Counter(r['task'] for r in rows if r['model_label']=='disagree'))
# Detect duplicate identities in the supplied comparison script.
results['legacy_agreement_key_collisions']=len(rows)-len({(r['run'],r['task'],r['arm'],r['step']) for r in rows})
rs=json.loads(Path('results/q10-native-dev-20260924/results.json').read_text())
results['arms']={}
for arm in ('s1_only','dual','guarded'):
 xs=[r for r in rs if r['arm']==arm];cost=sum(r['llm_cost_usd']+r['jev_cost_usd'] for r in xs);verified=sum(r['passed'] and r['is_done'] for r in xs)
 results['arms'][arm]={'n':len(xs),'passed':sum(r['passed'] for r in xs),'verified':verified,'estimated_cost':cost,'cost_per_verified':cost/verified,'per_task':{t:{'passed':sum(r['passed'] for r in xs if r['task_id']==t),'verified':sum(r['passed'] and r['is_done'] for r in xs if r['task_id']==t)} for t in sorted({r['task_id'] for r in xs})}}
(OUT/'sensitivity.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
