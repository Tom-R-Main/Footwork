"""SIM9 mechanical TCP faults; deterministic RGB conformance is not AI evidence.

Each case retains inputs, socket replies, native proof, logs and its outcome under
output/n9test-*. Only this harness's child processes are stopped during cleanup.
"""

import concurrent.futures
import copy
import hashlib
import http.client
import json
import math
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import unittest
import uuid
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import body_client
import image_guided as vision
import network_fault_proxy
import order_protocol as storage
import workcell as body

BASE = Path(__file__).resolve().parent
ZONE = {"x_min": .04, "x_max": .11, "y_min": -.025, "y_max": .025}
CORE_FILES = ("body_protocol.py", "body_network.py", "body_client.py", "network_fault_proxy.py",
              "agent_bench.py", "bench.py", "measurement.py", "workcell.py", "image_guided.py",
              "episode_cases.py", "order_protocol.py", "scene.xml", "../camera-capture-experiment/capture.py")


def retain(path, value):
    storage.create_file(path, storage.encoded(value))


def port():
    with socket.socket() as connection:
        connection.bind(("127.0.0.1", 0))
        return connection.getsockname()[1]


def tcp(origin, method, path, value=None, pinned=None, headers=None, timeout=15):
    """Exercise the same public wire as clients, never call service methods."""
    parsed = urlsplit(origin)
    request_headers = {}
    if pinned:
        request_headers.update({"X-Body-Id": pinned["body_id"],
                                "X-Adapter-Id": pinned["adapter_id"],
                                "X-Source-Sha256": pinned["source_sha256"]})
    content = None
    if value is not None:
        content = storage.encoded(value)
        request_headers["Content-Type"] = "application/json"
    request_headers.update(headers or {})
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=timeout)
    try:
        connection.request(method, path, content, request_headers)
        response = connection.getresponse()
        data = response.read(storage.MAX_BYTES + 1)
        return {"http_status": response.status, "body": storage.decode(data)}
    finally:
        connection.close()


