"""Conformance checks use fixtures, never a live camera."""

import base64
import contextlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from string import Template
from types import SimpleNamespace
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("camera_capture", BASE / "capture.py")
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
CAMERA = "MacBook Pro Camera"
LISTING = """[AVFoundation indev @ 0x123] AVFoundation video devices:
[AVFoundation indev @ 0x123] [0] MacBook Pro Camera
[AVFoundation indev @ 0x123] [1] OBS Virtual Camera
[AVFoundation indev @ 0x123] [2] Capture screen 0
[AVFoundation indev @ 0x123] AVFoundation audio devices:
[AVFoundation indev @ 0x123] [0] MacBook Pro Microphone
"""


def mac_cli():
    """Fresh-process Mac fixture, without a production platform override."""
    bootstrap = (
        "import runpy,sys,types; module=runpy.run_path(sys.argv.pop(1)); "
        "module['main'].__globals__['sys']=types.SimpleNamespace(platform='darwin'); "
        "raise SystemExit(module['main']())"
    )
    return [sys.executable, "-c", bootstrap, str(BASE / "capture.py")]


class CaptureTests(unittest.TestCase):
    def setUp(self):
        platform = patch.object(capture, "sys", SimpleNamespace(platform="darwin"))
        platform.start()
        self.addCleanup(platform.stop)
        capture.OUTPUT.mkdir(mode=0o700, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="conformance-", dir=capture.OUTPUT)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def inventory(self, permission="authorized"):
        return {"physical_cameras": [CAMERA], "avfoundation_video_devices": [CAMERA],
                "eligible_cameras": [CAMERA], "permission_status": permission,
                "programs": {"ffmpeg": "fixture-ffmpeg", "ffprobe": "fixture-ffprobe"}}

    def probe_result(self):
        return 0, json.dumps({"streams": [{"codec_name": "png", "width": 1, "height": 1,
                                          "nb_read_frames": "1"}]}), ""

    @contextlib.contextmanager
    def working_device(self):
        dispatched = []

        def run(argv, timeout):
            if argv[0] == "fixture-ffmpeg":
                ledger, _, _ = capture.paths(self.root, "first")
                self.assertEqual(capture.read_json(ledger)["state"], "pending")
                dispatched.append(argv)
                Path(argv[-1]).write_bytes(PNG)
                return 0, "", ""
            return self.probe_result()

        with patch.object(capture, "doctor", return_value=self.inventory()), \
                patch.object(capture, "binaries", return_value={"ffprobe": "fixture-ffprobe"}), \
                patch.object(capture, "run_process", side_effect=run):
            yield dispatched

    def test_physical_inventory_rejects_virtual_and_continuity(self):
        result = capture.parse_physical({"SPCameraDataType": [
            {"_name": CAMERA, "spcamera_model-id": CAMERA, "spcamera_unique-id": "private-id"},
            {"_name": "OBS Virtual Camera", "spcamera_model-id": "OBS"},
            {"_name": "Capture screen 0", "spcamera_model-id": "screen"},
            {"_name": "Phone", "spcamera_model-id": "Continuity Camera"},
            {"_name": "Incomplete device"},
        ]})
        self.assertEqual(result, [CAMERA])
        self.assertNotIn("private-id", repr(result))

    def test_video_inventory_never_contains_microphone(self):
        self.assertEqual(capture.parse_avfoundation(LISTING),
                         [CAMERA, "OBS Virtual Camera", "Capture screen 0"])

    def test_doctor_exact_intersection_and_duplicate_refusal(self):
        physical = {"SPCameraDataType": [{"_name": CAMERA, "spcamera_model-id": CAMERA}]}
        listing = LISTING.replace("[1] OBS Virtual Camera", "[1] " + CAMERA)
        with patch.object(capture, "binaries", return_value={"ffmpeg": "ffmpeg", "ffprobe": "ffprobe",
                                                               "swift": None, "system_profiler": "profiler"}), \
                patch.object(capture, "run_process", side_effect=[(0, json.dumps(physical), ""),
                                                                  (1, "", listing)]):
            inventory = capture.doctor(self.root)
        self.assertEqual(inventory["eligible_cameras"], [])
        with self.assertRaises(capture.Refusal):
            capture.select_camera(CAMERA, inventory)

    def test_unobserved_virtual_screen_and_index_selection_refused(self):
        for name in ("0", "OBS Virtual Camera", "Capture screen 0", "Another camera", CAMERA + ":none"):
            with self.subTest(name=name), self.assertRaises(capture.Refusal):
                capture.select_camera(name, self.inventory())

    def test_permission_is_inspection_only_and_prompt_requires_opt_in(self):
        for state in ("not_determined", "unknown", "unavailable"):
            with self.assertRaises(capture.Refusal):
                capture.select_camera(CAMERA, self.inventory(state))
            capture.select_camera(CAMERA, self.inventory(state), True)
        for state in ("denied", "restricted"):
            with self.assertRaises(capture.Refusal):
                capture.select_camera(CAMERA, self.inventory(state), True)
        source = (BASE / "permission.swift").read_text()
        self.assertIn("authorizationStatus(for: .video)", source)
        self.assertNotIn("requestAccess", source)

    def test_capture_persists_intent_and_uses_exact_camera_without_audio(self):
        with self.working_device() as dispatched:
            result = capture.capture(self.root, CAMERA, "first", 15)
            repeat = capture.capture(self.root, CAMERA, "first", 15)
        self.assertEqual(result["state"], "acquired")
        self.assertEqual(repeat["artifact"], result["artifact"])
        self.assertEqual(len(dispatched), 1)
        args = dispatched[0]
        self.assertEqual(args[args.index("-i") + 1], CAMERA + ":none")
        self.assertIn("-an", args)
        self.assertIn("-nostdin", args)
        self.assertIn("-n", args)
        self.assertNotIn("-video_size", args)
        self.assertEqual(args[args.index("-framerate") + 1], "30")
        self.assertLess(args.index("-framerate"), args.index("-i"))
        self.assertEqual(result["request"]["framerate_fps"], 30)

    def test_changed_token_arguments_refused_before_second_dispatch(self):
        with self.working_device() as dispatched:
            capture.capture(self.root, CAMERA, "first", 15)
            for camera, timeout, prompt in (("Other", 15, False), (CAMERA, 16, False),
                                             (CAMERA, 15, True)):
                with self.assertRaises(capture.Refusal):
                    capture.capture(self.root, camera, "first", timeout, prompt)
            ledger, _, _ = capture.paths(self.root, "first")
            record = capture.read_json(ledger)
            record["request"]["framerate_fps"] = 15
            capture.persist(ledger, record)
            with self.assertRaises(capture.Refusal):
                capture.capture(self.root, CAMERA, "first", 15)
            del record["request"]["framerate_fps"]
            capture.persist(ledger, record)
            with self.assertRaises(capture.Refusal):
                capture.capture(self.root, CAMERA, "first", 15)
        self.assertEqual(len(dispatched), 1)

    def test_original_mac_version_one_receipt_replays_without_opening_device(self):
        with self.working_device() as dispatched:
            capture.capture(self.root, CAMERA, "first", 15)
            ledger, _, _ = capture.paths(self.root, "first")
            record = capture.read_json(ledger)
            record["version"] = 1
            record["request"] = {
                "camera": CAMERA, "format": "png", "framerate_fps": 30,
                "timeout_seconds": 15, "allow_permission_prompt": False,
            }
            capture.persist(ledger, record)
            with patch.object(capture, "doctor", side_effect=AssertionError("device reopened")):
                self.assertEqual(capture.status(self.root, "first")["state"], "acquired")
                repeat = capture.capture(self.root, CAMERA, "first", 15)
            self.assertEqual(repeat["state"], "acquired")
            self.assertEqual(repeat["request"], record["request"])
            self.assertEqual(repeat["artifact"], record["artifact"])
            self.assertEqual(len(dispatched), 1)

    def test_unknown_and_valid_unreceipted_artifact_never_replay(self):
        ledger, artifact, _ = capture.paths(self.root, "first")
        request = {"camera": CAMERA, "format": "png", "framerate_fps": 30, "timeout_seconds": 15,
                   "allow_permission_prompt": False}
        capture.persist(ledger, {"token": "first", "request": request, "state": "pending"})
        artifact.write_bytes(PNG)
        with patch.object(capture, "doctor") as doctor:
            self.assertEqual(capture.capture(self.root, CAMERA, "first", 15)["state"], "unknown")
            with self.assertRaises(capture.Refusal):
                capture.capture(self.root, CAMERA, "second", 15)
        doctor.assert_not_called()

    def test_corrupt_or_missing_image_invalidates_receipt_and_blocks_new_capture(self):
        for mutate in (lambda p: p.write_bytes(b"changed"), lambda p: p.unlink()):
            with self.subTest(mutate=mutate):
                with self.working_device():
                    capture.capture(self.root, CAMERA, "first", 15)
                    ledger, artifact, _ = capture.paths(self.root, "first")
                    mutate(artifact)
                    self.assertEqual(capture.status(self.root, "first")["state"], "unknown")
                    self.assertEqual(capture.status(self.root, "first")["acquisition_outcome"], "acquired")
                    self.assertEqual(capture.read_json(ledger)["state"], "acquired")
                    with self.assertRaises(capture.Refusal):
                        capture.capture(self.root, CAMERA, "second", 15)
                for path in self.root.glob("*"):
                    path.unlink()

    def test_capture_timeout_retains_unknown(self):
        with patch.object(capture, "doctor", return_value=self.inventory()), \
                patch.object(capture, "run_process", side_effect=capture.Refusal("timeout")):
            self.assertEqual(capture.capture(self.root, CAMERA, "first", 1)["state"], "unknown")
        self.assertEqual(capture.status(self.root, "first")["state"], "unknown")

    def test_lost_receipt_does_not_promote_valid_frame(self):
        real_persist = capture.persist

        def fail_receipt(path, record):
            if record["state"] != "pending":
                raise OSError("injected persistence failure")
            real_persist(path, record)

        with self.working_device(), patch.object(capture, "persist", side_effect=fail_receipt):
            self.assertEqual(capture.capture(self.root, CAMERA, "first", 15)["state"], "unknown")
        self.assertTrue(capture.paths(self.root, "first")[1].exists())
        self.assertEqual(capture.status(self.root, "first")["state"], "unknown")

    def test_arbitrary_or_symlinked_run_paths_and_tokens_refused(self):
        with self.assertRaises(capture.Refusal):
            capture.private_directory(BASE / "escape")
        link = self.root / "link"
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(capture.Refusal):
            capture.private_directory(link / "child")
        for token in ("../outside", "", "a" * 129):
            with self.assertRaises(capture.Refusal):
                capture.paths(self.root, token)

    def test_lock_blocks_another_process(self):
        with capture.locked(self.root):
            result = subprocess.run([sys.executable, str(BASE / "capture.py"), "status", "--run-dir",
                                     str(self.root), "--token", "first"], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("another process", result.stdout)

    def test_timeout_kills_pipe_holding_descendants(self):
        marker = self.root / "survived"
        grandchild = f"import pathlib,time;time.sleep(.4);pathlib.Path({str(marker)!r}).write_text('alive')"
        parent = f"import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',{grandchild!r}]);time.sleep(5)"
        started = time.monotonic()
        with self.assertRaises(capture.Refusal):
            capture.run_process([sys.executable, "-c", parent], .15)
        self.assertLess(time.monotonic() - started, 2)
        time.sleep(.5)
        self.assertFalse(marker.exists())

    @unittest.skipUnless(shutil.which("ffprobe"), "installed ffprobe required for real fixture decoding")
    def test_real_ffprobe_decodes_fixture_and_rejects_header_only_png(self):
        image = self.root / "fixture.png"
        image.write_bytes(PNG)
        result = capture.artifact_info(image, shutil.which("ffprobe"))
        self.assertEqual((result["width"], result["height"], result["codec"]), (1, 1, "png"))
        image.write_bytes(PNG[:33])
        with self.assertRaises(capture.Refusal):
            capture.artifact_info(image, shutil.which("ffprobe"))

    def test_cli_repeat_token_across_fresh_processes_without_camera(self):
        bin_dir = self.root / "bin"
        bin_dir.mkdir(mode=0o700)
        marker = self.root / "dispatches"
        fixture = Template("""#!/usr/bin/env python3
import base64,json,pathlib,sys
name=pathlib.Path(sys.argv[0]).name
if name=='system_profiler':
    print(json.dumps({'SPCameraDataType':[{'_name':'MacBook Pro Camera','spcamera_model-id':'MacBook Pro Camera'}]}))
elif name=='swift': print('authorized')
elif name=='ffmpeg':
    if '-list_devices' in sys.argv:
        print($listing,file=sys.stderr); sys.exit(1)
    with open($marker,'a') as f: f.write('dispatch\\n')
    pathlib.Path(sys.argv[-1]).write_bytes(base64.b64decode($png))
elif name=='ffprobe':
    print(json.dumps({'streams':[{'codec_name':'png','width':1,'height':1,'nb_read_frames':'1'}]}))
""").substitute(listing=repr(LISTING), marker=repr(str(marker)), png=repr(base64.b64encode(PNG).decode()))
        for name in ("ffmpeg", "ffprobe", "swift", "system_profiler"):
            program = bin_dir / name
            program.write_text(fixture)
            program.chmod(0o700)
        env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"])
        args = [*mac_cli(), "capture", "--run-dir", str(self.root / "run"),
                "--camera", CAMERA, "--token", "fresh-process"]
        for _ in range(2):
            result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=10, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["state"], "acquired")
        self.assertEqual(marker.read_text(), "dispatch\n")
        status = subprocess.run([sys.executable, str(BASE / "capture.py"), "status", "--run-dir",
                                 str(self.root / "run"), "--token", "fresh-process"], env=env,
                                capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        self.assertEqual(json.loads(status.stdout)["state"], "acquired")
        self.assertEqual(marker.read_text(), "dispatch\n")

    def test_public_cli_failed_or_timed_out_dispatch_reports_unknown_and_private_diagnostics(self):
        for mode in ("failure", "timeout"):
            with self.subTest(mode=mode):
                bin_dir = self.root / mode
                bin_dir.mkdir(mode=0o700)
                fixture = Template("""#!/usr/bin/env python3
import json,pathlib,sys,time
name=pathlib.Path(sys.argv[0]).name
if name=='system_profiler':
    print(json.dumps({'SPCameraDataType':[{'_name':'MacBook Pro Camera','spcamera_model-id':'MacBook Pro Camera'}]}))
elif name=='swift': print('authorized')
elif name=='ffmpeg':
    if '-list_devices' in sys.argv:
        print($listing,file=sys.stderr); sys.exit(1)
    print('PRIVATE_CAPTURE_DIAGNOSTIC',file=sys.stderr,flush=True)
    if $mode == 'timeout': time.sleep(30)
    sys.exit(1)
""").substitute(listing=repr(LISTING), mode=repr(mode))
                for name in ("ffmpeg", "ffprobe", "swift", "system_profiler"):
                    program = bin_dir / name
                    program.write_text(fixture)
                    program.chmod(0o700)
                env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"])
                run_dir = self.root / (mode + "-run")
                args = [*mac_cli(), "capture", "--run-dir", str(run_dir),
                        "--camera", CAMERA, "--token", "failed-operation", "--timeout", "1"]
                result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=10, check=False)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                record = json.loads(result.stdout)
                self.assertEqual(record["state"], "unknown")
                self.assertEqual(record["claims"], [])
                self.assertNotIn("PRIVATE_CAPTURE_DIAGNOSTIC", result.stdout + result.stderr)
                self.assertIn("PRIVATE_CAPTURE_DIAGNOSTIC", (run_dir / record["diagnostic_name"]).read_text())
                diagnostic = run_dir / record["diagnostic_name"]
                self.assertEqual(diagnostic.stat().st_mode & 0o777, 0o600)
                again = subprocess.run(args, env=env, capture_output=True, text=True, timeout=10, check=False)
                self.assertEqual(json.loads(again.stdout)["state"], "unknown")

    def test_missing_permission_is_refused_without_ledger_or_dispatch(self):
        with patch.object(capture, "doctor", return_value=self.inventory("not_determined")), \
                patch.object(capture, "run_process") as dispatch, self.assertRaises(capture.Refusal):
            capture.capture(self.root, CAMERA, "first", 15)
        dispatch.assert_not_called()
        self.assertFalse(capture.paths(self.root, "first")[0].exists())


