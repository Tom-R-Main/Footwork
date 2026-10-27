# Building the current CUA reference dependency

Footwork uses the exact October 27 CUA reference snapshot
`d5373879e9e0baf5a63999ac4d26902340c0ce20`, including its native implementation.
Although its upstream version field is 0.38.0, the reference has native changes
after the 0.38.0 release. Footwork identifies the complete build as
`cua-driver==0.38.0+footwork.d5373879` so the released native binary cannot
silently satisfy this dependency.

`vendor/cua-driver/src/cua_driver` contains the six unchanged upstream Python
binding files. `vendor/cua-driver/native-source.tar.gz` is a minimal `git archive`
of the same commit: the Rust workspace, Linux helper, telemetry dependency and
its two external JSON resources, and MIT license. Source hashes, archive hash,
paths, and reconstruction command are recorded in
`vendor/cua-driver/PROVENANCE.md`. No compiled binaries are committed.

The build hook verifies the source archive against the hardcoded SHA256 in
`build_support.py`, restores its exact contents into an ignored source cache,
refuses unexpected cache files and links, and runs:

```sh
cargo +1.97.1 build --release --locked --jobs 2 -p cua-driver -p cua-driver-sdk
```

Windows adds `-p cua-driver-uia`. The exact commit is embedded through
`CUA_DRIVER_GIT_SHA`. macOS sets `MACOSX_DEPLOYMENT_TARGET=13.0` and packages
only the build host's architecture. Linux wheels use local `linux_x86_64` or
`linux_aarch64` tags; they make no manylinux compatibility claim. Windows
builds native amd64/arm64 wheels. Cross compilation is not supported by this
workflow. macOS arm64 is the locally exercised host; other hosts require CI
qualification.

Install the pinned Rust compiler before syncing or building:

```sh
rustup toolchain install 1.97.1 --profile minimal
```

macOS requires Xcode and its command-line tools. Linux requires the native
X11/AT-SPI/Cairo/keyboard/clipboard development libraries installed by the
repository CI workflow. Windows requires the matching MSVC build tools.
Cargo can download the dependencies in the upstream `Cargo.lock`; the hook
does not install a toolchain automatically. Building does not start the Driver,
load its library, request permissions, or change the reference checkout.

From `jevdual/`, `uv sync` uses `[tool.uv.sources]` to build the local source
package in isolation. To supply it alongside a Footwork consumer wheel:

```sh
uv build vendor/cua-driver --wheel --out-dir ../output/cua-wheelhouse
# Equivalent convenience helper (standard library only):
python3 scripts/build_cua_driver_wheel.py --output ../output/cua-wheelhouse
uv pip install --python /path/to/consumer/python \
  --find-links ../output/cua-wheelhouse /path/to/jevdual.whl
```

A normal Footwork wheel requires the exact local-version CUA distribution,
so consumers need this wheelhouse or an index serving that build. Development
`[tool.uv.sources]` settings are not embedded in standard wheel metadata. The
packaging workflow and onboarding source packet build the dependency before
installing Footwork.

`vendor/cua-driver/.native-cache/` holds the restored source and Cargo target
artifacts. Those are regenerable and remain ignored. The vendored source
archive, SDK files, build backend version and upstream Cargo lock provide a
repeatable source build procedure; the workflow does not claim native binaries
are byte-identical across different compilers, hosts or build paths. Retain
wheel hashes and native build receipts when qualifying an artifact.

An update requires reviewing Python/native ABI changes together, regenerating
the source archive and source hashes, advancing the local-version commit suffix,
and rerunning contracts, deterministic tests and consumer packaging checks.
