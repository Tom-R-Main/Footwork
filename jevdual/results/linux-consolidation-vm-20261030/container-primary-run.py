import os,subprocess
from pathlib import Path
output=Path('/workspace/scratch/fw-consolidated-primary')
env=os.environ.copy()
for key in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(key,None)
command=['docker','--host=unix:///var/run/docker.sock','run','--name','footwork-consolidated-primary','--init','--network','none','--pids-limit','512','--cpus','2','--memory','3g','--memory-swap','3g','--shm-size','512m','--cap-drop','ALL','--security-opt','no-new-privileges','--user','1000:1000']
for path in ['/usr/bin','/usr/lib','/usr/libexec','/usr/share','/etc/alternatives','/etc/fonts','/etc/dbus-1','/opt/codex/runtimes/codex-primary-runtime/dependencies/python','/workspace/Footwork','/workspace/.footwork-setup/sysroot','/workspace/scratch/fw-consolidated-final-consumer']:
 command+=['--mount',f'type=bind,src={path},dst={path},readonly']
command+=['--mount',f'type=bind,src={output}/passwd,dst=/etc/passwd,readonly','--mount',f'type=bind,src={output}/group,dst=/etc/group,readonly','--mount',f'type=bind,src={output},dst=/work','--workdir','/work','--env','PATH=/workspace/.footwork-setup/sysroot/usr/bin:/usr/bin:/bin','--entrypoint','/workspace/scratch/fw-consolidated-final-consumer/bin/python','debian:13-slim','-I','/work/accept.py']
result=subprocess.run(command,env=env,capture_output=True,text=True)
Path('/workspace/Footwork/jevdual/results/linux-consolidation-vm-20261030/container-primary.txt').write_text(result.stdout+result.stderr)
print(result.stdout[-6000:]+result.stderr[-3000:])
raise SystemExit(result.returncode)
