"""SIM7 conformance for the external AI boundary against actual native benches."""

import contextlib
import io
import json
import unittest
import uuid
from pathlib import Path
from unittest import mock

import agent_bench as agent

ZONE = {"x_min": .04, "x_max": .10, "y_min": -.025, "y_max": .025}


class AgentBenchTests(unittest.TestCase):
    def setUp(self):
        self.root = agent.bench.body.directory(agent.BASE / "output" / ("a7test-" + uuid.uuid4().hex[:10]), create=True)
        self.bench_dir = self.root / "bench"
        agent.bench.initialize(self.bench_dir, diagnostic_enabled=True)
        self.bench = agent.bench.Bench(self.bench_dir)
        self.bench.start_job("job-one", ZONE)
        self.session = self.root / "agent"
        agent.initialize(self.session, self.bench_dir)
        self.host = agent.AgentBench(self.session)
        self.events = []

    def tearDown(self):
        result = self._outcome.result
        failed = any(test is self for test, _ in (*result.failures, *result.errors))
        agent.bench.body.create_file(self.root / "conformance.json", agent.protocol.encoded(
            {"test_id": self.id(), "passed": not failed, "events": self.events}))

    def proposal(self, action="move", challenge=None, **kwargs):
        challenge = challenge or self.host.observe()
        if action == "move" and not kwargs:
            kwargs = {"target_x": -.25, "target_y": 0}
        p = self.host.propose(challenge["challenge_id"], action, "AI development conformance intent", **kwargs)
        self.events.append({"challenge": challenge, "proposal": p})
        return p

    def dispatch(self, p):
        result = self.host.dispatch(p["proposal_id"])
        self.events.append({"dispatch": result})
        return result

    def test_challenge_has_only_images_task_and_public_observation(self):
        c = self.host.observe()
        self.assertEqual(c["observation_sha256"], agent.protocol.sha(agent.protocol.encoded(c["observation"])))
        self.assertEqual(c["task"]["zone"], ZONE)
        self.assertEqual(Path(c["image_path"]).read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertNotIn("block_xyz", json.dumps(c))
        self.assertNotIn("pusher_xyz", json.dumps(c))
        self.assertEqual(self.host.status()["host_role"], "external_multimodal_AI_host")

    def test_proposal_persists_intent_without_effect(self):
        before = self.bench.status()
        p = self.proposal()
        self.assertEqual(before, self.bench.status())
        self.assertTrue((self.session / "proposals" / (p["proposal_id"] + ".json")).exists())
        self.assertEqual(list((self.session / "intents").iterdir()), [])

    def test_move_executes_once_duplicate_returns_exact_result(self):
        p = self.proposal()
        result = self.dispatch(p)
        self.assertEqual(result["outcome"], "executed")
        self.assertEqual(result["receipt"]["operation_id"], p["operation_id"])
        before = self.bench.status()
        self.assertEqual(result, self.dispatch(p))
        self.assertEqual(before, self.bench.status())

    def test_stale_move_refuses_and_returns_fresh_image(self):
        c = self.host.observe()
        p = self.proposal(challenge=c)
        self.bench.disturb("external-force", -.4, 50)
        generation = self.bench.status()["generation"]
        result = self.dispatch(p)
        self.assertEqual(result["outcome"], "refused")
        self.assertEqual(self.bench.status()["generation"], generation)
        self.assertGreater(result["next_observation"]["observation"]["generation"], c["observation"]["generation"])

    def test_measurement_placement_refusal_does_not_create_sqlite(self):
        result = self.dispatch(self.proposal("measure"))
        self.assertEqual(result["outcome"], "refused")
        self.assertFalse((self.bench_dir / "measurements.sqlite").exists())

    def test_wrong_reset_phase_preserves_bench(self):
        for action in ("begin_reset", "finish_reset"):
            before = self.bench.status()
            result = self.dispatch(self.proposal(action))
            self.assertEqual(result["outcome"], "refused")
            self.assertEqual(before, self.bench.status())

    def test_nonfinite_and_conflicting_arguments_never_create_proposal(self):
        c = self.host.observe()
        for action, x, y in (("move", float("nan"), 0), ("move", True, 0), ("move", 0, None), ("measure", 0, 0)):
            with self.assertRaises((agent.Refusal, agent.protocol.Refusal)):
                self.host.propose(c["challenge_id"], action, "intent", x, y)
        self.assertEqual(list((self.session / "proposals").iterdir()), [])

    def test_foreign_challenge_and_unsafe_identity_refuse(self):
        for token in ("challenge-" + uuid.uuid4().hex, "../bench/bench"):
            with self.assertRaises((agent.Refusal, agent.protocol.Refusal)):
                self.host.propose(token, "measure", "intent")

    def test_changed_proposal_refuses_before_dispatch(self):
        p = self.proposal()
        path = self.session / "proposals" / (p["proposal_id"] + ".json")
        path.write_bytes(path.read_bytes().replace(b'"target_x": -0.25', b'"target_x": 0.18'))
        before = self.bench.status()
        with self.assertRaises((agent.Refusal, agent.protocol.Refusal)):
            self.dispatch(p)
        self.assertEqual(before, self.bench.status())

    def test_changed_challenge_image_refuses(self):
        c = self.host.observe()
        p = self.proposal(challenge=c)
        Path(c["image_path"]).write_bytes(b"changed image")
        with self.assertRaises((agent.Refusal, agent.protocol.Refusal)):
            self.dispatch(p)
        self.assertEqual(list((self.session / "intents").iterdir()), [])

    def test_unresolved_intent_blocks_same_and_new_proposal(self):
        p = self.proposal()
        with agent.protocol.locked(self.session):
            m, _ = self.host._load()
            self.host._record(m, "intents", p["proposal_id"], {"interrupted_fixture": True})
        before = self.bench.status()
        self.assertEqual(self.dispatch(p)["outcome"], "unknown")
        self.assertEqual(self.dispatch(self.proposal())["outcome"], "unknown")
        self.assertEqual(before, self.bench.status())

    def test_measurement_worker_failure_retains_unknown_and_blocks_replay(self):
        packet = self.bench.observe()
        for index, x in enumerate((-.175, -.07, .015)):
            self.bench.move("stage-" + str(index), packet, x, 0)
            packet = self.bench.observe()
        p = self.proposal("measure")
        with mock.patch.object(agent.bench.subprocess, "run", return_value=mock.Mock(returncode=1, stdout=b"", stderr=b"fixture worker failure")):
            result = self.dispatch(p)
        self.assertEqual(result["outcome"], "unknown")
        self.assertEqual(self.bench.status()["state"], "unknown")
        self.assertIsNone(result["next_observation"])
        self.assertEqual(self.dispatch(p), result)
        self.assertIn(p["proposal_id"], self.host.status()["unresolved_proposals"])

    def test_source_change_and_foreign_bench_identity_block_dispatch(self):
        p = self.proposal()
        before = self.bench.status()
        with mock.patch.object(agent, "sources", return_value={"changed": "source"}), self.assertRaises(agent.Refusal):
            self.dispatch(p)
        m = agent.protocol.decode(agent.protocol.read_bytes(self.session / "agent.json"))
        m["bench_id"] = uuid.uuid4().hex
        agent.protocol.persist(self.session / "agent.json", m)
        with self.assertRaises(agent.Refusal):
            self.dispatch(p)
        self.assertEqual(before, self.bench.status())

    def test_error_after_real_move_stays_unknown_even_if_bench_ready(self):
        original = agent.bench.Bench.move

        def lost_reply(target, *args, **kwargs):
            original(target, *args, **kwargs)
            raise RuntimeError("fixture reply lost after real native motion")

        p = self.proposal()
        with mock.patch.object(agent.bench.Bench, "move", lost_reply):
            result = self.dispatch(p)
        self.assertEqual(result["outcome"], "unknown")
        self.assertEqual(self.bench.status()["state"], "ready")
        before = self.bench.status()
        self.assertEqual(self.dispatch(p), result)
        self.assertEqual(self.dispatch(self.proposal())["outcome"], "unknown")
        self.assertEqual(self.bench.status(), before)
        self.assertIn(p["proposal_id"], self.host.status()["unresolved_proposals"])

    def test_public_cli_measurement_reset_and_status_strip_detector_locations(self):
        packet = self.bench.observe()
        for index, x in enumerate((-.175, -.07, .015)):
            self.bench.move("stage-" + str(index), packet, x, 0)
            packet = self.bench.observe()

        def cli(*args):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(agent.main(["--session-dir", str(self.session), *args]), 0)
            value = json.loads(output.getvalue())
            self.events.append({"public_cli": value})
            return value

        p = self.proposal("measure")
        measured = cli("dispatch", "--proposal-id", p["proposal_id"])
        self.assertEqual(measured["outcome"], "executed")
        metric = measured["receipt"]["measurement_receipt"]["measurement"]
        self.assertIn("orange_pixel_count", metric)
        self.assertIn("footprint_area_m2", metric)
        private = agent.protocol.decode(agent.protocol.read_bytes(self.session / "results" / (p["proposal_id"] + ".json")))
        self.assertIn("block_center_xy", private["receipt"]["measurement_receipt"]["measurement"])
        reset = self.proposal("begin_reset", challenge=measured["next_observation"])
        responses = [measured, cli("dispatch", "--proposal-id", reset["proposal_id"]), cli("status")]

        def assert_no_locations(value):
            if isinstance(value, dict):
                self.assertFalse(agent.DERIVED_LOCATION_FIELDS.intersection(value))
                for item in value.values():
                    assert_no_locations(item)
            elif isinstance(value, list):
                for item in value:
                    assert_no_locations(item)

        for response in responses:
            assert_no_locations(response)
        future = {"nested": [{"native_pose": [1, 2, 3], "block_xyz": [1, 2, 3], "target_x": .1}]}
        self.assertEqual(agent.public_response(future), {"nested": [{"target_x": .1}]})


if __name__ == "__main__":
    unittest.main()
