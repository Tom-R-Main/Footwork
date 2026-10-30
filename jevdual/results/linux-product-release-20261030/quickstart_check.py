import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
import jevdual
root = Path('/artifacts')
manifest = json.loads((root/'bundle/MANIFEST.json').read_text())
wheel = root/'bundle'/manifest['product']
site = Path(jevdual.__file__).parent.parent
checked = 0
with zipfile.ZipFile(wheel) as z:
    for member in z.namelist():
        if member.startswith('jevdual/'):
            assert (site/member).read_bytes() == z.read(member), member
            checked += 1
work = Path(tempfile.mkdtemp(prefix='footwork-first-result-'))
expected = work/'expected.txt'; saved = work/'note.txt'
expected.write_text('Footwork checked this note.\n'); saved.write_bytes(expected.read_bytes())
sha = hashlib.sha256(expected.read_bytes()).hexdigest()
cli = str(Path(sys.executable).parent/'footwork')
results = []
for name,args,rc,ok in [
    ('tools',['tools'],0,None),
    ('doctor',['doctor'],0,None),
    ('schema',['schema','browser','start'],0,None),
    ('matching',['check-artifact',str(saved),'--expected-file',str(expected),'--expected-sha256',sha],0,True),
    ('changed',['check-artifact',str(saved),'--expected-file',str(expected),'--expected-sha256',sha],6,False),
]:
    if name == 'changed': saved.write_text('A different note.\n')
    run = subprocess.run([cli,*args],capture_output=True,text=True,timeout=45)
    (root/f'quickstart-{name}.stdout').write_text(run.stdout)
    (root/f'quickstart-{name}.stderr').write_text(run.stderr)
    assert run.returncode == rc, (name,run.returncode)
    payload = json.loads(run.stdout)
    if ok is not None: assert payload['ok'] is ok, payload
    results.append(dict(command=name,exit=run.returncode,ok=payload.get('ok')))
receipt = dict(source_revision='40ae59f',platform=sys.platform,wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),installed_package_files=checked,checks=results)
(root/'quickstart-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
