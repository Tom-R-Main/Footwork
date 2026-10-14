"""Synthetic measurement-worker storage boundaries; no renderer or live qualification."""

import os
import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import measurement


class MeasurementStorageTests(unittest.TestCase):
    def setUp(self):
        protocol = measurement.protocol
        protocol.OUTPUT.mkdir(mode=0o700, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="measurement-storage-", dir=protocol.OUTPUT)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.requests = protocol.directory(self.root / "requests", create=True)
        images = protocol.directory(self.root / "images", create=True)
        image = images / "synthetic.png"
        protocol.create_file(image, b"synthetic image boundary")
        self.packet = {"bench_id": "bench", "job_id": "job", "generation": 1, "native_time_s": 0,
                       "image_sha256": protocol.sha(image.read_bytes()), "state_sha256": "a" * 64,
                       "image_path": str(image)}
        self.packet_file = self.requests / "packet.json"
        packet_bytes = protocol.encoded(self.packet)
        protocol.create_file(self.packet_file, packet_bytes)
        self.packet_sha = protocol.sha(packet_bytes)
        manifest = {"bench_id": "bench", "generation": 1, "state_sha256": "a" * 64,
                    "active_job": {"job_id": "job"}, "busy": {"operation_id": "measure", "kind": "measure"}}
        protocol.create_file(self.root / "bench.json", protocol.encoded(manifest))
        self.compute = mock.patch.object(measurement, "compute", return_value={
            "method": "simulated_orange_RGB_footprint", "orange_pixel_count": 4,
            "centroid_pixel_xy": [2., 2.], "block_box": [1, 1, 3, 3],
            "block_center_xy": [0., 0.], "footprint_area_m2": .0004})
        self.compute.start()
        self.addCleanup(self.compute.stop)
        self.database = self.root / "measurements.sqlite"

    def run_worker(self):
        return measurement.run(self.root, "measure", self.packet_file, self.packet_sha)

    def test_crash_immediately_after_sqlite_open_leaves_private_file(self):
        connect = sqlite3.connect

        def crash(path, *args, **kwargs):
            connection = connect(path, *args, **kwargs)
            connection.close()
            raise RuntimeError("synthetic crash before insert")

        previous_umask = os.umask(0o022)
        try:
            with (mock.patch.object(measurement.sqlite3, "connect", side_effect=crash),
                  self.assertRaisesRegex(RuntimeError, "synthetic crash before insert")):
                self.run_worker()
        finally:
            os.umask(previous_umask)
        self.assertEqual(stat.S_IMODE(self.database.stat().st_mode), 0o600)
        self.assertEqual(self.database.stat().st_uid, os.getuid())

    def test_existing_public_database_is_refused_without_chmod_or_connection(self):
        with sqlite3.connect(self.database) as connection:
            connection.execute(measurement.SCHEMA)
        self.database.chmod(0o644)
        before = self.database.read_bytes()
        with mock.patch.object(measurement.sqlite3, "connect", wraps=sqlite3.connect) as connect:
            with self.assertRaises(measurement.body.Refusal):
                self.run_worker()
            connect.assert_not_called()
        self.assertEqual(self.database.read_bytes(), before)
        self.assertEqual(stat.S_IMODE(self.database.stat().st_mode), 0o644)

    def test_symlink_database_is_refused_without_touching_target(self):
        target = self.root / "other"
        measurement.protocol.create_file(target, b"unrelated")
        self.database.symlink_to(target)
        with mock.patch.object(measurement.sqlite3, "connect") as connect:
            with self.assertRaises(measurement.body.Refusal):
                self.run_worker()
            connect.assert_not_called()
        self.assertEqual(target.read_bytes(), b"unrelated")

    def test_existing_private_unknown_database_is_not_repaired_or_replaced(self):
        measurement.protocol.create_file(self.database, b"not a SQLite database")
        identity = self.database.stat().st_ino
        with self.assertRaises(sqlite3.DatabaseError):
            self.run_worker()
        self.assertEqual(self.database.read_bytes(), b"not a SQLite database")
        self.assertEqual(self.database.stat().st_ino, identity)

    def test_private_database_returns_exact_historical_row_without_duplicate_insert(self):
        first = self.run_worker()
        with mock.patch.object(measurement.os, "getpid", return_value=999999):
            self.assertEqual(self.run_worker(), first)
        self.assertEqual(measurement.read_result(self.root, "measure"), first)
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM measurements").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
