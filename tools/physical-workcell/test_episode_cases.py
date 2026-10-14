"""Independent development cases; never discovers or runs qualification fixtures."""

import copy
import importlib.util
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("case_vision", BASE / "image_guided.py")
vision = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vision)
body = vision.body


class EpisodeCaseTests(unittest.TestCase):
    def setUp(self):
        body.OUTPUT.mkdir(mode=0o700, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="case-development-", dir=body.OUTPUT)
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.counter = 0

    def case(self, **scene):
        return {"version": 1, "case_id": "independent-development", "max_actions": 8,
                "scene": {"block_xy": [-.16, .015], "illumination_scale": 1,
                          "occlusion_fraction": 0, "camera_offset_x_m": 0, **scene},
                "work_order": {"version": 1, "order_id": "independent-order",
                               "project": {"namespace": "test", "project_id": "development"},
                               "part_id": "block", "target_zone": {
                                   "x_min": .18, "x_max": .26, "y_min": -.04, "y_max": .04}}}

    def initialize(self, case):
        self.counter += 1
        root = body.directory(self.work / f"run-{self.counter}", create=True)
        source = self.work / f"case-{self.counter}.json"
        content = body.encoded(case)
        body.create_file(source, content)
        native = body.initialize_episode(root, str(source), body.sha(content))
        return root, source, body.sha(content), native

    def propose(self, root, packet, *, decision="complete", target=None, token="development"):
        proposal = {"version": 1, "run_dir": str(root), "generation": packet["generation"],
                    "image_sha256": packet["image_sha256"], "token": token,
                    "block_box": packet["perception"].get("block_box", [10, 10, 20, 20]), "decision": decision}
        if target is not None:
            proposal["target"] = target
        content = body.encoded(proposal)
        path = self.work / f"proposal-{self.counter}-{token}.json"
        body.create_file(path, content)
        return proposal, path, body.sha(content)

    def verdict(self, root, token="development"):
        return body.decoded(body.read_bytes(root / f"vision-verdict-{body.sha(token.encode())}.json"))

    def test_case_validation_exact_fields_finite_bounds_and_duplicates(self):
        cases = body.cases
        valid = self.case()
        variants = []
        extra = copy.deepcopy(valid)
        extra["oracle"] = True
        variants.append(extra)
        invalid = copy.deepcopy(valid)
        invalid["scene"]["block_xy"][0] = float("nan")
        variants.append(invalid)
        invalid = copy.deepcopy(valid)
        invalid["max_actions"] = True
        variants.append(invalid)
        invalid = copy.deepcopy(valid)
        invalid["scene"]["occlusion_fraction"] = 1.1
        variants.append(invalid)
        for candidate in variants:
            with self.subTest(candidate=candidate), self.assertRaises(cases.CaseError):
                cases.validate(candidate)
        with self.assertRaises(cases.CaseError):
            cases.decode(b'{"version":1,"version":1}')
        self.assertEqual(cases.validate(valid), valid)

    def test_initial_xy_applied_once_and_repeat_never_resets_motion(self):
        case = self.case(block_xy=[-.19, -.025])
        root, source, digest, native = self.initialize(case)
        self.assertAlmostEqual(native["block_xyz"][0], -.19, delta=.0001)
        self.assertAlmostEqual(native["block_xyz"][1], -.025, delta=.0001)
        body.act(root, "native-development", 0, -.21, 0)
        retained_state = body.read_bytes(root / "manifest.json")
        repeated = body.initialize_episode(root, str(source), digest)
        self.assertEqual(repeated["generation"], 1)
        self.assertEqual(body.read_bytes(root / "manifest.json"), retained_state)
        self.assertEqual(body.case_for(root), case)

    def test_changed_source_retained_case_and_partial_initialization_refuse(self):
        root, source, digest, _ = self.initialize(self.case())
        original = source.read_bytes()
        source.write_bytes(original + b" ")
        with self.assertRaises(body.Refusal):
            body.load(root)
        source.write_bytes(original)
        (root / "episode-case.json").write_bytes(original + b" ")
        with self.assertRaises(body.Refusal):
            body.initialize_episode(root, str(source), digest)
        partial = body.directory(self.work / "partial", create=True)
        body.create_file(partial / "episode-case.json", original)
        with self.assertRaises(body.Refusal):
            body.initialize_episode(partial, str(source), digest)
        self.assertFalse((partial / "manifest.json").exists())

    def test_case_source_symlink_and_bad_digest_refuse_before_initialization(self):
        content = body.encoded(self.case())
        source = self.work / "source.json"
        body.create_file(source, content)
        link = self.work / "link.json"
        link.symlink_to(source)
        root = body.directory(self.work / "symlink-run", create=True)
        for path, digest in ((link, body.sha(content)), (source, "0" * 64)):
            with self.subTest(path=path), self.assertRaises(body.Refusal):
                body.initialize_episode(root, str(path), digest)
        self.assertFalse((root / "manifest.json").exists())

    def test_unavailable_and_occluded_images_remain_inspectable_without_effects(self):
        for scene, expected in (({"illumination_scale": 0}, "unavailable"),
                                ({"occlusion_fraction": .7}, "ambiguous")):
            with self.subTest(scene=scene):
                root, _, _, _ = self.initialize(self.case(**scene))
                packet = vision.view(root)
                self.assertEqual(packet["phase"], "ready")
                self.assertEqual(packet["perception"]["state"], expected)
                self.assertEqual(vision.decode_png(body.read_bytes(Path(packet["image_path"]))).shape, (360, 640, 3))
                self.assertEqual(vision.view(root), packet)
                proposal, path, digest = self.propose(root, packet)
                with patch.object(body, "complete") as complete, self.assertRaises(body.Refusal):
                    vision.apply(root, str(path), digest)
                complete.assert_not_called()
                verdict = self.verdict(root)
                self.assertIsNone(verdict["visual_verdict"])
                self.assertTrue(verdict["before_oracle"])
                self.assertEqual(verdict["case_binding"], packet["binding"]["case_binding"])
                self.assertEqual(verdict["proposal"], proposal)
                self.assertEqual(body.action_budget(root)["admitted_dispatches"], 0)

    def test_offset_image_has_invalid_calibration_and_no_world_center(self):
        root, _, _, _ = self.initialize(self.case(camera_offset_x_m=.045))
        packet = vision.view(root)
        self.assertEqual(packet["perception"]["state"], "recognized")
        self.assertFalse(packet["calibration"]["valid"])
        self.assertNotIn("block_center_xy", packet["perception"])
        self.assertNotIn("pusher_center_xy", packet["perception"])
        _, path, digest = self.propose(root, packet, decision="move", target={"x": -.2, "y": 0})
        with patch.object(body, "act") as act, self.assertRaises(body.Refusal):
            vision.apply(root, str(path), digest)
        act.assert_not_called()
        self.assertEqual(body.action_budget(root)["remaining"], 8)
        output = json.dumps(packet)
        for forbidden in ("block_xyz", "pusher_xyz", "block_xy", "illumination_scale", "physical_condition_verified"):
            self.assertNotIn(forbidden, output)

    def test_false_visual_verdict_and_exact_request_retained_before_oracle(self):
        root, _, _, _ = self.initialize(self.case())
        packet = vision.view(root)
        proposal, path, digest = self.propose(root, packet)
        with patch.object(body, "complete") as complete, self.assertRaises(body.Refusal):
            vision.apply(root, str(path), digest)
        complete.assert_not_called()
        verdict = self.verdict(root)
        self.assertFalse(verdict["visual_verdict"])
        self.assertEqual(verdict["state_sha256"], packet["state_sha256"])
        self.assertEqual(verdict["image_sha256"], packet["image_sha256"])
        request = root / f"vision-request-{body.sha(proposal['token'].encode())}.json"
        self.assertEqual(body.read_bytes(request), body.read_bytes(path))
        self.assertFalse(vision.proposal_path(root, proposal["token"]).exists())

    def test_positive_visual_verdict_survives_native_gate_failure_as_unknown(self):
        root, _, _, _ = self.initialize(self.case(block_xy=[.195, .012]))
        packet = vision.view(root)
        _, path, digest = self.propose(root, packet)

        def refused(*_args):
            self.assertTrue(self.verdict(root)["visual_verdict"])
            raise body.Refusal("independent native gate refusal")

        with patch.object(body, "complete", side_effect=refused):
            result = vision.apply(root, str(path), digest)
        self.assertEqual(result["phase"], "unknown")
        self.assertTrue(self.verdict(root)["before_oracle"])
        with patch.object(body, "complete") as complete:
            self.assertEqual(vision.apply(root, str(path), digest)["phase"], "unknown")
        complete.assert_not_called()
        self.assertFalse((root / "order.json").exists())

    def test_budget_exhaustion_refuses_before_wrapper_or_native_intent(self):
        case = self.case(block_xy=[-.16, 0])
        case["max_actions"] = 1
        root, _, _, _ = self.initialize(case)
        packet = vision.view(root)
        _, path, digest = self.propose(root, packet, decision="move", target={"x": -.2, "y": 0}, token="first")
        self.assertEqual(vision.apply(root, str(path), digest)["phase"], "executed")
        packet = vision.view(root)
        self.assertEqual(packet["action_budget"], {"max_actions": 1, "admitted_dispatches": 1, "remaining": 0})
        proposal, path, digest = self.propose(root, packet, decision="move", target={"x": -.1, "y": 0}, token="exhausted")
        before = body.read_bytes(root / "manifest.json")
        with patch.object(body, "act") as act, self.assertRaises(body.Refusal):
            vision.apply(root, str(path), digest)
        act.assert_not_called()
        self.assertFalse(vision.proposal_path(root, proposal["token"]).exists())
        self.assertEqual(body.read_bytes(root / "manifest.json"), before)

    def test_completion_is_an_admitted_action_without_manufactured_motion(self):
        case = self.case(block_xy=[.195, .012])
        case["max_actions"] = 1
        root, _, _, _ = self.initialize(case)
        packet = vision.view(root)
        _, path, digest = self.propose(root, packet)
        result = vision.apply(root, str(path), digest)
        self.assertEqual(result["phase"], "staged")
        self.assertTrue(result["current_software_artifact_check"]["ok"])
        self.assertEqual(body.action_budget(root)["remaining"], 0)
        operations = [body.load_op(path) for path in root.glob("op-*.json")]
        self.assertEqual([operation["request"]["kind"] for operation in operations], ["complete"])
        self.assertEqual(body.load(root)[0]["generation"], 0)

    def test_initialization_marker_exact_case_timing_and_no_stray_file_exception(self):
        source = self.work / "marker-case.json"
        content = body.encoded(self.case())
        body.create_file(source, content)
        digest = body.sha(content)
        root = body.directory(self.work / "marker-run", create=True)
        marker = {"version": 1, "episode_id": "a" * 32, "run_dir": str(root), "case_path": str(source),
                  "case_sha256": digest, "participant": "fresh_host", "started_time_unix": time.time(),
                  "phase": "initializing", "fingerprint": {"runner_sha256": "b" * 64, "vision": vision.fingerprint()}}
        marker_path = root / "episode.json"
        body.create_file(marker_path, body.encoded(dict(marker, case_sha256="0" * 64)))
        with self.assertRaises(body.Refusal):
            body.initialize_episode(root, str(source), digest)
        marker_path.write_bytes(body.encoded(dict(marker, started_time_unix=-1)))
        with self.assertRaises(body.Refusal):
            body.initialize_episode(root, str(source), digest)
        marker_path.write_bytes(body.encoded(marker))
        body.create_file(root / "stray.json", b"{}")
        with self.assertRaises(body.Refusal):
            body.initialize_episode(root, str(source), digest)
        (root / "stray.json").unlink()
        self.assertEqual(body.initialize_episode(root, str(source), digest)["generation"], 0)


if __name__ == "__main__":
    unittest.main()
