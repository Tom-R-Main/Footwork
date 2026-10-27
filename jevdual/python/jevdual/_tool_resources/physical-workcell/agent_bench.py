"""Durable image challenges and guarded proposals for an external multimodal AI."""

import argparse
import json
import uuid
from pathlib import Path

import bench
import order_protocol as protocol

BASE = Path(__file__).resolve().parent
Refusal = bench.Refusal
ACTIONS = {"move", "measure", "begin_reset", "finish_reset"}
LIMIT = 256
DERIVED_LOCATION_FIELDS = {"block_center_xy", "pusher_center_xy", "block_box", "pusher_box",
                           "centroid_pixel_xy", "block_xyz", "pusher_xyz", "block_xy", "pusher_xy",
                           "native_pose", "native_position", "block_pose", "pusher_pose"}


def public_response(value):
    """Keep detector locations on disk; the AI plans from images and known geometry."""
    if isinstance(value, dict):
        return {key: public_response(item) for key, item in value.items() if key not in DERIVED_LOCATION_FIELDS}
    if isinstance(value, list):
        return [public_response(item) for item in value]
    return value


def sources():
    return {**bench.fingerprints(), "agent_bench_sha256": protocol.sha(protocol.read_bytes(BASE / "agent_bench.py"))}


def initialize(root, bench_dir):
    root = protocol.directory(root, create=True)
    bench_dir = protocol.directory(bench_dir)
    if root == bench_dir or root in bench_dir.parents or bench_dir in root.parents:
        raise Refusal("agent and bench directories must be separate")
    status = bench.Bench(bench_dir).status()
    if status["state"] != "ready":
        raise Refusal("agent requires a ready initialized bench")
    with protocol.locked(root):
        if any(p.name != "app.lock" for p in root.iterdir()):
            raise Refusal("agent initialization requires an empty owned directory")
        for name in ("challenges", "proposals", "intents", "results", "events"):
            (root / name).mkdir(mode=0o700)
        manifest = {"version": 1, "session_id": uuid.uuid4().hex,
                    "host_role": "external_multimodal_AI_host", "bench_dir": str(bench_dir),
                    "bench_id": status["bench_id"], "source_fingerprints": sources(),
                    "sequence": 0, "challenges": {}, "proposals": {}, "intents": {}, "results": {}}
        protocol.persist(root / "agent.json", manifest)
    return AgentBench(root).status()


