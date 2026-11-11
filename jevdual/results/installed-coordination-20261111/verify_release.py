"""Verify wheel bytes and real installed CLI behavior from a hostile owned cwd."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--bundle', type=Path, required=True)
parser.add_argument('--prefix', type=Path, required=True)
parser.add_argument('--report', type=Path, required=True)
parser.add_argument('--host', type=Path, required=True)
parser.add_argument('--launcher', type=Path)
args = parser.parse_args()
args.host.mkdir(parents=True, exist_ok=True)
poison = args.host/'jevdual'
poison.mkdir(exist_ok=True)
(poison/'__init__.py').write_text("raise RuntimeError('checkout/cwd shadow imported')\n")
manifest=json.loads((args.bundle/'MANIFEST.json').read_text())
result={'prefix':str(args.prefix.resolve()),'python':sys.executable,'bundle':str(args.bundle),
        'host':str(args.host),'wheel_checks':{},'commands':[],'failures':[]}
for name,digest in manifest['files'].items():
    if hashlib.sha256((args.bundle/name).read_bytes()).hexdigest()!=digest:
        result['failures'].append('bundle hash: '+name)
import jevdual,cua_driver
result['imports']={'jevdual':jevdual.__file__,'cua_driver':cua_driver.__file__}
for name in ('jevdual','cua-driver'):
    dist=importlib.metadata.distribution(name)
    role='product' if name=='jevdual' else 'cua'
    package='jevdual/' if name=='jevdual' else 'cua_driver/'
    checked=0
    with zipfile.ZipFile(args.bundle/manifest[role]) as archive:
        for f in archive.namelist():
            if not f.startswith(package) or f.endswith('/'):
                continue
            installed=Path(dist.locate_file(f))
            if not installed.is_relative_to(args.prefix.resolve()) or installed.read_bytes()!=archive.read(f):
                result['failures'].append('installed bytes: '+f)
            checked+=1
    result['wheel_checks'][name]={'version':dist.version,'checked_files':checked,'location':str(dist.locate_file(''))}
if importlib.metadata.version('cua-driver')!='0.46.0+footwork.5486b624.cleanup2':
    result['failures'].append('CUA version drift')
command=[str(args.launcher)] if args.launcher else [sys.executable,'-I','-m','jevdual.cli']
env=os.environ.copy()
env['PYTHONPATH']=str(args.host)
for words in (['--json','tools'],['--json','doctor'],['--json','schema','desktop','control'],['control','status']):
    p=subprocess.run(command+words,cwd=args.host,env=env,text=True,capture_output=True,timeout=30)
    row={'args':words,'exit':p.returncode,'stderr':p.stderr}
    path=args.report.with_name(args.report.stem+'-'+words[-1]+'.stdout')
    path.write_text(p.stdout)
    row['stdout']=str(path)
    try:
        data=json.loads(p.stdout)
        if isinstance(data,dict) and 'exit_code' in data and data['exit_code']!=0:
            result['failures'].append('CLI envelope: '+' '.join(words))
        if words[-1]=='status':
            row['active_requests']=len(data['requests'])
            row['active_reservations']=sum(r['state']=='active' for r in data['reservations'])
    except (ValueError,KeyError,TypeError):
        result['failures'].append('invalid CLI JSON: '+' '.join(words))
    if p.returncode:
        result['failures'].append('CLI exit: '+' '.join(words))
    result['commands'].append(row)
result['passed']=not result['failures']
args.report.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':result['passed'],'wheel_checks':result['wheel_checks'],'failures':result['failures']}))
sys.exit(0 if result['passed'] else 1)
