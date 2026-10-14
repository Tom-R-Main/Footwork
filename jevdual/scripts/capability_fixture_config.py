"""Create per-job configuration from an already observed, owned fixture scope.

This copies resource identifiers, not permission or execution authority. Binding
still checks actual resource identity. No app is started and no input is sent.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    with args.scope.open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        parser.error("Fixture scope exceeds the configuration input bound")
    try:
        scope = json.loads(raw)
        source, destination = scope["source"], scope["destination"]
        command = [
            sys.executable,
            "-I",
            "-m",
            "jevdual.capability.cli",
            "config",
            "--run-dir",
            str(args.run_dir),
            "--source-pid",
            str(source["pid"]),
            "--source-window",
            str(source["window_id"]),
            "--source-url",
            source["url"],
            "--destination-pid",
            str(destination["pid"]),
            "--destination-window",
            str(destination["window_id"]),
            "--document",
            destination["document"],
        ]
    except (ValueError, RecursionError, KeyError, TypeError):
        parser.error("Invalid observed fixture scope")
    return subprocess.run(command, check=False, timeout=30).returncode


if __name__ == "__main__":
    raise SystemExit(main())
