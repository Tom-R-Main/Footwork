import os,subprocess,sys,json
from pathlib import Path
label=sys.argv[1];script=Path(sys.argv[2]);out=Path('/workspace/scratch/fw-reliability-'+label)
out.mkdir(mode=0o777);out.chmod(0o777)
(out/'run.py').write_bytes(script.read_bytes());(out/'run.py').chmod(0o644)
(out/'passwd').write_text('root:x:0:0:root:/root:/bin/sh\nfixture:x:1000:1000:fixture:/home/agent:/bin/sh\n');(out/'passwd').chmod(0o644)
(out/'group').write_text('root:x:0:\nfixture:x:1000:\n');(out/'group').chmod(0o644)
env=os.environ.copy()
for k in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(k,None)
base=['docker','--host=unix:///var/run/docker.sock']; name='footwork-reliability-'+label
cmd=[*base,'run','--name',name,'--init','--network','none','--pids-limit','512','--cpus','2','--memory','3g','--memory-swap','3g','--shm-size','512m','--cap-drop','ALL','--security-opt','no-new-privileges','--user','1000:1000']
for path in ['/usr/bin','/usr/lib','/usr/libexec','/usr/share','/etc/alternatives','/etc/fonts','/etc/dbus-1','/opt/codex/runtimes/codex-primary-runtime/dependencies/python','/workspace/Footwork','/workspace/.footwork-setup/sysroot','/workspace/scratch/fw-reliability-diag-consumer']:
 cmd+=['--mount',f'type=bind,src={path},dst={path},readonly']
cmd+=['--mount',f'type=bind,src={out}/passwd,dst=/etc/passwd,readonly','--mount',f'type=bind,src={out}/group,dst=/etc/group,readonly','--mount',f'type=bind,src={out},dst=/work','--workdir','/work','--env','PATH=/workspace/.footwork-setup/sysroot/usr/bin:/usr/bin:/bin','--env','LD_LIBRARY_PATH=/workspace/.footwork-setup/sysroot/usr/lib/x86_64-linux-gnu','--env','ANONYMIZED_TELEMETRY=false','--env','IN_DOCKER=true','--entrypoint','/workspace/scratch/fw-reliability-diag-consumer/bin/python','debian:13-slim','-u','-I','/work/run.py']
r=subprocess.run(cmd,env=env,stdout=(out/'container.txt').open('w'),stderr=subprocess.STDOUT)
inspect=subprocess.run([*base,'inspect',name],env=env,capture_output=True,text=True)
# Only public config, never environment.
if inspect.returncode==0:
 obj=json.loads(inspect.stdout)[0];(out/'container-config.json').write_text(json.dumps({k:obj[k] for k in ['Id','State','HostConfig','Mounts']},indent=2))
print(label,r.returncode, str(out));raise SystemExit(r.returncode)
