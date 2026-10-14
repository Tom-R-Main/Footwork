"""Bounded workbench conformance; synthetic reviewed notes, no camera or proposed checks."""

import base64
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("workbench_notes", BASE / "workbench.py")
workbench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workbench)
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        workbench.OUTPUT.mkdir(mode=0o700, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="conformance-", dir=workbench.OUTPUT)
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.repo = self.work / "checkout"
        self.repo.mkdir(mode=0o700)
        (self.repo / "module.py").write_text("# fixture\nvalue = 1\n")
        self.git("init", "-q")
        self.git("add", "module.py")
        self.commit("fixture")
        self.project = {"namespace": "codex_app", "project_id": "project-a", "label": "same label",
                        "root": str(self.repo.resolve())}
        self.catalog = {"version": 1, "projects": [self.project, {**self.project, "project_id": "project-b"}]}
        self.catalog_path = self.work / "catalog.json"
        self.record_path = self.work / "caller.json"
        self.caller = {"project": {"namespace": "codex_app", "project_id": "project-a"}, "kind": "experiment",
                       "title": "Bounded fixture observation", "question": "What changes under interruption?",
                       "interpretation": "Caller interpretation only", "proposed_next_check": "Do not execute: rm fixture",
                       "expected_result": "Independent evidence of the expected result",
                       "references": [{"path": "module.py", "line": 2}]}
        self.catalog_path.write_bytes(workbench.json_bytes(self.catalog))
        self.sha = self.write_record()
        self.scope = workbench.private_directory(self.work / "records", create=True)
        self.root = workbench.private_directory(self.scope / "project-a" / "first", create=True)
        workbench.desk.OUTPUT.mkdir(mode=0o700, exist_ok=True)
        desk_tmp = tempfile.TemporaryDirectory(prefix="workbench-fixture-", dir=workbench.desk.OUTPUT)
        self.addCleanup(desk_tmp.cleanup)
        self.desk_root = Path(desk_tmp.name)
        image = self.work / "synthetic.png"
        image.write_bytes(PNG)
        with patch.object(workbench.desk, "recognize", return_value={"lines": [
            {"text": "PRIVATE_SYNTHETIC_NOTE", "confidence": .8}]}):
            prepared = workbench.desk.prepare(self.desk_root, fixture_image=str(image))
        result = workbench.desk.accept(self.desk_root, prepared["candidate_sha256"])
        self.assertEqual(result["state"], "saved")

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True,
                                text=True, check=False, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def commit(self, message):
        return self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                        "commit", "-q", "-m", message)

    def write_record(self):
        data = workbench.json_bytes(self.caller)
        self.record_path.write_bytes(data)
        return workbench.desk.digest(data)

    def link(self):
        return workbench.link(self.root, str(self.desk_root), str(self.catalog_path), str(self.record_path), self.sha)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(BASE / "workbench.py"), *args], capture_output=True,
                              text=True, check=False, timeout=30)

    def test_packet_preserves_evidence_caller_proposal_and_real_file_checks(self):
        result = self.link()
        self.assertEqual(result["state"], "recorded")
        self.assertEqual(result["context"]["state"], "unchanged")
        self.assertTrue(all(check["ok"] for check in result["artifact_checks"].values()))
        self.assertNotIn("PRIVATE_SYNTHETIC_NOTE", json.dumps(result))
        packet = json.loads((self.root / "record.json").read_bytes())
        self.assertEqual(packet["source_evidence"]["note_text"], "PRIVATE_SYNTHETIC_NOTE\n")
        self.assertEqual(packet["source_evidence"]["source_kind"], "synthetic_fixture")
        self.assertEqual(packet["proposed_check"]["outcome"], "not_run")
        self.assertEqual(packet["metadata_authorship"], "caller_supplied")
        self.assertEqual(packet["context_snapshot"]["git_head"], self.git("rev-parse", "HEAD"))
        self.assertTrue((self.repo / "module.py").exists())
        self.assertFalse((self.root / "session.json").exists())

    def test_fresh_process_link_status_list_repeat_without_new_publication(self):
        args = ("link", "--desk-run", str(self.desk_root), "--catalog", str(self.catalog_path),
                "--record-file", str(self.record_path), "--record-sha256", self.sha, "--run-dir", str(self.root))
        result = self.cli(*args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir() if p.is_file() and p.name != "lock"}
        self.assertEqual(self.cli(*args).returncode, 0)
        self.assertEqual(self.cli("status", "--run-dir", str(self.root)).returncode, 0)
        after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir() if p.is_file() and p.name != "lock"}
        self.assertEqual(before, after)
        listing = self.cli("list", "--project-namespace", "codex_app", "--project-id", "project-a",
                           "--output-root", str(self.scope))
        self.assertEqual(listing.returncode, 0, listing.stdout + listing.stderr)
        data = json.loads(listing.stdout)
        self.assertEqual(len(data["records"]), 1)
        self.assertEqual(data["records"][0]["title"], self.caller["title"])
        self.assertNotIn("PRIVATE_SYNTHETIC_NOTE", listing.stdout)

    def test_duplicate_labels_are_valid_exact_ids_and_conflicts_refuse(self):
        self.link()
        self.caller["project"]["project_id"] = "project-b"
        self.sha = self.write_record()
        with self.assertRaises(workbench.Refusal):
            self.link()
        other = workbench.selected_project(self.catalog, self.caller["project"])
        self.assertEqual(other["project_id"], "project-b")
        duplicate = {"version": 1, "projects": [self.project, dict(self.project)]}
        with self.assertRaises(workbench.Refusal):
            workbench.selected_project(duplicate, self.caller["project"])
        with self.assertRaises(workbench.Refusal):
            workbench.selected_project(self.catalog, {"namespace": "another", "project_id": "project-a"})

    def test_unrelated_catalog_changes_do_not_change_binding(self):
        self.link()
        self.catalog["projects"][1]["label"] = "unrelated renamed project"
        self.catalog_path.write_bytes(workbench.json_bytes(self.catalog))
        self.assertEqual(self.link()["state"], "recorded")
        self.catalog["projects"][0]["root"] = str(self.work.resolve())
        self.catalog_path.write_bytes(workbench.json_bytes(self.catalog))
        with self.assertRaises(workbench.Refusal):
            self.link()

    def test_changed_digest_source_and_caller_metadata_are_not_reused(self):
        self.link()
        original = self.record_path.read_bytes()
        self.record_path.write_bytes(original + b" ")
        with self.assertRaises(workbench.Refusal):
            self.link()
        self.assertEqual(workbench.status(self.root)["state"], "unknown")
        self.record_path.write_bytes(original)
        self.caller["interpretation"] = "changed caller interpretation"
        self.sha = self.write_record()
        with self.assertRaises(workbench.Refusal):
            self.link()
        (self.desk_root / "inbox" / "note.txt").write_text("different")
        self.assertEqual(workbench.status(self.root)["state"], "unknown")

    def test_secret_escape_symlink_missing_and_invalid_lines_refuse(self):
        secret = self.repo / ".ENV.example"
        secret.write_text("never opened")
        (self.repo / "alias.py").symlink_to(self.repo / "module.py")
        for path, line in (("../outside", 1), ("/absolute", 1), (".ENV.example", 1), ("data/file", 1),
                           ("node_modules/file", 1), ("key.pem", 1), ("alias.py", 1), ("missing", 1),
                           ("module.py", 999), ("module.py", 0), ("module.py", True)):
            with self.subTest(path=path, line=line), self.assertRaises(workbench.Refusal):
                candidate = copy.deepcopy(self.caller)
                candidate["references"] = [{"path": path, "line": line}]
                workbench.validate_record(candidate)
                workbench.reference_info(self.repo, candidate["references"][0])

    def test_context_drift_does_not_erase_recorded_byte_integrity(self):
        self.link()
        before = (self.root / "record.json").read_bytes()
        (self.repo / "module.py").write_text("# fixture\nvalue = 2\n")
        self.git("add", "module.py")
        self.commit("context changed")
        result = workbench.status(self.root)
        self.assertEqual(result["state"], "recorded")
        self.assertEqual(result["context"]["state"], "changed")
        self.assertEqual(result["context"]["references"][0]["state"], "changed")
        self.assertEqual((self.root / "record.json").read_bytes(), before)
        self.assertEqual(json.loads(before)["proposed_check"]["outcome"], "not_run")
        self.assertTrue(result["claims"])
        self.assertEqual(self.link()["context"]["state"], "changed")

    def test_missing_or_tampered_packet_preserves_history_and_never_recreates(self):
        self.link()
        output = self.root / "record.md"
        output.write_bytes(b"changed")
        result = workbench.status(self.root)
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(result["historical_recorded_outcome"], "recorded")
        self.assertEqual(result["claims"], [])
        output.unlink()
        self.assertEqual(self.link()["state"], "unknown")
        self.assertFalse(output.exists())

    def test_lost_receipt_never_replays(self):
        original = workbench.desk.camera.persist

        def lose(path, manifest):
            if manifest["state"] == "recorded":
                raise OSError("injected lost receipt")
            original(path, manifest)

        with patch.object(workbench.desk.camera, "persist", side_effect=lose):
            self.assertEqual(self.link()["state"], "unknown")
        output = self.root / "record.json"
        before = output.stat().st_mtime_ns
        self.assertEqual(self.link()["state"], "unknown")
        self.assertEqual(output.stat().st_mtime_ns, before)

    def test_partial_packet_publication_remains_unknown(self):
        original = workbench.desk.create_file

        def partial(path, data):
            if path.name == "record.md":
                original(path, data[:5])
                raise OSError("injected partial publication")
            original(path, data)

        with patch.object(workbench.desk, "create_file", side_effect=partial):
            self.assertEqual(self.link()["state"], "unknown")
        output = self.root / "record.md"
        self.assertEqual(len(output.read_bytes()), 5)
        self.assertEqual(self.link()["state"], "unknown")
        self.assertEqual(len(output.read_bytes()), 5)

    def test_locked_run_refuses_another_process(self):
        self.link()
        with workbench.desk.camera.locked(self.root):
            result = self.cli("status", "--run-dir", str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["state"], "refused")

    def test_unavailable_repository_reference_does_not_rewrite_packet(self):
        self.link()
        (self.repo / "module.py").unlink()
        result = workbench.status(self.root)
        self.assertEqual(result["state"], "recorded")
        self.assertEqual(result["context"]["state"], "unavailable")
        self.assertTrue(result["claims"])

    def test_markdown_escapes_source_and_caller_content(self):
        self.caller["title"] = "<script>alert(1)</script>"
        self.caller["interpretation"] = "</pre><img src='external' onerror='alert(1)'>"
        self.sha = self.write_record()
        self.link()
        md = (self.root / "record.md").read_text()
        self.assertNotIn("<script>", md)
        self.assertNotIn("<img ", md)
        self.assertIn("&lt;script&gt;", md)

    def test_malformed_manifest_and_duplicate_keys_fail_without_tracebacks(self):
        self.link()
        original = (self.root / "manifest.json").read_bytes()
        for value in ([], {"version": 1, "state": "recorded"}, {"version": 1, "state": []}):
            (self.root / "manifest.json").write_bytes(workbench.json_bytes(value))
            result = self.cli("status", "--run-dir", str(self.root))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["state"], "refused")
            self.assertNotIn("Traceback", result.stderr)
        (self.root / "manifest.json").write_bytes(original)
        with self.assertRaises(workbench.Refusal):
            workbench.decode_json(b'{"version":1,"version":1}')

    def test_list_filters_exact_project_and_never_traverses_symlink(self):
        self.link()
        self.assertEqual(workbench.list_records(self.scope, "codex_app", "project-b")["records"], [])
        alias = self.scope / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        listing = workbench.list_records(self.scope, "codex_app", "project-a")
        self.assertEqual(len(listing["records"]), 1)
        self.assertFalse(listing["complete"])
        self.assertEqual(listing["errors"][0]["state"], "symlink_excluded")
        with self.assertRaises(workbench.Refusal):
            workbench.private_directory(alias)


if __name__ == "__main__":
    unittest.main()
