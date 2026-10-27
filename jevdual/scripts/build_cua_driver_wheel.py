"""Build the source-pinned CUA Driver wheel for this host; never starts the Driver."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Wheelhouse directory")
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / "vendor" / "cua-driver"
    subprocess.run(
        ["uv", "build", str(source), "--wheel", "--out-dir", str(args.output.resolve())], check=True
    )


if __name__ == "__main__":
    main()
