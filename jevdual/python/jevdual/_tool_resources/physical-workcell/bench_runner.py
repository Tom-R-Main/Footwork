"""Inspectable RGB-only host for successive simulated bench experiments.

This is a deterministic diagnostic policy, not a language-model robotics trial.
All guidance comes from exact public PNGs; private native state belongs to scoring.
"""

import argparse
import importlib.util
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("persistent_bench", BASE / "bench.py")
bench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bench)
body, vision = bench.body, bench.vision
ZONE = {"x_min": .035, "x_max": .105, "y_min": -.025, "y_max": .025}
HOME_X = -.12
MAX_ACTIONS = 64


class RGBHost:
    def __init__(self, root, journal):
        self.root = body.directory(root)
        self.journal = body.directory(journal, create=True)
        self.events = []
        self.sequence = 0
        self.job_id = None

    def api(self):
        # Each call reloads the same retained body; never initializes an episode.
        return bench.Bench(self.root)

    def record(self, kind, **fields):
        event = {"index": len(self.events), "kind": kind, **fields}
        body.create_file(self.journal / f"event-{len(self.events):04d}.json", body.encoded(event))
        self.events.append(event)
        return event

    def observe(self):
        packet = self.api().observe()
        content = body.read_bytes(Path(packet["image_path"]))
        if body.sha(content) != packet["image_sha256"]:
            raise body.Refusal("public image bytes changed")
        located = vision.locate(vision.decode_png(content))
        block = vision.image_world_center(located["block"]["box"])
        pusher = vision.image_world_center(located["pusher"]["box"])
        self.record("rgb_observation", packet=packet, rgb_block_xy=block, rgb_pusher_xy=pusher)
        return packet, block, pusher

    def move(self, packet, pusher, target, purpose):
        delta = [target[i] - pusher[i] for i in (0, 1)]
        distance = math.hypot(*delta)
        if distance > .11:
            target = [pusher[i] + delta[i] * .11 / distance for i in (0, 1)]
        self.sequence += 1
        if self.sequence > MAX_ACTIONS:
            raise body.Refusal("RGB host motion budget exhausted")
        operation = f"{self.job_id}-motion-{self.sequence:03d}"
        receipt = self.api().move(operation, packet, *target)
        self.record("motion", purpose=purpose, target_xy=target, receipt=receipt)
        return receipt

    def position(self, center_x, purpose):
        for _ in range(MAX_ACTIONS):
            packet, block, pusher = self.observe()
            if abs(block[1]) > .018:
                raise body.Refusal("RGB block is outside the supported axial recovery corridor")
            if abs(block[0] - center_x) <= .012:
                return packet
            direction = 1 if center_x > block[0] else -1
            side = block[0] - direction * .065
            wrong_side = direction * (block[0] - pusher[0]) < .050
            if wrong_side:
                target = [pusher[0], .135] if pusher[1] < .125 else [side, .135]
            elif abs(pusher[1]) > .006:
                # Stay clear of the cube before descending from the bypass lane.
                target = [side, pusher[1]] if abs(pusher[0] - side) > .010 else [pusher[0], 0]
            else:
                gap = max(0, direction * (block[0] - pusher[0]) - .055)
                advance = min(.09, abs(center_x - block[0]) + gap)
                target = [pusher[0] + direction * advance, 0]
            if not -.32 <= target[0] <= .18:
                raise body.Refusal("RGB recovery requires a pusher target outside the workspace")
            self.move(packet, pusher, target, purpose)
        raise body.Refusal("RGB placement did not converge")

    def park(self, purpose):
        for _ in range(MAX_ACTIONS):
            packet, block, pusher = self.observe()
            if abs(pusher[0] + .3) <= .004 and abs(pusher[1]) <= .004:
                return packet
            if pusher[0] > block[0] - .065 and pusher[1] < .125:
                target = [pusher[0], .135]
            elif pusher[0] > -.29:
                target = [-.3, pusher[1]]
            else:
                target = [-.3, 0]
            self.move(packet, pusher, target, purpose)
        raise body.Refusal("RGB pusher parking did not converge")

    def run_job(self, job_id, *, disturbance=False):
        self.job_id, self.sequence = job_id, 0
        started = self.api().start_job(job_id, ZONE)
        self.record("job_started", status=started)
        self.position(.07, "prepare")
        packet = self.park("clear_measurement_area")
        recovery = None
        if disturbance:
            changed = self.api().disturb(f"{job_id}-external-force", -1.5, 80)
            self.record("diagnostic_external_force", receipt=changed)
            refused = []
            for command in ("move", "measure"):
                before = self.api().status()
                try:
                    if command == "move":
                        self.api().move(f"{job_id}-stale-motion", packet, -.28, 0)
                    else:
                        self.api().measure(f"{job_id}-stale-measurement", packet)
                except body.Refusal as exc:
                    after = self.api().status()
                    if before != after:
                        raise AssertionError("stale refusal changed durable public state") from exc
                    refused.append(command)
                    self.record("stale_effect_refused", command=command, reason=str(exc))
                else:
                    raise AssertionError(f"stale {command} was accepted")
            fresh, changed_block, _ = self.observe()
            previous = vision.image_world_center(vision.locate(vision.decode_png(
                body.read_bytes(Path(packet["image_path"]))))["block"]["box"])
            displacement = abs(changed_block[0] - previous[0])
            if displacement < .02:
                raise AssertionError("diagnostic force did not create a meaningful observed displacement")
            recovery = {"stale_refused": refused, "rgb_displacement_m": displacement,
                        "before_generation": packet["generation"], "after_generation": fresh["generation"]}
            self.position(.07, "recover_unexpected_displacement")
            packet = self.park("clear_recovered_measurement_area")
        measurement = self.api().measure(f"{job_id}-measurement", packet)
        self.record("computer_measurement", receipt=measurement)
        repeat = self.api().measure(f"{job_id}-measurement", packet)
        if repeat != measurement:
            raise AssertionError("measurement repeat differs from exact historical receipt")
        self.record("measurement_reply_reconciled", receipt=repeat)
        self.record("reset_started", status=self.api().begin_reset(job_id))
        self.position(HOME_X, "contact_reset")
        packet = self.park("return_pusher_home")
        finished = self.api().finish_reset(f"{job_id}-reset", packet)
        self.record("reset_verified", receipt=finished)
        return {"job_id": job_id, "measurement": measurement, "reset": finished,
                "recovery": recovery, "motion_count": self.sequence}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bench-dir", required=True)
    parser.add_argument("--journal-dir", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--disturb", action="store_true")
    args = parser.parse_args()
    host = RGBHost(Path(args.bench_dir), Path(args.journal_dir))
    try:
        result = host.run_job(args.job_id, disturbance=args.disturb)
    except Exception as exc:
        host.record("attempt_failed", error_type=type(exc).__name__, error=str(exc))
        raise
    print(body.encoded(result).decode(), end="")


if __name__ == "__main__":
    main()
