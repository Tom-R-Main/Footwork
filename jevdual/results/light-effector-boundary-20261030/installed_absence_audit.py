from pathlib import Path
import json,os,subprocess
root=Path(__file__).resolve().parent
case=root/'installed-absence-audit';case.mkdir()
env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV')}
exe=root/'package-audit-final/venv/bin/footwork'
receipt={'source_commit':'e32913b35fcddcff6b518fc61b3242b8ebe68f5a','wheel_sha256':'bc6d09d1387677b904ec717fb546ce4ed536198a56bdfeba0d2a45c9c82bf109','cases':[]}
for surface in ('native','browser'):
    for existing in (False,True):
        directory=case/f'{surface}-{existing}'
        if existing:
            directory.mkdir()
            for name in ('session.json','session.jsonl','carries.json','grants.json'):
                (directory/name).write_text('{"retained":"fixture"}\n')
        before={p.name:p.read_bytes() for p in directory.iterdir()} if existing else {}
        argv=[str(exe),'--json','start','fixture task','--session',str(directory)]
        if surface=='browser':argv.append('--browser')
        proc=subprocess.run(argv,cwd=case,env=env,text=True,capture_output=True,timeout=20)
        payload=json.loads(proc.stdout)
        assert proc.returncode==7 and 'effector_unavailable' in proc.stdout,(proc.returncode,payload,proc.stderr)
        if existing:
            for name,content in before.items():
                after=(directory/name).read_bytes()
                assert after.startswith(content) if name=='session.jsonl' else after==content
        else:assert not directory.exists()
        receipt['cases'].append({'surface':surface,'existing':existing,'exit':proc.returncode,'preserved':True,'response':payload})
output=case/'run-output-must-not-exist'
proc=subprocess.run([str(exe),'--json','run','fixture task','--app','Fixture','--out',str(output)],cwd=case,env=env,text=True,capture_output=True,timeout=20)
assert proc.returncode==7 and 'effector_unavailable' in proc.stdout,(proc.returncode,proc.stdout,proc.stderr)
assert not output.exists()
receipt['cases'].append({'surface':'run','exit':proc.returncode,'output_absent':True,'response':json.loads(proc.stdout)})
script='''import asyncio,json,importlib.util
from jevdual import browser_driver
from jevdual.effectors import EffectorUnavailable
assert importlib.util.find_spec("cua_driver") is None
def forbidden(*a,**kw):
    raise AssertionError("Chrome launch attempted without SDK")
browser_driver._begin_chrome=forbidden
try:
    asyncio.run(browser_driver.bind_footwork_chrome())
except EffectorUnavailable as e:
    assert e.dispatched is False
    print(json.dumps({"code":e.code,"dispatched":e.dispatched}))
else:
    raise AssertionError("missing SDK did not refuse")
'''
proc=subprocess.run([str(root/'package-audit-final/venv/bin/python'),'-I','-c',script],cwd=case,env=env,text=True,capture_output=True,timeout=20)
assert proc.returncode==0,(proc.returncode,proc.stdout,proc.stderr)
receipt['cases'].append({'surface':'direct_browser_api','exit':0,'response':json.loads(proc.stdout)})
(case/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'passed':True,'cases':len(receipt['cases'])}))
