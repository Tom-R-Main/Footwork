"""SIM3 conformance with private development cases; deterministic tests are not AI trials."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("episode_test", BASE / "episode_runner.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
body = runner.body
vision = runner.vision


class EpisodeTests(unittest.TestCase):
    def setUp(self):
        body.OUTPUT.mkdir(mode=0o700, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="sim3-private-dev-", dir=body.OUTPUT)
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.root = body.directory(self.work / "run", create=True)
        self.case = {"version": 1, "case_id": "private-dev-episode", "max_actions": 8,
                     "scene": {"block_xy": [-.17, .007], "illumination_scale": 1.0,
                               "occlusion_fraction": 0.0, "camera_offset_x_m": 0.0},
                     "work_order": {"version": 1, "order_id": "private-dev-order",
                                    "project": {"namespace": "codex_app", "project_id": "private-dev"},
                                    "part_id": "block", "target_zone": {
                                        "x_min": .13, "x_max": .21, "y_min": -.03, "y_max": .05}}}
        self.case_path = self.work / "dev-case.json"
        self.case_sha = self.save_case(self.case_path)

    def save_case(self, path):
        content = body.encoded(self.case)
        body.create_file(path, content)
        return body.sha(content)

    def init(self):
        return runner.initialize(self.root, str(self.case_path), self.case_sha)

    def declare(self, outcome="completed", interventions=None):
        content = b"Private development participant declaration.\n"
        path = self.work / "explanation.txt"
        if not path.exists():
            body.create_file(path, content)
        return runner.finish(self.root, outcome, str(path), body.sha(content), interventions)

    def snapshot(self):
        return {path.name: path.read_bytes() for path in self.root.iterdir() if path.is_file() and path.name != "lock"}

    def no_oracle(self, output):
        serialized = json.dumps(output)
        for forbidden in ("block_xyz", "pusher_xyz", "physical_condition_verified", "block_center_in_zone",
                          "physical_readback", "block_xy", "illumination_scale", "occlusion_fraction", "camera_offset_x_m"):
            self.assertNotIn(forbidden, serialized)

    def test_case_binding_no_implicit_reset_and_public_init_filtering(self):
        initial = self.init()
        self.no_oracle(initial)
        before = self.snapshot()
        repeat = self.init()
        self.assertEqual(initial, repeat)
        self.assertEqual(before, self.snapshot())
        self.case["scene"]["block_xy"] = [-.19, .005]
        other = self.work / "other-case.json"
        digest = self.save_case(other)
        with self.assertRaises(Refusal):
            runner.initialize(self.root, str(other), digest)
        self.assertEqual(before, self.snapshot())

    def test_finish_declaration_elapsed_idempotency_conflict_and_no_effects(self):
        self.init()
        states = {p.name: p.read_bytes() for p in self.root.glob("state-*.json")}
        declaration = self.declare("unresolved", interventions=2)
        self.no_oracle(declaration)
        before = self.snapshot()
        self.assertEqual(declaration, self.declare("unresolved", interventions=2))
        self.assertEqual(before, self.snapshot())
        with self.assertRaises(Refusal):
            self.declare("completed", interventions=2)
        self.assertEqual(states, {p.name: p.read_bytes() for p in self.root.glob("state-*.json")})
        score = runner.evaluate(self.root)
        self.assertGreaterEqual(score["elapsed_s"], 0)
        self.assertEqual(score["interventions_declared"], 2)
        self.assertEqual(score["unresolved"], 1)

    def test_false_completion_claim_is_visible_without_software(self):
        self.init()
        self.declare()
        score = runner.evaluate(self.root)
        self.assertTrue(score["incorrect_completion_claim"])
        self.assertFalse(score["qualified_completion"])
        self.assertEqual(score["completed"], 0)
        self.assertIsNone(score["interventions_declared"])
        self.assertFalse((self.root / "order.json").exists())

    def test_satisfactory_current_scene_does_not_manufacture_history(self):
        self.case["work_order"]["target_zone"] = {"x_min": -.20, "x_max": -.14, "y_min": -.02, "y_max": .03}
        self.case_path.unlink()
        self.case_sha = self.save_case(self.case_path)
        self.init()
        self.declare()
        score = runner.evaluate(self.root)
        self.assertTrue(score["physical_condition"])
        self.assertEqual(score["motion_executed_count"], 0)
        self.assertFalse(score["historical_software_staged"])
        self.assertTrue(score["incorrect_completion_claim"])

    def test_already_placed_case_real_visual_and_software_completion_has_zero_motion(self):
        self.case["work_order"]["target_zone"] = {"x_min": -.21, "x_max": -.13, "y_min": -.02, "y_max": .03}
        self.case_path.unlink()
        self.case_sha = self.save_case(self.case_path)
        result = runner.baseline(self.root, str(self.case_path), self.case_sha)
        self.assertEqual(result["declaration"]["outcome"], "completed", result)
        score = runner.evaluate(self.root)
        self.assertEqual(score["completed"], 1, score)
        self.assertEqual(score["motion_executed_count"], 0)
        self.assertEqual(score["action_count"], 1)

    def test_actual_rgb_baseline_completes_with_contact_and_independent_saved_file(self):
        public = runner.baseline(self.root, str(self.case_path), self.case_sha)
        self.no_oracle(public)
        self.assertEqual(public["participant"], "deterministic_rgb")
        score = runner.evaluate(self.root)
        self.assertEqual(score["completed"], 1, score)
        self.assertTrue(score["physical_condition"])
        self.assertTrue(score["current_software_ok"])
        self.assertGreater(score["motion_executed_count"], 0)
        self.assertLessEqual(score["action_count"], 8)
        before = self.snapshot()
        self.assertEqual(public, runner.baseline(self.root, str(self.case_path), self.case_sha))
        self.assertEqual(before, self.snapshot())
        self.assertEqual(score, runner.evaluate(self.root))
        self.assertEqual(before, self.snapshot())

    def test_failed_rgb_recognition_retains_image_and_declares_unresolved(self):
        self.case["scene"]["illumination_scale"] = .002
        self.case_path.unlink()
        self.case_sha = self.save_case(self.case_path)
        public = runner.baseline(self.root, str(self.case_path), self.case_sha)
        self.assertEqual(public["declaration"]["outcome"], "unresolved")
        self.assertTrue(list(self.root.glob("vision-frame-*.png")))
        self.assertEqual(runner.evaluate(self.root)["action_count"], 0)

    def test_invalid_calibration_retains_image_and_blocks_baseline(self):
        self.case["scene"]["camera_offset_x_m"] = .043
        self.case_path.unlink()
        self.case_sha = self.save_case(self.case_path)
        public = runner.baseline(self.root, str(self.case_path), self.case_sha)
        self.assertEqual(public["declaration"]["outcome"], "unresolved")
        self.assertTrue(list(self.root.glob("vision-frame-*.png")))
        score = runner.evaluate(self.root)
        self.assertEqual(score["action_count"], 0)
        self.assertEqual(score["unresolved"], 1)

    def test_small_budget_reserves_completion_slot_and_performs_no_unbudgeted_motion(self):
        self.case["max_actions"] = 1
        self.case_path.unlink()
        self.case_sha = self.save_case(self.case_path)
        result = runner.baseline(self.root, str(self.case_path), self.case_sha)
        self.assertEqual(result["declaration"]["outcome"], "unresolved", result)
        self.assertEqual(runner.evaluate(self.root)["action_count"], 0)
        self.assertTrue(list(self.root.glob("vision-frame-*.png")))

    def test_failed_setup_is_durable_counted_and_never_retried(self):
        with patch.object(body, "initialize_episode", side_effect=Refusal("dev setup failure")) as setup:
            initial = self.init()
            self.assertEqual(initial["phase"], "setup_failed")
            self.assertEqual(initial, self.init())
            setup.assert_called_once()
        self.declare("failed")
        score = runner.evaluate(self.root)
        self.assertTrue(score["setup_failed"])
        self.assertEqual(score["failed"], 1)
        self.assertEqual(score["attempted"], 1)

    def test_unexpected_baseline_driver_failure_is_finished_and_counted(self):
        with patch.object(vision, "view", side_effect=RuntimeError("private dev driver failure")):
            result = runner.baseline(self.root, str(self.case_path), self.case_sha)
        self.assertEqual(result["declaration"]["outcome"], "failed")
        score = runner.evaluate(self.root)
        self.assertTrue(score["driver_failed"])
        self.assertEqual(score["failed"], 1)
        self.assertIsNotNone(score["elapsed_s"])

    def test_bound_generation_verdict_counts_hidden_false_positive(self):
        self.init()
        packet = vision.view(self.root)
        located = vision.locate(vision.decode_png(body.read_bytes(Path(packet["image_path"]))))
        # Inject a false visual assertion into a private dev receipt to test the scorer;
        # this is not a claim about the real detector's accuracy.
        proposal = {"version": 1, "run_dir": str(self.root), "generation": packet["generation"],
                    "image_sha256": packet["image_sha256"], "token": "dev-false-visual",
                    "block_box": located["block"]["box"], "decision": "complete"}
        content = body.encoded(proposal)
        token_sha = body.sha(proposal["token"].encode())
        body.create_file(self.root / f"vision-request-{token_sha}.json", content)
        verdict = {"proposal": proposal, "proposal_sha256": body.sha(content),
                   "binding": packet["binding"], "case_binding": packet["binding"].get("case_binding"),
                   "generation": packet["generation"], "state_sha256": packet["state_sha256"],
                   "image_sha256": packet["image_sha256"], "visual_verdict": True, "before_oracle": True,
                   "reason": "injected private dev false assertion"}
        body.create_file(self.root / f"vision-verdict-{token_sha}.json", body.encoded(verdict))
        body.act(self.root, "dev-native-contact", 0, .11, 0)
        self.assertTrue(body.observation(self.root)["physical_condition_verified"])
        self.declare()
        before = self.snapshot()
        score = runner.evaluate(self.root)
        self.assertEqual(score["visual_positive_count"], 1, score)
        self.assertEqual(score["visual_false_positive_count"], 1, score)
        self.assertFalse(score["visual_verdicts"][0]["bound_native_condition"])
        self.assertTrue(score["physical_condition"])
        self.assertTrue(score["incorrect_completion_claim"])
        self.assertEqual(before, self.snapshot())

    def test_doctor_has_no_episode_or_persisted_simulator_effect(self):
        before = self.snapshot()
        result = runner.doctor()
        self.assertEqual(result["phase"], "ready", result)
        self.no_oracle(result)
        self.assertEqual(before, self.snapshot())


Refusal = runner.Refusal

if __name__ == "__main__":
    unittest.main()
