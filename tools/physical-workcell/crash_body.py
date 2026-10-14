"""Owned diagnostic body launcher for process-crash qualification, never completion.

after_native stops once after a move's native state save and before its Bench
receipt commit. The ordinary body server is used for restart and reconciliation.
This exposes a simulation persistence gap, not a physical hardware stop guarantee.
"""
import argparse
import copy
import os
import signal
import threading
from pathlib import Path

import bench
import body_network
import body_protocol as wire
import order_protocol as storage

GATES = {"after_native", "before_dispatch", "after_dispatch"}


class CrashBody(body_network.BodyService):
    def __init__(self, root, *, port=0, gate="after_native"):
        if gate not in GATES:
            raise wire.Refusal("unsupported diagnostic crash gate")
        root = storage.directory(root)
        if not bench.Bench(root / "bench").status()["diagnostic_enabled"]:
            raise wire.Refusal("crash gates require a diagnostic body")
        if (root / "barrier.json").exists():
            raise wire.Refusal("a crash gate requires an unused retained barrier identity")
        self.gate, self.fired = gate, False
        self.active_request = None
        super().__init__(root, port=port, barrier=gate if gate != "after_native" else None)

    def _native_gate(self, native_bench, manifest, operation_id, request, receipt):
        active = self.active_request
        if self.fired or not active or active["operation"] != "dispatch" or receipt.get("kind") != "move":
            return
        if native_bench.root != self.root / "bench":
            raise wire.Refusal("diagnostic move belongs to a foreign bench")
        accepted = self._read_record(self._directory(active["command_id"]))
        if accepted["request"] != active or accepted["result_sha256"] is not None:
            raise wire.Refusal("diagnostic gate is not bound to an accepted unresolved command")
        agent_manifest = storage.decode(storage.read_bytes(self.root / "agent" / "agent.json"))
        proposal_id = active["arguments"]["proposal_id"]
        proposal = self.agent._read(agent_manifest, "proposals", proposal_id)
        if (proposal["action"] != "move" or proposal["operation_id"] != operation_id or
                proposal["observation_sha256"] != storage.sha(storage.encoded(request["observation"])) or
                (proposal["target_x"], proposal["target_y"]) != (request["target_x"], request["target_y"])):
            raise wire.Refusal("native crash gate does not match its validated proposal")
        retained = storage.decode(storage.read_bytes(native_bench.root / "bench.json"))
        busy = {"operation_id": operation_id, "kind": "move", "generation": retained["generation"]}
        state_sha = bench.body.sha(bench.body.read_bytes(bench.body.state_path(native_bench.root, manifest["generation"])))
        if (retained["busy"] != busy or retained["diagnostic_enabled"] is not True or
                manifest["generation"] != retained["generation"] + 1 or state_sha != manifest["state_sha256"] or
                manifest["bench_id"] != self.pinned["body_id"] or receipt["operation_id"] != operation_id or
                receipt["generation"] != manifest["generation"] or receipt["state_sha256"] != state_sha or
                receipt["native_time_s"] <= retained["native_time_s"] or receipt["native_steps"] <= 0):
            raise wire.Refusal("native crash evidence is not the exact advanced unresolved move")
        marker = {"version": 1, "barrier": "after_native", "pid": os.getpid(),
                  "command_id": active["command_id"], "request_sha256": wire.command_digest(active),
                  "proposal_id": proposal_id, "operation_id": operation_id, "bench_id": manifest["bench_id"],
                  "manifest_generation": retained["generation"], "native_generation": manifest["generation"],
                  "native_state_sha256": state_sha, "native_time_s": receipt["native_time_s"],
                  "native_steps": receipt["native_steps"],
                  "pusher_block_contact_samples": receipt["pusher_block_contact_samples"],
                  "diagnostic_source_sha256": storage.sha(storage.read_bytes(Path(__file__)))}
        self.fired = True
        storage.persist(self.root / "barrier.json", marker)
        os.kill(os.getpid(), signal.SIGSTOP)

    def command(self, request):
        wire.validate_command(request)
        if self.gate != "after_native":
            return super().command(request)
        with self.lock:
            self.active_request = copy.deepcopy(request)
            original = bench.Bench._finish
            owner = self

            def finish(native_bench, manifest, operation_id, operation_request, receipt):
                owner._native_gate(native_bench, manifest, operation_id, operation_request, receipt)
                return original(native_bench, manifest, operation_id, operation_request, receipt)

            bench.Bench._finish = finish
            try:
                return super().command(request)
            finally:
                bench.Bench._finish = original
                self.active_request = None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--diagnostic", action="store_true")
    parser.add_argument("--gate", choices=sorted(GATES), default="after_native")
    args = parser.parse_args(argv)
    if args.initialize:
        body_network.initialize(args.root, diagnostic_enabled=args.diagnostic)
    service = CrashBody(args.root, port=args.port, gate=args.gate).start()
    print(storage.encoded({"origin": service.origin, "identity": service.identity()}).decode(), flush=True)
    stopped = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    try:
        stopped.wait()
    finally:
        service.close()


if __name__ == "__main__":
    main()
