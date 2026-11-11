"""Live macOS qualification of an UNACTIVATED release, against invocation-owned apps only.

Adapted from results/pointer-startup-20261111/installed_probe.py. Differences, all recorded in CVM3:
- every product command runs through the new release's own interpreter, exactly as the stable
  launcher would (`<release>/bin/python -I -m jevdual.cli`), never through `current`;
- the start is gated on an unlocked screen and >= 10 s of human idle, polled every 15 s for at most
  30 minutes; the original in-run lock/idle guards stay as they were;
- criteria 16-20 read the branch's filmed pointer record (pointer-gestures.jsonl);
- the two protected Chrome instances (debug ports 9333 and 9555) are identified by PID and start
  time only, never attached to, and confirmed unchanged afterwards.
Run it with the new release's own python: `<release>/bin/python -I release_probe.py`.
"""
import asyncio
import contextlib
import http.server
import importlib.metadata
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import psutil
import Quartz

from jevdual.coexist import TextEditInstance, idle_seconds
from jevdual.coordination import Coordinator
from jevdual.effectors.cua import create_desktop_driver
from jevdual.posture import frontmost_pid, screen_locked

RELEASE = Path('/Users/thomasmain/.local/share/footwork/releases/6d571a1ed7c7bf77576279a01053f77fc20ce469')
COMMAND = [str(RELEASE / 'bin/python'), '-I', '-m', 'jevdual.cli']
HOST = Path('/Users/thomasmain/.local/share/footwork/qualification/converge-release-20261111/host')
PRIVATE = Path('/Users/thomasmain/projects/footwork/jevdual/output/converge-release-20261111/live')
REPORT = PRIVATE / 'release-live.json'
GAP_LIMIT_MS = 50.0
IDLE_REQUIRED_S = 10.0
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


def protected_chromes():
    """PID and start time of Chrome instances on the two protected debug ports; read-only."""
    found = {}
    for proc in psutil.process_iter(['pid', 'cmdline', 'create_time']):
        cmd = proc.info.get('cmdline') or []
        for port in ('9333', '9555'):
            if f'--remote-debugging-port={port}' in cmd:
                found[port] = {'pid': proc.info['pid'], 'start': proc.info['create_time']}
    return found


def records(session):
    path = session / 'pointer-gestures.jsonl'
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


async def idle_gate(result):
    polls = []
    deadline = time.monotonic() + 30 * 60
    while True:
        row = {'at': time.time(), 'screen_locked': screen_locked(), 'idle_seconds': idle_seconds()}
        polls.append(row)
        result['idle_gate'] = {'required_idle_s': IDLE_REQUIRED_S, 'polls': polls}
        if not row['screen_locked'] and row['idle_seconds'] >= IDLE_REQUIRED_S:
            result['idle_gate']['passed'] = True
            return True
        if time.monotonic() + 15 > deadline:
            result['idle_gate']['passed'] = False
            return False
        await asyncio.sleep(15)


