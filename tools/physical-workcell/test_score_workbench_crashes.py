"""Pure retained-evidence negative controls; never actual-model qualification."""
import copy
import unittest
import uuid
from pathlib import Path
from unittest import mock

import body_client
import body_protocol as wire
import order_protocol as protocol
import score_workbench_crashes as scorer


def command():
    return {"protocol": wire.PROTOCOL, "adapter_id": "adapter", "body_id": "body", "source_sha256": "0" * 64,
        "client_id": "client", "lease_id": "lease", "epoch": 1, "command_id": "command-one",
        "operation": "dispatch", "arguments": {"proposal_id": "proposal-one"}}


def receipt(request):
    return {**{key: request[key] for key in ("protocol", "adapter_id", "body_id", "source_sha256", "command_id")},
        "request_sha256": protocol.sha(protocol.encoded(request)), "state": "completed", "result": {}, "reason": None,
        "receipt_scope": "retained_command_result", "recorded_epoch": request["epoch"]}


class CrashScorerTests(unittest.TestCase):
    def test_terminal_envelope_rejects_digest_identity_and_epoch_substitution(self):
        request = command()
        good = receipt(request)
        self.assertTrue(scorer.envelope_bound(request, good))
        for changes in ({"request_sha256": "1" * 64}, {"body_id": "foreign"}, {"recorded_epoch": 2}, {"recorded_epoch": True}):
            with self.subTest(changes=changes):
                self.assertFalse(scorer.envelope_bound(request, {**good, **changes}))

    def boundary_fixture(self):
        request = command()
        token = request["command_id"]
        identity = {**{key: request[key] for key in ("protocol", "adapter_id", "body_id", "source_sha256", "epoch")}, "simulation": True}
        public = {"runner_status": "blocked", "model_request_pending": False, "recovery": {"command_id": token}}
        before = {"host": {"app_id": "app", "body_identity": identity, "sequence": 10,
            "stage": {"operation": "dispatch", "arguments": request["arguments"], "command_id": token, "before_commands": []}},
            "client": {"commands": {token: {"request_sha256": protocol.sha(protocol.encoded(request)), "send_count": 1, "operation": "dispatch"}},
                "pending_command_ids": [token], "lease": {"lease_id": "lease", "epoch": 1}}, "posts": [{"sequence": 4, "command_id": token}],
            "public": public, "processes": {"body": 101}, "body_identity": identity,
            "body_command": {"terminal": receipt(request)}}
        offline = copy.deepcopy(before)
        offline["processes"]["body"] = None
        restored = copy.deepcopy(before)
        restored["host"]["sequence"] = 20
        restored["processes"]["body"] = 202
        restored["body_identity"]["epoch"] = 2
        boundary = {"case": "body-uncertain", "role": "body", "command_id": token, "request_sha256": protocol.sha(protocol.encoded(request)),
            "gate": None, "pre_snapshot": "before.json", "offline_snapshot": "offline.json", "restored_snapshot": "restored.json",
            "old_epoch": 1, "new_epoch": 2, "process": {"pid": 101, "group": 101, "exit_observed": True, "returncode": -9,
                "children_before": [], "children_after": []}}
        snapshots = {"before.json": before, "offline.json": offline, "restored.json": restored}
        events = [{"seq": 21, "kind": "reconciled", "outcome": token}, {"seq": 22, "kind": "resume"}]
        transport = {token: {"request": request, "result": receipt(request)}}
        return boundary, identity, transport, events, snapshots

    def test_crash_boundary_rejects_successor_command_before_recovery(self):
        args = self.boundary_fixture()
        with mock.patch.object(scorer, "read", side_effect=lambda path: args[4][path.name]):
            self.assertTrue(scorer.boundary_score(Path("/diagnostic"), *args[:4])["passed"])
            args[4]["restored.json"]["client"]["commands"]["new-command"] = {"request_sha256": "2" * 64, "send_count": 1, "operation": "observe"}
            with self.assertRaisesRegex(protocol.Refusal, "introduced"):
                scorer.boundary_score(Path("/diagnostic"), *args[:4])

    def test_crash_boundary_rejects_wrong_token_boot_and_owned_children(self):
        for mutation in ("token", "boot", "child"):
            args = self.boundary_fixture()
            if mutation == "token":
                args[0]["request_sha256"] = "2" * 64
            elif mutation == "boot":
                args[0]["new_epoch"] = 3
            else:
                args[0]["process"]["children_before"] = [{"pid": 303}]
            with self.subTest(mutation=mutation), mock.patch.object(scorer, "read", side_effect=lambda path, snapshots=args[4]: snapshots[path.name]), self.assertRaises(protocol.Refusal):
                scorer.boundary_score(Path("/diagnostic"), *args[:4])

    def test_receipt_after_resume_is_refused(self):
        args = self.boundary_fixture()
        args[3][0]["seq"], args[3][1]["seq"] = 23, 21
        with mock.patch.object(scorer, "read", side_effect=lambda path: args[4][path.name]), self.assertRaisesRegex(protocol.Refusal, "precede"):
            scorer.boundary_score(Path("/diagnostic"), *args[:4])

    def test_auxiliary_exact_state_is_not_admission_authority(self):
        request = command()
        identity = {key: request[key] for key in ("body_id", "adapter_id", "source_sha256", "epoch")}
        state = {"state": "ready", "identity": identity}
        evidence = {**identity, "state_sha256": protocol.sha(protocol.encoded(state))}
        proof = {"seq": 1, "kind": "admission_proof", "outcome": "dispatch", "time": 9.5, "evidence": evidence}
        relay = [{"request": {"method": "GET", "path": "/state", "started_time": 9, "headers": body_client.pinned_headers(request)},
            "upstream": {"status": 200, "time": 9.2}, "response": protocol.encoded(state)},
            {"request": {"method": "POST", "path": "/lease", "started_time": 9.6, "headers": {}}, "upstream": {"status": 200},
             "response": protocol.encoded({"lease_id": "lease"}), "payload": protocol.encoded({"expected_epoch": 1})}]
        transport = {"command-one": {"request": request, "received": {"sequence": 4}, "relay": {"request": {"started_time": 10.1}}}}
        self.assertTrue(scorer.fresh_admissions(transport, relay, [proof])[0]["passed"])
        relay[0]["request"]["headers"] = {"X-Footwork-Health-Probe": "1"}
        with self.assertRaisesRegex(protocol.Refusal, "auxiliary"):
            scorer.fresh_admissions(transport, relay, [proof])
        relay[0]["request"]["headers"] = {**body_client.pinned_headers(request), "X-Source-Sha256": "1" * 64}
        with self.assertRaisesRegex(protocol.Refusal, "different boot"):
            scorer.fresh_admissions(transport, relay, [proof])

    def test_native_gap_browser_cannot_claim_completion_or_successor(self):
        state = {"app_id": "app", "connection": {"body_id": "body"}, "runner_status": "blocked", "recovery": {"command_id": "command-one"}}
        names = ("crash-offline", "crash-restored", "crash-blocked", "crash-still-blocked")
        steps = [{"name": name, "state": copy.deepcopy(state), "browser_action": "Observed native gap", "visible_text": "Outcome uncertain",
            "client_commands": 4} for name in names]
        client = {"commands": {str(index): {} for index in range(4)}}
        boundary = {"command_id": "command-one"}
        with mock.patch.object(scorer, "read", return_value={"steps": steps}):
            self.assertTrue(scorer.ui_score(Path("/diagnostic"), "body-native-gap", boundary, state, client)["passed"])
            steps[-1]["state"]["runner_status"] = "running"
            with self.assertRaisesRegex(protocol.Refusal, "released"):
                scorer.ui_score(Path("/diagnostic"), "body-native-gap", boundary, state, client)

    def test_dead_host_browser_cache_requires_exact_provenance_and_is_not_live_state(self):
        root = scorer.BASE / "output" / ("sim13-score-offline-" + uuid.uuid4().hex[:10])
        (root / "snapshots").mkdir(parents=True, mode=0o700)
        before = {"app_id": "app", "runner_status": "running", "jobs": [], "connection": {"body_id": "body"},
            "recovery": {"state": "none", "command_id": None}, "model_request_pending": False,
            "active_job_id": "job", "current_frame": {"available": True}, "usage": {"calls": 1}}
        selected = {key: value for key, value in before.items() if key != "usage"}
        protocol.create_file(root / "snapshots/before.json", protocol.encoded({"public": before}))
        protocol.create_file(root / "snapshots/offline.json", protocol.encoded({"diagnostic": "owned dead host snapshot"}))
        state = {**selected, "runner_status": "blocked", "recovery": {"state": "uncertain", "command_id": "command-one"}}
        offline = {"name": "crash-offline", "state": None, "offline": True, "visible_text": "Disconnected: Failed to fetch",
            "browser_action": "Observed owned host SIGKILL", "cached_public": selected, "pins": {"app_id": "app", "body_id": "body"},
            "snapshot_provenance": {"name": "offline.json", "sha256": protocol.sha(protocol.read_bytes(root / "snapshots/offline.json"))}}
        steps = [offline, {"name": "crash-restored", "state": state, "visible_text": "Outcome uncertain", "browser_action": "Reloaded", "client_commands": 4},
            {"name": "crash-recovered", "state": {**state, "runner_status": "paused", "recovery": {"state": "recovered", "command_id": "command-one"}},
             "visible_text": "Receipt recovered", "browser_action": "Clicked Check receipt", "client_commands": 4},
            {"name": "crash-resumed", "state": {**state, "runner_status": "running"}, "visible_text": "Running", "browser_action": "Clicked Resume"},
            {"name": "crash-completed", "state": {**state, "jobs": []}, "visible_text": "Completed", "browser_action": "Observed", "client_commands": 5}]
        protocol.create_file(root / "ui-ledger.json", protocol.encoded({"steps": steps}))
        boundary = {"command_id": "command-one", "pre_snapshot": "before.json", "offline_snapshot": "offline.json"}
        client = {"commands": {str(index): {} for index in range(5)}}
        self.assertTrue(scorer.ui_score(root, "host-inflight", boundary, state, client)["passed"])
        offline["state"] = state
        with mock.patch.object(scorer, "read", return_value={"steps": steps}), self.assertRaisesRegex(protocol.Refusal, "live"):
            scorer.ui_score(root, "host-inflight", boundary, state, client)


if __name__ == "__main__":
    unittest.main()
