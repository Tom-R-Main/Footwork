"""Build the exact pinned Linux CUA candidate from local cached artifacts only.

Run inside the existing arm64 Footwork Docker image with /repo read-only and a
fresh writable /work/build directory. This compiles the complete Linux module;
only the IR1 test child module is appended after the candidate production text.
"""

import hashlib
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

REPO = Path("/repo/jevdual")
CACHE = Path("/workspace/cua-driver/.native-cache/target/release")
RUSTC = Path("/home/ubuntu/.cargo/bin/rustc")
FILES = (
    "libs/cua-driver/rust/crates/platform-linux/src/atspi/native.rs",
    "libs/cua-driver/rust/crates/platform-linux/src/atspi/mod.rs",
    "libs/cua-driver/rust/crates/platform-linux/src/tools/impl_.rs",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    task = Path(sys.argv[1])
    task.mkdir(parents=True, exist_ok=False)
    archive = REPO / "vendor/cua-driver/native-source.tar.gz"
    package = REPO / "scripts/ir2_replay_candidate"
    spec = json.loads((package / "candidate-manifest.json").read_text())
    assert sha(archive) == spec["archive_sha256"]
    assert sha(package / "candidate.patch") == spec["patch_sha256"]

    source = task / "source"
    source.mkdir()
    with tarfile.open(archive) as tf:
        members = tf.getmembers()
        for member in members:
            path = Path(member.name)
            assert not path.is_absolute() and ".." not in path.parts
            assert member.isfile() or member.isdir()
        tf.extractall(source, filter="data")
    workspace = source / "libs/cua-driver/rust"
    assert sha(workspace / "Cargo.lock") == "3a75d89d3f2fc53cf9e910beb3a754b28f27d29f2a2d4feed632b3959eed557f"
    for item in spec["files"]:
        assert item["path"] in FILES
        assert sha(source / item["path"]) == item["before_sha256"]
    patch = subprocess.run(
        ["/usr/bin/patch", "-p1", "-F", "0", "-d", str(source)],
        input=(package / "candidate.patch").read_bytes(),
        capture_output=True,
        check=False,
    )
    (task / "patch.stdout.txt").write_bytes(patch.stdout)
    (task / "patch.stderr.txt").write_bytes(patch.stderr)
    assert patch.returncode == 0, "candidate patch failed to apply without fuzz"
    for item in spec["files"]:
        assert sha(source / item["path"]) == item["candidate_sha256"]

    native = source / FILES[0]
    candidate = native.read_bytes()
    probe = REPO / "scripts/ir1_replay_audit/native_probe.rs"
    suffix = (
        "\n#[cfg(ir1_audit)]\n"
        f"#[path = {json.dumps(str(probe))}]\n"
        "pub mod ir1_audit;\n"
    ).encode()
    native.write_bytes(candidate + suffix)
    assert native.read_bytes()[: len(candidate)] == candidate

    fingerprints = sorted((CACHE / ".fingerprint").glob("platform-linux-*/lib-platform_linux.json"))
    assert len(fingerprints) == 1, fingerprints
    fingerprint = json.loads(fingerprints[0].read_text())
    assert fingerprint["features"] == '["default"]'
    extern = []
    deps = []
    for _, name, _, wanted in fingerprint["deps"]:
        matches = []
        for stamp in (CACHE / ".fingerprint").glob(f"*/lib-{name}"):
            if int.from_bytes(bytes.fromhex(stamp.read_text().strip()), "little") == wanted:
                suffix = stamp.parent.name.rsplit("-", 1)[1]
                matches.extend(
                    path
                    for path in (
                        CACHE / "deps" / f"lib{name}-{suffix}.rlib",
                        CACHE / "deps" / f"lib{name}-{suffix}.so",
                    )
                    if path.is_file()
                )
        assert len(matches) == 1, (name, matches)
        path = matches[0]
        extern.extend(("--extern", f"{name}={path}"))
        deps.append({"name": name, "path": str(path), "sha256": sha(path)})

    libs = ["-L", f"dependency={CACHE / 'deps'}"]
    for path in sorted((CACHE / "build").glob("*/out")):
        libs.extend(("-L", f"native={path}"))
    output = task / "bin"
    output.mkdir()
    env = dict(os.environ)
    env.update(
        CARGO_MANIFEST_DIR=str(workspace / "crates/platform-linux"),
        CARGO_PKG_VERSION="0.38.0",
        CARGO_PKG_NAME="platform-linux",
        CUA_DRIVER_GIT_SHA="d5373879e9e0baf5a63999ac4d26902340c0ce20",
    )
    compile_cmd = [
        str(RUSTC), "--edition=2021", "--crate-name", "platform_linux",
        "--crate-type", "rlib", str(workspace / "crates/platform-linux/src/lib.rs"),
        "--cfg", "ir1_audit", "--cfg", 'feature="default"',
        "-C", "debuginfo=0", "-o", str(output / "libplatform_linux.rlib"),
        *libs, *extern,
    ]
    manifest = {
        "candidate_patch_sha256": spec["patch_sha256"],
        "archive_sha256": sha(archive),
        "candidate_files": spec["files"],
        "test_probe_sha256": sha(probe),
        "cargo_lock_sha256": sha(workspace / "Cargo.lock"),
        "fingerprint": str(fingerprints[0]),
        "features": fingerprint["features"],
        "dependency_artifacts": deps,
        "candidate_native_prefix_byte_identical": native.read_bytes()[: len(candidate)] == candidate,
        "commands": [compile_cmd],
    }
    (task / "build.json").write_text(json.dumps(manifest, indent=2) + "\n")
    with (task / "compile.stdout.txt").open("w") as stdout, (task / "compile.stderr.txt").open("w") as stderr:
        build = subprocess.run(compile_cmd, cwd=workspace, env=env, stdout=stdout, stderr=stderr, check=False)
    manifest["compile_exit"] = build.returncode
    (task / "build.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if build.returncode:
        raise SystemExit(build.returncode)

    entry = task / "main.rs"
    entry.write_text("fn main(){platform_linux::atspi::native::ir1_audit::run();}\n")
    link_cmd = [
        str(RUSTC), "--edition=2021", str(entry),
        "--extern", f"platform_linux={output / 'libplatform_linux.rlib'}",
        *libs, "-C", "debuginfo=0", "-o", str(output / "ir1-probe"),
    ]
    manifest["commands"].append(link_cmd)
    with (task / "link.stdout.txt").open("w") as stdout, (task / "link.stderr.txt").open("w") as stderr:
        link = subprocess.run(link_cmd, cwd=workspace, env=env, stdout=stdout, stderr=stderr, check=False)
    manifest["link_exit"] = link.returncode
    if link.returncode == 0:
        manifest["probe_sha256"] = sha(output / "ir1-probe")
    (task / "build.json").write_text(json.dumps(manifest, indent=2) + "\n")
    raise SystemExit(link.returncode)


if __name__ == "__main__":
    main()
