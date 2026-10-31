import hashlib,json,zipfile,importlib.metadata as md
from pathlib import Path
bundle=Path('/workspace/scratch/fw-reliability-release-bundle');manifest=json.loads((bundle/'MANIFEST.json').read_text());out={'source':'51ee6e2f57c3959ce30e19f168baa864d9d38a6b','wheels':{},'versions':{d.metadata['Name']:d.version for d in md.distributions()}}
for role,package,prefix in [('product','jevdual','jevdual/'),('cua','cua-driver','cua_driver/')]:
 wheel=bundle/manifest[role];dist=md.distribution(package);files={}
 with zipfile.ZipFile(wheel) as z:
  for name in z.namelist():
   if name.startswith(prefix) and not name.endswith('/'):
    b=z.read(name);p=Path(dist.locate_file(name));assert p.read_bytes()==b,name;files[name]=hashlib.sha256(b).hexdigest()
 out['wheels'][role]={'filename':wheel.name,'sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'matched_files':len(files),'files':files}
print(json.dumps(out,indent=2))
