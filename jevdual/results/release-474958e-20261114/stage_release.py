"""Stage and verify the exact-commit full release of main at 474958e WITHOUT selecting it.

Adapted from results/converge-release-20261111/install_release.py: the same offline install into a new
release directory with the current release's interpreter, and the same verification from a hostile
directory; `current` is not touched. Selection (activate) comes only after a live qualification window.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

COMMIT = '474958e48c0db404ffbe3b302bacef0df101c3d5'
TREE = 'b1f83c4ed6779af2e4438d070192a637bd162767'
PRODUCT_SHA256 = 'cffe620bac2d33ab386f39a35a0f0d6424a827449c0b8e88f606fbbc37f0f656'
CUA_SHA256 = 'd199d8e601e5daeaf8b7a81b4597d6623e91511b76d818123fde2f1074d4f037'
CUA_VERSION = '0.46.0+footwork.5486b624.cleanup2.focus1.helptag1.connected4.locate10'
out = Path(__file__).parent
root = Path('/Users/thomasmain/.local/share/footwork')
built = root/'staging'/COMMIT/'build1'
current = root/'current'
previous = current.resolve()
launcher = Path('/Users/thomasmain/.local/bin/footwork')
launcher_sha = hashlib.sha256(launcher.read_bytes()).hexdigest()
assert previous == root/'releases/6d571a1ed7c7bf77576279a01053f77fc20ce469', previous
bundle = root/'bundles'/COMMIT
prefix = root/'releases'/COMMIT
assert not bundle.exists() and not prefix.exists()
shutil.copytree(built, bundle)
manifest = json.loads((bundle/'MANIFEST.json').read_text())
for name, digest in manifest['files'].items():
    assert hashlib.sha256((bundle/name).read_bytes()).hexdigest() == digest
assert manifest['files'][manifest['cua']] == CUA_SHA256 and manifest['files'][manifest['product']] == PRODUCT_SHA256
with (out/'release-install.txt').open('w') as log:
    subprocess.run([str(previous/'bin/python'), '-I', str(bundle/'install.py'), '--venv', str(prefix),
                    '--python', str(previous/'bin/python'), '--offline', '--profile', 'full'],
                   cwd=out, stdout=log, stderr=subprocess.STDOUT, check=True)
report = out/'release-verification.json'
host = root/'qualification/release-474958e-20261114/host'
host.mkdir(parents=True, exist_ok=True)
result = subprocess.run([str(prefix/'bin/python'), '-I', str(out/'verify_release.py'), '--bundle', str(bundle),
                         '--prefix', str(prefix), '--report', str(report), '--host', str(host),
                         '--cua-version', CUA_VERSION], cwd=host, capture_output=True, text=True)
(out/'release-verification-console.txt').write_text(result.stdout+result.stderr)
result.check_returncode()
verified = json.loads(report.read_text())
assert verified['passed']
assert current.resolve() == previous, 'current moved during staging'
q = prefix/'qualification'
q.mkdir()
shutil.copy2(report, q/report.name)
metadata = {'schema_version': 1, 'source_repository': 'https://github.com/Tom-R-Main/Footwork',
            'source_commit': COMMIT, 'source_tree': TREE, 'source_branch': 'main', 'source_merged': True,
            'pull_request': 'https://github.com/Tom-R-Main/Footwork/pull/32',
            'installed_at': datetime.now(timezone.utc).isoformat(), 'profile': 'full',
            'bundle': str(bundle), 'bundle_manifest': manifest,
            'installed_files': verified['wheel_checks'], 'previous_release': str(previous),
            'qualification': {'installed_bytes': 'passed', 'installed_discovery': 'passed',
                              'live_release_probe': 'pending', 'live_filmed_page_pointer': 'pending',
                              'live_drag_points': 'pending'},
            'evidence': str(out), 'qualification_directory': str(q),
            'launcher': str(launcher), 'launcher_sha256': launcher_sha, 'current': str(current)}
(prefix/'footwork-release.json').write_text(json.dumps(metadata, indent=2)+'\n')
print(json.dumps({'staged': str(prefix), 'current_unchanged': str(current.resolve()), 'verification': verified['wheel_checks']}))
