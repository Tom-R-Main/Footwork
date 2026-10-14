"""SIM4 actual-process development conformance; no qualification-case discovery.

Each test keeps private inputs, public replies and owned server logs under output.
Offline retained-write faults are labeled separately from live process termination.
"""

import importlib.util
import json
import os
import signal
import socket
import subprocess
import sys
import time
import unittest
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONTROLLER = BASE / "controller.py"
TERMINAL = {"executed", "staged", "cancelled", "refused", "unknown"}


class ControllerProcessTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("controller_dev_runner", BASE / "episode_runner.py")
        self.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runner)
        self.body = self.runner.body
        self.work = self.body.directory(self.body.OUTPUT / ("c4" + uuid.uuid4().hex[:6]), create=True)
        self.root = self.body.directory(self.work / "r", create=True)
        self.control = self.body.directory(self.work / "c", create=True)
        self.processes = []
        self.handles = []
        self.evidence = []
        self.incarnation = None
        self.case = {"version": 1, "case_id": "controller-private-development", "max_actions": 8,
                     "scene": {"block_xy": [-.155, .006], "illumination_scale": 1,
                               "occlusion_fraction": 0, "camera_offset_x_m": 0},
                     "work_order": {"version": 1, "order_id": "controller-development-order",
                                    "project": {"namespace": "test", "project_id": "controller-development"},
                                    "part_id": "block", "target_zone": {
                                        "x_min": .18, "x_max": .26, "y_min": -.04, "y_max": .04}}}
        self.case_path = self.work / "case.json"
        self.initialized = False

    def tearDown(self):
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=4)
        for handle in self.handles:
            handle.close()
        result = self._outcome.result
        failed = any(test is self for test, _ in (*result.failures, *result.errors))
        self.body.create_file(self.work / "conformance.json", self.body.encoded({
            "test_id": self.id(), "passed": not failed, "scenario_kind": "actual_process",
            "events": self.evidence, "private_run_dir": str(self.work)}))

    def init(self):
        content = self.body.encoded(self.case)
        self.body.create_file(self.case_path, content)
        self.runner.initialize(self.root, str(self.case_path), self.body.sha(content))
        self.initialized = True

    def serve(self, *, delay=.15, pace=0, control=None, fault_script=None):
        if not self.initialized:
            self.init()
        control = control or self.control
        logfile = open(self.work / f"server-{len(self.processes)}.log", "xb")  # noqa: SIM115 - owned until tearDown
        os.chmod(logfile.name, 0o600)
        self.handles.append(logfile)
        process = subprocess.Popen([sys.executable, str(fault_script or CONTROLLER), "serve", "--run-dir", str(self.root),
                                    "--controller-dir", str(control), "--dispatch-delay-s", str(delay),
                                    "--pace-s", str(pace)], stdout=logfile, stderr=subprocess.STDOUT)
        self.processes.append(process)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self.fail(f"controller startup exited {process.returncode}; private logs: {self.work}")
            binding = control / "controller-binding.json"
            if binding.exists() and self.socket_location(control).exists():
                reply = self.client("health", control=control, allow_failure=True)
                if reply.get("phase") != "refused":
                    self.incarnation = reply["current_incarnation"]
                    return process, reply
            time.sleep(.03)
        self.fail(f"controller startup timed out; private logs: {self.work}")

    def socket_location(self, control=None):
        control = control or self.control
        binding = self.body.decoded(self.body.read_bytes(control / "controller-binding.json"))
        path = Path(binding["socket_path"])
        self.assertTrue(path.is_relative_to(self.body.OUTPUT))
        self.assertLess(len(os.fsencode(path)), 104)
        return path

    def client(self, command, *args, control=None, allow_failure=False):
        argv = [sys.executable, str(CONTROLLER), command, "--controller-dir", str(control or self.control), *map(str, args)]
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=12, check=False)
        try:
            reply = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"non-JSON public reply: {completed.stdout!r}; stderr={completed.stderr!r}: {exc}")
        self.evidence.append({"command": command, "args": list(map(str, args)), "exit_code": completed.returncode, "reply": reply})
        self.no_oracle(reply)
        if not allow_failure:
            self.assertEqual(completed.returncode, 0, reply)
        return reply

    def no_oracle(self, reply):
        serialized = json.dumps(reply)
        for forbidden in ("block_xyz", "pusher_xyz", "physical_condition_verified", "block_center_in_zone",
                          "qpos", "xpos", "illumination_scale", "occlusion_fraction", "camera_offset_x_m"):
            self.assertNotIn(forbidden, serialized)

    def observe(self):
        reply = self.client("observe")
        self.assertEqual(reply["phase"], "ready", reply)
        return reply["observation"]

    def proposal(self, packet, token, *, complete=False, target_x=None):
        proposal = {"version": 1, "run_dir": str(self.root), "generation": packet["generation"],
                    "image_sha256": packet["image_sha256"], "token": token,
                    "block_box": packet["perception"]["block_box"], "decision": "complete" if complete else "move"}
        if not complete:
            proposal["target"] = {"x": packet["perception"]["pusher_center_xy"][0] + .10 if target_x is None else target_x, "y": 0}
        content = self.body.encoded(proposal)
        path = self.work / f"proposal-{token}.json"
        self.body.create_file(path, content)
        return path, self.body.sha(content), proposal

    def submit(self, operation_id, proposal, *, allow_failure=False):
        path, digest = proposal[:2]
        return self.client("submit", "--operation-id", operation_id, "--proposal-file", path,
                           "--proposal-sha256", digest, "--expected-incarnation", self.incarnation,
                           allow_failure=allow_failure)

    def status(self, operation_id, *, allow_failure=False):
        return self.client("status", "--operation-id", operation_id, allow_failure=allow_failure)

    def cancel(self, operation_id):
        return self.client("cancel", "--operation-id", operation_id, "--expected-incarnation", self.incarnation,
                           allow_failure=True)

    def until(self, operation_id, phases=TERMINAL, *, timeout=12):
        deadline = time.monotonic() + timeout
        last = None
        while time.monotonic() < deadline:
            last = self.status(operation_id, allow_failure=True)
            if last.get("phase") in phases:
                return last
            time.sleep(.025)
        self.fail(f"phase timeout waiting for {phases}: {last}; private evidence: {self.work}")

    def stop(self, process, *, kill=False):
        process.send_signal(signal.SIGKILL if kill else signal.SIGTERM)
        process.wait(timeout=6)

    def snapshot_state(self):
        return {path.name: path.read_bytes() for path in self.root.glob("state-*.json")}

    def goal_path(self, operation_id):
        return self.control / f"goal-{self.body.sha(operation_id.encode())}.json"

    def test_submitter_exit_and_lost_reply_leave_one_durable_effect(self):
        self.serve(delay=.4)
        proposal = self.proposal(self.observe(), "lost-reply")
        # A genuine socket caller sends then closes without consuming the server reply.
        request = {"command": "submit", "operation_id": "disconnect", "proposal_file": str(proposal[0]),
                   "proposal_sha256": proposal[1], "expected_incarnation": self.incarnation}
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as caller:
            caller.settimeout(2)
            caller.connect(str(self.socket_location()))
            caller.sendall(json.dumps(request).encode() + b"\n")
        self.evidence.append({"scenario": "actual_socket_closed_before_reply", "request": request})
        final = self.until("disconnect")
        self.assertEqual(final["phase"], "executed", final)
        state = self.snapshot_state()
        repeated = self.submit("disconnect", proposal)
        self.assertEqual(repeated["phase"], "executed")
        self.assertEqual(self.snapshot_state(), state)
        changed = self.proposal(self.observe(), "conflict")
        refused = self.submit("disconnect", changed, allow_failure=True)
        self.assertIn(refused["phase"], {"refused", "unknown"})
        self.assertEqual(self.snapshot_state(), state)

    def test_active_return_reports_busy_without_native_pose(self):
        self.serve(delay=.2, pace=.002)
        self.submit("active", self.proposal(self.observe(), "active"))
        running = self.until("active", {"running"})
        self.assertEqual(running["phase"], "running")
        busy = self.client("observe", allow_failure=True)
        self.assertEqual(busy["phase"], "busy", busy)
        self.assertIsNone(busy.get("observation"))
        self.assertEqual(self.until("active")["phase"], "executed")

    def test_queued_cancellation_does_not_dispatch_or_increment_generation(self):
        self.serve(delay=2)
        packet = self.observe()
        state = self.snapshot_state()
        self.submit("queued", self.proposal(packet, "queued"))
        self.cancel("queued")
        terminal = self.until("queued")
        self.assertEqual(terminal["phase"], "cancelled", terminal)
        self.assertEqual(self.observe()["generation"], packet["generation"])
        self.assertEqual(self.snapshot_state(), state)
        self.assertFalse(list(self.root.glob("op-*.json")))

    def test_running_cancel_verifies_stop_after_real_native_progress(self):
        self.serve(delay=.1, pace=.003)
        packet = self.observe()
        self.submit("cancel-running", self.proposal(packet, "cancel-running"))
        self.until("cancel-running", {"running"})
        time.sleep(.18)  # Pace keeps motion active; require the retained progress evidence below.
        requested = self.cancel("cancel-running")
        self.assertTrue(requested["cancel_requested"])
        terminal = self.until("cancel-running")
        self.assertEqual(terminal["phase"], "cancelled", terminal)
        self.assertEqual(terminal["cancellation_stage"], "during_motion")
        self.assertTrue(terminal["stop_evidence"]["stop_verified"])
        self.assertTrue(terminal["stop_evidence"]["state_retained"])
        self.assertGreater(terminal["stop_evidence"]["native_steps_before_cancel"], 0)
        current = self.observe()
        self.assertGreater(current["generation"], packet["generation"])
        self.assertEqual(terminal["stop_evidence"]["retained_generation"], current["generation"])
        self.assertEqual(terminal["stop_evidence"]["retained_state_sha256"], current["state_sha256"])
        state = self.snapshot_state()
        self.cancel("cancel-running")
        self.assertEqual(self.snapshot_state(), state)

    def test_controller_death_after_cancel_request_never_claims_verified_stop(self):
        process, _ = self.serve(delay=.1, pace=.003)
        proposal = self.proposal(self.observe(), "cancel-interrupted")
        self.submit("cancel-interrupted", proposal)
        self.until("cancel-interrupted", {"running"})
        time.sleep(.18)
        self.assertTrue(self.cancel("cancel-interrupted")["cancel_requested"])
        self.stop(process, kill=True)
        state = self.snapshot_state()
        self.serve(delay=.1, pace=.003)
        terminal = self.status("cancel-interrupted", allow_failure=True)
        self.assertEqual(terminal["phase"], "unknown", terminal)
        self.assertNotEqual(terminal.get("historical_outcome"), "cancelled")
        self.assertFalse(terminal.get("stop_evidence", {}).get("stop_verified", False))
        self.assertEqual(self.submit("cancel-interrupted", proposal, allow_failure=True)["phase"], "unknown")
        self.assertEqual(self.snapshot_state(), state)

    def test_late_cancellation_preserves_terminal_effect(self):
        self.serve()
        self.submit("late", self.proposal(self.observe(), "late"))
        final = self.until("late")
        self.assertEqual(final["phase"], "executed")
        state = self.snapshot_state()
        retained_goal = self.goal_path("late").read_bytes()
        late = self.cancel("late")
        self.assertEqual(late["phase"], "executed", late)
        self.assertEqual(self.snapshot_state(), state)
        self.assertEqual(self.goal_path("late").read_bytes(), retained_goal)

    def test_lifetime_excludes_second_owner_and_legacy_cli(self):
        self.serve()
        other = self.body.directory(self.work / "d", create=True)
        second = subprocess.run([sys.executable, str(CONTROLLER), "serve", "--run-dir", str(self.root),
                                 "--controller-dir", str(other)], capture_output=True, text=True, timeout=8, check=False)
        self.assertNotEqual(second.returncode, 0)
        self.evidence.append({"scenario": "second_owner", "exit_code": second.returncode, "stdout": second.stdout})
        legacy = subprocess.run([sys.executable, str(BASE / "workcell.py"), "observe", "--run-dir", str(self.root)],
                                capture_output=True, text=True, timeout=8, check=False)
        self.assertNotEqual(legacy.returncode, 0)
        self.evidence.append({"scenario": "legacy_exclusion", "exit_code": legacy.returncode, "stdout": legacy.stdout})
        self.assertEqual(self.observe()["generation"], 0)

    def test_sigkill_restart_new_incarnation_unknown_and_no_replay(self):
        process, health = self.serve(delay=.1, pace=.003)
        proposal = self.proposal(self.observe(), "kill-running")
        self.submit("kill-running", proposal)
        self.until("kill-running", {"running"})
        self.stop(process, kill=True)
        state = self.snapshot_state()
        _, restart = self.serve(delay=.1, pace=.003)
        self.assertNotEqual(restart["current_incarnation"], health["current_incarnation"])
        status = self.status("kill-running", allow_failure=True)
        self.assertEqual(status["phase"], "unknown", status)
        duplicate = self.submit("kill-running", proposal, allow_failure=True)
        self.assertEqual(duplicate["phase"], "unknown", duplicate)
        self.assertEqual(self.snapshot_state(), state)
        blocked = self.client("observe", allow_failure=True)
        self.assertIn(blocked["phase"], {"blocked", "unknown", "refused"})
        self.assertIsNone(blocked.get("observation"))

    def test_malformed_id_digest_and_stale_proposal_refuse_without_effect(self):
        self.serve()
        packet = self.observe()
        first = self.proposal(packet, "valid")
        state = self.snapshot_state()
        for operation_id, proposal in (("../escape", first), ("digest-bad", (first[0], "0" * 64))):
            with self.subTest(operation_id=operation_id):
                refused = self.submit(operation_id, proposal, allow_failure=True)
                self.assertEqual(refused["phase"], "refused", refused)
        self.assertEqual(self.snapshot_state(), state)
        self.submit("advance", first)
        self.assertEqual(self.until("advance")["phase"], "executed")
        state = self.snapshot_state()
        stale_proposal = self.proposal(packet, "stale")
        stale = self.submit("stale", stale_proposal, allow_failure=True)
        if stale["phase"] in {"accepted", "running"}:
            stale = self.until("stale")
        self.assertIn(stale["phase"], {"refused", "unknown"}, stale)
        self.assertEqual(self.snapshot_state(), state)

    def simulate_lost_controller_terminal_write(self, operation_id, *, phase="running"):
        """Labeled offline retained-write fault; native engine/process was not mocked."""
        path = self.goal_path(operation_id)
        original = path.read_bytes()
        self.body.create_file(self.work / f"original-goal-{operation_id}.json", original)
        goal = self.body.decoded(original)
        goal["phase"] = phase
        if phase == "unknown":
            goal["reason"] = "lower effect is unresolved"
        for field in ("receipt", "finished_at", "stop_evidence", "cancellation_stage", "reconciled"):
            goal.pop(field, None)
        self.body.utils.persist(path, goal)
        self.evidence.append({"scenario": "offline_retained_write_fault", "fault": "controller_terminal_write_lost",
                              "operation_id": operation_id, "saved_fallback_phase": phase, "native_receipts_unchanged": True})

    def test_exact_lower_receipt_reconciles_lost_controller_final_write(self):
        process, initial = self.serve()
        proposal = self.proposal(self.observe(), "reconcile")
        self.submit("reconcile", proposal)
        self.assertEqual(self.until("reconcile")["phase"], "executed")
        self.stop(process, kill=True)
        state = self.snapshot_state()
        self.simulate_lost_controller_terminal_write("reconcile")
        _, health = self.serve()
        self.assertNotEqual(initial["current_incarnation"], health["current_incarnation"])
        recovered = self.status("reconcile")
        self.assertEqual(recovered["phase"], "executed", recovered)
        self.assertEqual(recovered["accepted_incarnation"], initial["current_incarnation"])
        self.assertEqual(self.submit("reconcile", proposal)["phase"], "executed")
        self.assertEqual(self.snapshot_state(), state)

    def test_saved_unknown_fallback_reconciles_exact_terminal_lower_history(self):
        process, initial = self.serve()
        proposal = self.proposal(self.observe(), "fallback-unknown")
        self.submit("fallback-unknown", proposal)
        final = self.until("fallback-unknown")
        self.assertEqual(final["phase"], "executed")
        self.stop(process, kill=True)
        state = self.snapshot_state()
        lower = {path.name: path.read_bytes() for pattern in ("vision-op-*.json", "op-*.json")
                 for path in self.root.glob(pattern)}
        self.simulate_lost_controller_terminal_write("fallback-unknown", phase="unknown")
        self.serve()
        recovered = self.status("fallback-unknown", allow_failure=True)
        self.assertEqual(recovered["phase"], "executed", recovered)
        self.assertNotIn("reason", recovered)
        self.assertEqual(recovered["prior_reason"], "lower effect is unresolved")
        self.assertEqual(recovered["accepted_incarnation"], initial["current_incarnation"])
        self.assertEqual(recovered["receipt"]["after_state_sha256"], final["receipt"]["after_state_sha256"])
        self.assertEqual(recovered["receipt"]["image_sha256"], final["receipt"]["image_sha256"])
        self.assertEqual(self.submit("fallback-unknown", proposal)["phase"], "executed")
        self.assertEqual(self.snapshot_state(), state)
        self.assertEqual({path.name: path.read_bytes() for pattern in ("vision-op-*.json", "op-*.json")
                          for path in self.root.glob(pattern)}, lower)

    def test_satisfied_current_scene_cannot_replace_missing_execution_history(self):
        self.case["scene"]["block_xy"] = [.195, .006]
        process, _ = self.serve()
        proposal = self.proposal(self.observe(), "history-missing", complete=True)
        self.submit("history-missing", proposal)
        self.assertEqual(self.until("history-missing")["phase"], "staged")
        self.stop(process, kill=True)
        state = self.snapshot_state()
        self.assertTrue(self.body.observation(self.root)["physical_condition_verified"])
        self.assertTrue((self.root / "order.json").exists())
        self.simulate_lost_controller_terminal_write("history-missing")
        archive = self.body.directory(self.work / "a", create=True)
        removed = []
        for pattern in ("vision-op-*.json", "op-*.json"):
            for receipt in self.root.glob(pattern):
                removed.append(receipt.name)
                receipt.rename(archive / receipt.name)
        self.evidence.append({"scenario": "offline_retained_write_fault", "fault": "lower_history_unavailable",
                              "archived_receipts": removed, "current_placement_and_order_unchanged": True})
        self.serve()
        recovered = self.status("history-missing", allow_failure=True)
        self.assertEqual(recovered["phase"], "unknown", recovered)
        self.assertNotEqual(recovered.get("historical_outcome"), "staged")
        self.assertEqual(self.submit("history-missing", proposal, allow_failure=True)["phase"], "unknown")
        self.assertEqual(self.snapshot_state(), state)

    def test_accepted_undispatched_restart_never_replays_and_old_incarnation_refuses(self):
        process, original = self.serve(delay=3)
        proposal = self.proposal(self.observe(), "undispatched")
        accepted = self.submit("undispatched", proposal)
        self.assertEqual(accepted["phase"], "accepted", accepted)
        self.stop(process, kill=True)
        state = self.snapshot_state()
        _, health = self.serve(delay=0)
        self.assertNotEqual(original["current_incarnation"], health["current_incarnation"])
        self.assertEqual(self.status("undispatched", allow_failure=True)["phase"], "unknown")
        self.assertFalse(list(self.root.glob("op-*.json")))
        stale_submit = self.client("submit", "--operation-id", "old-owner", "--proposal-file", proposal[0],
                                   "--proposal-sha256", proposal[1], "--expected-incarnation",
                                   original["current_incarnation"], allow_failure=True)
        self.assertEqual(stale_submit["phase"], "refused", stale_submit)
        stale_cancel = self.client("cancel", "--operation-id", "undispatched", "--expected-incarnation",
                                   original["current_incarnation"], allow_failure=True)
        self.assertEqual(stale_cancel["phase"], "refused", stale_cancel)
        self.assertEqual(self.snapshot_state(), state)

    def test_changed_case_and_malformed_controller_binding_refuse_reuse(self):
        process, _ = self.serve()
        self.stop(process, kill=True)
        original = self.case_path.read_bytes()
        self.case_path.write_bytes(original + b" ")
        restarted = subprocess.run([sys.executable, str(CONTROLLER), "serve", "--run-dir", str(self.root),
                                    "--controller-dir", str(self.control)], capture_output=True, text=True,
                                   timeout=8, check=False)
        self.assertNotEqual(restarted.returncode, 0)
        self.evidence.append({"scenario": "changed_case_restart", "exit_code": restarted.returncode,
                              "stdout": restarted.stdout})
        self.case_path.write_bytes(original)
        binding = self.control / "controller-binding.json"
        original_binding = binding.read_bytes()
        self.body.create_file(self.work / "original-binding.json", original_binding)
        binding.write_bytes(b'{"version":1}')
        restarted = subprocess.run([sys.executable, str(CONTROLLER), "serve", "--run-dir", str(self.root),
                                    "--controller-dir", str(self.control)], capture_output=True, text=True,
                                   timeout=8, check=False)
        self.assertNotEqual(restarted.returncode, 0)
        self.evidence.append({"scenario": "offline_retained_write_fault", "fault": "malformed_controller_binding",
                              "exit_code": restarted.returncode, "stdout": restarted.stdout})
        changed_source = self.body.decoded(original_binding)
        changed_source["controller_sha256"] = "0" * 64
        binding.write_bytes(self.body.encoded(changed_source))
        restarted = subprocess.run([sys.executable, str(CONTROLLER), "serve", "--run-dir", str(self.root),
                                    "--controller-dir", str(self.control)], capture_output=True, text=True,
                                   timeout=8, check=False)
        self.assertNotEqual(restarted.returncode, 0)
        self.evidence.append({"scenario": "offline_retained_write_fault", "fault": "changed_controller_source_binding",
                              "exit_code": restarted.returncode, "stdout": restarted.stdout})
        self.assertFalse(list(self.root.glob("op-*.json")))

    def test_current_state_corruption_preserves_history_and_blocks_new_effects(self):
        process, health = self.serve()
        self.submit("historic", self.proposal(self.observe(), "historic"))
        self.assertEqual(self.until("historic")["phase"], "executed")
        packet = self.observe()
        next_proposal = self.proposal(packet, "blocked-current")
        path = self.body.state_path(self.root, packet["generation"])
        self.body.create_file(self.work / "original-current-state.json", path.read_bytes())
        path.write_bytes(b"{current state corrupted")
        self.evidence.append({"scenario": "offline_retained_write_fault", "fault": "current_state_corrupt",
                              "historical_receipts_unchanged": True})
        state = self.snapshot_state()
        historic = self.status("historic", allow_failure=True)
        self.assertEqual(historic["historical_outcome"], "executed", historic)
        self.assertIn(historic["current_health"], {"blocked", "unknown"}, historic)
        self.assertIn(self.client("observe", allow_failure=True)["phase"], {"blocked", "unknown", "refused"})
        rejected = self.submit("blocked-current", next_proposal, allow_failure=True)
        self.assertEqual(rejected["phase"], "refused", rejected)
        self.assertFalse(self.goal_path("blocked-current").exists())
        self.assertEqual(self.snapshot_state(), state)
        self.stop(process, kill=True)
        _, restart = self.serve()
        self.assertNotEqual(restart["current_incarnation"], health["current_incarnation"])
        historic = self.status("historic", allow_failure=True)
        self.assertEqual(historic["historical_outcome"], "executed", historic)
        self.assertIn(historic["current_health"], {"blocked", "unknown"}, historic)
        rejected = self.submit("blocked-after-restart", next_proposal, allow_failure=True)
        self.assertEqual(rejected["phase"], "refused", rejected)
        self.assertEqual(self.snapshot_state(), state)

    def test_live_retained_binding_tamper_blocks_health_and_new_acceptance(self):
        self.serve()
        proposal = self.proposal(self.observe(), "live-binding")
        state = self.snapshot_state()
        binding = self.control / "controller-binding.json"
        original = binding.read_bytes()
        self.body.create_file(self.work / "original-live-binding.json", original)
        changed = self.body.decoded(original)
        changed["controller_sha256"] = "0" * 64
        binding.write_bytes(self.body.encoded(changed))
        self.evidence.append({"scenario": "live_retained_binding_fault", "fault": "changed_source_binding",
                              "runtime_source_and_native_state_unchanged": True})
        health = self.client("health", allow_failure=True)
        self.assertEqual(health["phase"], "refused", health)
        refused = self.submit("live-binding", proposal, allow_failure=True)
        self.assertEqual(refused["phase"], "refused", refused)
        self.assertFalse(self.goal_path("live-binding").exists())
        self.assertEqual(self.snapshot_state(), state)

    def test_shutdown_join_timeout_never_releases_ownership_to_live_writer(self):
        self.case["scene"]["block_xy"] = [.195, .006]
        # This subprocess fault changes timing only: actual dynamics and the public checker run.
        # It establishes process/lock ownership; it is explicitly not native stop evidence.
        script = self.work / "slow-checker-fault.py"
        self.body.create_file(script, f'''import importlib.util
import sys
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location("controller_shutdown_fault", {str(CONTROLLER)!r})
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
work = Path({str(self.work)!r})
original_check = controller.body.artifact_check
original_execute = controller.Controller.execute
original_join = controller.threading.Thread.join

def slow_check(*args, **kwargs):
    if not (work / "checker-entered").exists():
        controller.body.create_file(work / "checker-entered", b"read-only checker timing fault\\n")
        time.sleep(2)
    return original_check(*args, **kwargs)

def tracked_execute(self, goal):
    try:
        return original_execute(self, goal)
    finally:
        controller.body.create_file(work / "worker-finished", b"writer thread finished\\n")

def short_join(self, timeout=None):
    if self.name == "native-controller-operation" and timeout == 15:
        timeout = .15
    return original_join(self, timeout)

controller.body.artifact_check = slow_check
controller.Controller.execute = tracked_execute
controller.threading.Thread.join = short_join
sys.exit(controller.main())
'''.encode())
        process, _ = self.serve(delay=0, fault_script=script)
        proposal = self.proposal(self.observe(), "slow-checker", complete=True)
        self.submit("slow-checker", proposal)
        deadline = time.monotonic() + 5
        while not (self.work / "checker-entered").exists() and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertTrue((self.work / "checker-entered").exists(), self.work)
        self.evidence.append({"scenario": "actual_process_with_labeled_timing_fault",
                              "fault": "read_only_checker_sleep_2s_worker_join_budget_0.15s",
                              "native_stop_proof": False})
        process.send_signal(signal.SIGTERM)
        probe = '''import fcntl,json,os,sys
result = {}
for path in sys.argv[1:]:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result[path] = "available"
        except BlockingIOError:
            result[path] = "owned"
    finally:
        os.close(fd)
print(json.dumps(result))
'''
        deadline = time.monotonic() + 5
        while process.poll() is None and time.monotonic() < deadline:
            locks = subprocess.run([sys.executable, "-c", probe, str(self.root / "lock"), str(self.control / "lock")],
                                   capture_output=True, text=True, timeout=3, check=False)
            self.assertEqual(locks.returncode, 0, locks.stderr)
            ownership = json.loads(locks.stdout)
            live_writer = process.poll() is None and not (self.work / "worker-finished").exists()
            self.evidence.append({"scenario": "shutdown_ownership_probe", "live_unfinished_writer": live_writer,
                                  "locks": ownership})
            if live_writer:
                self.assertTrue(all(value == "owned" for value in ownership.values()), ownership)
            time.sleep(.02)
        process.wait(timeout=5)
        completed_writer = (self.work / "worker-finished").exists()
        self.serve(delay=0)
        history = self.status("slow-checker", allow_failure=True)
        self.assertEqual(history["phase"], "staged" if completed_writer else "unknown", history)
        self.assertFalse(history.get("stop_evidence", {}).get("stop_verified", False))
        state = self.snapshot_state()
        repeated = self.submit("slow-checker", proposal, allow_failure=True)
        self.assertEqual(repeated["phase"], history["phase"])
        self.assertEqual(self.snapshot_state(), state)

    def test_image_feedback_contact_and_conditional_saved_json(self):
        self.serve(delay=0)
        contacts = 0
        for step in range(8):
            packet = self.observe()
            center = packet["perception"]["block_center_xy"]
            zone = packet["task_intent"]["target_zone"]
            inside = zone["x_min"] + .005 <= center[0] <= zone["x_max"] - .005 and zone["y_min"] + .005 <= center[1] <= zone["y_max"] - .005
            proposal = self.proposal(packet, f"loop-{step}", complete=inside,
                                     target_x=min(.17, packet["perception"]["pusher_center_xy"][0] + .10))
            self.submit(f"loop-{step}", proposal)
            final = self.until(f"loop-{step}")
            if inside:
                self.assertEqual(final["phase"], "staged", final)
                expected = self.root / "expected-order.json"
                checked = subprocess.run([str(BASE.parents[1] / "jevdual/.venv/bin/footwork"), "check-artifact",
                                          str(self.root / "order.json"), "--expected-file", str(expected),
                                          "--expected-sha256", self.body.sha(expected.read_bytes())],
                                         capture_output=True, text=True, timeout=8, check=False)
                self.assertEqual(checked.returncode, 0, checked.stdout)
                self.assertTrue(json.loads(checked.stdout)["ok"])
                self.assertGreater(contacts, 0)
                self.evidence.append({"scenario": "independent_public_footwork_check", "reply": json.loads(checked.stdout)})
                state = self.snapshot_state()
                order = self.root / "order.json"
                self.body.create_file(self.work / "original-saved-order.json", order.read_bytes())
                order.write_bytes(b"changed saved computer result")
                self.evidence.append({"scenario": "offline_retained_write_fault", "fault": "saved_order_tampered",
                                      "historical_staging_receipts_and_native_state_unchanged": True})
                historical = self.status(f"loop-{step}", allow_failure=True)
                self.assertEqual(historical["historical_outcome"], "staged", historical)
                self.assertEqual(historical["current_health"], "blocked", historical)
                self.assertFalse(historical["current_software_artifact_check"]["ok"])
                new_proposal = self.proposal(packet, "after-artifact-tamper", complete=True)
                refused = self.submit("after-artifact-tamper", new_proposal, allow_failure=True)
                self.assertEqual(refused["phase"], "refused", refused)
                self.assertFalse(self.goal_path("after-artifact-tamper").exists())
                self.assertEqual(self.snapshot_state(), state)
                return
            self.assertEqual(final["phase"], "executed", final)
            contacts += final["receipt"]["contact_statistics"]["pusher_block_contact_samples"]
        self.fail("independent bounded RGB feedback loop did not stage")


if __name__ == "__main__":
    unittest.main()
