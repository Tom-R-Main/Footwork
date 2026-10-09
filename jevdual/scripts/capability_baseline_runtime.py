"""Stage the exact published Chrome DevTools MCP baseline in private project output.

No global installation, lifecycle scripts, browser download, or reference checkout edits.
The published release is identified separately from the reference source revision.
Without --execute this prints the installation plan only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

VERSION = "1.10.1"
INTEGRITY = "sha512-Klw6HWDqHC/XS1JwZldd2r49aUhbUJN9m9Mvcx4SEueIPXtzuQX+QelxAViobv8YUkDZ7HWDrmViR6LeYK0wAw=="
REFERENCE_SHA = "f08dbe152502"
PROJECT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = args.run_dir.resolve()
    if not root.is_relative_to(PROJECT / "output"):
        parser.error("runtime must be staged within this project's private output directory")
    npm, node = shutil.which("npm"), shutil.which("node")
    if not npm or not node:
        parser.error("existing npm and Node are required")
    command = [
        npm,
        "install",
        "--prefix",
        str(root),
        "--save-exact",
        "--ignore-scripts",
        "--no-audit",
        "--no-fund",
        "--cache",
        str(root / "npm-cache"),
        f"chrome-devtools-mcp@{VERSION}",
    ]
    if not args.execute:
        print(json.dumps({"command": command, "version": VERSION, "integrity": INTEGRITY}))
        return
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    with (root / "install.log").open("w") as log:
        subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
    lock = json.loads((root / "package-lock.json").read_text())
    resolved = lock["packages"]["node_modules/chrome-devtools-mcp"]
    if resolved["version"] != VERSION or resolved["integrity"] != INTEGRITY:
        raise RuntimeError("published version or integrity differs from the pinned baseline")
    package = root / "node_modules" / "chrome-devtools-mcp"
    binary = package / "build/src/bin/chrome-devtools-mcp.js"
    receipt = {
        "release": f"chrome-devtools-mcp@{VERSION}",
        "reference_sha_prefix": REFERENCE_SHA,
        "release_is_reference_byte_identity": False,
        "resolved": resolved,
        "node": node,
        "node_version": subprocess.check_output([node, "--version"], text=True).strip(),
        "npm_version": subprocess.check_output([npm, "--version"], text=True).strip(),
        "cli": str(binary),
        "cli_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "lock_sha256": hashlib.sha256((root / "package-lock.json").read_bytes()).hexdigest(),
        "lifecycle_scripts": False,
        "global_install": False,
        "command": command,
    }
    (root / "runtime.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
