"""Focused harness guards; disposable owned processes, no model or body launches."""
import copy
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

import order_protocol as protocol
import qualify_workbench_restarts as harness

PUBLIC = {"app_id": "app", "connection": {"body_id": "body"}, "runner_status": "running",
          "model_request_pending": True, "active_job_id": "job", "usage": {"calls": 1},
          "recovery": {"command_id": None}}


class RestartHarnessGuards(unittest.TestCase):
    def test_exact_planning_and_uncertain_predicates(self):
        self.assertTrue(harness.matches(PUBLIC, "planning"))
        self.assertFalse(harness.matches(PUBLIC, "uncertain"))
        uncertain = copy.deepcopy(PUBLIC)
        uncertain.update(runner_status="blocked", model_request_pending=False)
        uncertain["recovery"]["command_id"] = "command"
        self.assertTrue(harness.matches(uncertain, "uncertain"))
        self.assertFalse(harness.matches(uncertain, "planning"))

    def test_malformed_controls_refuse_before_snapshots_or_signals(self):
        control = {"sequence": 1, "action": "stop-role", "role": "workbench", "predicate": "planning",
                   "expect": harness.expected(PUBLIC), "requested_time": 1}
        self.assertEqual(harness.validate_control(control), control)
        for key, value in (("sequence", True), ("sequence", -1), ("action", "kill"), ("role", "other"),
                           ("predicate", "none"), ("expect", None)):
            malformed = {**control, key: value}
            with self.assertRaises(protocol.Refusal):
                harness.validate_control(malformed)
        bad = copy.deepcopy(control)
        bad["expect"]["model_request_pending"] = 1
        with self.assertRaises(protocol.Refusal):
            harness.validate_control(bad)

    def test_stop_only_signals_registered_owned_handle_and_reaps_it(self):
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            trial = object.__new__(harness.Trial)
            trial.active, trial.processes, trial.ledger = {"body": process}, [], {}
            with self.assertRaises(protocol.Refusal):
                trial.stop("body")
            self.assertIsNone(process.poll())
            record = {"role": "body", "pid": process.pid}
            trial.processes.append((process, record))
            stopped = trial.stop("body")
            self.assertTrue(stopped["exit_observed"])
            self.assertIsNone(trial.active["body"])
            with self.assertRaises(protocol.Refusal):
                trial.stop("body")
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=3)

    def test_snapshot_reader_keeps_128k_journal_and_wire_limit_separate(self):
        directory = Path(__file__).resolve().parent / "output" / ("sim11-reader-" + uuid.uuid4().hex[:12])
        directory.mkdir(mode=0o700)
        path = directory / "journal.json"
        path.write_bytes(protocol.encoded({"payload": "x" * 70000}))
        path.chmod(0o600)
        self.assertEqual(len(harness.read(path)["payload"]), 70000)
        with self.assertRaises(protocol.Refusal):
            protocol.decode(path.read_bytes())


if __name__ == "__main__":
    unittest.main()
