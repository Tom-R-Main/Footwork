import sys,json,hashlib,importlib,importlib.metadata,platform,subprocess
from pathlib import Path
base=Path(sys.argv[1]).absolute();sys.path.insert(0,str(base/'site'));out={'commit':json.loads((base/'manifest.json').read_text())['commit'],'python':sys.executable,'os':platform.platform(),'sdk':importlib.metadata.version('cua-driver'),'modules':{}}
for name in ['session','session_operations','operator_evidence','native','ax','finder_targets','ticket_evidence','app_qualification']:
 m=importlib.import_module('jevdual.'+name);p=Path(m.__file__);assert p.is_relative_to(base/'site');out['modules'][name]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
for name,p in [('Finder','/System/Library/CoreServices/Finder.app'),('Preview','/System/Applications/Preview.app'),('Chrome','/Applications/Google Chrome.app')]:
 r=subprocess.run(['/usr/libexec/PlistBuddy','-c','Print :CFBundleShortVersionString',p+'/Contents/Info.plist'],capture_output=True,text=True);out[name]=r.stdout.strip()
out['harness']={'path':str(base.parent/'live_driver.py'),'sha256':hashlib.sha256((base.parent/'live_driver.py').read_bytes()).hexdigest()};(base/'runtime.json').write_text(json.dumps(out,indent=2));print(json.dumps({'commit':out['commit'],'verified_module_origins':len(out['modules'])}))
