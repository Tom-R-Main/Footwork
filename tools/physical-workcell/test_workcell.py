"""Conformance on the actual pinned native physics engine; no hardware or camera."""

import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("physical_workcell", BASE / "workcell.py")
cell = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cell)


class WorkcellTests(unittest.TestCase):
    def setUp(self):
        cell.OUTPUT.mkdir(mode=0o700, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="conformance-", dir=cell.OUTPUT)
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.root = cell.directory(self.work / "run", create=True)
        self.order = {"version": 1, "order_id": "fixture-order", "project": {"namespace": "codex_app", "project_id": "fixture"},
                      "part_id": "block", "target_zone": {"x_min": .18, "x_max": .26, "y_min": -.08, "y_max": .08}}
        self.order_path = self.work / "input.json"
        self.content = cell.encoded(self.order)
        cell.create_file(self.order_path, self.content)
        self.sha = cell.sha(self.content)
        self.before = cell.initialize(self.root, str(self.order_path), self.sha)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(BASE / "workcell.py"), *args],
                              capture_output=True, text=True, check=False, timeout=30)

    def push(self):
        return cell.act(self.root, "push", 0, .15, 0)

    def test_before_condition_false_and_completion_creates_nothing(self):
        self.assertEqual(cell.mujoco.__version__, "3.15.0")
        self.assertEqual(self.before["source_kind"], "mujoco_simulation")
        self.assertFalse(self.before["physical_condition_verified"])
        with self.assertRaises(cell.Refusal):
            cell.complete(self.root, "stage")
        self.assertFalse((self.root / "order.json").exists())
        self.assertFalse(cell.op_path(self.root, "stage").exists())

    def test_real_contact_changes_block_and_enables_independent_computer_result(self):
        result = self.push()
        after = result["observation"]
        self.assertEqual(result["operation"]["phase"], "executed")
        self.assertGreater(after["block_xyz"][0] - self.before["block_xyz"][0], .25)
        self.assertTrue(after["physical_condition_verified"])
        evidence = result["operation"]["controller_evidence"]
        self.assertGreater(evidence["pusher_block_contact_samples"], 0)
        self.assertLessEqual(evidence["max_axis_actuator_force_n"], 4)
        self.assertGreater(evidence["native_steps"], 0)
        done = cell.complete(self.root, "stage")
        self.assertEqual(done["operation"]["phase"], "staged")
        self.assertTrue(done["observation"]["current_software_artifact_check"]["ok"])
        order = json.loads((self.root / "order.json").read_bytes())
        self.assertEqual(order["state"], "staged")
        self.assertEqual(order["source_kind"], "mujoco_simulation")
        self.assertEqual(order["simulator_state_sha256"], after["state_sha256"])
        self.assertTrue(order["physical_predicate"]["block_center_in_zone"])

    def test_noncontact_command_does_not_fulfill_order(self):
        result = cell.act(self.root, "short", 0, -.25, 0)
        self.assertEqual(result["operation"]["phase"], "executed")
        self.assertEqual(result["operation"]["controller_evidence"]["pusher_block_contact_samples"], 0)
        self.assertFalse(result["observation"]["physical_condition_verified"])
        with self.assertRaises(cell.Refusal):
            cell.complete(self.root, "stage")

    def test_fresh_process_continuity_repeat_and_one_digital_result(self):
        args = ("act", "--run-dir", str(self.root), "--token", "push", "--expected-generation", "0",
                "--target-x", "0.15", "--target-y", "0")
        result = self.cli(*args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        after = json.loads(result.stdout)["observation"]
        observed = self.cli("observe", "--run-dir", str(self.root))
        self.assertEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertEqual(json.loads(observed.stdout)["state_sha256"], after["state_sha256"])
        self.assertEqual(json.loads(observed.stdout)["block_xyz"], after["block_xyz"])
        before_repeat = {p.name: p.read_bytes() for p in self.root.iterdir() if p.name != "lock"}
        repeat = self.cli(*args)
        self.assertEqual(repeat.returncode, 0, repeat.stdout + repeat.stderr)
        self.assertEqual(json.loads(repeat.stdout)["observation"]["simulation_time_s"], after["simulation_time_s"])
        self.assertEqual(before_repeat, {p.name: p.read_bytes() for p in self.root.iterdir() if p.name != "lock"})
        complete_args = ("complete", "--run-dir", str(self.root), "--token", "stage")
        self.assertEqual(self.cli(*complete_args).returncode, 0)
        before_repeat = {p.name: p.read_bytes() for p in self.root.iterdir() if p.name != "lock"}
        self.assertEqual(self.cli(*complete_args).returncode, 0)
        self.assertEqual(before_repeat, {p.name: p.read_bytes() for p in self.root.iterdir() if p.name != "lock"})
        self.assertEqual(len(list(self.root.glob("order.json"))), 1)

    def test_token_arguments_stale_generation_and_workspace_refuse_before_step(self):
        self.push()
        before = cell.observation(self.root)
        for args in (("push", 0, .14, 0), ("fresh", 0, .15, 0), ("fresh", 1, .9, 0),
                     ("fresh", 1, .15, -.3), ("fresh", 1, math.nan, 0), ("fresh", 1, math.inf, 0)):
            with self.subTest(args=args), self.assertRaises(cell.Refusal):
                cell.act(self.root, *args)
        self.assertEqual(cell.observation(self.root)["state_sha256"], before["state_sha256"])
        self.assertFalse(cell.op_path(self.root, "fresh").exists())

    def test_lost_motion_receipt_blocks_replay_and_completion(self):
        original = cell.utils.persist

        def lose(path, record):
            if path.name.startswith("op-") and record.get("phase") == "executed":
                raise OSError("injected lost motion receipt")
            original(path, record)

        with patch.object(cell.utils, "persist", side_effect=lose):
            result = self.push()
        self.assertEqual(result["operation"]["phase"], "unknown")
        self.assertEqual(result["observation"]["claims"], [])
        self.assertFalse(result["observation"]["physical_condition_verified"])
        with patch.object(cell, "motion") as motion:
            again = self.push()
        motion.assert_not_called()
        self.assertEqual(again["operation"]["phase"], "unknown")
        with self.assertRaises(cell.Refusal):
            cell.act(self.root, "another", 1, .1, 0)
        with self.assertRaises(cell.Refusal):
            cell.complete(self.root, "stage")

    def test_interrupted_state_publication_does_not_implicitly_reset_or_reexecute(self):
        with patch.object(cell, "save_state", side_effect=OSError("injected state write failure")):
            result = self.push()
        self.assertEqual(result["observation"]["phase"], "unknown")
        self.assertEqual(result["observation"]["state_authority"], "retained_unresolved_operation")
        self.assertEqual(result["observation"]["simulation_time_s"], self.before["simulation_time_s"])
        self.assertFalse(result["observation"]["physical_condition_verified"])
        with patch.object(cell, "motion") as motion:
            self.push()
        motion.assert_not_called()

    def test_lost_software_receipt_never_promotes_valid_bytes_or_replays(self):
        self.push()
        original = cell.utils.persist

        def lose(path, record):
            if path.name.startswith("op-") and record.get("phase") == "staged":
                raise OSError("injected lost staging receipt")
            original(path, record)

        with patch.object(cell.utils, "persist", side_effect=lose):
            result = cell.complete(self.root, "stage")
        self.assertEqual(result["operation"]["phase"], "unknown")
        self.assertTrue((self.root / "order.json").exists())
        before = (self.root / "order.json").stat().st_mtime_ns
        self.assertEqual(cell.complete(self.root, "stage")["operation"]["phase"], "unknown")
        self.assertEqual((self.root / "order.json").stat().st_mtime_ns, before)

    def test_tampered_or_missing_result_preserves_history_without_recreation(self):
        self.push()
        cell.complete(self.root, "stage")
        path = self.root / "order.json"
        path.write_bytes(b"changed")
        observed = cell.observation(self.root)
        self.assertEqual(observed["phase"], "unknown")
        self.assertEqual(observed["historical_software_outcome"], "staged")
        self.assertFalse(observed["current_software_artifact_check"]["ok"])
        path.unlink()
        repeat = cell.complete(self.root, "stage")
        self.assertEqual(repeat["operation"]["historical_software_outcome"], "staged")
        self.assertEqual(repeat["observation"]["phase"], "unknown")
        self.assertFalse(path.exists())
        with self.assertRaises(cell.Refusal):
            cell.complete(self.root, "another-completion")

    def test_model_state_order_and_runtime_tamper_refuse_implicit_reset(self):
        files = (self.root / "model.xml", self.root / "work-order.json", cell.state_path(self.root, 0), self.order_path)
        for path in files:
            with self.subTest(path=path):
                before = path.read_bytes()
                path.write_bytes(before + b" ")
                with self.assertRaises(cell.Refusal):
                    cell.observation(self.root)
                path.write_bytes(before)
        with patch.object(cell.mujoco, "__version__", "different"), self.assertRaises(cell.Refusal):
            cell.observation(self.root)
        self.assertEqual(cell.observation(self.root)["generation"], 0)

    def test_init_lookup_is_repeat_safe_and_changed_order_refused(self):
        self.push()
        observed = cell.initialize(self.root, str(self.order_path), self.sha)
        self.assertEqual(observed["generation"], 1)
        self.assertTrue(observed["block_center_in_zone"])
        changed = dict(self.order, order_id="different")
        content = cell.encoded(changed)
        self.order_path.write_bytes(content)
        with self.assertRaises(cell.Refusal):
            cell.initialize(self.root, str(self.order_path), cell.sha(content))

    def test_malformed_and_nonfinite_inputs_fail_without_traceback(self):
        with self.assertRaises(cell.Refusal):
            cell.decoded(b'{"value":NaN}')
        with self.assertRaises(cell.Refusal):
            cell.decoded(b'{"version":1,"version":1}')
        result = self.cli("act", "--run-dir", str(self.root), "--token", "bad", "--expected-generation", "0",
                          "--target-x", "nan", "--target-y", "0")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["phase"], "refused")
        self.assertNotIn("Traceback", result.stderr)

    def test_cross_process_lock_prevents_second_owner(self):
        with cell.utils.locked(self.root):
            result = self.cli("observe", "--run-dir", str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("another process", result.stdout)


if __name__ == "__main__":
    unittest.main()
