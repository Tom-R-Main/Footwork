"""Stage/verify a fresh exact-commit full release, then atomically select it."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid

project = Path(__file__).resolve().parents[2]
out = project / 'output/pointer-startup-20261111'
prep = json.loads((out/'qualified-preparation.json').read_text())
commit = prep['source_commit']
root = Path('/Users/thomasmain/.local/share/footwork')
current = root/'current'
previous = Path(prep['previous_release'])
launcher = Path('/Users/thomasmain/.local/bin/footwork')
assert current.resolve() == previous
assert hashlib.sha256(launcher.read_bytes()).hexdigest() == prep['launcher_sha256']
assert hashlib.sha256((previous/'footwork-release.json').read_bytes()).hexdigest() == prep['previous_metadata_sha256']
bundle = root/'bundles'/commit
prefix = root/'releases'/commit
assert not bundle.exists() and not prefix.exists()
shutil.copytree(prep['bundle_path'], bundle)
manifest = json.loads((bundle/'MANIFEST.json').read_text())
for name, digest in manifest['files'].items():
    assert hashlib.sha256((bundle/name).read_bytes()).hexdigest() == digest
with (out/'release-install.txt').open('w') as log:
    subprocess.run([str(previous/'bin/python'), '-I', str(bundle/'install.py'), '--venv', str(prefix),
                    '--python', str(previous/'bin/python'), '--offline', '--profile', 'full'],
                   cwd=out, stdout=log, stderr=subprocess.STDOUT, check=True)
report = out/'release-verification.json'
host = root/'qualification/macos-coordination-20261111/host'
result = subprocess.run([str(prefix/'bin/python'), '-I', str(Path(__file__).with_name('verify_release.py')),
                         '--bundle', str(bundle), '--prefix', str(prefix), '--report', str(report),
                         '--host', str(host)], cwd=host, capture_output=True, text=True)
(out/'release-verification-console.txt').write_text(result.stdout+result.stderr)
result.check_returncode()
verified = json.loads(report.read_text())
assert verified['passed']
q = prefix/'qualification'
q.mkdir()
shutil.copy2(report, q/report.name)
metadata = {'schema_version': 1, 'source_repository': 'https://github.com/Tom-R-Main/Footwork',
            'source_commit': commit, 'source_tree': prep['source_tree'],
            'source_branch': 'codex/macos-pointer-startup-fix', 'source_merged': False,
            'installed_at': datetime.now(timezone.utc).isoformat(), 'profile': 'full',
            'bundle': str(bundle), 'bundle_manifest': manifest,
            'installed_files': verified['wheel_checks'], 'previous_release': str(previous),
            'qualification': {'installed_bytes': 'passed', 'installed_discovery': 'passed',
                              'native_immediate_start': 'pending'},
            'evidence': str(Path(__file__).parent), 'qualification_directory': str(q),
            'launcher': str(launcher), 'launcher_sha256': prep['launcher_sha256'], 'current': str(current)}
(prefix/'footwork-release.json').write_text(json.dumps(metadata, indent=2)+'\n')
assert current.resolve() == previous
assert hashlib.sha256(launcher.read_bytes()).hexdigest() == prep['launcher_sha256']
temporary = root/('current-next-'+uuid.uuid4().hex)
os.symlink(prefix, temporary)
os.replace(temporary, current)
activation = {'source_commit': commit, 'source_tree': prep['source_tree'],
              'source_merged': False, 'active_release': str(current.resolve()),
              'previous_release': str(previous), 'launcher_unchanged': True,
              'offline_install': True, 'qualification': metadata['qualification']}
(out/'activation.json').write_text(json.dumps(activation, indent=2)+'\n')
print(json.dumps(activation, indent=2))