class LinuxCaptureTests(unittest.TestCase):
    def setUp(self):
        platform = patch.object(capture, "sys", SimpleNamespace(platform="linux"))
        platform.start()
        self.addCleanup(platform.stop)
        capture.OUTPUT.mkdir(mode=0o700, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="linux-conformance-", dir=capture.OUTPUT)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.device = {"path": "/dev/video7", "device": 5, "inode": 9, "rdev": os.makedev(81, 7)}
        self.inventory = {"backend": "v4l2", "video_devices": [self.device],
                          "programs": {"ffmpeg": "fixture-ffmpeg", "ffprobe": "fixture-ffprobe"}}

    def test_exact_character_node_identity_without_opening_device(self):
        info = SimpleNamespace(st_mode=stat.S_IFCHR | 0o660, st_dev=5, st_ino=9,
                               st_rdev=os.makedev(81, 7))
        with patch.object(Path, "lstat", return_value=info) as inspect, \
                patch.object(capture.os, "open") as opened:
            self.assertEqual(capture.linux_device_identity("/dev/video7"), self.device)
            inspect.assert_called_once_with()
            opened.assert_not_called()

    def test_implicit_noncanonical_paths_refused_before_metadata(self):
        with patch.object(Path, "lstat") as inspect:
            for path in ("0", "auto", "", "/dev/video01", "/dev/video7/../video0", "/dev/video7:none",
                         "/dev/v4l/by-id/camera", "/tmp/video7", "-i", None):
                with self.subTest(path=path), self.assertRaises(capture.Refusal):
                    capture.linux_device_identity(path)
            inspect.assert_not_called()

    def test_missing_symlink_regular_and_other_character_nodes_refused(self):
        for mode, major in ((stat.S_IFLNK, 81), (stat.S_IFREG, 81), (stat.S_IFCHR, 1)):
            info = SimpleNamespace(st_mode=mode | 0o600, st_rdev=os.makedev(major, 7))
            with self.subTest(mode=mode, major=major), patch.object(Path, "lstat", return_value=info), \
                    self.assertRaises(capture.Refusal):
                capture.linux_device_identity("/dev/video7")
        with patch.object(Path, "lstat", side_effect=FileNotFoundError), self.assertRaises(capture.Refusal):
            capture.linux_device_identity("/dev/video7")

    def test_doctor_inventory_does_not_open_or_claim_physical_devices_or_permission(self):
        with patch.object(capture, "binaries", return_value=self.inventory["programs"]), \
                patch.object(Path, "glob", return_value=[Path("/dev/video7")]), \
                patch.object(capture, "linux_device_identity", return_value=self.device), \
                patch.object(capture, "run_process") as process:
            result = capture.doctor(self.root)
        self.assertEqual(result["eligible_cameras"], ["/dev/video7"])
        self.assertEqual(result["permission_status"], "not_checked")
        self.assertNotIn("physical_cameras", result)
        process.assert_not_called()

    def test_unobserved_replaced_device_and_permission_prompt_refused(self):
        for identity, prompt in ((dict(self.device, inode=10), False), (self.device, True)):
            with patch.object(capture, "linux_device_identity", return_value=identity), \
                    self.assertRaises(capture.Refusal):
                capture.select_camera("/dev/video7", self.inventory, prompt)

    def test_unavailable_node_refuses_before_intent_and_missing_tools_do_not_install(self):
        with patch.object(capture, "doctor", return_value=self.inventory), \
                patch.object(capture, "linux_device_identity", side_effect=capture.Refusal("unavailable")), \
                patch.object(capture, "run_process") as process, self.assertRaises(capture.Refusal):
            capture.capture(self.root, "/dev/video7", "frame", 15)
        self.assertFalse(capture.paths(self.root, "frame")[0].exists())
        process.assert_not_called()
        with patch.object(capture.shutil, "which", return_value=None), self.assertRaises(capture.Refusal):
            capture.binaries()

    @contextlib.contextmanager
    def working_device(self):
        dispatched = []

        def run(argv, timeout):
            if argv[0] == "fixture-ffmpeg":
                retained = capture.read_json(capture.paths(self.root, "frame")[0])
                self.assertEqual(retained["state"], "pending")
                self.assertEqual(retained["request"]["device_identity"], self.device)
                dispatched.append(argv)
                Path(argv[-1]).write_bytes(PNG)
                return 0, "", ""
            return 0, json.dumps({"streams": [{"codec_name": "png", "width": 1, "height": 1,
                                               "nb_read_frames": "1"}]}), ""

        with patch.object(capture, "doctor", return_value=self.inventory), \
                patch.object(capture, "linux_device_identity", return_value=self.device), \
                patch.object(capture, "binaries", return_value=self.inventory["programs"]), \
                patch.object(capture, "run_process", side_effect=run):
            yield dispatched

    def test_capture_binds_v4l2_device_and_never_reopens_for_repeat(self):
        with self.working_device() as dispatched:
            result = capture.capture(self.root, "/dev/video7", "frame", 15)
            with patch.object(capture, "linux_device_identity", side_effect=AssertionError("device reopened")), \
                    patch.object(capture, "doctor", side_effect=AssertionError("inventory repeated")):
                repeat = capture.capture(self.root, "/dev/video7", "frame", 15)
            self.assertEqual(result["state"], "acquired")
            self.assertEqual(repeat["artifact"], result["artifact"])
            self.assertEqual(result["request"]["backend"], "v4l2")
            self.assertEqual(len(dispatched), 1)
            argv = dispatched[0]
            self.assertEqual(argv[argv.index("-i") + 1], "/dev/video7")
            self.assertEqual(argv[argv.index("-f") + 1], "v4l2")
            self.assertIn("-an", argv)
            self.assertIn("-n", argv)
            self.assertEqual(argv[argv.index("-frames:v") + 1], "1")
            with self.assertRaises(capture.Refusal):
                capture.capture(self.root, "/dev/video8", "frame", 15)

    def test_replacement_after_intent_retains_unknown_without_dispatch_or_replay(self):
        with patch.object(capture, "doctor", return_value=self.inventory), \
                patch.object(capture, "linux_device_identity", side_effect=[self.device, dict(self.device, inode=10)]), \
                patch.object(capture, "run_process") as process:
            result = capture.capture(self.root, "/dev/video7", "frame", 15)
            repeat = capture.capture(self.root, "/dev/video7", "frame", 15)
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(repeat["state"], "unknown")
        process.assert_not_called()

    def test_lost_receipt_never_promotes_frame_or_retries(self):
        persist = capture.persist

        def fail_receipt(path, record):
            if record["state"] != "pending":
                raise OSError("receipt lost")
            persist(path, record)

        with self.working_device() as dispatched, patch.object(capture, "persist", side_effect=fail_receipt):
            result = capture.capture(self.root, "/dev/video7", "frame", 15)
            repeat = capture.capture(self.root, "/dev/video7", "frame", 15)
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(repeat["state"], "unknown")
        self.assertEqual(len(dispatched), 1)

    def test_timeout_is_unknown_and_does_not_retry_a_different_mode(self):
        with patch.object(capture, "doctor", return_value=self.inventory), \
                patch.object(capture, "linux_device_identity", return_value=self.device), \
                patch.object(capture, "run_process", side_effect=capture.Refusal("timeout")) as process:
            result = capture.capture(self.root, "/dev/video7", "frame", 1)
            repeat = capture.capture(self.root, "/dev/video7", "frame", 1)
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(repeat["state"], "unknown")
        self.assertEqual(process.call_count, 1)


if __name__ == "__main__":
    unittest.main()
