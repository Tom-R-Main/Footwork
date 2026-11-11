"""Atomically select the qualified release, as results/pointer-startup-20261111/install_release.py does.

Refuses unless the live report passed every criterion; the launcher is not changed and the previous
release directory is kept for rollback.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid

COMMIT = '6d571a1ed7c7bf77576279a01053f77fc20ce469'
root = Path('/Users/thomasmain/.local/share/footwork')
current = root/'current'
prefix = root/'releases'/COMMIT
previous = root/'releases/eded45c48d550b6867e1ce1314de64c41cbcfae8'
launcher = Path('/Users/thomasmain/.local/bin/footwork')
out = Path('/Users/thomasmain/projects/footwork/jevdual/output/converge-release-20261111')
live = json.loads((out/'live/release-live.json').read_text())
assert not live.get('error') and live['criteria'] and all(v['passed'] for v in live['criteria'].values())
cleanup = json.loads((Path(__file__).with_name('release-cleanup.json')).read_text())
assert cleanup['clean']
metadata = json.loads((prefix/'footwork-release.json').read_text())
assert metadata['source_commit'] == COMMIT
assert current.resolve() == previous
assert hashlib.sha256(launcher.read_bytes()).hexdigest() == metadata['launcher_sha256']
gestures = live['criteria']['posting_gap_under_unchanged_limit']
metadata['qualification'].update({
    'native_immediate_start': 'passed', 'native_checks_passed': len(live['criteria']),
    'native_checks_total': len(live['criteria']), 'capture_startup_delay_seconds': 0,
    'timing_wrapper': False, 'max_gap_ms': gestures['max_gap_ms'], 'max_post_ms': gestures['max_post_ms'],
    'max_ack_ms': gestures['max_ack_ms'], 'stall_gap_ms': gestures['stall_gap_ms'], 'gap_limit_ms': 50,
    'pointer_record': 'pointer_gesture/1 complete; recorded posts equal moving samples',
    'qualified_at': datetime.now(timezone.utc).isoformat(), 'cleanup': 'owned apps exited; requests empty; owned reservations revoked'})
(prefix/'footwork-release.json').write_text(json.dumps(metadata, indent=2)+'\n')
temporary = root/('current-next-'+uuid.uuid4().hex)
os.symlink(prefix, temporary)
os.replace(temporary, current)
activation = {'source_commit': COMMIT, 'source_merged': False, 'active_release': str(current.resolve()),
              'previous_release': str(previous), 'previous_release_kept': previous.is_dir(),
              'launcher_unchanged': hashlib.sha256(launcher.read_bytes()).hexdigest() == metadata['launcher_sha256'],
              'offline_install': True, 'qualification': metadata['qualification']}
(Path(__file__).with_name('activation.json')).write_text(json.dumps(activation, indent=2)+'\n')
print(json.dumps(activation, indent=2))
