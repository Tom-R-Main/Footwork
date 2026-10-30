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
TSV_HEADER = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"


def tsv(width=100, height=100, words=None):
    page = f"1\t1\t0\t0\t0\t0\t0\t0\t{width}\t{height}\t-1\t\n"
    return (TSV_HEADER + page + (words or "")).encode()


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
        with patch.object(inbox.sys, "platform", "darwin"), \
                patch.object(inbox.shutil, "which", return_value="/fixture/swift"), \
                patch.object(inbox.camera, "run_process", return_value=(0, json.dumps(OCR), "")) as process:
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
        if sys.platform == "linux":
            program = bin_dir / "tesseract"
            evidence = tsv(1, 1, "5\t1\t1\t1\t1\t1\t0\t0\t1\t1\t80\tFirst note\n")
            fixture = ("#!/usr/bin/env python3\nimport pathlib,sys\n"
                       "if '--version' in sys.argv:\n print('tesseract 5.fixture'); sys.exit(0)\n"
                       f"with open({str(marker)!r},'a') as f: f.write('OCR\\n')\n"
                       f"pathlib.Path(sys.argv[2]+'.tsv').write_bytes({evidence!r})\n")
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

    def test_linux_tsv_groups_words_and_preserves_unicode_with_honest_bounds(self):
        data = tsv(words="5\t1\t1\t1\t1\t1\t10\t20\t20\t10\t80\tcafé\n"
                   "5\t1\t1\t1\t1\t2\t35\t20\t20\t10\t60\t世界\n"
                   "5\t1\t1\t1\t2\t1\t10\t40\t20\t10\t90\tnext\n")
        lines = inbox.parse_tesseract_tsv(data, 100, 100)
        self.assertEqual([line["text"] for line in lines], ["café 世界", "next"])
        self.assertEqual(lines[0]["confidence"], .7)
        self.assertEqual(lines[0]["bounds"], {"x": .1, "y": .7, "width": .45, "height": .1})
        self.assertEqual(inbox.parse_tesseract_tsv(tsv(), 100, 100), [])

    def test_linux_tsv_refuses_malformed_incomplete_or_unbounded_evidence(self):
        word = "5\t1\t1\t1\t1\t1\t10\t20\t20\t10\t80\tword\n"
        cases = [b"", TSV_HEADER.encode(), tsv(words=word.replace("80", "nan")),
                 tsv(words=word.replace("80", "101")), tsv(words=word.replace("20\t20", "99\t20")),
                 tsv(words=word + word), tsv(words=word.replace("5\t1", "5\t2", 1)),
                 tsv(words=word.replace("word", "x" * (inbox.MAX_NOTE_BYTES + 1))),
                 b"x" * (inbox.MAX_TSV_BYTES + 1), tsv() + b"\xff"]
        for data in cases:
            with self.subTest(data=data[:80]), self.assertRaises(inbox.Refusal):
                inbox.parse_tesseract_tsv(data, 100, 100)

    def test_linux_missing_tools_are_typed_refusals_without_dispatch(self):
        for mirror, tools in [(False, {}), (True, {"tesseract": "/fixture/tesseract"})]:
            with patch.object(inbox.shutil, "which", side_effect=tools.get), \
                    patch.object(inbox.camera, "run_process") as process, self.assertRaises(inbox.Refusal):
                inbox.recognize_linux(self.root, mirror)
            process.assert_not_called()

    def test_linux_mirror_is_private_derived_copy_with_provenance(self):
        inbox.create_file(self.root / "source.png", PNG)
        evidence = tsv(1, 1, "5\t1\t1\t1\t1\t1\t0\t0\t1\t1\t80\tnote\n")
        derived = PNG + b"fixture-derived"

        def run(argv, timeout):
            if "hflip" in argv:
                self.assertIn("-n", argv)
                inbox.create_file(Path(argv[-1]), derived)
            elif "--version" in argv:
                return 0, "tesseract 5.fixture\n", ""
            else:
                self.assertEqual(Path(argv[1]).name, "ocr-mirrored.png")
                self.assertEqual(argv[-5:], ["-c", "load_system_dawg=0", "-c", "load_freq_dawg=0", "tsv"])
                inbox.create_file(Path(argv[2] + ".tsv"), evidence)
            return 0, "", ""

        with patch.object(inbox.shutil, "which", side_effect=lambda name: "/fixture/" + name), \
                patch.object(inbox.camera, "run_process", side_effect=run) as process:
            result = inbox.recognize_linux(self.root, True)
        self.assertEqual(process.call_count, 3)
        self.assertEqual((self.root / "source.png").read_bytes(), PNG)
        self.assertEqual((self.root / "ocr-mirrored.png").stat().st_mode & 0o777, 0o600)
        self.assertEqual(result["preprocessing"]["source_sha256"], inbox.digest(PNG))
        self.assertEqual(result["preprocessing"]["derived_sha256"], inbox.digest(derived))
        self.assertEqual(result["tsv_sha256"], inbox.digest(evidence))
        self.assertIn("not a calibrated probability", result["confidence_semantics"])
        self.assertIsNone(result["language_correction"])

    def test_linux_failure_is_retained_without_retry_or_false_candidate(self):
        with patch.object(inbox.sys, "platform", "linux"), \
                patch.object(inbox.shutil, "which", return_value=None):
            result = inbox.prepare(self.root, fixture_image=str(self.image))
        self.assertEqual(result["state"], "unknown")
        self.assertIn("Tesseract", result["reason"])
        with patch.object(inbox, "recognize") as recognize:
            again = inbox.prepare(self.root, fixture_image=str(self.image))
        recognize.assert_not_called()
        self.assertEqual(again["state"], "unknown")
        self.assertFalse((self.root / "candidate.txt").exists())

    def test_linux_unmirrored_dispatch_and_source_change_refusal(self):
        inbox.create_file(self.root / "source.png", PNG)
        evidence = tsv(1, 1, "5\t1\t1\t1\t1\t1\t0\t0\t1\t1\t80\tnote\n")

        def run(argv, timeout):
            if "--version" in argv:
                return 0, "tesseract 5.fixture", ""
            self.assertEqual(Path(argv[1]).name, "source.png")
            inbox.create_file(Path(argv[2] + ".tsv"), evidence)
            (self.root / "source.png").write_bytes(PNG + b"changed")
            return 0, "", ""

        with patch.object(inbox.shutil, "which", return_value="/fixture/tesseract") as which, \
                patch.object(inbox.camera, "run_process", side_effect=run), \
                self.assertRaisesRegex(inbox.Refusal, "changed during"):
            inbox.recognize_linux(self.root, False)
        which.assert_called_once_with("tesseract")
        self.assertFalse((self.root / "ocr-mirrored.png").exists())

    def test_linux_malformed_ocr_and_failure_never_make_candidate(self):
        for fail in (False, True):
            with self.subTest(process_failure=fail):
                run_root = inbox.private_directory(self.work / f"failure-{fail}")

                def run(argv, timeout, fail=fail):
                    if "--version" in argv:
                        return 0, "tesseract 5.fixture", ""
                    if fail:
                        return 1, "", "fixture language data unavailable"
                    inbox.create_file(Path(argv[2] + ".tsv"), TSV_HEADER.encode())
                    return 0, "", ""

                with patch.object(inbox.sys, "platform", "linux"), \
                        patch.object(inbox.shutil, "which", return_value="/fixture/tesseract"), \
                        patch.object(inbox.camera, "run_process", side_effect=run):
                    result = inbox.prepare(run_root, fixture_image=str(self.image))
                self.assertEqual(result["state"], "unknown")
                self.assertFalse((run_root / "candidate.txt").exists())
                self.assertFalse((run_root / "inbox").exists())

    def test_linux_png_header_rejects_invalid_crc_or_pixel_bomb(self):
        self.assertEqual(inbox.png_dimensions(PNG), (1, 1))
        with self.assertRaises(inbox.Refusal):
            inbox.png_dimensions(PNG[:25] + b"wrong" + PNG[30:])
        header = PNG[:16] + inbox.struct.pack(">II", 100000, 100000) + PNG[24:29]
        bomb = header + inbox.struct.pack(">I", inbox.zlib.crc32(header[12:29])) + PNG[33:]
        with self.assertRaises(inbox.Refusal):
            inbox.png_dimensions(bomb)


if __name__ == "__main__":
    unittest.main()
