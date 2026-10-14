"""Qualifier provenance/cleanup boundaries with synthetic files and no qualification launch."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import controller
import qualify_order_handoff as qualifier


class QualifierBoundaryTests(unittest.TestCase):
    def setUp(self):
        output = qualifier.BASE / "output"
        output.mkdir(mode=0o700, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="qualifier-boundary-", dir=output)
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def fixture(self, bound_socket):
        fixture = qualifier.Fixture("test_real_contact_fulfillment_commits_exact_version_and_receipt")
        fixture.control = self.directory / "control"
        fixture.control.mkdir(mode=0o700)
        binding = {"version": 1, "source_kind": controller.body.SOURCE_KIND,
                   "controller_sha256": qualifier.sha(qualifier.CONTROLLER.read_bytes()),
                   "controller_dir": str(fixture.control), "socket_path": str(bound_socket)}
        (fixture.control / "controller-binding.json").write_text(json.dumps(binding))
        (fixture.control / "controller-binding.json").chmod(0o600)
        fixture.expected_native_pid = None
        fixture.adapter_stopped = True
        fixture.processes = []
        fixture.handles = []
        fixture.events = []
        return fixture

    def test_cleanup_observes_bound_socket_and_refuses_when_it_remains(self):
        socket = self.directory / "bound.sock"
        socket.touch(mode=0o600)
        fixture = self.fixture(socket)
        # Endpoint location is a boundary double; controller path safety has its own conformance suite.
        with (mock.patch.object(qualifier, "expected_socket_path", return_value=socket, create=True),
              self.assertRaisesRegex(RuntimeError, "socket")):
            fixture.cleanup()
        cleanup = fixture.events[-1]
        self.assertTrue(cleanup["socket_exists"])
        self.assertEqual(cleanup["socket_path"], str(socket))
        self.assertTrue(socket.exists())

    def test_cleanup_verifies_absence_of_exact_bound_socket(self):
        socket = self.directory / "absent.sock"
        fixture = self.fixture(socket)
        with mock.patch.object(qualifier, "expected_socket_path", return_value=socket, create=True):
            fixture.cleanup()
        cleanup = fixture.events[-1]
        self.assertEqual(cleanup["socket_path"], str(socket))
        self.assertFalse(cleanup["socket_exists"])
        self.assertTrue(cleanup["socket_absence_verified"])

    def test_cleanup_refuses_binding_to_an_unrelated_path(self):
        expected = self.directory / "expected.sock"
        other = self.directory / "other.sock"
        fixture = self.fixture(other)
        with (mock.patch.object(qualifier, "expected_socket_path", return_value=expected, create=True),
              self.assertRaisesRegex(RuntimeError, "binding")):
            fixture.cleanup()

    def assert_wrong_source_refuses_absence(self, key, value):
        socket = self.directory / "absent.sock"
        fixture = self.fixture(socket)
        binding_path = fixture.control / "controller-binding.json"
        binding = json.loads(binding_path.read_bytes())
        binding[key] = value
        binding_path.write_text(json.dumps(binding))
        with (mock.patch.object(qualifier, "expected_socket_path", return_value=socket),
              self.assertRaisesRegex(RuntimeError, "binding")):
            fixture.cleanup()
        self.assertIsNone(fixture.events[-1]["socket_exists"])
        self.assertFalse(fixture.events[-1]["socket_absence_verified"])

    def test_wrong_simulation_source_kind_cannot_prove_socket_absence(self):
        self.assert_wrong_source_refuses_absence("source_kind", "physical_hardware")

    def test_wrong_controller_source_hash_cannot_prove_socket_absence(self):
        self.assert_wrong_source_refuses_absence("controller_sha256", "0" * 64)

    def test_cleanup_dangling_socket_entry_is_not_misreported_absent(self):
        socket = self.directory / "dangling.sock"
        socket.symlink_to(self.directory / "missing")
        fixture = self.fixture(socket)
        with (mock.patch.object(qualifier, "expected_socket_path", return_value=socket, create=True),
              self.assertRaisesRegex(RuntimeError, "socket")):
            fixture.cleanup()
        self.assertTrue(fixture.events[-1]["socket_exists"])

    def test_missing_socket_binding_cannot_prove_absence(self):
        fixture = self.fixture(self.directory / "absent.sock")
        (fixture.control / "controller-binding.json").unlink()
        with self.assertRaisesRegex(RuntimeError, "unconfirmed"):
            fixture.cleanup()
        self.assertIsNone(fixture.events[-1]["socket_exists"])
        self.assertFalse(fixture.events[-1]["socket_absence_verified"])

    def test_dirty_bytes_refuse_before_output_creation_or_scenario_launch(self):
        base = self.directory / "tools" / "physical-workcell"
        base.mkdir(parents=True, mode=0o700)
        (base / "output").mkdir(mode=0o700)
        (base / "source.py").write_bytes(b"dirty current bytes")
        output = base / "output" / "must-not-run"
        commit = "a" * 40

        def git(command, **kwargs):
            if command[1:3] == ["rev-parse", "HEAD"]:
                return commit if kwargs.get("text") else commit.encode()
            return b"committed source bytes"

        with (mock.patch.object(qualifier, "BASE", base),
              mock.patch.object(qualifier, "SOURCE_FILES", ("source.py",)),
              mock.patch.object(qualifier.subprocess, "check_output", side_effect=git),
              mock.patch.object(qualifier, "Fixture", side_effect=AssertionError("qualification launched")) as fixture,
              mock.patch("sys.argv", ["qualifier", "--output-dir", str(output), "--source-commit", commit])):
            with self.assertRaisesRegex(ValueError, "source differs"):
                qualifier.main()
            fixture.assert_not_called()
        self.assertFalse(output.exists())

    def test_matching_committed_bytes_produce_content_bound_freeze(self):
        base = self.directory / "tools" / "physical-workcell"
        base.mkdir(parents=True, mode=0o700)
        content = b"committed source bytes"
        (base / "source.py").write_bytes(content)
        commit = "a" * 40
        with (mock.patch.object(qualifier, "BASE", base),
              mock.patch.object(qualifier, "SOURCE_FILES", ("source.py",)),
              mock.patch.object(qualifier.subprocess, "check_output", side_effect=[commit, content]) as git):
            self.assertEqual(qualifier.freeze(commit), {"source.py": qualifier.sha(content)})
        self.assertEqual(git.call_args.args[0], ["git", "show", f"{commit}:tools/physical-workcell/source.py"])

    def test_named_commit_mismatch_refuses_before_source_reads(self):
        with (mock.patch.object(qualifier.subprocess, "check_output", return_value="a" * 40),
              mock.patch.object(qualifier.protocol, "read_bytes") as read):
            with self.assertRaisesRegex(ValueError, "current HEAD"):
                qualifier.freeze("b" * 40)
            read.assert_not_called()


if __name__ == "__main__":
    unittest.main()
