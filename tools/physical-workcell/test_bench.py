"""SIM6 focused development conformance with actual native state and SQLite.

These gates are separate from the frozen public-interface qualification. Each
test retains its own private inputs and outcome beneath physical-workcell/output.
"""

import copy
import importlib.util
import json
import os
import sqlite3
import unittest
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parent
ZONE = {"x_min": .04, "x_max": .10, "y_min": -.025, "y_max": .025}


def load_backend():
    spec = importlib.util.spec_from_file_location("sim6_conformance_bench", BASE / "bench.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BenchBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.backend = load_backend()
        self.work = BASE / "output" / ("b6test-" + uuid.uuid4().hex[:10])
        self.work.mkdir(mode=0o700)
        self.root = self.work / "bench"
        self.events = []

    def tearDown(self):
        result = self._outcome.result
        failed = any(test is self for test, _ in (*result.failures, *result.errors))
        content = (json.dumps({"test_id": self.id(), "passed": not failed,
                               "scenario_kind": "actual_native_sqlite_conformance",
                               "events": self.events}, sort_keys=True, indent=2) + "\n").encode()
        path = self.work / "conformance.json"
        with path.open("xb") as handle:
            os.chmod(path, 0o600)
            handle.write(content)

    def event(self, label, value):
        self.events.append({"kind": label, "value": value})
        return value

    def snapshot(self):
        """Evidence around refusals; SQLite readback uses its own connection."""
        return {str(path.relative_to(self.root)): path.read_bytes()
                for path in self.root.rglob("*") if path.is_file() and path.suffix != ".lock"
                and path.parent.name != "images"}

    def sqlite_rows(self, query):
        path = self.root / "measurements.sqlite"
        with sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True) as database:
            database.row_factory = sqlite3.Row
            result = [dict(row) for row in database.execute(query)]
        return self.event("independent_sqlite_readback", result)

    def initialize(self, *, diagnostic=False):
        initial = self.event("initialize", self.backend.initialize(self.root, diagnostic))
        self.bench = self.backend.Bench(self.root)
        self.assertEqual(initial["generation"], 0)
        self.assertIsNone(initial["active_job"])
        return initial

    def start(self):
        self.event("start_job", self.bench.start_job("first-job", dict(ZONE)))
        return self.event("observation", self.bench.observe())

    def refusal_without_effect(self, callback):
        before = self.snapshot()
        with self.assertRaises((self.backend.Refusal, self.backend.protocol.Refusal)) as error:
            callback()
        self.event("refusal", str(error.exception))
        self.assertEqual(self.snapshot(), before, "refused request changed retained effects")

    def stage(self):
        """Fixed contact trajectory for a declared native development fixture."""
        packet = self.start()
        contact_samples = 0
        for index, x in enumerate((-.175, -.07, .015)):
            receipt = self.event("stage_move", self.bench.move(f"stage-{index}", packet, x, 0))
            self.assertGreater(receipt["native_steps"], 0)
            contact_samples += receipt["pusher_block_contact_samples"]
            packet = self.event("observation", self.bench.observe())
        self.assertGreater(contact_samples, 0)
        pixels = self.backend.vision.decode_png(Path(packet["image_path"]).read_bytes())
        center = self.backend.vision.image_world_center(self.backend.vision.locate(pixels)["block"]["box"])
        self.assertTrue(ZONE["x_min"] <= center[0] <= ZONE["x_max"], center)
        self.assertTrue(ZONE["y_min"] <= center[1] <= ZONE["y_max"], center)
        return packet

    def test_successive_job_gate_requires_measurement_and_verified_reset(self):
        self.initialize()
        packet = self.start()
        self.refusal_without_effect(lambda: self.bench.start_job("second-job", ZONE))
        self.refusal_without_effect(lambda: self.bench.begin_reset("first-job"))
        self.refusal_without_effect(lambda: self.bench.finish_reset("early-reset", packet))
        self.refusal_without_effect(lambda: self.bench.measure("early-measure", packet))
        self.assertFalse((self.root / "measurements.sqlite").exists())

    def test_measurement_is_a_separate_process_with_exact_persisted_image_binding(self):
        self.initialize()
        packet = self.stage()
        state_before = {path.name: path.read_bytes() for path in self.root.glob("state-*.json")}
        measured = self.event("measure", self.bench.measure("optical-first", packet))
        result = measured["measurement_receipt"]
        self.assertNotEqual(result["worker_pid"], os.getpid())
        self.assertIs(type(result["worker_pid"]), int)
        self.assertGreater(result["worker_pid"], 0)
        for key in ("bench_id", "job_id", "generation", "native_time_s", "image_sha256", "state_sha256"):
            self.assertEqual(result[key], packet[key])
        self.assertEqual(result["operation_id"], "optical-first")
        metric = result["measurement"]
        self.assertEqual(metric["method"], "simulated_orange_RGB_footprint")
        self.assertTrue(1600 <= metric["orange_pixel_count"] <= 2100, metric)
        self.assertAlmostEqual(metric["footprint_area_m2"], .0049, delta=.0009)
        self.assertTrue(.04 <= metric["block_center_xy"][0] <= .10, metric)
        self.assertTrue(-.025 <= metric["block_center_xy"][1] <= .025, metric)
        box = metric["block_box"]
        for center, lower, upper in zip(metric["centroid_pixel_xy"], box[:2], box[2:]):
            self.assertTrue(lower <= center < upper)
        rows = self.sqlite_rows("SELECT * FROM measurements")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(json.loads(row.pop("receipt_json")), result)
        self.assertEqual(row, {key: result[key] for key in row})
        worker = json.loads((self.root / "requests" / (self.backend.body.sha(b"optical-first") + ".worker.json")).read_bytes())
        self.assertEqual(worker["returncode"], 0)
        self.assertEqual(json.loads(worker["stdout"]), result)
        self.assertEqual(state_before, {path.name: path.read_bytes() for path in self.root.glob("state-*.json")})
        self.assertEqual(self.bench.status()["active_job"]["phase"], "measured")

    def test_measurement_replay_is_historical_and_does_not_run_another_worker(self):
        self.initialize()
        packet = self.stage()
        measured = self.event("measure", self.bench.measure("measurement", packet))
        before = self.snapshot()
        self.assertEqual(self.bench.measure("measurement", packet), measured)
        self.assertEqual(self.snapshot(), before)
        fresh = self.event("measured_observation", self.bench.observe())
        self.refusal_without_effect(lambda: self.bench.measure("measurement", fresh))
        self.refusal_without_effect(lambda: self.bench.measure("second-measurement", fresh))
        self.refusal_without_effect(lambda: self.bench.move("forbidden-measured-motion", fresh, -.1, 0))
        self.refusal_without_effect(lambda: self.bench.start_job("second-job", ZONE))
        self.event("begin_reset", self.bench.begin_reset("first-job"))
        self.assertEqual(self.bench.measure("measurement", packet), measured)
        resetting = self.event("resetting_observation", self.bench.observe())
        self.refusal_without_effect(lambda: self.bench.finish_reset("no-contact-reset", resetting))
        self.assertEqual(self.bench.status()["active_job"]["phase"], "resetting")
        self.assertEqual(len(self.sqlite_rows("SELECT * FROM measurements")), 1)

    def test_exact_motion_replay_retains_one_native_effect_and_conflicts_refuse(self):
        self.initialize()
        packet = self.start()
        moved = self.event("move", self.bench.move("one-motion", packet, -.175, 0))
        before = self.snapshot()
        self.assertEqual(self.bench.move("one-motion", packet, -.175, 0), moved)
        self.assertEqual(self.snapshot(), before)
        self.refusal_without_effect(lambda: self.bench.move("one-motion", packet, -.17, 0))
        self.refusal_without_effect(lambda: self.bench.measure("one-motion", packet))
        self.assertEqual(self.bench.status()["generation"], 1)

    def test_external_force_invalidates_stale_motion_and_measurement_before_dispatch(self):
        self.initialize(diagnostic=True)
        packet = self.stage()
        intervention = self.event("diagnostic_force", self.bench.disturb("unexpected-block-motion", 1.5, 80))
        self.assertEqual(intervention["kind"], "diagnostic_external_force")
        self.assertGreater(intervention["generation"], packet["generation"])
        self.assertGreater(intervention["native_time_s"], packet["native_time_s"])
        fresh = self.event("fresh_after_intervention", self.bench.observe())
        self.assertNotEqual(packet["image_sha256"], fresh["image_sha256"])
        self.refusal_without_effect(lambda: self.bench.move("stale-motion", packet, .025, 0))
        self.refusal_without_effect(lambda: self.bench.measure("stale-measurement", packet))
        self.assertFalse((self.root / "measurements.sqlite").exists())
        before = self.snapshot()
        self.assertEqual(self.bench.disturb("unexpected-block-motion", 1.5, 80), intervention)
        self.assertEqual(self.snapshot(), before)
        self.refusal_without_effect(lambda: self.bench.disturb("unexpected-block-motion", 1.4, 80))

    def test_diagnostic_force_needs_explicit_enablement_and_finite_bounds(self):
        self.initialize()
        self.start()
        for force, steps in ((1, 50), (float("nan"), 50), (2.1, 50), (1, True), (1, 151), (0, 50)):
            with self.subTest(force=force, steps=steps):
                self.refusal_without_effect(lambda force=force, steps=steps: self.bench.disturb("invalid-disturb", force, steps))

    def test_foreign_or_modified_observation_cannot_authorize_a_motion(self):
        self.initialize()
        packet = self.start()
        changes = (("bench_id", "0" * 32), ("job_id", "different-job"), ("generation", False),
                   ("state_sha256", "0" * 64), ("native_time_s", packet["native_time_s"] + .002),
                   ("image_sha256", "0" * 64), ("phase", "resetting"), ("source_kind", "real_camera"))
        for key, value in changes:
            with self.subTest(field=key):
                foreign = copy.deepcopy(packet)
                foreign[key] = value
                self.refusal_without_effect(lambda foreign=foreign: self.bench.move("foreign-packet", foreign, -.175, 0))

    def test_corrupted_native_state_never_causes_an_implicit_reset(self):
        self.initialize()
        self.start()
        path = self.root / "state-000000.json"
        with path.open("ab") as handle:
            handle.write(b" ")
        self.event("offline_fault", {"kind": "native_state_bytes_modified", "path": str(path)})
        before = path.read_bytes()
        with self.assertRaises(self.backend.Refusal):
            self.bench.observe()
        with self.assertRaises(self.backend.Refusal):
            self.backend.initialize(self.root)
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.root / "state-000001.json").exists())

    def test_corrupted_source_binding_refuses_without_a_new_generation(self):
        self.initialize()
        packet = self.start()
        manifest_path = self.root / "bench.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["source_fingerprints"]["bench_sha256"] = "0" * 64
        manifest_path.write_bytes(self.backend.body.encoded(manifest))
        self.event("offline_fault", {"kind": "retained_source_binding_modified"})
        self.refusal_without_effect(lambda: self.bench.move("changed-source", packet, -.175, 0))
        self.assertFalse((self.root / "state-000001.json").exists())

    def test_corrupted_retained_model_refuses_without_recreating_the_body(self):
        self.initialize()
        packet = self.start()
        with (self.root / "model.xml").open("ab") as handle:
            handle.write(b" ")
        self.event("offline_fault", {"kind": "retained_model_bytes_modified"})
        self.refusal_without_effect(lambda: self.bench.move("changed-model", packet, -.175, 0))
        self.assertFalse((self.root / "state-000001.json").exists())

    def test_corrupted_image_refuses_measurement_and_does_not_create_a_database(self):
        self.initialize()
        packet = self.stage()
        path = Path(packet["image_path"])
        with path.open("ab") as handle:
            handle.write(b"changed-image")
        self.event("offline_fault", {"kind": "retained_image_bytes_modified", "path": str(path)})
        corrupted = path.read_bytes()
        self.refusal_without_effect(lambda: self.bench.measure("corrupted-image-measurement", packet))
        self.assertEqual(path.read_bytes(), corrupted)
        self.assertFalse((self.root / "measurements.sqlite").exists())

    def test_measurement_receipt_corruption_refuses_historical_replay(self):
        self.initialize()
        packet = self.stage()
        self.event("measure", self.bench.measure("measurement", packet))
        with sqlite3.connect(self.root / "measurements.sqlite") as database:
            receipt = json.loads(database.execute("SELECT receipt_json FROM measurements").fetchone()[0])
            receipt["measurement"]["orange_pixel_count"] += 1
            database.execute("UPDATE measurements SET receipt_json=?", (json.dumps(receipt),))
        self.event("offline_fault", {"kind": "retained_measurement_receipt_modified"})
        self.refusal_without_effect(lambda: self.bench.measure("measurement", packet))

    def test_measurement_column_corruption_is_not_hidden_by_an_unchanged_receipt(self):
        self.initialize()
        packet = self.stage()
        self.event("measure", self.bench.measure("measurement", packet))
        with sqlite3.connect(self.root / "measurements.sqlite") as database:
            database.execute("UPDATE measurements SET job_id='different-job'")
        self.event("offline_fault", {"kind": "retained_measurement_job_column_modified"})
        self.refusal_without_effect(lambda: self.bench.measure("measurement", packet))
        self.assertEqual(self.bench.status()["state"], "unknown")

    def test_retained_interrupted_intent_blocks_all_new_dispatch(self):
        self.initialize()
        packet = self.start()
        path = self.root / "bench.json"
        manifest = json.loads(path.read_bytes())
        manifest["busy"] = {"operation_id": "interrupted", "kind": "move", "generation": packet["generation"]}
        path.write_bytes(self.backend.body.encoded(manifest))
        self.event("offline_fault", {"kind": "retained_interrupted_dispatch_intent"})
        status = self.event("unknown_status", self.bench.status())
        self.assertEqual(status["state"], "unknown")
        self.assertEqual(status["unresolved_effect"]["operation_id"], "interrupted")
        self.refusal_without_effect(lambda: self.bench.start_job("next-job", ZONE))
        self.refusal_without_effect(lambda: self.bench.observe())
        self.refusal_without_effect(lambda: self.bench.move("new-move", packet, -.175, 0))
        self.refusal_without_effect(lambda: self.bench.measure("new-measurement", packet))


if __name__ == "__main__":
    unittest.main()
