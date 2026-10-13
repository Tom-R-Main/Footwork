"""Pure diagnostic/scorer controls; no paid model or product actions."""
import tempfile
import unittest
from pathlib import Path

import crash_operator as diagnostic
import order_protocol as protocol
import qualify_workbench_recovery as harness
import score_workbench_recovery as scorer


class RecoveryTrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sim14-trial-control-", dir=Path(__file__).parent / "output")
        self.root = Path(self.temp.name)
        self.host = self.root / "operator"
        (self.host / "events").mkdir(parents=True)
        (self.host / "client/responses").mkdir(parents=True)
        self.token = "original-dispatch"
        protocol.persist(self.host / "operator.json", {"sequence": 12, "stage": {"operation": "dispatch", "command_id": self.token, "context": {"action": {"action": "move"}}}})
        envelope = {"command_id": self.token, "request_sha256": "a" * 64, "result": {"outcome": "executed"}}
        reply = protocol.encoded(envelope)
        digest = protocol.sha(reply)
        protocol.create_file(self.host / "client/responses" / (self.token + "-" + digest + ".json"), reply)
        protocol.persist(self.host / "client/client.json", {"commands": {self.token: {"state": "completed", "request_sha256": "a" * 64,
            "response_sha256": digest}}})
        self.event = {"seq": 13, "kind": "rpc_applied", "outcome": "dispatch: " + self.token}

    def tearDown(self):
        self.temp.cleanup()

    def gate(self, event=None):
        return diagnostic.publication_gate(self.host, 123, self.host / "events/000013.json", protocol.encoded(event or self.event))

    def test_publication_gate_binds_retained_original_stage_and_durable_event(self):
        value = self.gate()
        self.assertEqual(value["command_id"], self.token)
        self.assertEqual(value["event_sequence"], value["manifest_sequence"] + 1)
        self.assertEqual(value["event_sha256"], protocol.sha(protocol.encoded(self.event)))
        self.assertEqual(value["manifest_sha256"], protocol.sha(protocol.read_bytes(self.host / "operator.json")))

    def test_non_dispatch_event_cannot_arm_gate(self):
        self.assertIsNone(self.gate({"seq": 13, "kind": "rpc_applied", "outcome": "observe: other"}))

    def test_wrong_command_or_sequence_refuses_diagnostic(self):
        for event in ({**self.event, "outcome": "dispatch: another"}, {**self.event, "seq": 14}):
            with self.assertRaises((protocol.Refusal, KeyError)):
                self.gate(event)

    def test_manual_pid_crashes_are_not_accepted(self):
        for action, role in (("crash-role", "workbench"), ("start-role", "body"), ("finish", "workbench")):
            with self.assertRaises(protocol.Refusal):
                harness.request(self.root, action, role)

    def planner_boundary(self):
        (self.root / "snapshots").mkdir()
        call = self.host / "calls/job-01"
        call.mkdir(parents=True)
        closure = {"owner": "incarnation", "guardian_pid": 333, "process_exit_observed": True, "group_closed": True}
        protocol.persist(call / "planner-closure.json", closure)
        snap = {"client": {"commands": {"old-observe": {"send_count": 1}}}, "posts": ["old-observe"],
            "host": {"app_id": "app", "sequence": 4}, "body_identity": {"body_id": "body"}, "time": 20,
            "public": {"model_request_pending": False, "runner_status": "paused", "recovery": {"command_id": None}}}
        protocol.persist(self.root / "snapshots/before.json", snap)
        protocol.persist(self.root / "snapshots/restored.json", snap)
        boundary = {"case": "host-planning", "pre_snapshot": "before.json", "restored_snapshot": "restored.json",
            "process": {"pid": 123, "returncode": -9, "signal_target": "host_pid_only"},
            "gate": {"pid": 123, "call_directory": "job-01", "planner": {"owner": "incarnation", "guardian_pid": 333}}}
        transport = {"old-observe": {"relay": {"request": {"started_time": 1}}},
            "new-observe": {"relay": {"request": {"started_time": 31}}, "received": {"sequence": 2},
                "request": {"operation": "observe"}, "result": {"result": {"challenge_id": "fresh"}}}}
        events = [{"kind": "resume", "seq": 5, "time": 30}]
        return boundary, transport, events, closure

    def test_planner_boundary_requires_closure_before_fresh_explicit_resume(self):
        boundary, transport, events, _ = self.planner_boundary()
        value = scorer.boundary_score(self.root, boundary, transport, events)
        self.assertTrue(value["passed"])
        self.assertEqual(value["fresh_challenge"], "fresh")
        with self.assertRaises(protocol.Refusal):
            scorer.boundary_score(self.root, boundary, transport, [])

    def test_unclosed_guardian_and_replayed_command_are_refused(self):
        boundary, transport, events, closure = self.planner_boundary()
        path = self.host / "calls/job-01/planner-closure.json"
        protocol.persist(path, {**closure, "group_closed": False})
        with self.assertRaises(protocol.Refusal):
            scorer.boundary_score(self.root, boundary, transport, events)
        protocol.persist(path, closure)
        snap = harness.read(self.root / "snapshots/restored.json")
        snap["client"]["commands"]["old-observe"]["send_count"] = 2
        protocol.persist(self.root / "snapshots/restored.json", snap)
        with self.assertRaises(protocol.Refusal):
            scorer.boundary_score(self.root, boundary, transport, events)

    def test_receipt_recovery_keeps_original_token_while_clearing_pending(self):
        boundary, _, _, _ = self.planner_boundary()
        boundary.update(case="host-publication", command_id=self.token)
        paused = {"runner_status": "paused", "model_request_pending": False,
            "recovery": {"state": "uncertain", "command_id": self.token}}
        steps = [{"name": "crash-offline", "time": 21, "offline": True, "state": None, "visible_text": "Disconnected"},
            {"name": "restored", "time": 22, "offline": False, "state": paused, "visible_text": "Uncertain paused", "client_commands": 4},
            {"name": "recovered", "time": 23, "offline": False, "state": {**paused, "recovery": {"state": "recovered", "command_id": self.token}},
                "visible_text": "Receipt recovered", "client_commands": 4, "pending_command_ids": []},
            {"name": "resumed", "time": 24, "offline": False, "state": {"runner_status": "running"}, "visible_text": "Running"},
            {"name": "completed", "time": 25, "offline": False, "state": {"jobs": [{"status": "completed"}]}, "visible_text": "Completed"}]
        protocol.persist(self.root / "ui-ledger.json", {"steps": steps})
        self.assertTrue(scorer.ui_score(self.root, boundary)["passed"])
        steps[2]["client_commands"] += 1
        protocol.persist(self.root / "ui-ledger.json", {"steps": steps})
        with self.assertRaises(protocol.Refusal):
            scorer.ui_score(self.root, boundary)

    def test_reuses_exact_prior_wire_relay_and_indexed_command(self):
        import qualify_workbench_crashes as previous
        self.assertIs(harness.HeldReplyRelay, previous.HeldReplyRelay)
        self.assertIs(harness.indexed_command, previous.indexed_command)
        self.assertIs(harness.descendants, previous.descendants)


if __name__ == "__main__":
    unittest.main()
