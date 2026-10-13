"""Actual host death while a labelled fake planner refuses to read its pipe."""
import fcntl
import os
import signal
import subprocess
import sys
import time
import unittest
import uuid
from pathlib import Path

import order_protocol as protocol
import planner_guard

BASE = Path(__file__).resolve().parent


def fixture(root):
    fd = os.open(root / "planner.lock", os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    read, write = os.pipe()
    protocol.create_file(root / "planner-intent.json", protocol.encoded({"version": 1, "host_pid": os.getpid(),
        "owner": "backpressure-fixture", "request_sha256": "b" * 64}))
    protocol.create_file(root / "reservation.json", protocol.encoded({"planner_owner": "backpressure-fixture"}))
    protocol.create_file(root / "prompt.txt", b"p" * protocol.MAX_BYTES)
    protocol.create_file(root / "request.json", protocol.encoded({"flags": [str(root)]}))
    with (root / "events.jsonl").open("xb") as out, (root / "stderr.log").open("xb") as err:
        child = subprocess.Popen([sys.executable, str(BASE / "planner_guard.py"), "--root", str(root),
            "--executable", str(root / "fake-cli"), "--lifetime-fd", str(read), "--lock-fd", str(fd)],
            stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True, close_fds=True, pass_fds=(read, fd))
        os.close(read)
        os.close(fd)
        protocol.persist(root / "host-ready.json", {"host_pid": os.getpid(), "guardian_pid": child.pid})
        try:
            while True:
                time.sleep(.1)
        finally:
            os.close(write)


class PlannerBackpressureTests(unittest.TestCase):
    def test_observed_detached_descendant_withholds_closure_without_signalling_unrelated_process(self):
        root = BASE / "output" / ("sim14-planner-detached-" + uuid.uuid4().hex[:10])
        root.mkdir(mode=0o700)
        fake = root / "fake-cli"
        fake.write_text("#!" + sys.executable + "\n" + '''import json,os,subprocess,sys,time
from pathlib import Path
root=Path(sys.argv[-1])
child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(120)'],start_new_session=True)
(root/'.detached-ready.json').write_text(json.dumps({'pid':os.getpid(),'detached_pid':child.pid}))
(root/'.detached-ready.json').replace(root/'detached-ready.json')
while True:
    time.sleep(.1)
''')
        fake.chmod(0o700)
        sink = (root / "host.log").open("wb")
        host = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--fixture", str(root)], stdout=sink, stderr=subprocess.STDOUT)
        unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"], start_new_session=True)
        known = None
        startup = None
        evidence = {"fake_policy": True, "passed": False}
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if (root / "detached-ready.json").exists() and (root / "planner-descendants.json").exists():
                    ready = protocol.decode(protocol.read_bytes(root / "detached-ready.json"))
                    proof = protocol.decode(protocol.read_bytes(root / "planner-descendants.json"))
                    known = next((row for row in proof["observed"] if row["pid"] == ready["detached_pid"]), None)
                    if known:
                        break
                time.sleep(.02)
            self.assertIsNotNone(known)
            startup = protocol.decode(protocol.read_bytes(root / "planner-process.json"))
            self.assertEqual(startup["host_pid"], host.pid)
            self.assertNotEqual(known["group"], startup["planner_pgid"])
            self.assertEqual(known["group"], known["pid"])
            host.kill()
            self.assertEqual(host.wait(5), -signal.SIGKILL)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                try:
                    os.kill(startup["guardian_pid"], 0)
                except ProcessLookupError:
                    break
                time.sleep(.02)
            self.assertFalse((root / "planner-closure.json").exists())
            proof = protocol.decode(protocol.read_bytes(root / "planner-descendants.json"))
            self.assertFalse(proof["complete"])
            self.assertIn(known["pid"], [row["pid"] for row in proof["remaining"]])
            with self.assertRaisesRegex(protocol.Refusal, "without group cleanup"):
                planner_guard.recover(root)
            self.assertIsNone(unrelated.poll())
            self.assertTrue(planner_guard._same_process(planner_guard._processes().get(known["pid"]), known))
            evidence.update(passed=True, proof=proof, unrelated_alive=True, detached_alive=True)
        finally:
            if host.poll() is None:
                host.kill()
                host.wait(5)
            unrelated.terminate()
            unrelated.wait(5)
            if known and planner_guard._same_process(planner_guard._processes().get(known["pid"]), known):
                os.killpg(known["group"], signal.SIGKILL)
            if startup:
                for key in ("planner_pid", "guardian_pid"):
                    pid = startup[key]
                    try:
                        if os.getpgid(pid) == pid:
                            os.killpg(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            sink.close()
            protocol.create_file(root / "conformance.json", protocol.encoded(evidence))

    def test_nonblocking_delivery_preserves_entire_maximum_bound_prompt(self):
        root = BASE / "output" / ("sim14-planner-delivery-" + uuid.uuid4().hex[:10])
        root.mkdir(mode=0o700)
        fake = root / "fake-cli"
        fake.write_text("#!" + sys.executable + "\n" + '''import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[-1])
prompt=sys.stdin.buffer.read()
(root/'delivered.json').write_text(json.dumps({'bytes':len(prompt),'sha256':hashlib.sha256(prompt).hexdigest()}))
''')
        fake.chmod(0o700)
        sink = (root / "host.log").open("wb")
        host = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--fixture", str(root)], stdout=sink, stderr=subprocess.STDOUT)
        evidence = {"fake_policy": True, "passed": False}
        try:
            deadline = time.monotonic() + 5
            while not (root / "planner-closure.json").exists() and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue((root / "planner-closure.json").exists())
            delivered = protocol.decode(protocol.read_bytes(root / "delivered.json"))
            prompt = protocol.read_bytes(root / "prompt.txt")
            self.assertEqual(delivered, {"bytes": len(prompt), "sha256": protocol.sha(prompt)})
            self.assertEqual(len(prompt), protocol.MAX_BYTES)
            closure = protocol.decode(protocol.read_bytes(root / "planner-closure.json"))
            self.assertEqual(closure["reason"], "completed")
            self.assertTrue(closure["group_closed"])
            evidence.update(passed=True, delivered=delivered, closure=closure)
        finally:
            host.kill()
            host.wait(5)
            sink.close()
            protocol.create_file(root / "conformance.json", protocol.encoded(evidence))

    def test_sigkill_host_with_full_nonreading_stdin_retires_exact_owned_group(self):
        root = BASE / "output" / ("sim14-planner-backpressure-" + uuid.uuid4().hex[:10])
        root.mkdir(mode=0o700)
        fake = root / "fake-cli"
        fake.write_text("#!" + sys.executable + "\n" + '''import array,fcntl,json,os,sys,termios,time
from pathlib import Path
root=Path(sys.argv[-1])
(root/'.nonreading-ready').write_text(str(os.getpid()))
(root/'.nonreading-ready').replace(root/'nonreading-ready')
pending=array.array('i',[0])
deadline=time.monotonic()+3
while time.monotonic()<deadline:
    fcntl.ioctl(0,termios.FIONREAD,pending,True)
    if pending[0]>=16384:
        break
    time.sleep(.01)
(root/'.buffered.json').write_text(json.dumps({'bytes':pending[0]}))
(root/'.buffered.json').replace(root/'buffered.json')
while True:
    time.sleep(.1)
''')
        fake.chmod(0o700)
        sink = (root / "host.log").open("wb")
        host = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--fixture", str(root)], stdout=sink, stderr=subprocess.STDOUT)
        startup = None
        evidence = {"fake_policy": True, "case": "host-death-during-full-planner-stdin", "passed": False}
        try:
            deadline = time.monotonic() + 5
            while not (root / "nonreading-ready").exists() and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue((root / "nonreading-ready").exists())
            startup = protocol.decode(protocol.read_bytes(root / "planner-process.json"))
            registered = protocol.decode(protocol.read_bytes(root / "host-ready.json"))
            self.assertEqual(startup["host_pid"], host.pid)
            self.assertEqual(startup["guardian_pid"], registered["guardian_pid"])
            self.assertEqual(startup["planner_pid"], int((root / "nonreading-ready").read_text()))
            self.assertGreater((root / "prompt.txt").stat().st_size, 32768)
            self.assertEqual(os.getpgid(startup["planner_pid"]), startup["planner_pgid"])
            deadline = time.monotonic() + 4
            while not (root / "buffered.json").exists() and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue((root / "buffered.json").exists())
            buffered = protocol.decode(protocol.read_bytes(root / "buffered.json"))
            evidence["buffered_bytes_before_host_kill"] = buffered["bytes"]
            self.assertGreaterEqual(buffered["bytes"], 16384)
            host.kill()
            self.assertEqual(host.wait(5), -signal.SIGKILL)
            deadline = time.monotonic() + 5
            while not (root / "planner-closure.json").exists() and time.monotonic() < deadline:
                time.sleep(.02)
            evidence.update(startup=startup, host_exit=host.returncode,
                closure_saved=(root / "planner-closure.json").exists())
            self.assertTrue(evidence["closure_saved"], "EOF cleanup stalled behind full planner stdin")
            closure = protocol.decode(protocol.read_bytes(root / "planner-closure.json"))
            self.assertEqual(closure["reason"], "host liveness pipe closed")
            self.assertTrue(closure["group_closed"])
            with self.assertRaises(ProcessLookupError):
                os.kill(startup["planner_pid"], 0)
            evidence.update(passed=True, closure=closure)
        finally:
            if host.poll() is None:
                host.kill()
                host.wait(5)
            # Only the just-spawned fixture's registered, separate process
            # groups are eligible; no restart cleanup signals stored PIDs.
            if startup:
                for key in ("planner_pid", "guardian_pid"):
                    pid = startup[key]
                    try:
                        if os.getpgid(pid) == pid:
                            os.killpg(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            sink.close()
            protocol.create_file(root / "conformance.json", protocol.encoded(evidence))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--fixture":
        fixture(protocol.directory(Path(sys.argv[2])))
    else:
        unittest.main()
