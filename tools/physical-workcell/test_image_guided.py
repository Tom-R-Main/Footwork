"""Real RGB/native-engine conformance; this deterministic harness is not the AI trial."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("image_wrapper", BASE / "image_guided.py")
vision = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vision)


class ImageGuidedTests(unittest.TestCase):
    def setUp(self):
        vision.body.OUTPUT.mkdir(mode=0o700, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="image-conformance-", dir=vision.body.OUTPUT)
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.root = vision.body.directory(self.work / "run", create=True)
        order = {"version": 1, "order_id": "image-fixture", "project": {"namespace": "codex_app", "project_id": "fixture"},
                 "part_id": "block", "target_zone": {"x_min": .18, "x_max": .26, "y_min": -.04, "y_max": .04}}
        path = self.work / "order.json"
        content = vision.body.encoded(order)
        vision.body.create_file(path, content)
        vision.body.initialize(self.root, str(path), vision.body.sha(content))
        self.counter = 0

    def view(self):
        packet = vision.view(self.root)
        image = vision.decode_png(vision.body.read_bytes(Path(packet["image_path"])))
        return packet, image, vision.locate(image)

    def proposal(self, packet, located, decision="move", target=None, token=None):
        self.counter += 1
        proposal = {"version": 1, "run_dir": str(self.root), "generation": packet["generation"],
                    "image_sha256": packet["image_sha256"], "token": token or f"fixture-{self.counter}",
                    "block_box": located["block"]["box"], "decision": decision}
        if decision == "move":
            proposal["target"] = target or {"x": vision.image_world_center(located["pusher"]["box"])[0] + .10, "y": 0}
        return proposal

    def submit(self, proposal):
        content = vision.body.encoded(proposal)
        path = self.work / f"proposal-{self.counter}-{proposal['token']}.json"
        if not path.exists():
            vision.body.create_file(path, content)
        else:
            path.write_bytes(content)
        return vision.apply(self.root, str(path), vision.body.sha(content)), path, vision.body.sha(content)

    def finish_loop(self):
        contact_residual = False
        for _ in range(8):
            packet, _, located = self.view()
            center = vision.image_world_center(located["block"]["box"])
            if .185 <= center[0] <= .255 and abs(center[1]) <= .035:
                proposal = self.proposal(packet, located, "complete")
                result, path, digest = self.submit(proposal)
                self.assertEqual(result["phase"], "staged")
                return result, path, digest, contact_residual
            target = {"x": min(.16, vision.image_world_center(located["pusher"]["box"])[0] + .10), "y": 0}
            result, _, _ = self.submit(self.proposal(packet, located, target=target))
            self.assertEqual(result["phase"], "executed")
            next_packet, _, next_located = self.view()
            next_center = vision.image_world_center(next_located["block"]["box"])
            if result["contact_statistics"]["pusher_block_contact_samples"] > 0 and next_center[0] < .185:
                contact_residual = True
            self.assertGreater(next_packet["generation"], packet["generation"])
        self.fail("bounded fixture loop did not finish")

    def assert_no_oracle(self, value):
        output = json.dumps(value)
        for forbidden in ("block_xyz", "pusher_xyz", "physical_condition_verified", "block_center_in_zone", "physical_readback", "qpos", "xpos"):
            self.assertNotIn(forbidden, output)

    def test_native_rgb_calibration_full_silhouette_and_no_oracle_fields(self):
        packet, image, located = self.view()
        self.assertEqual(image.shape, (360, 640, 3))
        block = located["block"]["box"]
        self.assertEqual((block[2] - block[0], block[3] - block[1]), (42, 42))
        self.assertAlmostEqual(vision.image_world_center(block)[0], -.12, delta=.002)
        self.assertAlmostEqual(vision.image_world_center(located["pusher"]["box"])[0], -.30, delta=.002)
        self.assert_no_oracle(packet)
        receipt, _, _ = self.submit(self.proposal(packet, located))
        self.assert_no_oracle(receipt)

    def test_premature_visual_completion_refuses_before_native_effect(self):
        packet, _, located = self.view()
        proposal = self.proposal(packet, located, "complete")
        with patch.object(vision.body, "complete") as complete, self.assertRaises(vision.Refusal):
            self.submit(proposal)
        complete.assert_not_called()
        self.assertFalse(vision.proposal_path(self.root, proposal["token"]).exists())
        self.assertFalse((self.root / "order.json").exists())

    def test_wrong_box_reverse_oversize_and_lateral_targets_refuse(self):
        packet, _, located = self.view()
        original = self.proposal(packet, located)
        variants = [copy.deepcopy(original) for _ in range(4)]
        variants[0]["block_box"] = [value + 20 for value in original["block_box"]]
        variants[1]["target"]["x"] = -.31
        variants[2]["target"]["x"] = -.1
        variants[3]["target"]["y"] = .02
        for proposal in variants:
            with self.subTest(proposal=proposal), patch.object(vision.body, "act") as act, self.assertRaises(vision.Refusal):
                self.submit(proposal)
            act.assert_not_called()
        self.assertEqual(vision.body.load(self.root)[0]["generation"], 0)

    def test_bad_silhouettes_reject_blank_multiple_occluded_and_off_frame(self):
        _, image, located = self.view()
        blank = np.zeros_like(image)
        occluded = image.copy()
        left, top, right, bottom = located["block"]["box"]
        occluded[top:bottom, left:(left + right) // 2] = 0
        multiple = image.copy()
        multiple[40:82, 400:442] = image[top:bottom, left:right]
        off_frame = image.copy()
        off_frame[top:bottom, left:right] = 0
        off_frame[0:42, 0:42] = image[top:bottom, left:right]
        for name, candidate in (("blank", blank), ("occluded", occluded), ("multiple", multiple), ("off-frame", off_frame)):
            with self.subTest(name=name), self.assertRaises(vision.Refusal):
                vision.locate(candidate)

    def test_tampered_image_stale_proposal_and_changed_token_never_step(self):
        packet, _, located = self.view()
        proposal = self.proposal(packet, located)
        result, path, digest = self.submit(proposal)
        self.assertEqual(result["phase"], "executed")
        with patch.object(vision.body, "act") as act:
            repeat = vision.apply(self.root, str(path), digest)
        act.assert_not_called()
        self.assertEqual(repeat["phase"], "executed")
        changed = copy.deepcopy(proposal)
        changed["target"]["x"] += .01
        with self.assertRaises(vision.Refusal):
            self.submit(changed)
        stale = copy.deepcopy(proposal)
        stale["token"] = "stale"
        with self.assertRaises(vision.Refusal):
            self.submit(stale)
        next_packet, _, next_located = self.view()
        image_path = Path(next_packet["image_path"])
        image_path.write_bytes(image_path.read_bytes() + b"changed")
        with self.assertRaises(vision.Refusal):
            self.submit(self.proposal(next_packet, next_located))

    def test_partial_view_is_not_rerendered_or_promoted(self):
        with patch.object(vision, "render_rgb", side_effect=vision.Refusal("injected render failure")), self.assertRaises(vision.Refusal):
            vision.view(self.root)
        with patch.object(vision, "render_rgb") as render, self.assertRaises(vision.Refusal):
            vision.view(self.root)
        render.assert_not_called()
        receipt = vision.body.decoded(vision.body.read_bytes(vision.image_paths(self.root, 0)[1]))
        self.assertEqual(receipt["phase"], "pending")

    def test_lost_wrapper_receipt_blocks_replay_and_new_views(self):
        packet, _, located = self.view()
        proposal = self.proposal(packet, located)
        original = vision.body.utils.persist

        def lose(path, record):
            if path.name.startswith("vision-op-") and record.get("phase") == "executed":
                raise OSError("injected wrapper receipt loss")
            original(path, record)

        with patch.object(vision.body.utils, "persist", side_effect=lose):
            result, path, digest = self.submit(proposal)
        self.assertEqual(result["phase"], "unknown")
        with patch.object(vision.body, "act") as act:
            self.assertEqual(vision.apply(self.root, str(path), digest)["phase"], "unknown")
        act.assert_not_called()
        with self.assertRaises(vision.Refusal):
            self.view()

    def test_rgb_feedback_correction_and_final_private_oracle_agreement(self):
        result, _, _, had_residual = self.finish_loop()
        self.assertTrue(had_residual)
        self.assert_no_oracle(result)
        self.assertTrue(result["current_software_artifact_check"]["ok"])
        # Native pose is used only for this final independent evaluator assertion, never targets.
        native = vision.body.observation(self.root)
        pixel_center = result["historical_visual_check"]["image_center_world_xy"]
        self.assertTrue(native["physical_condition_verified"])
        self.assertAlmostEqual(pixel_center[0], native["block_xyz"][0], delta=.005)

    def test_current_result_tamper_or_missing_preserves_historical_staging_without_replay(self):
        _, path, digest, _ = self.finish_loop()
        output = self.root / "order.json"
        output.write_bytes(b"changed")
        repeated = vision.apply(self.root, str(path), digest)
        self.assertEqual(repeated["phase"], "unknown")
        self.assertEqual(repeated["historical_phase"], "staged")
        self.assertTrue(repeated["historical_software_artifact_check"]["historical"])
        self.assertFalse(repeated["current_software_artifact_check"]["ok"])
        self.assert_no_oracle(repeated)
        output.unlink()
        repeated = vision.apply(self.root, str(path), digest)
        self.assertEqual(repeated["phase"], "unknown")
        self.assertFalse(output.exists())

    def test_tampered_task_metadata_and_historical_receipt_refuse(self):
        packet, _, located = self.view()
        receipt_path = vision.image_paths(self.root, 0)[1]
        before = receipt_path.read_bytes()
        changed = dict(packet, task_intent={**packet["task_intent"], "part_id": "another-object"})
        vision.body.utils.persist(receipt_path, changed)
        with self.assertRaises(vision.Refusal):
            self.view()
        receipt_path.write_bytes(before)
        result, path, digest = self.submit(self.proposal(packet, located))
        record_path = vision.proposal_path(self.root, result["token"])
        receipt = vision.body.decoded(record_path.read_bytes())
        receipt["after_state_sha256"] = "0" * 64
        vision.body.utils.persist(record_path, receipt)
        with self.assertRaises(vision.Refusal):
            vision.apply(self.root, str(path), digest)

    def test_source_freeze_and_png_limits_are_enforced(self):
        packet, _, _ = self.view()
        with patch.object(vision, "fingerprint", return_value={"changed": True}), self.assertRaises(vision.Refusal):
            self.view()
        content = Path(packet["image_path"]).read_bytes()
        for changed in (content[:30], content + b"x", content[:60] + b"broken" + content[60:]):
            with self.assertRaises(vision.Refusal):
                vision.decode_png(changed)

    def test_forged_oracle_extra_field_or_perception_scope_is_not_returned(self):
        packet, _, located = self.view()
        receipt_path = vision.image_paths(self.root, 0)[1]
        original = receipt_path.read_bytes()
        for changed in (dict(packet, block_xyz=[0.22, 0, 0.035]),
                        dict(packet, perception_scope="native oracle verified the block")):
            with self.subTest(changed=changed):
                vision.body.utils.persist(receipt_path, changed)
                with self.assertRaises(vision.Refusal):
                    self.view()
                with patch.object(vision.body, "act") as act, self.assertRaises(vision.Refusal):
                    self.submit(self.proposal(packet, located))
                act.assert_not_called()
                process = subprocess.run([sys.executable, str(BASE / "image_guided.py"), "view", "--run-dir", str(self.root)],
                                         capture_output=True, text=True, check=False, timeout=30)
                self.assertEqual(process.returncode, 2)
                self.assertEqual(json.loads(process.stdout)["phase"], "refused")
                self.assert_no_oracle(json.loads(process.stdout))
                receipt_path.write_bytes(original)

    def test_public_fresh_process_view_apply_repeats_are_filtered(self):
        packet, _, located = self.view()
        proposal = self.proposal(packet, located)
        path = self.work / "public-proposal.json"
        content = vision.body.encoded(proposal)
        vision.body.create_file(path, content)
        args = [sys.executable, str(BASE / "image_guided.py"), "apply", "--run-dir", str(self.root),
                "--proposal-file", str(path), "--proposal-sha256", vision.body.sha(content)]
        for _ in range(2):
            process = subprocess.run(args, capture_output=True, text=True, check=False, timeout=30)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            result = json.loads(process.stdout)
            self.assertEqual(result["phase"], "executed")
            self.assert_no_oracle(result)
        view = subprocess.run([sys.executable, str(BASE / "image_guided.py"), "view", "--run-dir", str(self.root)],
                              capture_output=True, text=True, check=False, timeout=30)
        self.assertEqual(view.returncode, 0, view.stdout + view.stderr)
        self.assertEqual(json.loads(view.stdout)["generation"], 1)
        self.assert_no_oracle(json.loads(view.stdout))


if __name__ == "__main__":
    unittest.main()
