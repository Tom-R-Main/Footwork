"""Install a verified merged bundle, then atomically advance the stable release pointer."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

parser=argparse.ArgumentParser()
parser.add_argument('--merge',required=True)
args=parser.parse_args()
if not re.fullmatch('[0-9a-f]{40}',args.merge):
    raise SystemExit('expected an exact merged commit')
project=Path(__file__).resolve().parents[2]
repo=project.parent
out=project/'output/installed-coordination-20261111'
prep=json.loads((out/'preparation.json').read_text())
merge_tree=subprocess.check_output(['git','rev-parse',args.merge+'^{tree}'],cwd=repo,text=True).strip()
if merge_tree!=prep['build_tree']:
    raise SystemExit('merged tree differs from the candidate; rebuild and reverify before activation')
base=Path('/Users/thomasmain/.local/share/footwork')
current=base/'current'; old=Path(prep['previous_release'])
launcher=Path('/Users/thomasmain/.local/bin/footwork')
if current.resolve()!=old:
    raise SystemExit('current release changed since preparation')
if hashlib.sha256(launcher.read_bytes()).hexdigest()!=prep['launcher_sha256']:
    raise SystemExit('stable launcher changed since preparation')
if hashlib.sha256((old/'footwork-release.json').read_bytes()).hexdigest()!=prep['previous_metadata_sha256']:
    raise SystemExit('previous release metadata changed')
bundle=base/'bundles'/args.merge; prefix=base/'releases'/args.merge
if bundle.exists() or prefix.exists():
    raise SystemExit('new bundle/release must not already exist')
shutil.copytree(out/'bundle',bundle)
manifest=json.loads((bundle/'MANIFEST.json').read_text())
for name,digest in manifest['files'].items():
    if hashlib.sha256((bundle/name).read_bytes()).hexdigest()!=digest:
        raise SystemExit('bundle copy hash mismatch')
cmd=[str(old/'bin/python'),'-I',str(bundle/'install.py'),'--venv',str(prefix),'--python',str(old/'bin/python'),'--offline','--profile','full']
with (out/'release-install.txt').open('w') as log:
    p=subprocess.run(cmd,cwd=out,stdout=log,stderr=subprocess.STDOUT)
if p.returncode:
    raise SystemExit('fresh release installation failed; current was not changed')
verify=[str(prefix/'bin/python'),'-I',str(Path(__file__).with_name('verify_release.py')),
        '--bundle',str(bundle),'--prefix',str(prefix),'--report',str(out/'release-verification.json'),
        '--host',str(base/'qualification/macos-coordination-20261111/host')]
p=subprocess.run(verify,cwd=out,text=True,capture_output=True)
(out/'release-verification-console.txt').write_text(p.stdout+p.stderr)
if p.returncode:
    raise SystemExit('installed byte/CLI verification failed; current was not changed')
verified=json.loads((out/'release-verification.json').read_text())
qualification=prefix/'qualification';qualification.mkdir()
shutil.copyfile(project/'results/macos-coordination-20261111-fix/REPORT.md',qualification/'source-qualification.md')
shutil.copyfile(out/'release-verification.json',qualification/'installed-byte-verification.json')
metadata={'schema_version':1,'source_repository':'https://github.com/Tom-R-Main/Footwork',
          'source_commit':args.merge,'source_tree':merge_tree,'qualified_pr_head':prep['build_head'],
          'installed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'profile':'full','bundle':str(bundle),'bundle_manifest':manifest,
          'installed_files':verified['wheel_checks'],'previous_release':str(old),
          'qualification':{'installed_discovery':'passed','installed_bytes':'passed','native_coordination':'pending'},
          'evidence':str(project/'results/installed-coordination-20261111'),
          'launcher':str(launcher),'launcher_sha256':prep['launcher_sha256'],'current':str(current),
          'qualification_directory':str(qualification)}
(prefix/'footwork-release.json').write_text(json.dumps(metadata,indent=2)+'\n')
if current.resolve()!=old:
    raise SystemExit('current changed before activation; new release retained inactive')
temporary=current.with_name('current-next-'+uuid.uuid4().hex)
os.symlink(prefix,temporary)
os.replace(temporary,current)
record={'merged_source':args.merge,'source_tree':merge_tree,'candidate_tree_equal':True,
        'previous_release':str(old),'active_release':str(current.resolve()),'launcher_unchanged':hashlib.sha256(launcher.read_bytes()).hexdigest()==prep['launcher_sha256'],
        'activated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(out/'activation.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
