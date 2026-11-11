"""Stage and verify a fresh exact-commit full release WITHOUT selecting it.

Adapted from results/pointer-startup-20261111/install_release.py: the same offline install and
verification, but `current` is left untouched; activate_release.py selects it only after the live
qualification passes.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

COMMIT = '6d571a1ed7c7bf77576279a01053f77fc20ce469'
TREE = '48c36d07a5b7f4802d7948cf63af0d4c12025372'
CUA_SHA256 = '22083ce34aa45a2404bda2b27ad120156c7380da8a659879e00df139a69393ec'
out = Path('/Users/thomasmain/projects/footwork/jevdual/output/converge-release-20261111')
root = Path('/Users/thomasmain/.local/share/footwork')
current = root/'current'
previous = current.resolve()
launcher = Path('/Users/thomasmain/.local/bin/footwork')
launcher_sha = hashlib.sha256(launcher.read_bytes()).hexdigest()
assert previous == root/'releases/eded45c48d550b6867e1ce1314de64c41cbcfae8'
bundle = root/'bundles'/COMMIT
prefix = root/'releases'/COMMIT
assert not bundle.exists() and not prefix.exists()
shutil.copytree(out/'bundle', bundle)
manifest = json.loads((bundle/'MANIFEST.json').read_text())
for name, digest in manifest['files'].items():
    assert hashlib.sha256((bundle/name).read_bytes()).hexdigest() == digest
assert manifest['files'][manifest['cua']] == CUA_SHA256
with (out/'release-install.txt').open('w') as log:
    subprocess.run([str(previous/'bin/python'), '-I', str(bundle/'install.py'), '--venv', str(prefix),
                    '--python', str(previous/'bin/python'), '--offline', '--profile', 'full'],
                   cwd=out, stdout=log, stderr=subprocess.STDOUT, check=True)
report = out/'release-verification.json'
host = root/'qualification/converge-release-20261111/host'
host.mkdir(parents=True, exist_ok=True)
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
            'source_commit': COMMIT, 'source_tree': TREE,
            'source_branch': 'claude/converge-main-20261111', 'source_merged': False,
            'pull_request': 'https://github.com/Tom-R-Main/Footwork/pull/24',
            'installed_at': datetime.now(timezone.utc).isoformat(), 'profile': 'full',
            'bundle': str(bundle), 'bundle_manifest': manifest,
            'installed_files': verified['wheel_checks'], 'previous_release': str(previous),
            'qualification': {'installed_bytes': 'passed', 'installed_discovery': 'passed',
                              'native_immediate_start': 'pending'},
            'evidence': str(Path(__file__).parent), 'qualification_directory': str(q),
            'launcher': str(launcher), 'launcher_sha256': launcher_sha, 'current': str(current)}
(prefix/'footwork-release.json').write_text(json.dumps(metadata, indent=2)+'\n')
assert current.resolve() == previous
assert hashlib.sha256(launcher.read_bytes()).hexdigest() == launcher_sha
summary = {'source_commit': COMMIT, 'prefix': str(prefix), 'bundle': str(bundle),
           'current_unchanged': str(current.resolve()), 'launcher_sha256': launcher_sha,
           'verification': {k: verified[k] for k in ('passed', 'wheel_checks', 'failures', 'imports')}}
(out/'install-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps(summary, indent=2))