class NetworkRGBPlanner:
    """Only public client calls and their hash-checked PNGs guide this policy."""

    def __init__(self, client, record):
        self.client, self.record = client, record
        self.actions = 0

    def observe(self):
        self.client.acquire()
        challenge = self.client.observe()
        packet = challenge["observation"]
        content = Path(challenge["image_path"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != packet["image_sha256"]:
            raise AssertionError("downloaded public image digest differs")
        if not packet["calibration"]["valid"]:
            raise AssertionError("RGB policy requires valid published calibration")
        located = vision.locate(vision.decode_png(content))
        block = vision.image_world_center(located["block"]["box"])
        pusher = vision.image_world_center(located["pusher"]["box"])
        self.record("deterministic_RGB_observation", challenge=challenge,
                    rgb_block_xy=block, rgb_pusher_xy=pusher)
        return challenge, block, pusher

    def dispatch(self, challenge, action, intent, target=None):
        self.actions += 1
        if self.actions > 64:
            raise AssertionError("deterministic RGB action budget exhausted")
        self.client.acquire()
        proposal = self.client.propose(challenge["challenge_id"], action, intent,
                                       *(target or (None, None)))
        result = self.client.dispatch(proposal["proposal_id"])
        self.record("deterministic_RGB_dispatch", proposal=proposal, result=result)
        if result["outcome"] != "executed":
            raise AssertionError("RGB action did not execute: " + str(result))
        return result

    def move(self, challenge, pusher, target, intent):
        delta = [target[i] - pusher[i] for i in (0, 1)]
        distance = math.hypot(*delta)
        if distance > .11:
            target = [pusher[i] + delta[i] * .11 / distance for i in (0, 1)]
        return self.dispatch(challenge, "move", intent, target)

    def position(self, center, intent):
        for _ in range(48):
            challenge, block, pusher = self.observe()
            if abs(block[1]) > .018:
                raise AssertionError("RGB block left supported axial corridor")
            if abs(block[0] - center) <= .012:
                return
            direction = 1 if center > block[0] else -1
            side = block[0] - direction * .065
            if direction * (block[0] - pusher[0]) < .050:
                target = [pusher[0], .135] if pusher[1] < .125 else [side, .135]
            elif abs(pusher[1]) > .006:
                target = [side, pusher[1]] if abs(pusher[0] - side) > .010 else [pusher[0], 0]
            else:
                gap = max(0, direction * (block[0] - pusher[0]) - .055)
                target = [pusher[0] + direction * min(.09, abs(center - block[0]) + gap), 0]
            if not -.32 <= target[0] <= .18:
                raise AssertionError("RGB target outside published workspace")
            self.move(challenge, pusher, target, intent)
        raise AssertionError("RGB positioning did not converge")

    def park(self):
        for _ in range(24):
            challenge, block, pusher = self.observe()
            if abs(pusher[0] + .3) <= .004 and abs(pusher[1]) <= .004:
                return challenge
            if pusher[0] > block[0] - .065 and pusher[1] < .125:
                target = [pusher[0], .135]
            elif pusher[0] > -.29:
                target = [-.3, pusher[1]]
            else:
                target = [-.3, 0]
            self.move(challenge, pusher, target, "deterministic RGB clear and park pusher")
        raise AssertionError("RGB parking did not converge")

    def cycle(self, job_id, zone):
        self.actions = 0
        self.client.acquire()
        started = self.client.start_job(job_id, zone)
        self.record("network_job_started", result=started)
        self.position((zone["x_min"] + zone["x_max"]) / 2, "deterministic RGB prepare part")
        measured = self.dispatch(self.park(), "measure", "measure image-guided placement")
        challenge, _, _ = self.observe()
        self.dispatch(challenge, "begin_reset", "start contact reset after measurement")
        self.position(-.12, "deterministic RGB contact return to home")
        reset = self.dispatch(self.park(), "finish_reset", "verify RGB part and pusher at home")
        return {"job_id": job_id, "zone": zone, "measurement": measured,
                "reset": reset, "actions": self.actions}


class NetworkBodyFaultTests(unittest.TestCase):
    def setUp(self):
        self.root = BASE / "output" / ("n9test-" + uuid.uuid4().hex[:10])
        self.root.mkdir(mode=0o700)
        self.server_root = self.root / "body"
        self.events, self.processes, self.logs, self.proxies, self.clients = [], [], [], [], []
        self.sources = {name: hashlib.sha256((BASE / name).read_bytes()).hexdigest()
                        for name in CORE_FILES}
        self.process = None
        self.client = None
        self.record("case_started", test_id=self.id(), preregistration="c976508",
                    planner="mechanical_deterministic_RGB_only_not_AI")

    def tearDown(self):
        for client in reversed(self.clients):
            client.close()
        for proxy in reversed(self.proxies):
            try:
                proxy.close()
            except Exception as exc:  # noqa: BLE001 - retain cleanup failures while reaping owned children.
                self.record("proxy_cleanup_error", error=str(exc))
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        for handle in self.logs:
            handle.close()
        result = self._outcome.result
        errors = [trace for test, trace in (*result.failures, *result.errors)
                  if test is self or getattr(test, "test_case", None) is self]
        unchanged = self.sources == {name: hashlib.sha256((BASE / name).read_bytes()).hexdigest()
                                    for name in CORE_FILES}
        retain(self.root / "conformance.json", {"test_id": self.id(), "passed": not errors and unchanged,
               "source_unchanged": unchanged, "source_sha256": self.sources,
               "scope": "real_loopback_TCP_native_body_mechanical_fault_matrix",
               "processes_reaped": all(p.poll() is not None for p in self.processes),
               "errors": errors, "events": self.events})
        self.assertTrue(unchanged, "network/core source changed during mechanical case")

    def record(self, kind, **value):
        event = {"sequence": len(self.events), "kind": kind, **value}
        retain(self.root / f"event-{len(self.events):04d}.json", event)
        self.events.append(event)
        return value

    def start(self, *, initialize=True, barrier=None):
        number = len(self.processes)
        chosen_port = getattr(self, "server_port", None) or port()
        self.server_port = chosen_port
        self.origin = f"http://127.0.0.1:{chosen_port}"
        log = (self.root / f"service-{number}.log").open("xb")
        self.logs.append(log)
        command = [sys.executable, str(BASE / "body_network.py"), "--root", str(self.server_root),
                   "--port", str(chosen_port)]
        if initialize:
            command += ["--initialize", "--diagnostic"]
        if barrier:
            command += ["--barrier", barrier]
        self.process = subprocess.Popen(command, stdout=log, stderr=log)
        self.processes.append(self.process)
        deadline = time.monotonic() + 20
        while True:
            try:
                reply = tcp(self.origin, "GET", "/identity", timeout=.5)
                if reply["http_status"] == 200:
                    self.identity = reply["body"]
                    break
            except (OSError, http.client.HTTPException, ValueError):
                pass
            if self.process.poll() is not None or time.monotonic() >= deadline:
                raise AssertionError("owned body service did not become ready; inspect retained service log")
            time.sleep(.05)
        self.record("service_ready", identity=self.identity, pid=self.process.pid,
                    initialize=initialize, barrier=barrier)
        return self.identity

    def stop(self, *, crash=False):
        process = self.process
        if process.poll() is None:
            if crash:
                process.kill()
            else:
                process.terminate()
            process.wait(timeout=8)
        self.record("owned_service_stopped", pid=process.pid, crashed=crash,
                    returncode=process.returncode)

    def connect(self, *, timeout=15, proxy=False):
        origin = self.origin
        if proxy:
            self.proxy = network_fault_proxy.FaultProxy(origin, self.root / "proxy")
            self.proxy.start()
            self.proxies.append(self.proxy)
            origin = self.proxy.origin
        self.client = body_client.BodyClient(self.root / "client", origin, timeout=timeout)
        self.clients.append(self.client)
        self.lease = self.client.acquire()
        self.record("client_acquired", lease=self.lease, via_proxy=proxy)
        return self.client

    def state(self):
        reply = tcp(self.origin, "GET", "/state", pinned=self.identity)
        self.assertEqual(reply["http_status"], 200, reply)
        return reply["body"]

    def generation(self):
        return self.state()["bench"]["generation"]

    def proposal(self):
        self.client.start_job("fault-job", ZONE)
        challenge = self.client.observe()
        proposal = self.client.propose(challenge["challenge_id"], "move",
                                       "mechanical network conformance motion", -.25, 0)
        self.record("public_proposal", challenge=challenge, proposal=proposal)
        return proposal

    def command(self, operation, arguments, *, token=None):
        return {**{k: self.identity[k] for k in ("protocol", "adapter_id", "body_id", "source_sha256")},
                **{k: self.lease[k] for k in ("client_id", "lease_id", "epoch")},
                "command_id": token or "matrix-" + uuid.uuid4().hex,
                "operation": operation, "arguments": arguments}

    def send(self, request, *, pinned=None):
        reply = tcp(self.origin, "POST", "/commands", request, pinned=pinned or self.identity)
        self.record("raw_public_command", request=request, reply=reply)
        return reply

    def retained_dispatch_request(self, command_id):
        # Fault assertions may inspect outgoing bytes. Policy never reads these.
        for path in (self.root / "client").rglob("*.json"):
            try:
                value = json.loads(path.read_bytes())
            except (ValueError, OSError):
                continue
            if isinstance(value, dict) and value.get("command_id") == command_id and value.get("operation") == "dispatch":
                return value
            if isinstance(value, dict) and isinstance(value.get("request"), dict):
                request = value["request"]
                if request.get("command_id") == command_id and request.get("operation") == "dispatch":
                    return request
        raise AssertionError("immutable outgoing dispatch request not found")

    def uncertain_dispatch(self, proposal):
        with self.assertRaises(body_client.Uncertain) as error:
            self.client.dispatch(proposal["proposal_id"])
        token = error.exception.command_id
        self.record("client_uncertain", command_id=token, status=self.client.status())
        return token

    def reconcile(self, token, *, expected=None):
        if expected in {"unknown", "not_seen"}:
            with self.assertRaises(body_client.Uncertain) as error:
                self.client.reconcile(token)
            self.assertEqual(error.exception.command_id, token)
            request = self.retained_dispatch_request(token)
            query = urlencode({**{key: request[key] for key in ("client_id", "lease_id", "epoch")},
                               "request_sha256": storage.sha(storage.encoded(request))})
            response = tcp(self.origin, "GET", "/commands/" + token + "?" + query, pinned=self.identity)
            self.assertEqual(response["http_status"], 200)
            reply = response["body"]
            self.assertEqual(reply["state"], expected)
            self.assertIn(token, self.client.status()["pending_command_ids"])
        else:
            reply = self.client.reconcile(token)
        self.record("read_only_reconciliation", command_id=token, reply=reply)
        return reply

    def assert_single_send(self, token):
        journal = storage.decode((self.root / "client" / "client.json").read_bytes())
        request = self.retained_dispatch_request(token)
        entry = journal["commands"][token]
        self.assertEqual(entry["send_count"], 1)
        self.assertEqual(entry["request_sha256"], storage.sha(storage.encoded(request)))
        self.record("independent_single_send_journal_check", command_id=token,
                    request_sha256=entry["request_sha256"], send_count=entry["send_count"])

    def journal_count(self):
        return len(list((self.server_root / "commands").glob("*/intent.json")))

    def barrier(self, expected):
        path = self.server_root / "barrier.json"
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if path.exists():
                value = storage.decode(path.read_bytes())
                self.assertEqual(value["barrier"], expected)
                self.assertEqual(value["pid"], self.process.pid)
                self.record("actual_process_barrier", evidence=value)
                return value
            if self.process.poll() is not None:
                break
            time.sleep(.02)
        raise AssertionError("owned service never reached crash barrier")

    def frozen_effects(self):
        """Independent persisted effects; no authority inferred from current scene."""
        roots = (self.server_root / "bench", self.server_root / "agent")
        return {str(path.relative_to(self.server_root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for root in roots for path in root.rglob("*") if path.is_file()
                and path.name != "app.lock"}

    def assert_no_private_pose(self, value):
        if isinstance(value, dict):
            self.assertFalse({"block_xyz", "pusher_xyz", "qpos", "qvel", "values", "native_pose"} & value.keys())
            for item in value.values():
                self.assert_no_private_pose(item)
        elif isinstance(value, list):
            for item in value:
                self.assert_no_private_pose(item)

    def score_native(self, receipt, zone):
        root = self.server_root / "bench"
        content = body.read_bytes(body.state_path(root, receipt["generation"]))
        self.assertEqual(body.sha(content), receipt["state_sha256"])
        state = body.decoded(content)
        manifest = storage.decode((root / "bench.json").read_bytes())
        self.assertEqual(hashlib.sha256((root / "model.xml").read_bytes()).hexdigest(), manifest["model_sha256"])
        model = body.mujoco.MjModel.from_xml_path(str(root / "model.xml"))
        data = body.mujoco.MjData(model)
        body.mujoco.mj_setState(model, data, body.np.asarray(state["values"]),
                              body.mujoco.mjtState.mjSTATE_INTEGRATION)
        body.mujoco.mj_forward(model, data)
        block = data.xpos[model.body("block").id].tolist()
        pusher = data.xpos[model.body("pusher").id].tolist()
        proof = {"role": "independent_native_read_only_scorer", "block_xyz": block,
                 "pusher_xyz": pusher, "generation": receipt["generation"],
                 "state_sha256": receipt["state_sha256"], "native_time_s": float(data.time)}
        self.record("independent_native_proof", proof=proof)
        self.assertTrue(zone["x_min"] <= block[0] <= zone["x_max"])
        self.assertTrue(zone["y_min"] <= block[1] <= zone["y_max"])
        self.assertTrue(.02 <= block[2] <= .08)
        self.assertFalse(body.np.any(data.xfrc_applied))
        return proof

    def test_01_successive_network_cycles_with_RGB_only_policy(self):
        self.start()
        self.connect()
        planner = NetworkRGBPlanner(self.client, self.record)
        first = planner.cycle("tcp-cycle-one", ZONE)
        second_zone = {"x_min": .035, "x_max": .105, "y_min": -.025, "y_max": .025}
        second = planner.cycle("tcp-cycle-two", second_zone)
        public = self.state()
        self.assert_no_private_pose(public)
        self.stop()
        root = self.server_root / "bench"
        manifest = storage.decode((root / "bench.json").read_bytes())
        self.assertIsNone(manifest["active_job"])
        self.assertEqual(len(manifest["jobs"]), 2)
        with sqlite3.connect((root / "measurements.sqlite").as_uri() + "?mode=ro", uri=True) as db:
            rows = db.execute("SELECT job_id,bench_id,generation,state_sha256,receipt_json FROM measurements ORDER BY job_id").fetchall()
        self.record("independent_SQLite_readback", rows=rows)
        self.assertEqual(len(rows), 2)
        previous_generation = 0
        previous_time = None
        for cycle in (first, second):
            job = manifest["jobs"][cycle["job_id"]]
            measured = job["measurement_receipt"]
            reset = job["reset_receipt"]
            self.assertEqual(job["phase"], "completed")
            self.assertEqual(job["started_generation"], previous_generation)
            if previous_time is not None:
                self.assertEqual(job["started_native_time_s"], previous_time)
            stage = self.score_native(measured, cycle["zone"])
            home = self.score_native(reset, {"x_min": -.16, "x_max": -.08, "y_min": -.03, "y_max": .03})
            self.assertLess(stage["native_time_s"], home["native_time_s"])
            self.assertAlmostEqual(home["pusher_xyz"][0], -.3, delta=.005)
            self.assertAlmostEqual(home["pusher_xyz"][1], 0, delta=.005)
            self.assertGreater(reset["reset_contact_samples"], 0)
            self.assertGreater(reset["reset_native_steps"], 0)
            self.assertEqual(measured["bench_id"], self.identity["body_id"])
            row = next(row for row in rows if row[0] == cycle["job_id"])
            self.assertEqual(json.loads(row[4]), measured)
            self.assertEqual(row[1:4], (measured["bench_id"], measured["generation"], measured["state_sha256"]))
            for key, item in (("measurement", cycle["measurement"]), ("reset", cycle["reset"])):
                self.assertEqual(item["outcome"], "executed", key)
            previous_generation, previous_time = job["completed_generation"], job["completed_native_time_s"]

    def test_02_bounded_delays_preserve_exact_effect(self):
        self.start()
        self.connect(proxy=True)
        proposal = self.proposal()
        for mode in ("delay_before", "delay_after"):
            if mode == "delay_after":
                challenge = self.client.observe()
                proposal = self.client.propose(challenge["challenge_id"], "move", "second delayed motion", -.2, 0)
            before = self.generation()
            self.proxy.arm(mode, operation="dispatch", delay_s=.15)
            started = time.monotonic()
            result = self.client.dispatch(proposal["proposal_id"])
            elapsed = time.monotonic() - started
            self.record("bounded_delay_result", mode=mode, elapsed_s=elapsed, result=result)
            self.assertGreaterEqual(elapsed, .13)
            self.assertLess(elapsed, 10)
            self.assertEqual(result["outcome"], "executed")
            self.assertEqual(self.generation(), before + 1)

    def test_03_drop_before_acceptance_stays_pending_until_fenced(self):
        self.start()
        self.connect(proxy=True)
        proposal = self.proposal()
        self.client.acquire(duration_s=2)
        before, count = self.generation(), self.journal_count()
        self.proxy.arm("drop_before", operation="dispatch")
        token = self.uncertain_dispatch(proposal)
        self.assertEqual(self.reconcile(token, expected="not_seen")["state"], "not_seen")
        with self.assertRaises((body_client.Refusal, body_client.Uncertain)):
            self.client.observe()
        self.assertEqual(self.journal_count(), count)
        time.sleep(2.1)
        self.assertEqual(self.reconcile(token)["state"], "not_accepted")
        self.assertEqual(self.generation(), before)
        self.assertEqual(self.journal_count(), count)
        self.assert_single_send(token)
        self.client.acquire()
        self.client.observe()

    def test_04_drop_after_effect_reconciles_without_resending(self):
        self.start()
        self.connect(proxy=True)
        proposal = self.proposal()
        before, count = self.generation(), self.journal_count()
        self.proxy.arm("drop_after", operation="dispatch")
        token = self.uncertain_dispatch(proposal)
        effects = self.frozen_effects()
        reconciled = self.reconcile(token)
        self.assertEqual(reconciled["state"], "completed")
        self.assertEqual(reconciled["result"]["outcome"], "executed")
        self.assertEqual(self.reconcile(token), reconciled)
        self.assertEqual(self.generation(), before + 1)
        self.assertEqual(self.journal_count(), count + 1)
        self.assertEqual(self.frozen_effects(), effects)
        self.assert_single_send(token)

    def test_05_exact_concurrent_duplicate_has_one_result_one_motion(self):
        self.start()
        self.connect()
        proposal = self.proposal()
        request = self.command("dispatch", {"proposal_id": proposal["proposal_id"]})
        before, count = self.generation(), self.journal_count()
        gate = threading.Barrier(3)

        def concurrent_send():
            gate.wait(timeout=5)
            started = time.monotonic()
            reply = tcp(self.origin, "POST", "/commands", request, self.identity)
            return {"started": started, "ended": time.monotonic(), "reply": reply}

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(concurrent_send) for _ in range(2)]
            gate.wait(timeout=5)
            calls = [future.result(timeout=20) for future in futures]
        replies = [call["reply"] for call in calls]
        self.assertLess(max(call["started"] for call in calls), min(call["ended"] for call in calls))
        self.record("actual_concurrent_duplicate", request=request, calls=calls)
        self.assertEqual(replies[0], replies[1])
        self.assertEqual(replies[0]["body"]["state"], "completed")
        self.assertEqual(replies[0]["body"]["result"]["outcome"], "executed")
        self.assertEqual(self.generation(), before + 1)
        self.assertEqual(self.journal_count(), count + 1)
        frozen = self.frozen_effects()
        self.assertEqual(self.send(request), replies[0])
        self.assertEqual(self.frozen_effects(), frozen)

    def test_06_conflicting_duplicate_refuses_without_second_effect(self):
        self.start()
        self.connect()
        proposal = self.proposal()
        request = self.command("dispatch", {"proposal_id": proposal["proposal_id"]})
        self.assertEqual(self.send(request)["body"]["state"], "completed")
        frozen, count = self.frozen_effects(), self.journal_count()
        conflict = copy.deepcopy(request)
        conflict["arguments"]["proposal_id"] = "proposal-" + uuid.uuid4().hex
        reply = self.send(conflict)
        self.assertIn(reply["body"]["state"], ("refused", "not_accepted"))
        self.assertEqual(self.frozen_effects(), frozen)
        self.assertEqual(self.journal_count(), count)

    def test_07_stale_image_proposal_cannot_dispatch_effect(self):
        self.start()
        self.connect()
        proposal = self.proposal()
        self.client.disturb("external-force", -.4, 50)
        before = self.generation()
        result = self.client.dispatch(proposal["proposal_id"])
        self.record("stale_public_dispatch", result=result)
        self.assertEqual(result["outcome"], "refused")
        self.assertEqual(self.generation(), before)
        self.assertGreater(result["next_observation"]["observation"]["generation"], 0)

    def test_08_delay_past_lease_expiry_never_admits_late_effect(self):
        self.start()
        self.connect(proxy=True)
        proposal = self.proposal()
        self.client.acquire(duration_s=.2)
        before, count = self.generation(), self.journal_count()
        self.client.timeout = .1
        self.proxy.arm("delay_before", operation="dispatch", delay_s=.5)
        token = self.uncertain_dispatch(proposal)
        time.sleep(.7)
        self.assertEqual(self.reconcile(token)["state"], "not_accepted")
        self.proxy.close()  # Drain actual late-forward threads before checking physical state.
        events = [storage.decode(path.read_bytes()) for path in sorted((self.root / "proxy" / "events").glob("*.json"))]
        self.assertTrue(any(event["kind"] == "forwarded" and event.get("command_id") == token for event in events))
        self.record("late_proxy_threads_drained", proxy_events=events)
        self.assertEqual(self.generation(), before)
        self.assertEqual(self.journal_count(), count)
        self.assert_single_send(token)
        self.record("late_admission_fenced", command_id=token)

    def test_09_identity_source_epoch_and_exclusive_lease_fence(self):
        self.start()
        self.connect()
        proposal = self.proposal()
        request = self.command("dispatch", {"proposal_id": proposal["proposal_id"]})
        frozen, count = self.frozen_effects(), self.journal_count()
        for key, value in (("body_id", uuid.uuid4().hex), ("adapter_id", uuid.uuid4().hex),
                           ("source_sha256", "0" * 64), ("epoch", self.identity["epoch"] + 1)):
            foreign = copy.deepcopy(request)
            foreign[key] = value
            reply = self.send(foreign)
            self.assertIn(reply["body"]["state"], ("not_accepted", "refused"))
        for key in ("body_id", "adapter_id", "source_sha256"):
            headers = dict(self.identity)
            headers[key] = "0" * (64 if key == "source_sha256" else 32)
            self.assertEqual(self.send(request, pinned=headers)["http_status"], 409)
        other = body_client.BodyClient(self.root / "other-client", self.origin)
        self.clients.append(other)
        with self.assertRaises(body_client.Refusal):
            other.acquire()
        old_lease = dict(self.lease)
        self.lease = self.client.acquire()
        self.assertNotEqual(old_lease["lease_id"], self.lease["lease_id"])
        self.assertEqual(self.send(request)["body"]["state"], "not_accepted")
        self.assertEqual(self.frozen_effects(), frozen)
        self.assertEqual(self.journal_count(), count)

    def test_10_process_restart_preserves_terminal_history_and_body(self):
        self.start()
        self.connect(proxy=True)
        proposal = self.proposal()
        self.proxy.arm("drop_after", operation="dispatch")
        token = self.uncertain_dispatch(proposal)
        original_identity = dict(self.identity)
        effects = self.frozen_effects()
        self.stop(crash=True)
        self.start(initialize=False)
        self.assertEqual(self.identity["body_id"], original_identity["body_id"])
        self.assertEqual(self.identity["adapter_id"], original_identity["adapter_id"])
        self.assertGreater(self.identity["epoch"], original_identity["epoch"])
        reply = self.reconcile(token)
        self.assertEqual(reply["state"], "completed")
        self.assertEqual(reply["recorded_epoch"], original_identity["epoch"])
        self.assertEqual(reply["result"]["outcome"], "executed")
        self.assertEqual(self.frozen_effects(), effects)
        self.assert_single_send(token)
        self.client.acquire()
        self.client.observe()

    def crash_at_boundary(self, boundary):
        self.start(barrier=boundary)
        self.connect()
        proposal = self.proposal()
        self.client.timeout = 1
        # Child SIGSTOP occurs before timeout and before this owned SIGKILL.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.client.dispatch, proposal["proposal_id"])
            barrier = self.barrier(boundary)
            self.stop(crash=True)
            with self.assertRaises(body_client.Uncertain) as error:
                future.result(timeout=5)
        self.assertEqual(error.exception.command_id, barrier["command_id"])
        token = error.exception.command_id
        self.record("crash_client_uncertain", command_id=token, boundary=boundary)
        effects = self.frozen_effects()
        self.start(initialize=False)
        return token, effects

    def test_11_restart_recovers_exact_lower_receipt_without_dispatch(self):
        token, effects = self.crash_at_boundary("after_dispatch")
        reply = self.reconcile(token)
        self.assertEqual(reply["state"], "completed")
        self.assertEqual(reply["result"]["outcome"], "executed")
        self.assertEqual(self.generation(), 1)
        self.assertEqual(self.frozen_effects(), effects)
        self.assertEqual(self.reconcile(token), reply)
        self.assertEqual(self.frozen_effects(), effects)
        self.assert_single_send(token)

    def test_12_accepted_without_lower_proof_and_client_restart_stays_unknown(self):
        self.start(barrier="before_dispatch")
        self.connect()
        proposal = self.proposal()
        self.client.close()
        # Both dispatch and resumed readback have distinct OS process lifetimes.
        script = """
import json,sys
from pathlib import Path
import body_client
client=body_client.BodyClient(Path(sys.argv[1]),sys.argv[2],timeout=3)
try:
    try:
        client.dispatch(sys.argv[3])
    except body_client.Uncertain as exc:
        print(json.dumps({'command_id':exc.command_id,'pending':client.status()['pending_command_ids']}),flush=True)
finally:
    client.close()
"""
        handle = (self.root / "client-before-crash.log").open("xb")
        self.logs.append(handle)
        child = subprocess.Popen([sys.executable, "-c", script, str(self.root / "client"),
                                  self.origin, proposal["proposal_id"]], cwd=BASE, stdout=handle, stderr=handle)
        self.processes.append(child)
        barrier = self.barrier("before_dispatch")
        self.stop(crash=True)
        child.wait(timeout=8)
        self.assertEqual(child.returncode, 0)
        token = barrier["command_id"]
        effects = self.frozen_effects()
        self.start(initialize=False)
        resume = """
import json,sys
from pathlib import Path
import body_client
client=body_client.BodyClient(Path(sys.argv[1]),sys.argv[2],timeout=3)
blocked={}
try:
    for name,call in [('reconcile',lambda:client.reconcile(sys.argv[3])),('observe',client.observe),('acquire',client.acquire)]:
        try:
            call()
            blocked[name]=False
        except body_client.Uncertain as exc:
            blocked[name]=exc.command_id==sys.argv[3]
    print(json.dumps({'blocked':blocked,'status':client.status(),'pid':__import__('os').getpid()}),flush=True)
finally:
    client.close()
"""
        completed = subprocess.run([sys.executable, "-c", resume, str(self.root / "client"), self.origin, token],
                                   cwd=BASE, capture_output=True, timeout=12, check=False)
        storage.create_file(self.root / "client-resume.stdout", completed.stdout)
        storage.create_file(self.root / "client-resume.stderr", completed.stderr)
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())
        resumed = json.loads(completed.stdout)
        self.record("actual_client_process_restart", old_pid=child.pid, public_result=resumed,
                    dispatch_client_exit_observed=child.poll() is not None,
                    dispatch_client_returncode=child.returncode, resumed_client_returncode=completed.returncode)
        self.assert_single_send(token)
        self.assertNotEqual(child.pid, resumed["pid"])
        self.assertEqual(resumed["blocked"], {"reconcile": True, "observe": True, "acquire": True})
        self.assertIn(token, resumed["status"]["pending_command_ids"])
        self.assertEqual(self.generation(), 0)
        self.assertEqual(self.state()["state"], "unknown")
        self.assertEqual(self.frozen_effects(), effects)
        # A fresh holder cannot bypass the server's independent unresolved-intent guard.
        fresh = body_client.BodyClient(self.root / "fresh-client", self.origin)
        self.clients.append(fresh)
        self.lease = fresh.acquire()
        count = self.journal_count()
        self.assertIn(self.send(self.command("observe", {}))["body"]["state"],
                      ("refused", "not_accepted", "unknown"))
        self.assertEqual(self.journal_count(), count)
        self.assertEqual(self.frozen_effects(), effects)


if __name__ == "__main__":
    unittest.main()
