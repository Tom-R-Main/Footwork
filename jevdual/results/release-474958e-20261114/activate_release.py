"""Atomically select the qualified release of main at 474958e (notebook RDP1 to RDP4).

Adapted from results/converge-release-20261111/activate_release.py. Refuses unless all three live
records of the qualification held, `current` is still 6d571a1, the launcher is the one recorded at
staging, no Footwork process is running and the coordination registry is empty. The launcher is not
changed and every earlier release is kept; rollback is pointing `current` back at 6d571a1.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid

COMMIT = '474958e48c0db404ffbe3b302bacef0df101c3d5'
root = Path('/Users/thomasmain/.local/share/footwork')
current = root/'current'
prefix = root/'releases'/COMMIT
previous = root/'releases/6d571a1ed7c7bf77576279a01053f77fc20ce469'
launcher = Path('/Users/thomasmain/.local/bin/footwork')
live = Path(__file__).with_name('live')
release = json.loads((live/'release/release-live.json').read_text())
assert not release.get('error') and len(release['criteria']) == 20 and all(v['passed'] for v in release['criteria'].values())
assert release['release'] == str(prefix) and release['current_at_end'] == str(previous)
assert json.loads((live/'filmed/verdict.json').read_text())['held'] is True
drag = json.loads((live/'drag/run.json').read_text())
assert drag['held'] is True and len(drag['runs']) == 6
metadata = json.loads((prefix/'footwork-release.json').read_text())
assert metadata['source_commit'] == COMMIT
assert current.resolve() == previous, current.resolve()
assert hashlib.sha256(launcher.read_bytes()).hexdigest() == metadata['launcher_sha256']
running = subprocess.run(['pgrep', '-f', 'jevdual.cli|jevdual.browser_holder|probe_'], capture_output=True, text=True).stdout.split()
running = [p for p in running if int(p) != os.getpid()]
assert not running, f'Footwork processes running: {running}'
from jevdual.coordination import Coordinator
status = Coordinator().status()
assert not status['requests'] and not any(r['state'] == 'active' for r in status['reservations']), status
metadata['qualification'].update({
    'live_release_probe': 'passed', 'release_probe_criteria': f"{sum(v['passed'] for v in release['criteria'].values())}/20",
    'live_filmed_page_pointer': 'passed', 'live_drag_points': 'passed (6/6)',
    'qualified_at': datetime.now(timezone.utc).isoformat(), 'evidence': str(live),
    'note': 'protected-port readings in release-live.json are renderer processes (notebook RDP4)'})
(prefix/'footwork-release.json').write_text(json.dumps(metadata, indent=2)+'\n')
temporary = root/('current-next-'+uuid.uuid4().hex)
os.symlink(prefix, temporary)
os.replace(temporary, current)
activation = {'source_commit': COMMIT, 'source_merged': True, 'pull_request': 'https://github.com/Tom-R-Main/Footwork/pull/32',
              'active_release': str(current.resolve()), 'previous_release': str(previous),
              'previous_release_kept': previous.is_dir(), 'kept_releases': sorted(p.name for p in (root/'releases').iterdir()),
              'launcher_unchanged': hashlib.sha256(launcher.read_bytes()).hexdigest() == metadata['launcher_sha256'],
              'selected_at': datetime.now(timezone.utc).isoformat(), 'qualification': metadata['qualification'],
              'rollback': f'ln -s {previous} <tmp> && mv -h <tmp> {current} (atomic repoint)'}
(Path(__file__).with_name('activation.json')).write_text(json.dumps(activation, indent=2)+'\n')
print(json.dumps(activation, indent=2))
