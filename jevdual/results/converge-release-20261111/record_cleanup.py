"""Record post-run cleanup like results/pointer-startup-20261111/installed-cleanup.json (run with the new release's python -I)."""
import json
from pathlib import Path
import subprocess

import psutil

from jevdual.coordination import Coordinator

import os as _os
PRIVATE = Path(_os.environ.get('FW_PROBE_PRIVATE', '/Users/thomasmain/projects/footwork/jevdual/output/converge-release-20261111/live'))
live = json.loads((PRIVATE/'release-live.json').read_text())
status = Coordinator().status()
owned = [r for r in status['reservations'] if str(r.get('owner', '')).startswith(str(PRIVATE))
         or r['token'] in live.get('owned_tokens', [])]
owned_requests = [r for r in status['requests'] if str(r.get('owner', '')).startswith(str(PRIVATE))]
pids = [p for p in (live.get('owned_chrome', {}).get('pid'), live.get('owned_textedit', {}).get('pid')) if p]
present = [p for p in pids if psutil.pid_exists(p)]
video = PRIVATE/'rehearsal.mov'
probe = None
if video.exists():
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,width,height:format=duration',
                        '-of', 'json', str(video)], capture_output=True, text=True)
    probe = json.loads(p.stdout) if p.returncode == 0 else {'error': p.stderr[-300:]}
# The probe's own protected_chrome snapshot keeps the LAST process carrying each port flag, which is
# a Chrome helper child, not the browser. Identify the browsers by their listening sockets instead,
# against the listeners this session observed (lsof) before the probe was written.
BASELINE_LISTENERS = {'9333': {'pid': 57062, 'started': 'Wed Nov 11 00:10:01 2026'},
                      '9555': {'pid': 29337, 'started': 'Wed Nov 11 17:08:33 2026'}}
listeners = {}
for port in BASELINE_LISTENERS:
    p = subprocess.run(['lsof', '-nP', f'-iTCP:{port}', '-sTCP:LISTEN', '-t'], capture_output=True, text=True)
    pid = int(p.stdout.split()[0]) if p.stdout.split() else None
    started = subprocess.run(['ps', '-o', 'lstart=', '-p', str(pid)], capture_output=True, text=True).stdout.strip() if pid else None
    listeners[port] = {'pid': pid, 'started': started}
protected_same = listeners == BASELINE_LISTENERS
run_started = live['commands'][0]['started'] if live.get('commands') else None
helpers = {}
for port, snap in (live.get('protected_chrome_after') or {}).items():
    changed = snap != (live.get('protected_chrome_before') or {}).get(port)
    helpers[port] = {'snapshot_changed': changed, 'after_started_before_first_command':
                     run_started is not None and snap['start'] < run_started,
                     'after_parent_is_protected_browser': psutil.pid_exists(snap['pid']) and
                     psutil.Process(snap['pid']).ppid() == BASELINE_LISTENERS[port]['pid']}
current = str(Path('/Users/thomasmain/.local/share/footwork/current').resolve())
record = {'target': live['target'], 'source': live['source'], 'sdk': live['sdk'],
          'criteria_passed': sum(v['passed'] for v in live['criteria'].values()),
          'criteria_total': len(live['criteria']), 'error': live.get('error'),
          'owned_pids_present': present, 'requests': status['requests'],
          'owned_requests': owned_requests,
          'owned_reservations': [{'token': r['token'], 'state': r['state']} for r in owned],
          'protected_chrome_unchanged': protected_same, 'protected_listeners': listeners,
          'protected_listener_baseline': BASELINE_LISTENERS, 'probe_helper_snapshots': helpers,
          'video': probe,
          'owned_chrome_exited': live.get('owned_chrome_exited'), 'current': current}
record['clean'] = (not present and not status['requests'] and all(r['state'] != 'active' for r in owned)
                   and protected_same)
(Path(_os.environ['FW_PROBE_CLEANUP']) if _os.environ.get('FW_PROBE_CLEANUP') else Path(__file__).with_name('release-cleanup.json')).write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps({k: record[k] for k in ('clean', 'owned_pids_present', 'owned_reservations', 'protected_chrome_unchanged', 'current')}, indent=2))
