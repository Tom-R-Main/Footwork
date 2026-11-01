"""Finite IR1 first run; independent fixture journal precedes client grading."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time


def save(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n')


def command(argv, cwd, env, timeout, out):
    start=time.monotonic()
    with (out/'client.stdout.txt').open('w') as stdout,(out/'client.stderr.txt').open('w') as stderr:
        child=subprocess.Popen(argv,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
        expired=False
        try:code=child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            expired=True;child.terminate()
            try:code=child.wait(timeout=3)
            except subprocess.TimeoutExpired:child.kill();code=child.wait()
    raw=(out/'client.stdout.txt').read_text()
    try:result=json.loads(raw.strip().splitlines()[-1])
    except (ValueError,IndexError):result=None
    return {'argv':argv,'cwd':str(cwd),'returncode':code,'signal':-code if code<0 else None,'watchdog_expired':expired,'elapsed_seconds':time.monotonic()-start,'result':result}


def target_case(package, task, output, arm, mode, timeout, label):
    out=output/label;out.mkdir(mode=0o700)
    bus=None;target=None;cleanup=[]
    env=dict(os.environ)
    for key in list(env):
        if key in ['DISPLAY','WAYLAND_DISPLAY','DBUS_SESSION_BUS_ADDRESS','AT_SPI_BUS_ADDRESS','OPENAI_API_KEY','ANTHROPIC_API_KEY','TYPESAFE_API_KEY','PYTHONPATH']:
            env.pop(key,None)
    try:
        bus=subprocess.Popen(['/usr/bin/dbus-daemon','--session','--nofork','--print-address=1'],stdout=subprocess.PIPE,stderr=(out/'bus.stderr.txt').open('w'),text=True)
        assert select.select([bus.stdout],[],[],3)[0], 'private bus startup timeout'
        address=bus.stdout.readline().strip();assert address.startswith('unix:')
        env.update(DBUS_SESSION_BUS_ADDRESS=address,AT_SPI_BUS_ADDRESS=address)
        primary='InsertText' if arm=='write_through_editable_proxies' else 'SetTextContents'
        target_argv=[sys.executable,str(package/'target.py'),'--address',address,'--journal',str(out/'target.jsonl'),'--ready',str(out/'ready.json'),'--mode',mode,'--primary',primary,'--invocation',label]
        target=subprocess.Popen(target_argv,env=env,stdout=(out/'target.stdout.txt').open('w'),stderr=(out/'target.stderr.txt').open('w'))
        deadline=time.monotonic()+4
        while not (out/'ready.json').exists() and time.monotonic()<deadline:
            if target.poll() is not None:raise RuntimeError('target startup failed')
            time.sleep(.02)
        ready=json.loads((out/'ready.json').read_text());env['IR1_TARGET_BUS']=ready['bus']
        if timeout is not None:env['IR1_TIMEOUT_MS']=str(timeout)
        if arm=='linux_ax':
            env['PYTHONPATH']=str(package.parents[1]/'python')
            argv=[sys.executable,str(package/'ax_control.py')]
        else:argv=[str(task/'bin/ir1-probe'),arm]
        record=command(argv,package,env,40,out)
        journal=[json.loads(x) for x in (out/'target.jsonl').read_text().splitlines()]
        attempts=[x for x in journal if x['kind']=='method_received'];effects=[x for x in journal if x['kind']=='effect_applied']
        record.update(label=label,boundary=arm,fixture_mode=mode,client_timeout_ms=timeout,attempts=len(attempts),effects=len(effects),methods=[x['method'] for x in attempts],transitions=[{'before':x['before'],'after':x['after']} for x in effects],final_value=effects[-1]['after'] if effects else '',target_argv=target_argv)
        expected=2 if arm=='double_set_control' else (1 if mode in ['ack','false'] or arm in ['direct_timeout','linux_ax'] else None)
        record['expected_control_effects']=expected
        record['control_passed']=None if expected is None else len(effects)==expected and (record['result'] is not None)
        record['safety_one_effect']=len(effects)<=1
        save(out/'receipt.json',record)
    except Exception as error:
        record={'label':label,'boundary':arm,'fixture_mode':mode,'infrastructure_error':f'{type(error).__name__}: {error}'}
        save(out/'receipt.json',record)
    finally:
        for name,child in [('target',target),('private_bus',bus)]:
            if child is None:continue
            before=child.poll()
            if before is None:child.terminate()
            escalated=False
            try:code=child.wait(timeout=3)
            except subprocess.TimeoutExpired:escalated=True;child.kill();code=child.wait()
            cleanup.append({'owned':name,'pid':child.pid,'pre_stop_returncode':before,'returncode':code,'escalated':escalated,'wait_completed':True})
        save(out/'cleanup.json',cleanup)
    print(json.dumps(record),flush=True)
    return record


def main():
    p=argparse.ArgumentParser();p.add_argument('task',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    package=Path(__file__).resolve().parent;a.output.mkdir(mode=0o700)
    cases=[]
    for arm in ['set_value_on','write_through_editable_proxies']:
        for mode in ['ack','false','error','withhold']:
            cases.append((arm,mode,100 if mode=='withhold' else None,arm+'-'+mode))
        cases.append((arm,'withhold',None,arm+'-withhold-default25s'))
    for mode in ['ack','false','error','withhold']:cases.append(('public_set_ref',mode,None,'public-set-ref-'+mode))
    cases += [('direct_timeout','withhold',100,'direct-client-timeout-control'),('double_set_control','ack',None,'equal-final-value-double-effect-control'),('linux_ax','ack',None,'footwork-adapter-ack'),('linux_ax','withhold',None,'footwork-adapter-withhold')]
    records=[target_case(package,a.task,a.output,*case) for case in cases]
    batch_cases=[('ack',None,None),('pre_refusal','true',None),('post_error','true',None),('post_error','false',None),('post_error',None,None),('post_error','true','explicit'),('post_error','true','inherited'),('post_error',None,'direct')]
    for i,(mode,fallback,delivery) in enumerate(batch_cases):
        out=a.output/f'batch-{i+1:02d}';out.mkdir(mode=0o700);env=dict(os.environ,IR1_MODE=mode,IR1_JOURNAL=str(out/'target.jsonl'))
        for key in ['IR1_FOREGROUND_FALLBACK','IR1_EXPLICIT_BACKGROUND','IR1_INHERITED_BACKGROUND','IR1_DIRECT','DISPLAY','DBUS_SESSION_BUS_ADDRESS','AT_SPI_BUS_ADDRESS']:env.pop(key,None)
        if fallback is not None:env['IR1_FOREGROUND_FALLBACK']=fallback
        if delivery is not None:env['IR1_'+{'explicit':'EXPLICIT_BACKGROUND','inherited':'INHERITED_BACKGROUND','direct':'DIRECT'}[delivery]]='1'
        record=command([str(a.task/'bin/ir1-probe'),'batch'],package,env,15,out)
        journal=[json.loads(x) for x in (out/'target.jsonl').read_text().splitlines()] if (out/'target.jsonl').exists() else []
        record.update(label=out.name,mode=mode,fallback=fallback,delivery=delivery,attempts=len(journal),effects=sum(x['effect_applied'] for x in journal))
        save(out/'receipt.json',record);records.append(record);print(json.dumps(record),flush=True)
    save(a.output/'summary.json',{'cases':records,'native_archive_sha256':'5588fa808559de5982f9195c1031696f51a67b057164fd42b60485ac6c30b401','binary_sha256':hashlib.sha256((a.task/'bin/ir1-probe').read_bytes()).hexdigest(),'scope':'audit only; actual helpers/private bus versus separate real registry dispatch; no full product identity qualification'})
    red=any(x.get('effects',0)>1 and x.get('fixture_mode') in ['error','withhold'] for x in records)
    raise SystemExit(1 if red else 0)


if __name__=='__main__':main()
