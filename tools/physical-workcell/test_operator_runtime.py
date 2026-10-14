"""Labelled deterministic conformance; fake decisions are not AI-control evidence."""
import json
import threading
import time
import unittest
import uuid
from http.client import HTTPConnection
from unittest import mock

import bench_operator
import operator_runtime as runtime
import order_protocol as protocol


def action(name="stop", x=None, y=None):
    return {"action": name, "target_x": x, "target_y": y, "intent": "Deterministic conformance fixture"}


class OperatorTests(unittest.TestCase):
    def setUp(self):
        self.root = runtime.BASE / "output" / ("operator-test-" + uuid.uuid4().hex[:10])
        self.patcher = mock.patch.object(runtime, "sources", return_value={"diagnostic_source": "frozen"})
        self.patcher.start()
        runtime.initialize(self.root)
        self.operator = None
        self.server = None
        self.thread = None

    def tearDown(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(5)
        if self.operator:
            self.operator.close()
        result = self._outcome.result
        failed = any(test is self for test, _ in (*result.failures, *result.errors))
        protocol.create_file(self.root / "conformance.json", protocol.encoded(
            {"test_id": self.id(), "passed": not failed, "policy": "explicitly_fake_diagnostic",
             "state": protocol.decode(protocol.read_bytes(self.root / "operator.json"))}))
        self.patcher.stop()

    def open(self, policy=None, worker=False):
        self.operator = runtime.Operator(self.root, policy or (lambda *_: (action(), {})), start_worker=worker)
        return self.operator

    def job(self, name="one", **changes):
        return {"job_id": name, "label": "Diagnostic job", "target": "A", "disturbance_test": False, **changes}

    def wait(self, predicate):
        until = time.monotonic() + 15
        while not predicate() and time.monotonic() < until:
            time.sleep(.02)
        self.assertTrue(predicate())

    def test_new_identity_bound_to_separate_persistent_bench(self):
        op = self.open()
        self.assertNotEqual(op.m["app_id"], op.body.status()["bench_id"])
        self.assertEqual(op.state()["current_frame"]["generation"], 0)
        self.assertEqual(op.body.status()["generation"], 0)
        self.assertTrue(op.frame().startswith(b"\x89PNG"))

    def test_pause_between_outer_loop_check_and_step_admission_starts_nothing(self):
        policy_calls = []
        def policy(*args):
            policy_calls.append(args)
            return action(), {}
        op = self.open(policy)
        op.enqueue(self.job())
        # The outer loop's running check already passed; Pause now wins the admission lock.
        op.pause()
        self.assertFalse(op._step())
        self.assertIsNone(op.body.status()["active_job"])
        self.assertIsNone(op.state()["active_job_id"])
        self.assertEqual(op.state()["jobs"][0]["status"], "queued")
        self.assertEqual(op.state()["jobs"][0]["call_count"], 0)
        self.assertEqual(op.state()["usage"]["calls"], 0)
        self.assertEqual(list((self.root / "calls").glob("*/reservation.json")), [])
        self.assertEqual(policy_calls, [])

    def test_get_state_and_frame_do_not_capture_or_call_model(self):
        op = self.open(lambda *_: self.fail("GET invoked model"))
        before = op.agent.status()["sequence"]
        for _ in range(3):
            op.state()
            op.frame()
        self.assertEqual(op.agent.status()["sequence"], before)

    def test_queue_validation_duplicate_and_path_schema(self):
        op = self.open()
        for value in (self.job("../bad"), self.job(target="C"), self.job(disturbance_test=1),
                      self.job(command="rm"), self.job(label=""), self.job(disturbance_test=True)):
            with self.assertRaises((protocol.Refusal, TypeError)):
                op.enqueue(value)
        op.enqueue(self.job())
        with self.assertRaises(protocol.Refusal):
            op.enqueue(self.job())
        self.assertEqual(len(op.state()["jobs"]), 1)

    def test_stop_decision_pauses_without_completion(self):
        op = self.open(worker=True)
        op.enqueue(self.job())
        self.wait(lambda: op.state()["runner_status"] == "paused")
        self.assertEqual(op.state()["jobs"][0]["status"], "paused")
        self.assertEqual(op.body.status()["generation"], 0)
        self.assertFalse((self.root / "bench" / "measurements.sqlite").exists())

    def test_pause_during_model_prevents_late_reply_dispatch(self):
        entered, release = threading.Event(), threading.Event()
        def policy(*_):
            entered.set()
            release.wait(5)
            return action("move", -.25, 0), {"usage": {"input_tokens": 7, "output_tokens": 3}}
        op = self.open(policy, worker=True)
        op.enqueue(self.job())
        self.assertTrue(entered.wait(10))
        op.pause()
        with self.assertRaises(protocol.Refusal):
            op.resume()
        release.set()
        self.wait(lambda: not op.in_model)
        self.wait(lambda: any(e["kind"] == "decision_withheld" for e in op.m["activity"]))
        self.assertEqual(op.body.status()["generation"], 0)
        self.assertEqual(op.state()["usage"]["calls"], 1)
        self.assertEqual(op.state()["usage"]["input_tokens"], 7)
        self.assertEqual(len(list((self.root / "agent" / "proposals").glob("*.json"))), 0)

    def test_cancelled_reply_stays_withheld_after_event_clears(self):
        # Simulate the narrow interval after owned process exit but before old reply dispatch.
        op = self.open()
        def policy(*_):
            op.pause()
            op.in_model = False
            op.resume()
            return action("move", -.25, 0), {}
        op.policy = policy
        op.enqueue(self.job())
        self.assertFalse(op._step())
        self.assertEqual(op.body.status()["generation"], 0)
        self.assertEqual(len(list((self.root / "agent" / "proposals").glob("*.json"))), 0)
        self.assertTrue(any(e["kind"] == "decision_withheld" for e in op.state()["activity"]))

    def test_model_unavailable_pauses_counts_attempt_and_never_completes(self):
        def policy(*_):
            raise RuntimeError("Diagnostic model unavailable")
        op = self.open(policy, worker=True)
        op.enqueue(self.job())
        self.wait(lambda: op.state()["runner_status"] == "paused")
        self.assertEqual(op.state()["jobs"][0]["call_count"], 1)
        self.assertEqual(op.body.status()["generation"], 0)

    def test_model_cannot_claim_completion_or_bypass_guard(self):
        op = self.open(lambda *_: (dict(action("finish_reset"), completed=True), {}))
        op.enqueue(self.job())
        with self.assertRaises(protocol.Refusal):
            op._step()
        self.assertEqual(op.body.status()["active_job"]["phase"], "prepare")
        self.assertNotEqual(op.state()["jobs"][0]["status"], "completed")

    def test_invalid_finish_reset_refuses_native_guard(self):
        op = self.open(lambda *_: (action("finish_reset"), {}))
        op.enqueue(self.job())
        op._step()
        self.assertEqual(op.m["jobs"][0]["history"][-1]["outcome"], "refused")
        self.assertEqual(op.body.status()["active_job"]["phase"], "prepare")

    def test_restart_retains_body_and_queue_without_replay(self):
        op = self.open()
        op.enqueue(self.job())
        op.close()
        self.operator = None
        op = self.open(lambda *_: self.fail("restart invoked model"), worker=True)
        time.sleep(.1)
        self.assertEqual(op.state()["runner_status"], "paused")
        self.assertEqual(op.state()["jobs"][0]["status"], "queued")
        self.assertEqual(op.body.status()["generation"], 0)
        self.assertEqual(op.state()["usage"]["calls"], 0)

    def test_unknown_native_blocks_resume_and_no_reset(self):
        op = self.open()
        manifest = protocol.decode(protocol.read_bytes(self.root / "bench" / "bench.json"))
        manifest["busy"] = {"operation_id": "interrupted", "kind": "move"}
        protocol.persist(self.root / "bench" / "bench.json", manifest)
        with self.assertRaises(protocol.Refusal):
            op.resume()
        self.assertEqual(op.state()["runner_status"], "blocked")
        self.assertEqual(op.body.status()["state"], "unknown")

    def test_source_change_refuses_mutation(self):
        op = self.open()
        with (mock.patch.object(runtime, "sources", return_value={"diagnostic_source": "changed"}),
              self.assertRaises(protocol.Refusal)):
            op.enqueue(self.job())
        self.assertEqual(len(op.state()["jobs"]), 0)

    def test_two_jobs_replay_public_action_fixture_and_disturbance_guard(self):
        # Replay a declared previous development trajectory, not a model qualification.
        audit = runtime.BASE.parent.parent / "jevdual/results/agent-visual-bench-20261011/AI-action-audit.json"
        proposals = iter(json.loads(audit.read_text())["actions"])
        def policy(*_):
            recorded = next(proposals)["proposal"]
            return {key: recorded[key] for key in ("action", "target_x", "target_y", "intent")}, {}
        op = self.open(policy)
        op.enqueue(self.job())
        op.enqueue(self.job("two", target="B", disturbance_test=True))
        for _ in range(40):
            if not op._step():
                break
        self.assertEqual([j["status"] for j in op.state()["jobs"]], ["completed", "completed"])
        self.assertEqual(len(op.body.status()["jobs"]), 2)
        self.assertIsNone(op.body.status()["active_job"])
        events = [protocol.decode(protocol.read_bytes(p)) for p in (self.root / "calls").glob("event-*.json")]
        self.assertTrue(any("stale" in e["outcome"] for e in events))
        self.assertEqual(op.state()["usage"]["calls"], 29)
        self.assertTrue(all(j["measurement"]["orange_pixel_count"] > 0 for j in op.state()["jobs"]))

    def test_frame_identity_changes_when_zone_repaint_keeps_generation(self):
        op = self.open()
        first_url = op.state()["current_frame"]["image_url"]
        op.enqueue(self.job())
        op._step()
        second_url = op.state()["current_frame"]["image_url"]
        self.assertNotEqual(first_url, second_url)
        self.assertEqual(op.state()["current_frame"]["generation"], 0)
        with self.assertRaises(protocol.Refusal):
            op.frame(first_url)
        self.assertTrue(op.frame(second_url).startswith(b"\x89PNG"))

    def test_interrupted_start_intent_blocks_restart_without_replay(self):
        op = self.open()
        op.enqueue(self.job())
        op.m["active_job_id"] = "one"
        op.m["jobs"][0]["status"] = "running"
        op._save()
        op.close()
        self.operator = None
        op = self.open(lambda *_: self.fail("replayed interrupted start"), worker=True)
        self.assertEqual(op.state()["runner_status"], "blocked")
        with self.assertRaises(protocol.Refusal):
            op.resume()
        self.assertIsNone(op.body.status()["active_job"])
        self.assertEqual(op.body.status()["generation"], 0)

    def test_mutated_operator_manifest_and_fabricated_completion_refuse(self):
        op = self.open()
        op.enqueue(self.job())
        op.m["jobs"][0]["status"] = "completed"
        op._save()
        self.assertEqual(op.state()["runner_status"], "blocked")
        self.assertEqual(op.state()["jobs"][0]["status"], "unknown")
        retained = protocol.decode(protocol.read_bytes(self.root / "operator.json"))
        retained["reason"] = "Changed externally"
        protocol.persist(self.root / "operator.json", retained)
        with self.assertRaises(protocol.Refusal):
            op.enqueue(self.job("two"))

    def test_global_reserved_call_budget_blocks_starting_another_job(self):
        op = self.open(lambda *_: self.fail("budget-exhausted model request"))
        op.enqueue(self.job())
        op.m["usage"]["calls"] = runtime.MAX_TOTAL_CALLS
        op._save()
        self.assertFalse(op._step())
        self.assertEqual(op.state()["runner_status"], "paused")
        self.assertIsNone(op.body.status()["active_job"])
        self.assertFalse(op.state()["usage"]["token_usage_complete"])

    def test_shutdown_cancelled_model_exit_persists_stopped_after_worker_exits(self):
        entered = threading.Event()
        def policy(challenge, history, directory, cancel):
            entered.set()
            cancel.wait(5)
            raise RuntimeError("Diagnostic owned process cancellation")
        op = self.open(policy, worker=True)
        op.enqueue(self.job())
        self.assertTrue(entered.wait(10))
        op.close()
        self.operator = None
        retained = protocol.decode(protocol.read_bytes(self.root / "operator.json"))
        self.assertFalse(op.worker.is_alive())
        self.assertEqual(retained["runner_status"], "stopped")
        self.assertEqual(op.body.status()["generation"], 0)

    def test_http_origin_identity_duplicate_keys_and_body_schema(self):
        op = self.open()
        self.server = bench_operator.Server(("127.0.0.1", 0), op)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        headers = {"Origin": self.server.origin, "X-Footwork-App-ID": op.m["app_id"], "Content-Type": "application/json"}
        def post(content, override=None):
            connection = HTTPConnection(*self.server.server_address, timeout=5)
            connection.request("POST", "/api/jobs", content, headers | (override or {}))
            response = connection.getresponse()
            response.read()
            connection.close()
            return response.status
        self.assertEqual(post(json.dumps(self.job()), {"Origin": "http://foreign.invalid"}), 409)
        self.assertEqual(post(json.dumps(self.job()), {"X-Footwork-App-ID": "foreign"}), 409)
        self.assertEqual(post('{"job_id":"one","job_id":"two"}'), 409)
        self.assertEqual(post(json.dumps(self.job(command="override"))), 409)
        self.assertEqual(len(op.state()["jobs"]), 0)
        self.assertEqual(post(json.dumps(self.job())), 200)
        self.assertEqual(len(op.state()["jobs"]), 1)


if __name__ == "__main__":
    unittest.main()
