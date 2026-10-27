"""Simulated bench vocabulary on the reusable durable single-send client.

Existing callers keep BodyClient. Other adapters use PersistentBodyClient with
an explicit operation contract; they do not inherit block or PNG semantics.
"""
import order_protocol as protocol
from bench_body_contract import BenchOperations, challenge_packet
from persistent_body_client import (
    ENVELOPE_KEYS,
    IDENTITY_KEYS,
    MAX_CLIENT_JOURNAL,
    PROTOCOL,
    PersistentBodyClient,
    Refusal,
    Uncertain,
    endpoint,
    http_call,
    identity,
    pinned_headers,
    read_journal,
)

__all__ = [
    "ENVELOPE_KEYS",
    "IDENTITY_KEYS",
    "MAX_CLIENT_JOURNAL",
    "PROTOCOL",
    "BodyClient",
    "PersistentBodyClient",
    "Refusal",
    "Uncertain",
    "endpoint",
    "http_call",
    "identity",
    "pinned_headers",
    "read_journal",
]

MAX_IMAGE = 8 * 1024 * 1024


class BodyClient(PersistentBodyClient):
    def __init__(self, root, origin, timeout=15):
        super().__init__(root, origin, BenchOperations(), timeout=timeout)

    def _challenge(self, m, challenge):
        return challenge_packet(m["identity"], challenge)

    def _download(self, m, challenge):
        if challenge is None:
            return None
        packet = self._challenge(m, challenge)
        status, content = http_call(self.origin, "GET", "/images/" + challenge["challenge_id"], pinned_headers(m["identity"]),
                                    timeout=self.timeout, maximum=MAX_IMAGE)
        if status != 200 or protocol.sha(content) != packet["image_sha256"] or not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise Refusal("downloaded body image failed its exact PNG digest check")
        path = self.root / "images" / (challenge["challenge_id"] + "-" + packet["image_sha256"] + ".png")
        if path.exists():
            if protocol.read_bytes(path, maximum=MAX_IMAGE) != content:
                raise Refusal("client image changed")
        else:
            protocol.create_file(path, content)
        return {**challenge, "image_path": str(path)}

    def _result(self, m, operation, result):
        if operation == "observe":
            return self._download(m, result)
        return result

    def start_job(self, job_id, zone):
        protocol.identity(job_id)
        protocol.validate_zone(zone)
        return self._command("start_job", {"job_id": job_id, "target_zone": zone})

    def observe(self):
        return self._command("observe", {})

    def propose(self, challenge_id, action, intent, target_x=None, target_y=None):
        protocol.identity(challenge_id)
        if action not in {"move", "measure", "begin_reset", "finish_reset"} or not isinstance(intent, str) or not 1 <= len(intent.strip()) <= 2000:
            raise Refusal("proposal needs a supported action and bounded intent")
        if action == "move":
            target_x, target_y = protocol.finite(target_x), protocol.finite(target_y)
        elif target_x is not None or target_y is not None:
            raise Refusal("only movement proposals accept targets")
        return self._command("propose", {"challenge_id": challenge_id, "action": action, "intent": intent,
                                         "target_x": target_x, "target_y": target_y})

    def dispatch(self, proposal_id):
        protocol.identity(proposal_id)
        return self._command("dispatch", {"proposal_id": proposal_id})

    def disturb(self, operation_id, force_x_n, steps):
        protocol.identity(operation_id)
        force = protocol.finite(force_x_n)
        if type(steps) is not int:
            raise Refusal("diagnostic steps must be an integer")
        return self._command("disturb", {"operation_id": operation_id, "force_x_n": force, "steps": steps})
