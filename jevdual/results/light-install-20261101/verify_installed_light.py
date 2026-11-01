"""Exercise a built light wheel through its installed public CLI and a local engine."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import importlib.util
import json
import subprocess
import threading
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--run', type=Path, required=True)
parser.add_argument('--wheel', type=Path, required=True)
parser.add_argument('--engine', type=Path, required=True)
parser.add_argument('--engine-work', type=Path, required=True)
args = parser.parse_args()
project = Path('/Users/thomasmain/projects/footwork')
run = args.run.resolve()
spec = importlib.util.spec_from_file_location('install_env', project / 'jevdual/scripts/capability_clean_install.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
env = mod.isolated_environment(run)
exe, python = run / 'venv/bin/footwork', run / 'venv/bin/python'
records = []

def execute(words, expected=0):
    command = [str(exe), '--json', *words]
    result = subprocess.run(command, cwd=run / 'outside-source', env=env, capture_output=True, text=True, timeout=45)
    name = 'public-' + '-'.join(words[:4]).replace('/', '_')
    (run / (name + '.stdout.json')).write_text(result.stdout)
    (run / (name + '.stderr.log')).write_text(result.stderr)
    value = json.loads(result.stdout)
    assert result.returncode == value['exit_code'] == expected, (words, result.returncode, result.stderr)
    assert value['effect_verification'] == 'not_asserted', value
    records.append({'command': words, 'exit': result.returncode})
    return value

catalog = execute(['tools'])['data']
assert catalog['installation']['profile'] == 'light', catalog['installation']
execute(['schema', 'browser', 'lightpanda', 'read'])
doctor = execute(['doctor'])['data']
assert doctor['installation']['profile'] == 'light', doctor
refusal = execute(['apps'], expected=7)
assert not refusal['command_completed'] and 'effector_unavailable' in refusal['diagnostics'], refusal

probe = '''import importlib.util,importlib.metadata,json,jevdual,sys
print(json.dumps({"missing":{n:importlib.util.find_spec(n) is None for n in ["cua_driver","browser_use","Quartz","ApplicationServices","jeepney"]},"packages":sorted(d.metadata["Name"] for d in importlib.metadata.distributions()),"package":jevdual.__file__,"backend":jevdual.BACKEND,"prefix":sys.prefix,"sys_path":sys.path}))'''
result = subprocess.run([str(python), '-I', '-c', probe], cwd=run / 'outside-source', env=env, capture_output=True, text=True, check=True)
closure = json.loads(result.stdout)
assert all(closure['missing'].values()), closure
assert Path(closure['package']).is_relative_to(run / 'venv'), closure
assert closure['backend'] == 'pure-python', closure
assert not any('site-packages' in p and not Path(p).is_relative_to(run / 'venv') for p in closure['sys_path']), closure
site = Path(closure['package']).parent.parent
with zipfile.ZipFile(args.wheel) as archive:
    product_files = [name for name in archive.namelist() if name.startswith('jevdual/')]
    assert all((site / name).read_bytes() == archive.read(name) for name in product_files)
(run / 'public-closure.json').write_text(json.dumps(closure, indent=2) + '\n')
posts = []
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        content = b'''<!doctype html><title>Light installation fixture</title>
<h1>Installed light runtime</h1><p id="ready">Waiting</p><a href="/next">Next report</a>
<input type="password" value="PRIVATE_FIXTURE_PASSWORD"><input value="PRIVATE_FIXTURE_TEXT">
<button type="button" onclick="fetch('/effect',{method:'POST'})">Commit</button>
<script>document.getElementById('ready').textContent='Script content ready'</script>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(content)
    def do_POST(self):
        posts.append(self.path)
        self.send_response(200)
        self.end_headers()
    def log_message(self, *words):
        pass
server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    data = execute(['browser', 'lightpanda', 'read', f'http://127.0.0.1:{server.server_port}/',
                    '--executable', str(args.engine.resolve()), '--work-dir', str(args.engine_work.resolve()),
                    '--timeout', '15'])['data']
    raw = json.dumps(data.get('observation', {}))
    checks = {
        'capture_completed': data.get('capture_completed') is True,
        'semantic_heading': 'Installed light runtime' in raw,
        'script_content': 'Script content ready' in raw,
        'private_fields_withheld': 'PRIVATE_FIXTURE_' not in raw,
        'no_actions': data.get('observation', {}).get('actions') == [],
        'no_input': data.get('input') == {'supported': False, 'dispatched': False},
        'no_business_completion': data.get('completion') == 'not_asserted',
        'no_post_effects': posts == [],
        'bounded_cleanup': data.get('cleanup', {}).get('status') == 'bounded_owned_processes_stopped',
    }
    summary = {'checks': checks, 'commands': records, 'installation': catalog['installation'],
               'missing_optional_modules': closure['missing'], 'packages': len(closure['packages']),
               'installed_product_files_match_wheel': len(product_files), 'cleanup': data.get('cleanup'),
               'wheel': str(args.wheel.resolve()), 'wheel_sha256': json.loads((run / 'receipt.json').read_text())['wheel_sha256']}
    (run / 'installed-public-verification.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    assert all(checks.values()), checks
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
