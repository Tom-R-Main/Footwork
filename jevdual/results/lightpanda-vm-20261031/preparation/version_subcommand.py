"""One documented version command; preserve the earlier guessed flag as a failed attempt."""
import ctypes
import hashlib
import os
import subprocess
import time

from check_binary import EXPECTED, ROOT, children, digest, no_core, save

binary = ROOT / 'lightpanda-x86_64-linux'
assert binary.stat().st_size == 77129032 and digest(binary) == EXPECTED
assert ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) == 0
env = dict(os.environ)
for key in ['TYPESAFE_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY']:
    env.pop(key, None)
env.update(LIGHTPANDA_DISABLE_TELEMETRY='true', LIGHTPANDA_DISABLE_CORE_DUMP='1')
before = time.monotonic()
process = subprocess.Popen([str(binary), 'version'], cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                           preexec_fn=no_core)
timed_out = False
try:
    out, err = process.communicate(timeout=10)
except subprocess.TimeoutExpired:
    timed_out = True
    process.kill()
    out, err = process.communicate(timeout=3)
(ROOT / 'version-subcommand.stdout.txt').write_bytes(out)
(ROOT / 'version-subcommand.stderr.txt').write_bytes(err)
receipt = {'command': [str(binary), 'version'], 'pid': process.pid, 'returncode': process.returncode,
           'signal': -process.returncode if process.returncode < 0 else None, 'timeout': timed_out,
           'wait_complete': True, 'elapsed_seconds': time.monotonic() - before,
           'stdout_sha256': hashlib.sha256(out).hexdigest(), 'stderr_sha256': hashlib.sha256(err).hexdigest(),
           'binary_sha256_after': digest(binary), 'owned_descendants_after': children(),
           'metadata_only': True}
save('version-subcommand.json', receipt)
raise SystemExit(1 if process.returncode or timed_out or receipt['owned_descendants_after'] else 0)
