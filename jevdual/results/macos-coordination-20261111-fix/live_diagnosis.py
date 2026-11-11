"""Public-CLI macOS rehearsal against invocation-owned native apps only."""
import asyncio
import contextlib
import http.server
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import psutil
import Quartz

from jevdual import ax
from jevdual.coexist import TextEditInstance, idle_seconds
from jevdual.coordination import Coordinator
from jevdual.effectors.cua import create_desktop_driver
from jevdual.posture import frontmost_pid, screen_locked

PROJECT = Path(__file__).resolve().parents[2]
PRIVATE = PROJECT / 'output/macos-coordination-20261111-fix/native-diagnosis'
REPORT = Path(__file__).with_name('live-diagnosis.json')
EVENTS = []
HTML = b'''<!doctype html><title>Footwork macOS coordination fixture</title>
<style>body{margin:0;background:#fafafa;font:24px system-ui}button{position:absolute;left:300px;top:230px;width:300px;height:120px;font:24px system-ui}h1{margin:25px;font-size:26px}</style>
<h1>Owned coordination fixture</h1><button id="target">Coordination target</button>
<script>const t=document.querySelector('button');for(const e of ['pointerenter','pointerleave','click'])t.addEventListener(e,()=>fetch('/event',{method:'POST',body:JSON.stringify({event:e})}));</script>'''


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header('Content-Type', 'text/html'); self.end_headers(); self.wfile.write(HTML)
    def do_POST(self):
        EVENTS.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        self.send_response(200); self.end_headers(); self.wfile.write(b'{}')
    def log_message(self, *_):
        pass


def pointer():
    p = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
    return [float(p.x), float(p.y)]


