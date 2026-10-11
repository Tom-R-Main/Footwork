"""Deterministic real-socket workbench conformance; never model qualification."""
import json
import threading
import time
import unittest
import uuid
from unittest import mock

import body_client
import body_network
import network_operator_runtime as runtime
import order_protocol as protocol


def action(name="stop", x=None, y=None):
    return {"action": name, "target_x": x, "target_y": y, "intent": "Declared deterministic network conformance"}


class NetworkOperatorTests(unittest.TestCase):
    def setUp(self):
        self.root = runtime.BASE / "output" / ("net-operator-test-" + uuid.uuid4().hex[:10])
        self.body_root = self.root / "body"
        body_network.initialize(self.body_root, diagnostic_enabled=True)
        self.service = body_network.BodyService(self.body_root).start()
        self.host = self.root / "host"
        self.patcher = mock.patch.object(runtime, "sources", return_value={"diagnostic_source": "fixed"})
        self.patcher.start()
        runtime.initialize(self.host, self.service.origin)
        self.op = None

    def tearDown(self):
        if self.op:
            self.op.close()
        if self.service:
            self.service.close()
        failed = any(test is self for test, _ in (*self._outcome.result.failures, *self._outcome.result.errors))
        protocol.create_file(self.root / "conformance.json", protocol.encoded({"test_id": self.id(), "passed": not failed,
            "policy": "explicitly_fake_diagnostic", "host_state": body_client.read_journal(self.host / "operator.json")}))
        self.patcher.stop()

    def open(self, policy=None, worker=False):
        self.op = runtime.Operator(self.host, policy or (lambda *_: (action(), {})), start_worker=worker)
        return self.op

    def job(self, name="one", **changes):
        return {"job_id": name, "label": "Network inspection", "target": "A", "disturbance_test": False, **changes}

    def wait(self, predicate, timeout=15):
        until = time.monotonic() + timeout
        while time.monotonic() < until and not predicate():
            time.sleep(.02)
        self.assertTrue(predicate())

    def test_pause_wins_while_resume_waits_for_actual_socket_status(self):
        op = self.open()
        op.pause()
        entered, release = threading.Event(), threading.Event()
        original = self.service.state
        errors = []
        def delayed_status():
            entered.set()
            release.wait(5)
            return original()
        def resume():
            try:
                op.resume()
            except protocol.Refusal as exc:
                errors.append(str(exc))
        with mock.patch.object(self.service, "state", side_effect=delayed_status):
            thread = threading.Thread(target=resume)
            thread.start()
            self.assertTrue(entered.wait(5))
            op.pause()
            release.set()
            thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(op.state()["runner_status"], "paused")
        self.assertTrue(errors)
        self.assertEqual(len(op._journal()["commands"]), 0)
        self.assertEqual(self.service.body.status()["generation"], 0)

    def test_two_successive_jobs_and_disturbance_using_declared_replay(self):
        audit = runtime.BASE.parent.parent / "jevdual/results/agent-visual-bench-20261011/AI-action-audit.json"
        proposals = iter(json.loads(audit.read_text())["actions"])
        def policy(*_):
            recorded = next(proposals)["proposal"]
            return {k: recorded[k] for k in ("action", "target_x", "target_y", "intent")}, {}
        op = self.open(policy)
        op.enqueue(self.job())
        op.enqueue(self.job("two", target="B", disturbance_test=True))
        for _ in range(40):
            if not op._step():
                break
        self.assertEqual([j["status"] for j in op.state()["jobs"]], ["completed", "completed"])
        self.assertEqual(op.state()["usage"]["calls"], 29)
        self.assertTrue(all(j["measurement"]["orange_pixel_count"] > 0 for j in op.state()["jobs"]))
        self.assertTrue(all(j["reset"]["reset_contact_samples"] > 0 for j in op.state()["jobs"]))
        self.assertEqual(len(self.service.body.status()["jobs"]), 2)
        self.assertIsNone(op.m["stage"])
        self.assertLess(len(op._journal()["commands"]), runtime.MAX_COMMANDS)

    def test_lost_dispatch_disconnect_recovery_and_explicit_resume(self):
        decisions = iter((action("move", -.25, 0), action()))
        seen = []
        def policy(challenge, *_):
            seen.append(challenge["observation"]["generation"])
            return next(decisions), {}
        op = self.open(policy)
        op.enqueue(self.job())
        op.fault({"mode": "drop_after", "delay_s": 0})
        self.assertFalse(op._step())
        token = op.state()["recovery"]["command_id"]
        self.assertEqual(op.state()["recovery"]["state"], "uncertain")
        self.assertEqual(self.service.body.status()["generation"], 1)
        before = len(op._journal()["commands"])
        op.disconnect()
        with self.assertRaises(protocol.Refusal):
            op.reconcile()
        op.reconnect()
        self.assertEqual(len(op._journal()["commands"]), before)
        op.reconcile()
        self.assertEqual(op.state()["recovery"]["state"], "recovered")
        self.assertEqual(op.state()["runner_status"], "paused")
        self.assertEqual(op.m["applied_commands"].count(token), 1)
        self.assertEqual(self.service.body.status()["generation"], 1)
        with self.assertRaises(protocol.Refusal):
            op.reconcile()
        op.resume()
        self.assertFalse(op._step())
        self.assertEqual(seen, [0, 1])
        self.assertEqual(op._journal()["commands"][token]["send_count"], 1)

    def test_unknown_start_observe_and_proposal_settle_without_replay_or_old_decision(self):
        for index, operation in enumerate(("start_job", "observe", "propose")):
            with self.subTest(operation=operation):
                if index:
                    self.op.close()
                    self.op = None
                    self.service.close()
                    next_body = self.root / ("body-" + operation)
                    body_network.initialize(next_body, diagnostic_enabled=True)
                    self.service = body_network.BodyService(next_body).start()
                    self.host = self.root / ("host-" + operation)
                    runtime.initialize(self.host, self.service.origin)
                op = self.open(lambda *_: (action("move", -.25, 0), {}))
                op.enqueue(self.job(operation))
                op.link.arm("drop_after", operation=operation, delay_s=0)
                self.assertFalse(op._step())
                self.assertEqual(op.state()["recovery"]["operation"], operation)
                before = len(op._journal()["commands"])
                op.reconcile()
                self.assertEqual(op.state()["runner_status"], "paused")
                self.assertEqual(self.service.body.status()["generation"], 0)
                self.assertEqual(len(op._journal()["commands"]), before)
                self.assertIsNone(op.m["stage"])

    def test_restart_recovers_exact_queue_stage_once_from_historical_receipt(self):
        op = self.open(lambda *_: (action("move", -.25, 0), {}))
        op.enqueue(self.job())
        op.fault({"mode": "drop_after", "delay_s": 0})
        self.assertFalse(op._step())
        token = op.m["stage"]["command_id"]
        before = len(op._journal()["commands"])
        origin = op.link.origin
        op.close()
        self.op = None
        op = self.open(lambda *_: self.fail("restart ran model"), worker=True)
        self.assertEqual(op.link.origin, origin)
        self.assertEqual(op.state()["runner_status"], "blocked")
        op.reconcile()
        self.assertEqual(op.state()["runner_status"], "paused")
        self.assertEqual(len(op._journal()["commands"]), before)
        self.assertEqual(op.m["applied_commands"].count(token), 1)
        self.assertEqual(self.service.body.status()["generation"], 1)

    def test_pause_before_host_admission_suppresses_stage_and_socket_command(self):
        op = self.open(lambda *_: self.fail("paused model"))
        op.enqueue(self.job())
        op.pause()
        self.assertFalse(op._step())
        self.assertIsNone(op.m["stage"])
        self.assertEqual(len(op._journal()["commands"]), 0)
        self.assertIsNone(self.service.body.status()["active_job"])

    def test_pause_after_host_admission_allows_exact_receipt_but_no_successor(self):
        op = self.open(lambda *_: (action("move", -.25, 0), {}))
        op.enqueue(self.job())
        entered, release = threading.Event(), threading.Event()
        original = op.client.dispatch
        def delayed_dispatch(proposal_id):
            self.assertEqual(op.m["stage"]["operation"], "dispatch")
            entered.set()
            release.wait(5)
            return original(proposal_id)
        with mock.patch.object(op.client, "dispatch", side_effect=delayed_dispatch):
            worker = threading.Thread(target=op._step)
            worker.start()
            self.assertTrue(entered.wait(10))
            op.pause()
            release.set()
            worker.join(10)
        self.assertFalse(worker.is_alive())
        self.assertEqual(op.state()["runner_status"], "paused")
        self.assertEqual(self.service.body.status()["generation"], 1)
        self.assertIsNone(op.m["stage"])
        before = len(op._journal()["commands"])
        self.assertFalse(op._step())
        self.assertEqual(len(op._journal()["commands"]), before)

    def test_pause_during_model_withholds_unadmitted_decision(self):
        entered, release = threading.Event(), threading.Event()
        def policy(*_):
            entered.set()
            release.wait(5)
            return action("move", -.25, 0), {}
        op = self.open(policy, worker=True)
        op.enqueue(self.job())
        self.assertTrue(entered.wait(10))
        before = len(op._journal()["commands"])
        op.pause()
        release.set()
        self.wait(lambda: not op.in_model)
        self.wait(lambda: any(e["kind"] == "decision_withheld" for e in op.m["activity"]))
        self.assertEqual(len(op._journal()["commands"]), before)
        self.assertEqual(self.service.body.status()["generation"], 0)

    def test_state_and_frame_are_responsive_while_transport_pending(self):
        op = self.open()
        op.enqueue(self.job())
        op._step()
        op.resume()
        entered, release = threading.Event(), threading.Event()
        original = op.client.observe
        def delayed_observe():
            entered.set()
            release.wait(5)
            return original()
        with mock.patch.object(op.client, "observe", side_effect=delayed_observe):
            worker = threading.Thread(target=op._step)
            worker.start()
            self.assertTrue(entered.wait(10))
            started = time.monotonic()
            state = op.state()
            self.assertTrue(state["transport_pending"])
            self.assertTrue(op.frame(state["current_frame"]["image_url"]).startswith(b"\x89PNG"))
            self.assertLess(time.monotonic() - started, .2)
            release.set()
            worker.join(10)
        self.assertFalse(worker.is_alive())

    def test_changed_image_and_source_refuse_without_network_effect(self):
        op = self.open()
        op.enqueue(self.job())
        op._step()
        before = len(op._journal()["commands"])
        with (mock.patch.object(runtime, "sources", return_value={"changed": True}), self.assertRaises(protocol.Refusal)):
            op.state()
        image = runtime.Path(op.m["frame"]["path"])
        image.write_bytes(b"changed cached image")
        with self.assertRaises(protocol.Refusal):
            op.frame()
        self.assertEqual(len(op._journal()["commands"]), before)

    def test_invalid_body_identity_health_is_blocked_without_thread_crash(self):
        op = self.open()
        with mock.patch.object(self.service, "identity", side_effect=protocol.Refusal("diagnostic invalid identity")):
            self.assertFalse(op._refresh_health())
            self.assertEqual(op.state()["connection"]["state"], "unavailable")
            self.assertEqual(op.state()["runner_status"], "blocked")
        self.assertTrue(op.health_worker.is_alive())
        self.assertEqual(len(op._journal()["commands"]), 0)

    def test_full_local_manifest_capacity_keeps_wire_limits(self):
        op = self.open()
        for i in range(6):
            op.enqueue(self.job("job-" + str(i), label="L" * 120))
        for job in op.m["jobs"]:
            job["history"] = [{"action": dict(action("move", -.25, 0), intent="I" * 500), "outcome": "executed", "reason": ""} for _ in range(6)]
        ids = ["command-" + uuid.uuid4().hex for _ in range(240)]
        op.m["applied_commands"] = ids
        op.m["stage"] = {"before_commands": ids, "operation": "observe", "arguments": {}, "command_id": None, "context": {"job_id": "job-0"}, "control_epoch": 0}
        op.m["activity"] = [{"seq": i, "time": 1, "kind": "diagnostic", "intent": "I" * 1000, "outcome": "O" * 1000} for i in range(24)]
        op._save()
        size = len(protocol.encoded(op.m))
        self.assertGreater(size, protocol.MAX_BYTES)
        self.assertLessEqual(size, body_client.MAX_CLIENT_JOURNAL)
        self.assertEqual(body_client.read_journal(self.host / "operator.json"), op.m)
        self.assertLessEqual(len(protocol.encoded(op.state())), protocol.MAX_BYTES)

    def test_stale_health_timeout_after_known_socket_dispatch_does_not_pause(self):
        op = self.open()
        op.enqueue(self.job())
        op._step()
        op.resume()
        op.policy = lambda *_: (action("move", -.25, 0), {})
        op.health_stop.set()
        op.health_worker.join(4)
        entered, release = threading.Event(), threading.Event()
        original = self.service.state
        def delayed_health_state():
            entered.set()
            release.wait(5)
            return original()
        with mock.patch.object(self.service, "state", side_effect=delayed_health_state):
            health = threading.Thread(target=op._refresh_health)
            health.start()
            self.assertTrue(entered.wait(5))
            self.assertTrue(op._step())
            health.join(3)
            release.set()
        self.assertFalse(health.is_alive())
        self.assertEqual(self.service.body.status()["generation"], 1)
        self.assertEqual(op.state()["connection"]["state"], "connected")
        self.assertEqual(op.state()["runner_status"], "running")
        self.assertIsNone(op.m["stage"])

    def test_idle_body_outage_becomes_unavailable_without_effect_polling(self):
        op = self.open()
        before = len(op._journal()["commands"])
        self.service.close()
        self.service = None
        time.sleep(2.5)
        self.assertEqual(op.state()["connection"]["state"], "unavailable")
        self.assertEqual(op.state()["runner_status"], "paused")
        self.assertEqual(len(op._journal()["commands"]), before)


if __name__ == "__main__":
    unittest.main()