async def main():
    PRIVATE.mkdir(parents=True, exist_ok=False)
    release = json.loads((RELEASE / 'footwork-release.json').read_text())
    current = Path('/Users/thomasmain/.local/share/footwork/current').resolve()
    result = {'target': release['source_commit'], 'release': str(RELEASE), 'current_at_start': str(current),
              'python': sys.executable, 'source': __import__('jevdual').__file__,
              'cua_source': __import__('cua_driver').__file__,
              'sdk': importlib.metadata.version('cua-driver'), 'criteria': {}, 'commands': [],
              'protected_chrome_before': protected_chromes()}
    def write():
        REPORT.write_text(json.dumps(result, indent=2) + '\n')
    def check(name, passed, **detail):
        result['criteria'][name] = {'passed': bool(passed), **detail}
        write()
    if not (sys.executable.startswith(str(RELEASE)) and result['source'].startswith(str(RELEASE))
            and result['cua_source'].startswith(str(RELEASE)) and current != RELEASE):
        result['error'] = 'probe is not running from the unactivated release'
        write(); return 1
    if not await idle_gate(result):
        result['error'] = 'never idle and unlocked within 30 minutes; nothing started'
        write(); print(json.dumps({'error': result['error'], 'report': str(REPORT)})); return 2
    result['initial'] = {'screen_locked': screen_locked(), 'idle_seconds': idle_seconds(),
                         'front_pid': frontmost_pid(), 'pointer': pointer()}
    async def cli(*args, label=None, wait=True):
        index = len(result['commands'])
        name = f'{index:02}-{label or args[0]}'
        stdout = open(PRIVATE / f'{name}.stdout', 'wb')
        stderr = open(PRIVATE / f'{name}.stderr', 'wb')
        env = os.environ.copy(); env.pop('PYTHONPATH', None); env.pop('FOOTWORK_SESSION', None)
        process = await asyncio.create_subprocess_exec(*COMMAND, *map(str, args),
                  stdout=stdout, stderr=stderr, env=env, cwd=HOST)
        stdout.close(); stderr.close()
        row = {'name': name, 'args': list(map(str, args)), 'pid': process.pid, 'started': time.time()}
        result['commands'].append(row)
        if not wait:
            return process, row
        try:
            await asyncio.wait_for(process.wait(), 45)
        except asyncio.TimeoutError:
            process.terminate(); await process.wait(); row['deadline_exceeded'] = True
        row.update(exit=process.returncode, elapsed=round(time.time()-row['started'], 3))
        return row, (PRIVATE / f'{name}.stdout').read_text(), (PRIVATE / f'{name}.stderr').read_text()
    registry = None; chrome = None; textedit = None; server = None; video = None
    film = PRIVATE/'film'; other = PRIVATE/'other'; subject = PRIVATE/'subject'
    driver = None; owned_tokens = []
    try:
        if result['initial']['screen_locked'] or result['initial']['idle_seconds'] < 3:
            raise RuntimeError('real desktop locked or human active; no fixture/input started')
        registry = Coordinator()
        baseline = registry.status()
        result['initial']['existing_active_owners'] = len([r for r in baseline['requests'] if r['state'] in ['active', 'orphaned']])
        if result['initial']['existing_active_owners'] or any(r['state'] == 'active' for r in baseline['reservations']):
            raise RuntimeError('existing coordinator ownership; no takeover attempted')
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}/'
        chrome = subprocess.Popen(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            f'--user-data-dir={PRIVATE / "chrome-profile"}', '--remote-debugging-port=0',
            '--no-first-run', '--no-default-browser-check', '--force-renderer-accessibility',
            '--window-size=900,650', '--window-position=100,100', url],
            stdout=open(PRIVATE/'chrome.stdout', 'wb'), stderr=open(PRIVATE/'chrome.stderr', 'wb'), start_new_session=True)
        result['owned_chrome'] = {'pid': chrome.pid, 'start': psutil.Process(chrome.pid).create_time()}
        await asyncio.sleep(2)
        driver = create_desktop_driver()
        doc = PRIVATE/'independent.txt'; doc.write_text('Owned background baseline\n')
        textedit = await TextEditInstance.launch(driver, [doc])
        result['owned_textedit'] = {'pid': textedit.pid, 'windows': textedit.windows}
        await driver.shutdown(); driver = None
        r, out, err = await cli('start', 'Append only to owned background fixture', '--app', 'TextEdit', '--pid', textedit.pid,
                                '--window', doc.name, '--session', other, label='background-start')
        check('background_native_start', r['exit'] == 0, exit=r['exit'], error=err[-400:])
        if r['exit']: raise RuntimeError('background start unavailable')
        r, out, err = await cli('start', 'Observe owned subject', '--app', 'Google Chrome', '--pid', chrome.pid,
                                '--window', 'Footwork macOS coordination fixture', '--session', subject, label='subject-start')
        check('subject_native_start', r['exit'] == 0, exit=r['exit'], error=err[-400:])
        if r['exit']: raise RuntimeError('subject start unavailable')
        r, out, err = await cli('start', 'Film owned pointer rehearsal', '--app', 'Google Chrome', '--pid', chrome.pid,
              '--window', 'Footwork macOS coordination fixture', '--session', film, '--mode', 'exclusive_desktop',
              '--pointer-motion', 'filmed', '--rest', '100,100', label='film-start')
        check('filmed_native_start', r['exit'] == 0, exit=r['exit'], error=err[-400:])
        if r['exit']: raise RuntimeError('film start unavailable')
        state = json.loads((film/'session.json').read_text()); token = state['coordination_token']; owned_tokens.append(token)
        result['film_binding'] = {'pid': state['pid'], 'window_id': state['window_id'], 'token': token, 'geometry': state['filmed']}
        check('persistent_desktop_subject_reservation', any(r['token'] == token and r['state'] == 'active' and
                     'desktop' in r['resources'] and 'app/google%20chrome' in r['resources'] for r in registry.status()['reservations']))
        r, out, err = await cli('control', 'observe', '--session', film, label='observe-only')
        check('saved_observe_only', r['exit'] == 0 and json.loads(out)['live'] is False)
        if screen_locked() or idle_seconds() < 3: raise RuntimeError('human/lock guard before pointer rehearsal')
        r, out, err = await cli('park', '--place', '--session', film, label='park-place')
        check('pointer_setup', r['exit'] == 0, exit=r['exit'], error=err[-400:])
        if r['exit']: raise RuntimeError('pointer setup refused')
        lines_before_point = len(records(film))
        bgstate = json.loads((other/'session.json').read_text())
        fields = [c for c in bgstate['last_candidates'] if 'append' in c.get('operations', [])]
        if len(fields) != 1: raise RuntimeError('background append field is not unique')
        # Capture only the owned window; no microphone or other windows are selected.
        video = subprocess.Popen(['/usr/sbin/screencapture', '-v', '-x', f'-l{state["window_id"]}', '-V6', str(PRIVATE/'rehearsal.mov')],
                   stdout=open(PRIVATE/'video.stdout', 'wb'), stderr=open(PRIVATE/'video.stderr', 'wb'))
        before_front = frontmost_pid()
        bg = asyncio.create_task(cli('do', 'append', str(fields[0]['id']), 'Background concurrency marker', '--session', other, label='background-append'))
        r, out, err = await cli('point', 'Coordination target', '--session', film, label='filmed-point')
        check('filmed_point', r['exit'] == 0, exit=r['exit'], error=err[-400:])
        br, bo, be = await bg
        actual = textedit.value(doc.name)
        check('independent_native_append', br['exit'] == 0 and actual == 'Owned background baseline\nBackground concurrency marker',
              exit=br['exit'], actual=actual, error=be[-400:])
        current_state = json.loads((film/'session.json').read_text())
        expected = current_state['filmed'].get('last_pointer'); observed = pointer()
        check('pointer_readback', bool(expected) and max(abs(a-b) for a, b in zip(expected, observed)) <= 2,
              expected=expected, observed=observed, gestures=current_state['filmed'].get('gestures'))
        check('background_did_not_steal_front', frontmost_pid() == before_front, before=before_front, after=frontmost_pid())
        await asyncio.sleep(.2)
        check('independent_page_hover', any(e['event'] == 'pointerenter' for e in EVENTS), events=list(EVENTS))
        # Filmed pointer record (branch addition): criteria 16-20.
        approach = next((g for g in reversed(current_state['filmed'].get('gestures') or []) if g.get('kind') == 'approach'), None)
        added = records(film)[lines_before_point:]
        line = next((x for x in added if x.get('kind') == 'approach' and x.get('label') == 'Coordination target'), None)
        result['point_record_summary'] = [{k: x.get(k) for k in ('kind', 'label', 'outcome', 'completeness', 'posted_basis', 'posted')}
                                          | {'planned': None if x.get('planned_samples') is None else len(x['planned_samples']),
                                             'posted_samples': None if x.get('posted_samples') is None else len(x['posted_samples'])}
                                          for x in added]
        if line and approach:
            posted = line['posted_samples'] or []
            moving = approach['samples'] - 1  # the admitted start sample is not posted again
            post_ms = [(p['post_returned_ns'] - p['t_ns']) / 1e6 for p in posted]
            check('pointer_record_complete', line['completeness'] == 'complete' and line.get('geometry_complete') is True
                  and line['posted_basis'].startswith('CGEventPost') and line['schema'] == 'pointer_gesture/1'
                  and line['clock'] == 'CLOCK_UPTIME_RAW', completeness=line['completeness'],
                  geometry_complete=line.get('geometry_complete'), posted_basis=line['posted_basis'])
            check('recorded_posts_equal_moving_samples', len(posted) == moving == approach['posted'] == line.get('posted')
                  and len(line['planned_samples']) == approach['samples'] and all(p['event'] == 'move' for p in posted),
                  recorded_posts=len(posted), moving_samples=moving, player_posted=approach['posted'],
                  record_posted=line.get('posted'), planned=len(line['planned_samples']))
            check('posting_gap_under_unchanged_limit', approach['outcome'] == 'arrived' and approach['stall_gap_ms'] is None
                  and approach['max_gap_ms'] < GAP_LIMIT_MS, max_gap_ms=approach['max_gap_ms'],
                  stall_gap_ms=approach['stall_gap_ms'], limit_ms=GAP_LIMIT_MS,
                  max_post_ms=approach['max_post_ms'], max_ack_ms=approach['max_ack_ms'],
                  recorder_max_post_call_ms=round(max(post_ms), 3) if post_ms else None,
                  recorder_median_post_call_ms=round(sorted(post_ms)[len(post_ms)//2], 3) if post_ms else None)
            last = posted[-1] if posted else None
            check('record_endpoint_matches_readback', last is not None and line['final_location'] is not None
                  and math.dist((last['x'], last['y']), line['requested_target']) < 0.01
                  and max(abs(a-b) for a, b in zip(line['final_location'], line['requested_target'])) <= 2
                  and max(abs(a-b) for a, b in zip(line['final_location'], observed)) <= 2,
                  requested=line['requested_target'], last_posted=None if last is None else [last['x'], last['y']],
                  record_final=line['final_location'], independent=observed)
        else:
            check('pointer_record_complete', False, record_found=bool(line), approach_found=bool(approach))
        # Public CLI reachability of circular waiting; both commands are read-only.
        waiter, wr = await cli('look', '--session', subject, label='competing-look', wait=False)
        waiter_token = None
        for _ in range(150):
            waiter_token = next((r['token'] for r in registry.status()['requests'] if r['pid'] == waiter.pid and r['state'] == 'waiting' and any(x.startswith('app/') for x in r['resources'])), None)
            if waiter_token: break
            await asyncio.sleep(.02)
        if not waiter_token: raise RuntimeError('CLI waiter not established')
        owner, orr = await cli('look', '--session', film, label='owner-look', wait=False)
        try:
            await asyncio.wait_for(asyncio.shield(owner.wait()), 5)
        except asyncio.TimeoutError:
            pass
        status = registry.status()
        owner_waiting = any(r['pid'] == owner.pid and r['state'] == 'waiting' and r['reservation'] == token for r in status['requests'])
        check('reserved_owner_continues_with_waiter', owner.returncode == 0 and waiter.returncode is None and not owner_waiting and any(r['token'] == waiter_token and r['state'] == 'waiting' for r in status['requests']), requests=status['requests'])
        await cli('control', 'cancel', waiter_token, label='cancel-waiter')
        await asyncio.wait_for(waiter.wait(), 10); await asyncio.wait_for(owner.wait(), 15)
        wr.update(exit=waiter.returncode); orr.update(exit=owner.returncode)
        check('owner_completed_before_competitor_handoff', owner.returncode == 0, exit=owner.returncode)
        await cli('control', 'cancel', token, label='cancel-reservation')
        p0 = pointer(); lines_before_revoked = len(records(film))
        r, out, err = await cli('point', 'Coordination target', '--session', film, label='revoked-point')
        revoked_lines = records(film)[lines_before_revoked:]
        check('revocation_fences_pointer', r['exit'] != 0 and 'reservation unavailable' in err and pointer() == p0,
              exit=r['exit'], error=err[-400:])
        check('revoked_point_records_no_posts', not any(x.get('posted_samples') for x in revoked_lines),
              new_lines=len(revoked_lines))
        r, out, err = await cli('control', 'reserve', '--session', film, label='explicit-handoff')
        newer = json.loads(out)['token']; owned_tokens.append(newer)
        await cli('control', 'yield', token, label='stale-yield')
        check('stale_yield_preserves_new_owner', any(r['token'] == newer and r['state'] == 'active' for r in registry.status()['reservations']))
        await cli('control', 'yield', newer, label='yield-new-owner')
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if driver:
            with contextlib.suppress(Exception): await driver.shutdown()
        if video:
            try: await asyncio.to_thread(video.wait, 10)
            except subprocess.TimeoutExpired: video.terminate(); video.wait(timeout=5)
            result['video'] = {'exit': video.returncode, 'path': str(PRIVATE/'rehearsal.mov'),
                               'exists': (PRIVATE/'rehearsal.mov').exists()}
        if registry:
            for token in owned_tokens:
                with contextlib.suppress(Exception): registry.revoke(token)
            result['cleanup_registry'] = registry.status()
        if textedit:
            with contextlib.suppress(Exception): textedit.close()
        if chrome:
            with contextlib.suppress(Exception): chrome.terminate(); chrome.wait(timeout=8)
            result['owned_chrome_exited'] = chrome.poll() is not None
        if server: server.shutdown(); server.server_close()
        result['events'] = list(EVENTS)
        result['final_pointer'] = pointer()
        result['owned_tokens'] = owned_tokens
        result['protected_chrome_after'] = protected_chromes()
        result['current_at_end'] = str(Path('/Users/thomasmain/.local/share/footwork/current').resolve())
        write()
        print(json.dumps({'checks': {k: v['passed'] for k, v in result['criteria'].items()}, 'error': result.get('error'),
                          'report': str(REPORT), 'video': result.get('video')}, indent=2))
    return 0 if not result.get('error') and all(v['passed'] for v in result['criteria'].values()) else 1


if __name__ == '__main__': sys.exit(asyncio.run(main()))