async def main():
    PRIVATE.mkdir(parents=True, exist_ok=False)
    await asyncio.sleep(4)  # allow the explicit user handoff click to become idle
    result = {'target': 'ac892a75211900ca6e252a46bca4f0da2362af6b',
              'python': sys.executable, 'source': __import__('jevdual').__file__,
              'sdk': importlib.metadata.version('cua-driver'), 'criteria': {}, 'commands': [],
              'initial': {'screen_locked': screen_locked(), 'idle_seconds': idle_seconds(),
                          'front_pid': frontmost_pid(), 'pointer': pointer()}}
    def check(name, passed, **detail):
        result['criteria'][name] = {'passed': bool(passed), **detail}
        REPORT.write_text(json.dumps(result, indent=2) + '\n')
    async def cli(*args, label=None, wait=True):
        index = len(result['commands'])
        name = f'{index:02}-{label or args[0]}'
        stdout = open(PRIVATE / f'{name}.stdout', 'wb')
        stderr = open(PRIVATE / f'{name}.stderr', 'wb')
        command = ([sys.executable, str(Path(__file__).with_name('diagnostic_cli.py')), str(PRIVATE / f'{name}.timing.json')] if args[0] == 'point' else [sys.executable, '-m', 'jevdual.cli'])
        process = await asyncio.create_subprocess_exec(*command, *map(str,args),
                  stdout=stdout, stderr=stderr, env=os.environ.copy(), cwd=PROJECT)
        stdout.close(); stderr.close()
        row = {'name': name, 'args': list(map(str,args)), 'pid': process.pid, 'started': time.time()}
        result['commands'].append(row)
        if not wait:
            return process, row
        try:
            await asyncio.wait_for(process.wait(), 45)
        except asyncio.TimeoutError:
            process.terminate(); await process.wait(); row['deadline_exceeded'] = True
        row.update(exit=process.returncode, elapsed=round(time.time()-row['started'],3))
        return row, (PRIVATE / f'{name}.stdout').read_text(), (PRIVATE / f'{name}.stderr').read_text()
    registry = None; chrome = None; textedit = None; server = None; video = None
    film = PRIVATE/'film'; other = PRIVATE/'other'; subject = PRIVATE/'subject'
    driver = None; owned_tokens = []
    try:
        if result['initial']['screen_locked'] or result['initial']['idle_seconds'] < 3:
            raise RuntimeError('real desktop locked or human active; no fixture/input started')
        registry = Coordinator()
        baseline = registry.status()
        result['initial']['existing_active_owners'] = len([r for r in baseline['requests'] if r['state'] in ['active','orphaned']])
        if result['initial']['existing_active_owners'] or any(r['state']=='active' for r in baseline['reservations']):
            raise RuntimeError('existing coordinator ownership; no takeover attempted')
        server = http.server.ThreadingHTTPServer(('127.0.0.1',0), Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}/'
        chrome = subprocess.Popen(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            f'--user-data-dir={PRIVATE / "chrome-profile"}', '--remote-debugging-port=0',
            '--no-first-run','--no-default-browser-check','--force-renderer-accessibility',
            '--window-size=900,650','--window-position=100,100',url],
            stdout=open(PRIVATE/'chrome.stdout','wb'),stderr=open(PRIVATE/'chrome.stderr','wb'),start_new_session=True)
        result['owned_chrome']={'pid':chrome.pid,'start':psutil.Process(chrome.pid).create_time()}
        await asyncio.sleep(2)
        driver=create_desktop_driver()
        doc=PRIVATE/'independent.txt'; doc.write_text('Owned background baseline\n')
        textedit=await TextEditInstance.launch(driver,[doc])
        result['owned_textedit']={'pid':textedit.pid,'windows':textedit.windows}
        await driver.shutdown(); driver=None
        r,out,err=await cli('start','Append only to owned background fixture','--app','TextEdit','--pid',textedit.pid,
                            '--window',doc.name,'--session',other,label='background-start')
        check('background_native_start',r['exit']==0,exit=r['exit'],error=err[-400:])
        if r['exit']: raise RuntimeError('background start unavailable')
        r,out,err=await cli('start','Observe owned subject','--app','Google Chrome','--pid',chrome.pid,
                            '--window','Footwork macOS coordination fixture','--session',subject,label='subject-start')
        check('subject_native_start',r['exit']==0,exit=r['exit'],error=err[-400:])
        if r['exit']: raise RuntimeError('subject start unavailable')
        r,out,err=await cli('start','Film owned pointer rehearsal','--app','Google Chrome','--pid',chrome.pid,
              '--window','Footwork macOS coordination fixture','--session',film,'--mode','exclusive_desktop',
              '--pointer-motion','filmed','--rest','100,100',label='film-start')
        check('filmed_native_start',r['exit']==0,exit=r['exit'],error=err[-400:])
        if r['exit']: raise RuntimeError('film start unavailable')
        state=json.loads((film/'session.json').read_text()); token=state['coordination_token']; owned_tokens.append(token)
        result['film_binding']={'pid':state['pid'],'window_id':state['window_id'],'token':token,'geometry':state['filmed']}
        check('persistent_desktop_subject_reservation',any(r['token']==token and r['state']=='active' and
                     'desktop' in r['resources'] and 'app/google%20chrome' in r['resources'] for r in registry.status()['reservations']))
        r,out,err=await cli('control','observe','--session',film,label='observe-only')
        check('saved_observe_only',r['exit']==0 and json.loads(out)['live'] is False)
        if screen_locked() or idle_seconds()<3: raise RuntimeError('human/lock guard before pointer rehearsal')
        r,out,err=await cli('park','--place','--session',film,label='park-place')
        check('pointer_setup',r['exit']==0,exit=r['exit'],error=err[-400:])
        if r['exit']: raise RuntimeError('pointer setup refused')
        bgstate=json.loads((other/'session.json').read_text())
        fields=[c for c in bgstate['last_candidates'] if 'append' in c.get('operations',[])]
        if len(fields)!=1: raise RuntimeError('background append field is not unique')
        # Capture only the owned window; no microphone or other windows are selected.
        video=subprocess.Popen(['/usr/sbin/screencapture','-v','-x',f'-l{state["window_id"]}','-V6',str(PRIVATE/'rehearsal.mov')],
                   stdout=open(PRIVATE/'video.stdout','wb'),stderr=open(PRIVATE/'video.stderr','wb'))
        before_front=frontmost_pid()
        bg=asyncio.create_task(cli('do','append',str(fields[0]['id']),'Background concurrency marker','--session',other,label='background-append'))
        r,out,err=await cli('point','Coordination target','--session',film,label='filmed-point')
        check('filmed_point',r['exit']==0,exit=r['exit'],error=err[-400:])
        br,bo,be=await bg
        actual=textedit.value(doc.name)
        check('independent_native_append',br['exit']==0 and actual=='Owned background baseline\nBackground concurrency marker',
                  exit=br['exit'],actual=actual,error=be[-400:])
        current=json.loads((film/'session.json').read_text())
        expected=current['filmed'].get('last_pointer'); observed=pointer()
        check('pointer_readback',bool(expected) and max(abs(a-b) for a,b in zip(expected,observed))<=2,
              expected=expected,observed=observed,gestures=current['filmed'].get('gestures'))
        check('background_did_not_steal_front',frontmost_pid()==before_front,before=before_front,after=frontmost_pid())
        await asyncio.sleep(.2)
        check('independent_page_hover',any(e['event']=='pointerenter' for e in EVENTS),events=list(EVENTS))
        # Public CLI reachability of circular waiting; both commands are read-only.
        waiter,wr=await cli('look','--session',subject,label='competing-look',wait=False)
        waiter_token=None
        for _ in range(150):
            waiter_token=next((r['token'] for r in registry.status()['requests'] if r['pid']==waiter.pid and r['state']=='waiting' and any(x.startswith('app/') for x in r['resources'])),None)
            if waiter_token: break
            await asyncio.sleep(.02)
        if not waiter_token: raise RuntimeError('CLI waiter not established')
        owner,orr=await cli('look','--session',film,label='owner-look',wait=False)
        await asyncio.sleep(1.2)
        status=registry.status()
        owner_waiting=any(r['pid']==owner.pid and r['state']=='waiting' and r['reservation']==token for r in status['requests'])
        check('reserved_owner_continues_with_waiter',not owner_waiting,requests=status['requests'])
        await cli('control','cancel',waiter_token,label='cancel-waiter')
        await asyncio.wait_for(waiter.wait(),10); await asyncio.wait_for(owner.wait(),15)
        wr.update(exit=waiter.returncode);orr.update(exit=owner.returncode)
        check('owner_recovers_after_waiter_cancel',owner.returncode==0,exit=owner.returncode)
        await cli('control','cancel',token,label='cancel-reservation')
        p0=pointer()
        r,out,err=await cli('point','Coordination target','--session',film,label='revoked-point')
        check('revocation_fences_pointer',r['exit']!=0 and 'reservation unavailable' in err and pointer()==p0,exit=r['exit'],error=err[-400:])
        r,out,err=await cli('control','reserve','--session',film,label='explicit-handoff')
        newer=json.loads(out)['token'];owned_tokens.append(newer)
        await cli('control','yield',token,label='stale-yield')
        check('stale_yield_preserves_new_owner',any(r['token']==newer and r['state']=='active' for r in registry.status()['reservations']))
        await cli('control','yield',newer,label='yield-new-owner')
    except Exception as exc:
        result['error']=f'{type(exc).__name__}: {exc}'
    finally:
        if driver:
            with contextlib.suppress(Exception): await driver.shutdown()
        if video:
            try: await asyncio.to_thread(video.wait,10)
            except subprocess.TimeoutExpired: video.terminate(); video.wait(timeout=5)
            result['video']={'exit':video.returncode,'path':str(PRIVATE/'rehearsal.mov'),
                             'exists':(PRIVATE/'rehearsal.mov').exists()}
        if registry:
            for token in owned_tokens:
                with contextlib.suppress(Exception): registry.revoke(token)
            result['cleanup_registry']=registry.status()
        if textedit:
            with contextlib.suppress(Exception): textedit.close()
        if chrome:
            with contextlib.suppress(Exception): chrome.terminate(); chrome.wait(timeout=8)
            result['owned_chrome_exited']=chrome.poll() is not None
        if server: server.shutdown(); server.server_close()
        result['events']=list(EVENTS)
        result['final_pointer']=pointer()
        REPORT.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'checks':{k:v['passed'] for k,v in result['criteria'].items()},'error':result.get('error'),
                          'report':str(REPORT),'video':result.get('video')},indent=2))
    return 0 if not result.get('error') and all(v['passed'] for v in result['criteria'].values()) else 1


if __name__=='__main__': sys.exit(asyncio.run(main()))
