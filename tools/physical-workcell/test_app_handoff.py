"""Actual local app/controller adapter conformance; independent private development inputs."""

import copy
import importlib.util
import json
import os
import signal
import socket
import sqlite3
import subprocess
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("handoff_test", BASE / "app_handoff.py")
handoff = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(handoff)
protocol = handoff.protocol
PYTHON = BASE / ".venv/bin/python"


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.work = protocol.directory(protocol.OUTPUT / ("h5" + uuid.uuid4().hex[:6]), create=True)
        self.app_dir = protocol.directory(self.work / "a", create=True)
        self.evidence = []
        self.processes = []
        self.handles = []
        self.owned_controllers = []
        self.order = {"version": 1, "order_id": "handoff-private-order",
                      "project": {"namespace": "test", "project_id": "handoff-development"}, "part_id": "block",
                      "target_zone": {"x_min": .18, "x_max": .26, "y_min": -.04, "y_max": .04},
                      "revision": 1, "state": "open"}
        self.scene = {"block_xy": [-.17, 0], "illumination_scale": 1,
                      "occlusion_fraction": 0, "camera_offset_x_m": 0}
        self.scene_path = self.work / "scene.json"
        self.handoff_dir = None
        self.counter = 0

    def tearDown(self):
        for controller_dir, pid, incarnation in self.owned_controllers:
            reply = self.raw_controller(controller_dir, "health", allow_failure=True)
            if reply.get("pid") == pid and reply.get("current_incarnation") == incarnation:
                with self.subTest(cleanup_pid=pid):
                    os.kill(pid, signal.SIGTERM)
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=6)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=4)
        for handle in self.handles:
            handle.close()
        result = self._outcome.result
        failed = any(test is self or getattr(test, "test_case", None) is self
                     for test, _ in (*result.failures, *result.errors))
        protocol.create_file(self.work / "conformance.json", protocol.encoded({
            "test_id": self.id(), "passed": not failed, "events": self.evidence,
            "scope": "actual_local_process_adapter; mechanical HTTP use is not browser evidence"}))

    def command(self, script, command, *args, allow_failure=False, timeout=25):
        result = subprocess.run([str(PYTHON), str(BASE / script), command, *map(str, args)],
                                capture_output=True, timeout=timeout, check=False)
        try:
            value = protocol.decode(result.stdout)
        except protocol.Refusal as exc:
            self.fail(f"public CLI returned no bounded JSON: {result.stdout!r}; {result.stderr!r}; {exc}")
        self.evidence.append({"script": script, "command": command, "exit_code": result.returncode, "reply": value})
        self.no_oracle(value)
        if not allow_failure:
            self.assertEqual(result.returncode, 0, value)
        return value

    def no_oracle(self, value):
        serialized = json.dumps(value)
        for forbidden in ("block_xyz", "pusher_xyz", "physical_condition_verified", "block_center_in_zone", "qpos", "xpos"):
            self.assertNotIn(forbidden, serialized)

    def start_app(self, *, restart=False):
        if not restart:
            source = self.work / "order.json"
            content = protocol.encoded(self.order)
            protocol.create_file(source, content)
            initialized = self.command("order_app.py", "init", "--app-dir", self.app_dir,
                                       "--order-file", source, "--order-sha256", protocol.sha(content))
            self.app_id = initialized["app_id"]
            port = 0
        else:
            port = urllib.parse.urlsplit(self.url).port
        logfile = open(self.work / f"app-{len(self.processes)}.log", "xb")  # noqa: SIM115 - owned until tearDown
        os.chmod(logfile.name, 0o600)
        self.handles.append(logfile)
        process = subprocess.Popen([str(PYTHON), str(BASE / "order_app.py"), "serve", "--app-dir", str(self.app_dir),
                                    "--port", str(port)], stdout=logfile, stderr=subprocess.STDOUT)
        self.processes.append(process)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self.fail(f"app startup failed; private logs: {self.work}")
            readiness = self.app_dir / "readiness.json"
            if readiness.exists():
                value = protocol.decode(readiness.read_bytes())
                if value.get("phase") == "ready" and value.get("pid") == process.pid:
                    self.url = value["origin"]
                    self.assertEqual(value["app_id"], self.app_id)
                    return process
            time.sleep(.02)
        self.fail("app readiness timeout")

    def http(self, route, value=None, *, allow_failure=False):
        request = urllib.request.Request(self.url + route, data=None if value is None else protocol.encoded(value),
                                         headers={"Content-Type": "application/json", "Origin": self.url,
                                                  "X-Footwork-App-ID": self.app_id})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            response = opener.open(request, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            code = response.code
            reply = protocol.decode(response.read(protocol.MAX_BYTES + 1))
        self.evidence.append({"http": route, "method": "GET" if value is None else "POST", "code": code, "reply": reply})
        self.no_oracle(reply)
        if not allow_failure:
            self.assertEqual(code, 200, reply)
        return code, reply

    def bind(self):
        _, value = self.http(f"/api/orders/{self.order['order_id']}/bind", {
            "expected_revision": 1, "binding_operation_id": "private-binding"})
        self.lease = value["lease"]
        self.handoff_dir = Path(self.lease["handoff_dir"])

    def prepare(self, *, pace=0, delay=0):
        if not hasattr(self, "lease"):
            self.start_app()
            self.bind()
        if not self.scene_path.exists():
            protocol.create_file(self.scene_path, protocol.encoded(self.scene))
        self.scene_sha = protocol.sha(self.scene_path.read_bytes())
        value = self.command("app_handoff.py", "prepare", "--app-url", self.url, "--expected-app-id", self.app_id,
                             "--lease-id", self.lease["lease_id"], "--scene-file", self.scene_path,
                             "--scene-sha256", self.scene_sha, "--pace-s", pace, "--dispatch-delay-s", delay)
        self.assertEqual(value["phase"], "prepared", value)
        controller = value["controller"]
        ownership = (self.lease["controller_dir"], controller["pid"], controller["current_incarnation"])
        if ownership not in self.owned_controllers:
            self.owned_controllers.append(ownership)
        return value

    def adapter(self, command, *args, allow_failure=False):
        return self.command("app_handoff.py", command, "--handoff-dir", self.handoff_dir,
                            *args, allow_failure=allow_failure)

    def raw_controller(self, control, command, *args, allow_failure=False):
        return self.command("controller.py", command, "--controller-dir", control, *args, allow_failure=allow_failure)

    def packet(self):
        value = self.adapter("observe")
        self.assertEqual(value["phase"], "ready", value)
        return value["observation"]

    def proposal(self, packet, token, *, complete=False, noncanonical=False):
        value = {"version": 1, "run_dir": self.lease["run_dir"], "generation": packet["generation"],
                 "image_sha256": packet["image_sha256"], "token": token,
                 "block_box": packet["perception"]["block_box"], "decision": "complete" if complete else "move"}
        if not complete:
            value["target"] = {"x": min(.17, packet["perception"]["pusher_center_xy"][0] + .10), "y": 0}
        content = json.dumps(value, indent=4).encode() if noncanonical else protocol.encoded(value)
        path = self.work / f"proposal-{token}.json"
        protocol.create_file(path, content)
        return path, protocol.sha(content)

    def submit(self, operation_id, proposal, *, allow_failure=False):
        return self.adapter("submit", "--operation-id", operation_id, "--proposal-file", proposal[0],
                            "--proposal-sha256", proposal[1], allow_failure=allow_failure)

    def until(self, operation_id, phases=("executed", "staged", "cancelled", "refused", "unknown")):
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            value = self.adapter("status", "--operation-id", operation_id, allow_failure=True)
            if value.get("phase") in phases:
                return value
            time.sleep(.02)
        self.fail("controller phase timeout")

    def states(self):
        return {path.name: path.read_bytes() for path in Path(self.lease["run_dir"]).glob("state-*.json")}

    def test_prepare_submit_fresh_caller_repeat_and_exact_raw_proposal_digest(self):
        prepared = self.prepare()
        packet = self.packet()
        proposal = self.proposal(packet, "first-move", noncanonical=True)
        self.submit("first-move", proposal)
        final = self.until("first-move")
        self.assertEqual(final["phase"], "executed", final)
        before = self.states()
        repeated = self.prepare()
        self.assertEqual(repeated["controller"]["pid"], prepared["controller"]["pid"])
        self.assertEqual(repeated["controller"]["current_incarnation"], prepared["controller"]["current_incarnation"])
        self.assertEqual(self.submit("first-move", proposal)["phase"], "executed")
        self.assertEqual(self.states(), before)
        changed = self.proposal(self.packet(), "conflict")
        self.assertEqual(self.submit("first-move", changed, allow_failure=True)["phase"], "refused")
        self.assertEqual(self.states(), before)

    def changed_during_motion(self, action):
        self.prepare(pace=.003)
        self.submit("contact", self.proposal(self.packet(), "contact"))
        first = self.until("contact")
        self.assertEqual(first["phase"], "executed")
        self.assertGreater(first["receipt"]["contact_statistics"]["pusher_block_contact_samples"], 0)
        packet = self.packet()
        self.submit("active", self.proposal(packet, "active"))
        self.until("active", phases=("running",))
        time.sleep(.18)
        mutation = {"expected_revision": 1}
        if action == "edit":
            mutation["target_zone"] = {"x_min": .16, "x_max": .24, "y_min": -.04, "y_max": .04}
        self.http(f"/api/orders/{self.order['order_id']}/{action}", mutation)
        guarded = self.adapter("guard", allow_failure=True)
        self.assertFalse(guarded["guard_current"])
        self.assertTrue(guarded["physical_effects_may_be_partial"])
        self.assertFalse(guarded["rollback_claim"])
        terminal = self.until("active")
        self.assertEqual(terminal["phase"], "cancelled", terminal)
        self.assertGreater(terminal["stop_evidence"]["native_steps_before_cancel"], 0)
        self.assertTrue(terminal["stop_evidence"]["stop_verified"])
        before = self.states()
        blocked_proposal = self.proposal(packet, "withheld")
        self.assertIn(self.submit("withheld", blocked_proposal, allow_failure=True)["phase"], {"withheld", "unknown"})
        self.assertEqual(self.states(), before)
        record = handoff.load(self.handoff_dir)
        self.assertNotIn("withheld", record["operations"])
        _, order = self.http(f"/api/orders/{self.order['order_id']}")
        self.assertEqual(order["order"]["revision"], 2)
        self.assertEqual(order["order"]["state"], "cancelled" if action == "cancel" else "open")
        self.assertEqual(self.adapter("reconcile", allow_failure=True)["phase"], "unknown")

    def test_order_edit_during_native_progress_guards_and_cancels(self):
        self.changed_during_motion("edit")

    def test_order_cancel_during_native_progress_guards_and_cancels(self):
        self.changed_during_motion("cancel")

    def test_exact_committed_app_effect_reconciles_after_lost_reply(self):
        self.scene["block_xy"] = [.195, .006]
        self.prepare()
        completion_id = self.lease["physical_completion_id"]
        wrong = self.proposal(self.packet(), "wrong-stage", complete=True)
        self.assertEqual(self.submit("wrong-stage", wrong, allow_failure=True)["phase"], "refused")
        self.submit(completion_id, self.proposal(self.packet(), completion_id, complete=True))
        self.assertEqual(self.until(completion_id)["phase"], "staged")
        content = protocol.encoded({"lease_id": self.lease["lease_id"],
                                    "completion_operation_id": self.lease["completion_operation_id"]})
        parsed = urllib.parse.urlsplit(self.url)
        header = (f"POST /api/orders/{self.order['order_id']}/fulfill HTTP/1.1\r\nHost: {parsed.netloc}\r\n"
                  f"Origin: {self.url}\r\nX-Footwork-App-ID: {self.app_id}\r\nContent-Type: application/json\r\n"
                  f"Content-Length: {len(content)}\r\n\r\n").encode()
        with socket.create_connection(("127.0.0.1", parsed.port), timeout=3) as client:
            client.sendall(header + content)
        self.evidence.append({"scenario": "actual_fulfillment_client_closed_before_reply", "blind_resubmissions": 0})
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            reconciled = self.adapter("reconcile", allow_failure=True)
            if reconciled["phase"] == "fulfilled":
                break
            time.sleep(.02)
        self.assertEqual(reconciled["phase"], "fulfilled", reconciled)
        self.assertEqual(reconciled["receipt"]["completion_operation_id"], self.lease["completion_operation_id"])
        self.assertEqual(reconciled["receipt"]["lease_id"], self.lease["lease_id"])
        before = self.states()
        self.assertEqual(self.adapter("reconcile")["receipt"], reconciled["receipt"])
        self.assertEqual(self.states(), before)
        self.assertFalse(self.adapter("guard", allow_failure=True)["guard_current"])

    def test_app_restart_same_origin_reconnects_without_native_replay(self):
        prepared = self.prepare()
        self.submit("restart-history", self.proposal(self.packet(), "restart-history"))
        self.assertEqual(self.until("restart-history")["phase"], "executed")
        before = self.states()
        self.processes[0].terminate()
        self.processes[0].wait(timeout=5)
        self.start_app(restart=True)
        repeated = self.prepare()
        self.assertEqual(repeated["controller"]["pid"], prepared["controller"]["pid"])
        self.assertEqual(self.adapter("status", "--operation-id", "restart-history")["historical_outcome"], "executed")
        self.assertEqual(self.states(), before)

    def test_malformed_retained_receipt_actual_api_readback_never_claims_effect(self):
        self.scene["block_xy"] = [.195, .006]
        self.prepare()
        physical_id = self.lease["physical_completion_id"]
        self.submit(physical_id, self.proposal(self.packet(), physical_id, complete=True))
        self.assertEqual(self.until(physical_id)["phase"], "staged")
        self.http(f"/api/orders/{self.order['order_id']}/fulfill", {
            "lease_id": self.lease["lease_id"], "completion_operation_id": self.lease["completion_operation_id"]})
        self.assertEqual(self.adapter("reconcile")["phase"], "fulfilled")
        database = self.app_dir / "orders.sqlite3"
        with sqlite3.connect(database) as connection:
            original_receipt = connection.execute("SELECT receipt_json FROM operations WHERE operation_id=?", (
                self.lease["completion_operation_id"],)).fetchone()[0]
            original_order = connection.execute("SELECT revision,state,work_order_json FROM orders WHERE order_id=?", (
                self.order["order_id"],)).fetchone()
        protocol.create_file(self.work / "original-application-receipt.json", original_receipt.encode())
        before = self.states()
        variants = (("receipt_state", {"state": "open"}, {}),
                    ("boolean_leased_revision", {"leased_revision": True}, {}),
                    ("fulfilled_revision", {"fulfilled_revision": 4}, {}),
                    ("terminal_current_state", {}, {"state": "cancelled"}),
                    ("current_revision_before_receipt", {}, {"revision": 1}),
                    ("current_order_identity", {}, {"order_id": "another-order"}))
        for name, receipt_changes, order_changes in variants:
            with self.subTest(fault=name):
                receipt = protocol.decode(original_receipt.encode())
                receipt.update(receipt_changes)
                order_json = protocol.decode(original_order[2].encode())
                if "order_id" in order_changes:
                    order_json["order_id"] = order_changes["order_id"]
                with sqlite3.connect(database) as connection:
                    connection.execute("UPDATE operations SET receipt_json=? WHERE operation_id=?", (
                        protocol.encoded(receipt).decode(), self.lease["completion_operation_id"]))
                    connection.execute("UPDATE orders SET revision=?,state=?,work_order_json=? WHERE order_id=?", (
                        order_changes.get("revision", original_order[0]), order_changes.get("state", original_order[1]),
                        protocol.encoded(order_json).decode(), self.order["order_id"]))
                self.evidence.append({"scenario": "labeled_retained_store_readback_fault", "fault": name,
                                      "source_store_identity_and_native_history_unchanged": True})
                result = self.adapter("reconcile", allow_failure=True)
                self.assertEqual(result["phase"], "refused", result)
                self.assertFalse(result.get("application_effect_confirmed", False))
                self.assertEqual(self.states(), before)
        with sqlite3.connect(database) as connection:
            connection.execute("UPDATE operations SET receipt_json=? WHERE operation_id=?", (
                original_receipt, self.lease["completion_operation_id"]))
            connection.execute("UPDATE orders SET revision=?,state=?,work_order_json=? WHERE order_id=?", (
                *original_order, self.order["order_id"]))
        self.assertEqual(self.adapter("reconcile")["phase"], "fulfilled")

    def test_external_controller_restart_allows_history_but_no_ownership_takeover(self):
        self.prepare()
        self.submit("external-history", self.proposal(self.packet(), "external-history"))
        self.assertEqual(self.until("external-history")["phase"], "executed")
        stopped = self.adapter("stop")
        self.assertTrue(stopped["process_termination_observed"])
        logfile = open(self.work / "external-controller.log", "xb")  # noqa: SIM115 - owned until tearDown
        os.chmod(logfile.name, 0o600)
        self.handles.append(logfile)
        process = subprocess.Popen([str(PYTHON), str(BASE / "controller.py"), "serve", "--run-dir", self.lease["run_dir"],
                                    "--controller-dir", self.lease["controller_dir"]], stdout=logfile, stderr=subprocess.STDOUT)
        self.processes.append(process)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            health = self.raw_controller(self.lease["controller_dir"], "health", allow_failure=True)
            if health.get("pid") == process.pid:
                break
            time.sleep(.02)
        before = self.states()
        self.assertEqual(self.adapter("status", "--operation-id", "external-history")["historical_outcome"], "executed")
        proposal = self.proposal(self.packet(), "unowned-submit")
        self.assertEqual(self.submit("unowned-submit", proposal, allow_failure=True)["phase"], "refused")
        self.assertEqual(self.adapter("stop", allow_failure=True)["phase"], "refused")
        self.assertIsNone(process.poll())
        self.assertEqual(self.states(), before)

    def test_wrong_app_lease_scene_digest_and_retained_paths_refuse(self):
        self.start_app()
        self.bind()
        protocol.create_file(self.scene_path, protocol.encoded(self.scene))
        digest = protocol.sha(self.scene_path.read_bytes())
        for app_id, lease_id, scene_sha in (("wrong-app", self.lease["lease_id"], digest),
                                             (self.app_id, "0" * 32, digest),
                                             (self.app_id, self.lease["lease_id"], "0" * 64)):
            with self.subTest(app_id=app_id, lease_id=lease_id):
                result = self.command("app_handoff.py", "prepare", "--app-url", self.url, "--expected-app-id", app_id,
                                      "--lease-id", lease_id, "--scene-file", self.scene_path, "--scene-sha256", scene_sha,
                                      allow_failure=True)
                self.assertEqual(result["phase"], "refused")
        self.assertFalse((self.handoff_dir / "handoff.json").exists())
        health = handoff.api(self.url, self.app_id, "/api/health")
        changed = copy.deepcopy(self.lease)
        changed["run_dir"] = str(self.work / "arbitrary-proof")
        with self.assertRaises(protocol.Refusal):
            handoff.lease_schema(changed, health, self.url, self.app_id, self.lease["lease_id"])

    def test_scene_change_repeat_never_reinitializes_or_replaces_controller(self):
        self.prepare()
        before = self.states()
        original = self.scene_path.read_bytes()
        self.scene_path.write_bytes(original + b" ")
        result = self.command("app_handoff.py", "prepare", "--app-url", self.url, "--expected-app-id", self.app_id,
                              "--lease-id", self.lease["lease_id"], "--scene-file", self.scene_path,
                              "--scene-sha256", protocol.sha(self.scene_path.read_bytes()), allow_failure=True)
        self.assertEqual(result["phase"], "refused")
        self.assertEqual(self.states(), before)
        self.scene_path.write_bytes(original)

    def test_missing_app_readback_stays_unknown_and_guard_withholds(self):
        self.prepare()
        self.assertEqual(self.adapter("reconcile", allow_failure=True)["phase"], "unknown")
        proposal = self.proposal(self.packet(), "app-down")
        before = self.states()
        self.processes[0].terminate()
        self.processes[0].wait(timeout=5)
        guarded = self.adapter("guard", allow_failure=True)
        self.assertFalse(guarded["guard_current"])
        self.assertEqual(guarded["phase"], "unknown")
        self.assertEqual(self.submit("app-down", proposal, allow_failure=True)["phase"], "unknown")
        self.assertEqual(self.states(), before)
        self.assertNotIn("app-down", handoff.load(self.handoff_dir)["operations"])

    def test_loopback_origin_strict_and_scene_symlink_refusal(self):
        for url in ("https://127.0.0.1:1234", "http://localhost:1234", "http://127.0.0.1:1234/",
                    "http://user:secret@127.0.0.1:1234", "http://127.0.0.1:1234?other=1"):
            with self.subTest(url=url), self.assertRaises(protocol.Refusal):
                handoff.origin(url)
        self.start_app()
        self.bind()
        protocol.create_file(self.scene_path, protocol.encoded(self.scene))
        linked = self.work / "linked-scene.json"
        linked.symlink_to(self.scene_path)
        result = self.command("app_handoff.py", "prepare", "--app-url", self.url, "--expected-app-id", self.app_id,
                              "--lease-id", self.lease["lease_id"], "--scene-file", linked,
                              "--scene-sha256", protocol.sha(self.scene_path.read_bytes()), allow_failure=True)
        self.assertEqual(result["phase"], "refused")
        self.assertFalse((self.handoff_dir / "handoff.json").exists())


if __name__ == "__main__":
    unittest.main()
