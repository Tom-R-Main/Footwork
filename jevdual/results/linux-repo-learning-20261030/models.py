"""Deterministic source-function models; no OS signals or browser processes."""
import ast
import asyncio
import copy
import json
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

ROOT=Path('/Users/thomasmain/projects/footwork/.worktrees/linux-cloud-grounding')
OUT=Path(__file__).parent


def signal_model(replace, guarded=False):
    tree=ast.parse((ROOT/'jevdual/python/jevdual/linux_session.py').read_text())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Session')
    function=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='signal_owned')
    live={42:{'start':'root-A','session':42,'state':'S'},43:{'start':'member-A','session':42,'state':'S'}}
    captured=copy.deepcopy(live)
    delivered=[]
    def group(pid,sig):
        if replace:live[43]['start']='replacement-B'
    def single(pid,sig):delivered.append({'pid':pid,'incarnation':live[pid]['start']})
    ns={'os':SimpleNamespace(killpg=group,kill=single),'signal':__import__('signal')}
    exec(compile(ast.Module(body=[function],type_ignores=[]),'cloud-signal-owned','exec'),ns)
    fake=SimpleNamespace(capture=lambda:copy.deepcopy(captured),processes={'root':SimpleNamespace(pid=42)})
    if guarded:
        group(42,15)
        for pid,row in captured.items():
            if live[pid]['start']==row['start']:single(pid,15)
    else:ns['signal_owned'](fake,['root'],15)
    violation=any(row['incarnation']=='replacement-B' for row in delivered)
    return {'replace_after_group':replace,'test_only_revalidation_control':guarded,
            'delivered':delivered,'replacement_addressed':violation,'real_signals_sent':False}


async def browser_model(case):
    tree=ast.parse((ROOT/'jevdual/python/jevdual/browser_driver.py').read_text())
    functions=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
               and n.name in {'chrome_pid','_chrome_args','bind_footwork_chrome'}]
    helper_started=False
    spawned=[]
    helper=SimpleNamespace(pid=99,poll=lambda:0 if case=='exited-helper' else None)
    profile=Path('/owned/profile');port=9334
    root_args=['/qualified/chromium',f'--user-data-dir={profile}',f'--remote-debugging-port={port}']
    def process(pid,args):return SimpleNamespace(info={'pid':pid,'cmdline':args,'exe':'/qualified/chromium','uids':SimpleNamespace(real=42)})
    def processes(attrs):
        rows=[process(42,root_args)]
        if case=='unrelated-root':rows.append(process(77,root_args))
        if helper_started and case=='live-helper':rows.append(process(99,spawned[0]))
        return iter(rows)
    class Driver:
        calls=0
        async def list_windows(self,args):
            self.calls+=1
            window=SimpleNamespace(pid=42,window_id=1,bounds=SimpleNamespace(width=100,height=100))
            return SimpleNamespace(windows=[] if self.calls==1 else [window])
        async def shutdown(self):pass
    class Bridge:
        def __init__(self,*a,**k):pass
        async def attach(self):pass
    driver=Driver()
    def spawn(args,**kw):
        nonlocal helper_started
        helper_started=True;spawned.append(args)
        return helper
    ns={'Any':Any,'Path':Path,'PROFILE_DIR':profile,'PORT':port,'asyncio':asyncio,'time':time,
        'sys':SimpleNamespace(platform='linux'),'os':SimpleNamespace(getuid=lambda:42),
        'subprocess':SimpleNamespace(Popen=spawn,DEVNULL=subprocess.DEVNULL),'chrome_executable':lambda:'/qualified/chromium',
        '_incarnation':lambda pid:1.0,'_begin_chrome':lambda url:(42,None),
        'configured_driver':lambda pid:driver,'_recovery_flags':lambda *a:[],
        'BrowserBridge':Bridge,'_stop_launch':lambda process:None}
    exec(compile(ast.Module(body=functions,type_ignores=[]),'cloud-browser-functions','exec'),ns)
    import psutil
    with patch.object(psutil,'process_iter',processes):
        try:
            await ns['bind_footwork_chrome']('http://owned.invalid/')
            outcome='bound'
        except RuntimeError as exc:outcome=str(exc)
    return {'case':case,'outcome':outcome,'helper_started':helper_started,'real_processes_started':False}

signals=[signal_model(False),signal_model(True),signal_model(True,True)]
assert not signals[0]['replacement_addressed']
assert signals[1]['replacement_addressed']
assert not signals[2]['replacement_addressed']
assert any(r['pid']==42 for r in signals[2]['delivered'])
browsers=[asyncio.run(browser_model(c)) for c in ['exited-helper','live-helper','unrelated-root']]
assert browsers[0]['outcome']=='bound',browsers
assert 'multiple browser processes' in browsers[1]['outcome'],browsers
assert 'multiple browser processes' in browsers[2]['outcome'],browsers
result={'target':'bd6f185c24327f5cf292067b7f84ed50bd118a31','level':'model',
        'signal_snapshot':signals,'browser_discovery':browsers,
        'limits':'Synthetic tables and sinks; does not execute Linux kernel or browser. Immediate revalidation still has a check-to-kill gap.'}
(OUT/'models.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
