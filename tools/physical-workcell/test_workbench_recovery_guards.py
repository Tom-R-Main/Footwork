"""Bounded negative fixtures for audit recovery and planner ownership proofs."""
import os
import tempfile
import unittest
from pathlib import Path

import network_operator_runtime as runtime
import order_protocol as protocol
import planner_guard


class RecoveryGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sim14-recovery-", dir=protocol.OUTPUT)
        self.root = Path(self.temp.name)
        (self.root / "events").mkdir(mode=0o700)
        self.op = runtime.Operator.__new__(runtime.Operator)
        self.op.root = self.root
        self.op.m = {"sequence": 0, "activity": []}

    def tearDown(self):
        self.temp.cleanup()

    def event(self, seq):
        value = {"seq": seq, "time": 1.0, "kind": "rpc_applied", "intent": "audit only", "outcome": "dispatch"}
        protocol.create_file(self.root / "events" / f"{seq:06d}.json", protocol.encoded(value))
        return value

    def test_contiguous_audit_tail_preserves_stage_and_applied_identity(self):
        first = self.event(1)
        self.event(2)
        self.op.m.update(sequence=1, activity=[first], stage={"command_id": "original"}, applied_commands=[])
        self.assertEqual(self.op._recover_events(), 1)
        self.assertEqual(self.op.m["sequence"], 2)
        self.assertEqual(self.op.m["stage"], {"command_id": "original"})
        self.assertEqual(self.op.m["applied_commands"], [])

    def test_missing_event_refuses(self):
        self.event(2)
        with self.assertRaisesRegex(protocol.Refusal, "contiguous"):
            self.op._recover_events()

    def test_malformed_tail_refuses(self):
        protocol.create_file(self.root / "events" / "000001.json", b'{"seq":1,"seq":2}')
        with self.assertRaises(protocol.Refusal):
            self.op._recover_events()

    def test_indexed_activity_conflict_refuses(self):
        self.event(1)
        self.op.m.update(sequence=1, activity=[])
        with self.assertRaisesRegex(protocol.Refusal, "differs"):
            self.op._recover_events()

    def test_missing_indexed_file_refuses(self):
        self.op.m["sequence"] = 1
        with self.assertRaisesRegex(protocol.Refusal, "incomplete"):
            self.op._recover_events()

    def test_symlink_event_refuses(self):
        protocol.create_file(self.root / "target", protocol.encoded({}))
        (self.root / "events" / "000001.json").symlink_to(self.root / "target")
        with self.assertRaises(protocol.Refusal):
            self.op._recover_events()

    def planner(self):
        call = self.root / "call"
        call.mkdir(mode=0o700)
        intent = {"version": 1, "host_pid": os.getpid(), "owner": "owner", "request_sha256": "a" * 64}
        protocol.create_file(call / "planner-intent.json", protocol.encoded(intent))
        protocol.create_file(call / "reservation.json", protocol.encoded({"planner_owner": "owner"}))
        return call, intent

    def test_before_guardian_launch_has_no_old_writer(self):
        call, _ = self.planner()
        recovered = planner_guard.recover(call)
        self.assertEqual(recovered["reason"], "host exited before planner startup")
        self.assertTrue(recovered["group_closed"])

    def test_guardian_start_without_closure_is_ambiguous(self):
        call, intent = self.planner()
        protocol.create_file(call / "planner-process.json", protocol.encoded({**intent, "guardian_pid": 123}))
        with self.assertRaisesRegex(protocol.Refusal, "without group cleanup"):
            planner_guard.recover(call)

    def test_inconsistent_closure_refuses_without_pid_signals(self):
        call, intent = self.planner()
        base = {k: intent[k] for k in ("host_pid", "owner", "request_sha256")}
        startup = {**base, "guardian_pid": os.getpid(), "process_exit_observed": False, "group_closed": False}
        protocol.create_file(call / "planner-process.json", protocol.encoded(startup))
        closure = {**startup, "owner": "different", "group_closed": True, "process_exit_observed": True,
                   "exit_code": 0, "reason": "completed"}
        protocol.create_file(call / "planner-closure.json", protocol.encoded(closure))
        with self.assertRaisesRegex(protocol.Refusal, "inconsistent"):
            planner_guard.recover(call)

    def test_reservation_owner_conflict_refuses(self):
        call, _ = self.planner()
        protocol.persist(call / "reservation.json", {"planner_owner": "changed"})
        with self.assertRaisesRegex(protocol.Refusal, "reservation owner"):
            planner_guard.recover(call)

    def test_orphan_guardian_artifacts_refuse(self):
        call = self.root / "call"
        call.mkdir(mode=0o700)
        protocol.create_file(call / "planner-process.json", protocol.encoded({"guardian_pid": os.getpid()}))
        with self.assertRaisesRegex(protocol.Refusal, "have no intent"):
            planner_guard.recover(call)

    def spawned_planner_proof(self):
        call, intent = self.planner()
        base = {k: intent[k] for k in ("host_pid", "owner", "request_sha256")}
        startup = {**base, "guardian_pid": os.getpid(), "process_exit_observed": False, "group_closed": False,
                   "planner_pid": 12345, "planner_pgid": 12345}
        protocol.create_file(call / "planner-process.json", protocol.encoded(startup))
        protocol.create_file(call / "planner-closure.json", protocol.encoded({k: v for k, v in {
            **startup, "group_closed": True, "process_exit_observed": True, "reason": "completed", "exit_code": 0}.items()
            if k not in {"planner_pid", "planner_pgid"}}))
        proof = {**base, "guardian_pid": os.getpid(), "version": 1, "complete": True,
                 "observed": [{"pid": 12345, "parent": os.getpid(), "group": 12345, "uid": os.getuid(),
                               "started": "Bounded identity fixture"}], "remaining": []}
        return call, proof

    def test_spawned_planner_without_descendant_proof_refuses(self):
        call, _ = self.spawned_planner_proof()
        with self.assertRaises(protocol.Refusal):
            planner_guard.recover(call)

    def test_inconsistent_or_incomplete_descendant_proof_refuses(self):
        call, proof = self.spawned_planner_proof()
        for change in ({"owner": "other"}, {"complete": False}, {"remaining": [{}]}, {"version": True},
                       {"guardian_pid": os.getpid() + 1}, {"observed": [{}]}):
            with self.subTest(change=change):
                protocol.persist(call / "planner-descendants.json", {**proof, **change})
                with self.assertRaises(protocol.Refusal):
                    planner_guard.recover(call)

    def test_empty_complete_descendant_proof_refuses(self):
        call, proof = self.spawned_planner_proof()
        protocol.persist(call / "planner-descendants.json", {**proof, "observed": []})
        with self.assertRaisesRegex(protocol.Refusal, "inconsistent"):
            planner_guard.recover(call)

    def test_truncated_or_unbound_leader_descendant_proof_refuses(self):
        call, proof = self.spawned_planner_proof()
        for change in ({"pid": 54321}, {"group": 54321}, {"parent": os.getpid() + 1}):
            with self.subTest(change=change):
                protocol.persist(call / "planner-descendants.json", {**proof, "observed": [{**proof["observed"][0], **change}]})
                with self.assertRaisesRegex(protocol.Refusal, "spawned leader"):
                    planner_guard.recover(call)


if __name__ == "__main__":
    unittest.main()
