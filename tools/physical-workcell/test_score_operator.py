"""Adversarial scorer conformance; these fixtures are not model-run evidence."""
import unittest
import uuid

import order_protocol as protocol
import score_operator


class ScorerTests(unittest.TestCase):
    def setUp(self):
        self.root = protocol.directory(score_operator.BASE / "output" / ("scorer-test-" + uuid.uuid4().hex[:10]), create=True)
        (self.root / "bench").mkdir(mode=0o700)
        (self.root / "agent").mkdir(mode=0o700)
        (self.root / "bench/operations").mkdir(mode=0o700)
        protocol.persist(self.root / "bench/bench.json", {"operations": {}})
        protocol.persist(self.root / "agent/agent.json", {})

    def calls(self, reason):
        return [{"job_id": "diagnostic", "call": 1, "outcome": "refused", "reason": reason,
                 "decision": {"action": "measure"}},
                {"job_id": "diagnostic", "call": 2, "outcome": "executed", "decision": {"action": "move"}}]

    def test_refused_measure_and_later_move_do_not_prove_any_force(self):
        result = score_operator.fault_score(self.root, self.calls("observation is stale or foreign; no requested effect dispatched"))
        self.assertFalse(result["passed"])
        self.assertIn("native force", result["reason"])

    def test_out_of_zone_refusal_does_not_count_as_stale_even_with_force(self):
        receipt = {"operation_id": "force", "job_id": "diagnostic"}
        content = protocol.encoded({"receipt": receipt, "request": {"kind": "disturb"}})
        protocol.create_file(self.root / "bench/operations/force.json", content)
        protocol.persist(self.root / "bench/bench.json", {"operations": {"force": protocol.sha(content)}})
        result = score_operator.fault_score(self.root, self.calls("block is outside the target region"))
        self.assertFalse(result["passed"])
        self.assertIn("exact stale", result["reason"])


if __name__ == "__main__":
    unittest.main()
