# Building the CUA Driver 0.38.0 dependency

The October 27 reference checkout is at
`d5373879e9e0baf5a63999ac4d26902340c0ce20`. Its Python SDK and native release
are 0.38.0; PyPI publishes only through 0.37.0 at the time of this update.
Footwork therefore carries the unchanged Python binding sources in
`vendor/cua-driver`, with the upstream MIT license and source hashes in
`vendor/cua-driver/PROVENANCE.md`. No compiled binaries are committed.

`uv sync` uses the local path in `[tool.uv.sources]` and builds this dependency
in isolation. The build hook downloads the versioned upstream native archive
for the build host, checks its SHA256 against a value recorded in `build_support.py`,
and packages only the named executables and shared library. Cached archives
are verified on every build; builds never fetch a replacement checksum.
A mismatch or unsupported platform fails before packaging. Building does not
load the library, start a Driver, request permissions, or modify the reference
checkout.

Supported assets match upstream: macOS universal2 (13+), Linux x86_64/aarch64
(glibc 2.31+), Windows amd64/arm64. Selection uses the actual build host;
this workflow does not cross-compile. Only macOS arm64 is exercised locally
by this refresh. Other platforms require their corresponding CI/build hosts.

To supply the dependency alongside a Footwork consumer wheel, from `jevdual/`:

```sh
uv build vendor/cua-driver --wheel --out-dir ../output/cua-wheelhouse
# Equivalent convenience helper (standard library only):
python3 scripts/build_cua_driver_wheel.py --output ../output/cua-wheelhouse
# Install both from the wheelhouse, retaining PyPI for other dependencies:
uv pip install --python /path/to/consumer/python \
  --find-links ../output/cua-wheelhouse /path/to/jevdual.whl
```

`[tool.uv.sources]` is a repository development setting and is not embedded in
Footwork's standard wheel dependency metadata. A consumer needs the built CUA
wheel through `--find-links` or a package index that serves it. The packaging
workflow builds it before its clean-install checks.

The ignored `vendor/cua-driver/.native-cache/` holds only downloaded native
release archives and can be removed when no build uses it. Wheel output stays
under ignored `output/` or the caller's chosen artifact directory. A warm
verified cache allows CUA's hook to run offline; the isolated build backend and
other dependencies must also be available in uv's cache.

An upstream version change requires reviewing the SDK/native ABI together,
copying the new binding source with provenance, updating native hashes in `build_support.py` and
platform tags, and rerunning the CUA contract and packaging checks. Once an
appropriate upstream Python wheel is published, this local packaging can be
retired in a separate dependency change.