class AgentBench:
    def __init__(self, root):
        self.root = protocol.directory(root)

    def _load(self):
        m = protocol.decode(protocol.read_bytes(self.root / "agent.json"))
        protocol.fields(m, ("version", "session_id", "host_role", "bench_dir", "bench_id",
                            "source_fingerprints", "sequence", "challenges", "proposals", "intents", "results"), "agent manifest")
        if (type(m["version"]) is not int or m["version"] != 1 or
                m["host_role"] != "external_multimodal_AI_host" or m["source_fingerprints"] != sources() or
                type(m["sequence"]) is not int or not 0 <= m["sequence"] <= LIMIT * 8):
            raise Refusal("agent identity, sequence or source changed")
        for key in ("session_id", "bench_id"):
            if not isinstance(m[key], str) or not protocol.UUID.fullmatch(m[key]):
                raise Refusal("agent or bench identity is invalid")
        for kind in ("challenges", "proposals", "intents", "results"):
            if not isinstance(m[kind], dict) or len(m[kind]) > LIMIT:
                raise Refusal("agent record index exceeds its bounded schema")
            for token, digest in m[kind].items():
                protocol.identity(token)
                if not isinstance(digest, str) or not protocol.DIGEST.fullmatch(digest):
                    raise Refusal("agent record digest is invalid")
        target = bench.Bench(protocol.directory(m["bench_dir"]))
        if target.status()["bench_id"] != m["bench_id"]:
            raise Refusal("bound bench identity changed")
        return m, target

    def _save(self, m):
        protocol.persist(self.root / "agent.json", m)

    def _record(self, m, kind, token, value):
        protocol.identity(token)
        if token in m[kind] or len(m[kind]) >= LIMIT:
            raise Refusal("agent record identity reused or budget exhausted")
        content = protocol.encoded(value)
        if len(content) > protocol.MAX_BYTES:
            raise Refusal("agent record exceeds bounded size")
        bench.body.create_file(self.root / kind / (token + ".json"), content)
        m[kind][token] = protocol.sha(content)
        self._save(m)

    def _read(self, m, kind, token):
        protocol.identity(token)
        if token not in m[kind]:
            raise Refusal("agent record is not owned by this session")
        content = protocol.read_bytes(self.root / kind / (token + ".json"))
        if protocol.sha(content) != m[kind][token]:
            raise Refusal("immutable agent record changed")
        return protocol.decode(content)

    def _event(self, m, kind, value):
        if m["sequence"] >= LIMIT * 8:
            raise Refusal("agent event budget exhausted")
        sequence = m["sequence"] + 1
        bench.body.create_file(self.root / "events" / f"{sequence:06d}.json",
                              protocol.encoded({"sequence": sequence, "kind": kind, "value": value}))
        m["sequence"] = sequence
        self._save(m)

    def _observe(self, m, target):
        try:
            packet = target.observe()
            state = target.status()
            job = state["active_job"]
            if packet["bench_id"] != m["bench_id"] or packet["job_id"] != (job["job_id"] if job else None):
                raise Refusal("observation and task identity disagree")
            challenge = {"challenge_id": "challenge-" + uuid.uuid4().hex,
                         "session_id": m["session_id"], "sequence": m["sequence"] + 1,
                         "observation_sha256": protocol.sha(protocol.encoded(packet)), "observation": packet,
                         "task": {"zone": job["target_zone"] if job else None,
                                  "home_zone": dict(bench.HOME_ZONE),
                                  "pusher_dimensions_m": {"x": .04, "y": .14},
                                  "bounds": {"x_min": -.32, "x_max": .18, "y_min": -.15, "y_max": .15}},
                         "image_path": packet["image_path"]}
            self._record(m, "challenges", challenge["challenge_id"], challenge)
            self._event(m, "observe", {"challenge_id": challenge["challenge_id"]})
            return challenge
        except Exception as exc:
            self._event(m, "observe_failed", {"reason": str(exc)})
            raise

    def observe(self):
        with protocol.locked(self.root):
            return self._observe(*self._load())

    def _challenge(self, m, token):
        c = self._read(m, "challenges", token)
        protocol.fields(c, ("challenge_id", "session_id", "sequence", "observation_sha256", "observation", "task", "image_path"), "challenge")
        packet = c["observation"]
        protocol.fields(packet, bench.OBSERVATION_FIELDS, "observation")
        image_path = Path(packet["image_path"])
        if (c["session_id"] != m["session_id"] or c["challenge_id"] != token or
                c["observation_sha256"] != protocol.sha(protocol.encoded(packet)) or
                packet["bench_id"] != m["bench_id"] or c["image_path"] != str(image_path) or
                image_path.parent != Path(m["bench_dir"]) / "images" or
                protocol.sha(protocol.read_bytes(image_path, maximum=8 * 1024 * 1024)) != packet["image_sha256"]):
            raise Refusal("challenge image or identity binding changed")
        return c

    @staticmethod
    def _validate_action(action, intent, x, y):
        if action not in ACTIONS or not isinstance(intent, str) or not 1 <= len(intent.strip()) <= 2000:
            raise Refusal("proposal requires a supported action and bounded AI intent")
        if action == "move":
            return protocol.finite(x), protocol.finite(y)
        if x is not None or y is not None:
            raise Refusal("only move accepts target coordinates")
        return None, None

    def propose(self, challenge_id, action, intent, target_x=None, target_y=None):
        x, y = self._validate_action(action, intent, target_x, target_y)
        with protocol.locked(self.root):
            m, _ = self._load()
            c = self._challenge(m, challenge_id)
            proposal = {"proposal_id": "proposal-" + uuid.uuid4().hex,
                        "session_id": m["session_id"], "challenge_id": challenge_id,
                        "observation_sha256": c["observation_sha256"], "action": action, "intent": intent,
                        "target_x": x, "target_y": y, "operation_id": "agent-" + uuid.uuid4().hex}
            self._record(m, "proposals", proposal["proposal_id"], proposal)
            self._event(m, "propose", {"proposal_id": proposal["proposal_id"], "intent": intent})
            return proposal

    def dispatch(self, proposal_id):
        with protocol.locked(self.root):
            m, target = self._load()
            p = self._read(m, "proposals", proposal_id)
            protocol.fields(p, ("proposal_id", "session_id", "challenge_id", "observation_sha256", "action", "intent", "target_x", "target_y", "operation_id"), "proposal")
            self._validate_action(p["action"], p["intent"], p["target_x"], p["target_y"])
            protocol.identity(p["operation_id"])
            c = self._challenge(m, p["challenge_id"])
            if p["proposal_id"] != proposal_id or p["session_id"] != m["session_id"] or p["observation_sha256"] != c["observation_sha256"]:
                raise Refusal("proposal and challenge binding changed")
            if proposal_id in m["results"]:
                self._read(m, "intents", proposal_id)
                return self._read(m, "results", proposal_id)
            if any(token not in m["results"] or self._read(m, "results", token)["outcome"] == "unknown"
                   for token in m["intents"]):
                return {"proposal_id": proposal_id, "outcome": "unknown", "reason": "unresolved dispatch intent; no replay or new effect allowed", "next_observation": None}
            self._record(m, "intents", proposal_id, {"proposal_sha256": m["proposals"][proposal_id],
                         "challenge_sha256": m["challenges"][p["challenge_id"]], "operation_id": p["operation_id"]})
            self._event(m, "dispatch_intent", {"proposal_id": proposal_id})
            result = {"proposal_id": proposal_id, "outcome": "unknown",
                      "observation_scope": "snapshot_at_dispatch_result"}
            try:
                if p["action"] == "begin_reset":
                    if target.observe() != c["observation"]:
                        raise Refusal("reset proposal observation is stale; no effect dispatched")
                    receipt = target.begin_reset(c["observation"]["job_id"])
                elif p["action"] == "move":
                    receipt = target.move(p["operation_id"], c["observation"], p["target_x"], p["target_y"])
                else:
                    receipt = getattr(target, p["action"])(p["operation_id"], c["observation"])
                result.update(outcome="executed", receipt=receipt)
            except Exception as exc:  # noqa: BLE001 - persist unknown after any dispatched failure.
                result["reason"] = str(exc)
                try:
                    if isinstance(exc, (Refusal, protocol.Refusal)) and target.status()["state"] == "ready":
                        result["outcome"] = "refused"
                except Exception as status_exc:  # noqa: BLE001 - uncertain status cannot clear the intent.
                    result["status_error"] = str(status_exc)
            try:
                result["next_observation"] = self._observe(m, target)
            except Exception as exc:  # noqa: BLE001 - preserve effect result when subsequent observation fails.
                result.update(next_observation=None, observation_error=str(exc))
            self._record(m, "results", proposal_id, result)
            self._event(m, "dispatch_result", {"proposal_id": proposal_id, "outcome": result["outcome"]})
            return result

    def status(self):
        with protocol.locked(self.root):
            m, target = self._load()
            return {"session_id": m["session_id"], "host_role": m["host_role"], "bench_id": m["bench_id"],
                    "source_fingerprints": m["source_fingerprints"], "sequence": m["sequence"],
                    "unresolved_proposals": [k for k in m["intents"] if k not in m["results"] or
                                             self._read(m, "results", k)["outcome"] == "unknown"],
                    "bench": target.status()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True, type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--bench-dir", required=True, type=Path)
    for name in ("observe", "status"):
        sub.add_parser(name)
    proposal = sub.add_parser("propose")
    proposal.add_argument("--challenge-id", required=True)
    proposal.add_argument("--action", required=True, choices=sorted(ACTIONS))
    proposal.add_argument("--intent", required=True)
    proposal.add_argument("--target-x", type=float)
    proposal.add_argument("--target-y", type=float)
    dispatch = sub.add_parser("dispatch")
    dispatch.add_argument("--proposal-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = initialize(args.session_dir, args.bench_dir)
        else:
            host = AgentBench(args.session_dir)
            if args.command == "propose":
                result = host.propose(args.challenge_id, args.action, args.intent, args.target_x, args.target_y)
            elif args.command == "dispatch":
                result = host.dispatch(args.proposal_id)
            else:
                result = getattr(host, args.command)()
        print(json.dumps(public_response(result), sort_keys=True, allow_nan=False))
        return 0
    except (Refusal, protocol.Refusal, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"outcome": "refused", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
