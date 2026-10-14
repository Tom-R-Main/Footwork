"""Desk conformance at file and process boundaries; real Vision is a separate run."""

import base64
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("desk_inbox", BASE / "inbox.py")
inbox = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inbox)
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
OCR = {"engine": "fixture", "orientation": "up", "lines": [
    {"text": "First note", "confidence": .8, "bounds": {"x": .1, "y": .8, "width": .5, "height": .1}},
    {"text": "Second note", "confidence": .7, "bounds": {"x": .1, "y": .6, "width": .5, "height": .1}},
]}


class InboxTests(unittest.TestCase):
    def setUp(self):
        inbox.OUTPUT.mkdir(mode=0o700, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="conformance-", dir=inbox.OUTPUT)
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.root = inbox.private_directory(self.work / "run")
        self.image = self.work / "printed<&>.png"
        self.image.write_bytes(PNG)

    def prepare(self, result=OCR, mirror=False):
        with patch.object(inbox, "recognize", return_value=result) as recognize:
            prepared = inbox.prepare(self.root, fixture_image=str(self.image), mirror_input=mirror)
        return prepared, recognize

    def test_prepare_and_accept_use_real_footwork_checker_without_text_output(self):
        prepared, _ = self.prepare()
        self.assertEqual(prepared["state"], "needs_review")
        self.assertEqual(prepared["request"]["source_kind"], "synthetic_fixture")
        self.assertEqual((self.root / "candidate.txt").read_bytes(), b"First note\nSecond note\n")
        result = inbox.accept(self.root, prepared["candidate_sha256"])
        self.assertEqual(result["state"], "saved")
        self.assertTrue(result["current_artifact_check"]["ok"])
        self.assertNotIn("First note", json.dumps(result))
        self.assertEqual((self.root / "inbox" / "note.txt").read_bytes(), (self.root / "candidate.txt").read_bytes())
        self.assertFalse((self.root / "session.json").exists())
        self.assertFalse((self.root / "carries.json").exists())

    def test_repeated_prepare_and_accept_do_not_rewrite(self):
        prepared, _ = self.prepare()
        before = (self.root / "manifest.json").read_bytes()
        with patch.object(inbox, "recognize") as recognize:
            again = inbox.prepare(self.root, fixture_image=str(self.image))
        recognize.assert_not_called()
        self.assertEqual(again["candidate_sha256"], prepared["candidate_sha256"])
        self.assertEqual((self.root / "manifest.json").read_bytes(), before)
        inbox.accept(self.root, prepared["candidate_sha256"])
        before = (self.root / "manifest.json").read_bytes()
        note_before = (self.root / "inbox" / "note.txt").stat()
        again = inbox.accept(self.root, prepared["candidate_sha256"])
        self.assertEqual(again["state"], "saved")
        self.assertEqual((self.root / "manifest.json").read_bytes(), before)
        self.assertEqual((self.root / "inbox" / "note.txt").stat().st_mtime_ns, note_before.st_mtime_ns)
        self.assertEqual(len(list((self.root / "inbox").iterdir())), 1)

    def test_mirror_is_bound_explicit_and_preview_escapes_text(self):
        malicious = {"lines": [{"text": "<script>alert(1)</script> & commands", "confidence": .9}]}
        prepared, recognize = self.prepare(malicious, mirror=True)
        self.assertTrue(prepared["request"]["mirror_input"])
        recognize.assert_called_once_with(self.root, True)
        page = (self.root / "review.html").read_text()
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("printed&lt;&amp;&gt;.png", page)
        self.assertIn("Horizontal mirror correction (explicit)", page)
        self.assertIn("scaleX(-1)", page)
        self.assertEqual((self.root / "source.png").read_bytes(), PNG)
        with self.assertRaises(inbox.Refusal):
            inbox.prepare(self.root, fixture_image=str(self.image), mirror_input=False)

    def test_real_helper_invocation_sets_orientation_without_rewriting_image(self):
        inbox.create_file(self.root / "source.png", PNG)
        with patch.object(inbox.camera, "run_process", return_value=(0, json.dumps(OCR), "")) as process:
            result = inbox.recognize(self.root, True)
        argv = process.call_args.args[0]
        self.assertEqual(argv[-1], "up_mirrored")
        self.assertEqual(argv[-2], str(self.root / "source.png"))
        self.assertEqual(result, OCR)
        self.assertEqual((self.root / "source.png").read_bytes(), PNG)
        source = (BASE / "recognize.swift").read_text()
        self.assertIn(".upMirrored : .up", source)
        self.assertIn("usesLanguageCorrection = false", source)

    def test_empty_ocr_cannot_save_note(self):
        prepared, _ = self.prepare({"lines": []})
        self.assertEqual(prepared["state"], "needs_text")
        self.assertFalse((self.root / "candidate.txt").exists())
        with self.assertRaises(inbox.Refusal):
            inbox.accept(self.root, "a" * 64)
        self.assertFalse((self.root / "inbox").exists())

    def test_changed_source_or_candidate_refuses_review(self):
        prepared, _ = self.prepare()
        self.image.write_bytes(PNG + b"changed")
        with self.assertRaises(inbox.Refusal):
            inbox.accept(self.root, prepared["candidate_sha256"])
        with self.assertRaises(inbox.Refusal):
            inbox.prepare(self.root, fixture_image=str(self.image))
        self.image.write_bytes(PNG)
        (self.root / "candidate.txt").write_bytes(b"altered\n")
        with self.assertRaises(inbox.Refusal):
            inbox.accept(self.root, prepared["candidate_sha256"])
        self.assertFalse((self.root / "inbox").exists())

    def test_source_changed_during_ocr_leaves_unknown_without_note(self):
        def alter(root, mirrored):
            self.image.write_bytes(PNG + b"different")
            return OCR

        with patch.object(inbox, "recognize", side_effect=alter):
            result = inbox.prepare(self.root, fixture_image=str(self.image))
        self.assertEqual(result["state"], "unknown")
        self.assertFalse((self.root / "inbox").exists())

    def test_wrong_digest_and_empty_correction_refuse_before_intent(self):
        prepared, _ = self.prepare()
        for sha in ("a" * 64, "bad"):
            with self.assertRaises(inbox.Refusal):
                inbox.accept(self.root, sha)
        correction = self.work / "correction.txt"
        correction.write_bytes(b" \n")
        with self.assertRaises(inbox.Refusal):
            inbox.accept(self.root, inbox.digest(correction.read_bytes()), str(correction))
        self.assertEqual(inbox.load(self.root)["state"], "needs_review")
        self.assertFalse((self.root / "approved.txt").exists())
        self.assertEqual(prepared["candidate_sha256"], inbox.digest((self.root / "candidate.txt").read_bytes()))

    def test_corrected_review_retains_original_ocr_and_exact_corrected_bytes(self):
        prepared, _ = self.prepare()
        correction = self.work / "reviewed.txt"
        correction.write_bytes(b"Human corrected\nNo implicit terminal newline")
        sha = inbox.digest(correction.read_bytes())
        result = inbox.accept(self.root, sha, str(correction))
        self.assertEqual(result["state"], "saved")
        self.assertEqual(result["review_kind"], "corrected_text")
        self.assertEqual((self.root / "inbox" / "note.txt").read_bytes(), correction.read_bytes())
        self.assertEqual(inbox.digest((self.root / "candidate.txt").read_bytes()), prepared["candidate_sha256"])
        with self.assertRaises(inbox.Refusal):
            inbox.accept(self.root, prepared["candidate_sha256"])

    def test_missing_or_tampered_note_never_recreated_and_history_retained(self):
        prepared, _ = self.prepare()
        inbox.accept(self.root, prepared["candidate_sha256"])
        note = self.root / "inbox" / "note.txt"
        note.write_bytes(b"different")
        result = inbox.status(self.root)
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(result["historical_save_outcome"], "saved")
        self.assertEqual(result["claims"], [])
        self.assertEqual(inbox.load(self.root)["state"], "saved")
        note.unlink()
        self.assertEqual(inbox.accept(self.root, prepared["candidate_sha256"])["state"], "unknown")
        self.assertFalse(note.exists())

    def test_lost_receipt_is_unknown_and_never_replayed(self):
        prepared, _ = self.prepare()
        original = inbox.persist

        def lose_receipt(root, record):
            if record["state"] == "saved":
                raise OSError("injected receipt failure")
            original(root, record)

        with patch.object(inbox, "persist", side_effect=lose_receipt):
            result = inbox.accept(self.root, prepared["candidate_sha256"])
        self.assertEqual(result["state"], "unknown")
        note = self.root / "inbox" / "note.txt"
        self.assertTrue(note.exists())
        before = note.stat().st_mtime_ns
        self.assertEqual(inbox.accept(self.root, prepared["candidate_sha256"])["state"], "unknown")
        self.assertEqual(note.stat().st_mtime_ns, before)

    def test_partial_publication_is_unknown_and_cannot_finish_by_retry(self):
        prepared, _ = self.prepare()
        original = inbox.create_file

        def partial(path, data):
            if path.name == "note.txt":
                original(path, data[:5])
                raise OSError("injected interrupted write")
            original(path, data)

        with patch.object(inbox, "create_file", side_effect=partial):
            result = inbox.accept(self.root, prepared["candidate_sha256"])
        self.assertEqual(result["state"], "unknown")
        note = self.root / "inbox" / "note.txt"
        before = note.read_bytes()
        self.assertEqual(len(before), 5)
        self.assertEqual(inbox.accept(self.root, prepared["candidate_sha256"])["state"], "unknown")
        self.assertEqual(note.read_bytes(), before)

    def test_native_preparation_uses_status_only_and_refuses_unknown_source(self):
        inbox.camera.OUTPUT.mkdir(mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=inbox.camera.OUTPUT) as run:
            frame = inbox.camera.paths(Path(run), "source-token")[1]
            frame.write_bytes(PNG)
            with patch.object(inbox.camera, "status", return_value={"state": "acquired"}) as status, \
                    patch.object(inbox.camera, "capture") as acquire, \
                    patch.object(inbox, "recognize", return_value=OCR):
                result = inbox.prepare(self.root, run, "source-token")
            self.assertEqual(result["state"], "needs_review")
            self.assertEqual(result["request"]["source_kind"], "native_camera_frame")
            acquire.assert_not_called()
            self.assertGreaterEqual(status.call_count, 1)
            with patch.object(inbox.camera, "status", return_value={"state": "unknown"}), self.assertRaises(inbox.Refusal):
                inbox.source_request(run, "source-token")

    def test_private_output_lock_and_symlink_guard(self):
        with self.assertRaises(inbox.Refusal):
            inbox.private_directory(self.work.parent.parent)
        symlink = self.work / "link"
        symlink.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(inbox.Refusal):
            inbox.private_directory(symlink / "child")
        with inbox.camera.locked(self.root):
            result = subprocess.run([sys.executable, str(BASE / "inbox.py"), "status", "--run-dir", str(self.root)],
                                    capture_output=True, text=True, check=False, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn("another process", result.stdout)

    def test_public_cli_prepare_accept_and_status_across_fresh_processes(self):
        bin_dir = self.work / "bin"
        bin_dir.mkdir(mode=0o700)
        marker = self.work / "ocr-dispatches"
        program = bin_dir / "swift"
        fixture = ("#!/usr/bin/env python3\nimport json,pathlib\n"
                   f"with open({str(marker)!r},'a') as f: f.write('OCR\\n')\n"
                   f"print({json.dumps(OCR)!r})\n")
        program.write_text(fixture)
        program.chmod(0o700)
        env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"])
        prepare_args = [sys.executable, str(BASE / "inbox.py"), "prepare", "--run-dir", str(self.root),
                        "--fixture-image", str(self.image)]
        for _ in range(2):
            result = subprocess.run(prepare_args, env=env, capture_output=True, text=True, check=False, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            prepared = json.loads(result.stdout)
            self.assertEqual(prepared["state"], "needs_review")
        self.assertEqual(marker.read_text(), "OCR\n")
        args = [sys.executable, str(BASE / "inbox.py"), "accept", "--run-dir", str(self.root),
                "--approved-sha256", prepared["candidate_sha256"]]
        for _ in range(2):
            result = subprocess.run(args, env=env, capture_output=True, text=True, check=False, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["state"], "saved")
            self.assertNotIn("First note", result.stdout)
        result = subprocess.run([sys.executable, str(BASE / "inbox.py"), "status", "--run-dir", str(self.root)],
                                env=env, capture_output=True, text=True, check=False, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["state"], "saved")
        self.assertEqual(marker.read_text(), "OCR\n")
        self.assertEqual(len(list((self.root / "inbox").iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
