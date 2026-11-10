# CUA Driver source provenance

Source repository: https://github.com/trycua/cua
Reference commit: `5486b6246e4c807c0d793216e52df283671d9362` (release `cua-driver-rs-v0.46.0`).
Source directory: `libs/cua-driver/python/src/cua_driver`.
Python/native version: `0.46.0`. License: upstream MIT (`LICENSE.md`, copied as `LICENSE`).

Footwork distribution version: `0.46.0+footwork.5486b624.cleanup2`. The published 0.46.0 wheel does not contain the required shutdown cleanup patch and cannot satisfy this exact dependency. The upstream Python `__version__` remains `0.46.0`.

The six Python files are copied byte-for-byte from the exact release source. The published macOS wheel has the same files except that its packaging removes the `x-release-please-version` comment from `__init__.py`. Generated records and native library must always be upgraded together.

| Source file | SHA256 |
| --- | --- |
| `__init__.py` | `968e30886e29ef5fc66316d4bb5aef46a30c9b8f5422635ac48982ab15379ddd` |
| `__main__.py` | `bcb78a6283dc6da69f3338879ae34a0f2dbeea3b444e4c3dd43f170d2922a387` |
| `_daemon.py` | `f6ce97a08ab5c124ba0210b00e44bd652b41cca5a9ae20a511a6409093e8f01e` |
| `_native.py` | `8bb3927dd6579d94468eb5c08b1700230359813074cd1959c2e226c318dd4828` |
| `_native_contract.py` | `f5237aa6dac954ea15959347ddaeb38e99b6df18c6c323093fabe275f27c808f` |
| `wrapper.py` | `cfd7abe6215aab7c1d8f66f2c15e6cd6ab7f150918de7b301b73c253e90a61d6` |

## Source archive

`native-source.tar.gz` SHA256: `8f517900274522a8447e44ca7e063f5c2d49bf8de2e2c812dcc8d9c9dad8a304` (6,403,447 bytes).

The complete upstream release archive has SHA256 `032ce99f2e33154082cf854a1a04213e8a7b9eeae0e524564c7c6adb0ae93112`. The selected, unpatched native archive has SHA256 `257a36f5a793ad66d9c3e276709a7c81b667ed960ca5a3544e2d0ea43678fad1`.

Selection includes `libs/cua-driver/rust`, `libs/cua-driver/wayland-helper`, `libs/cua/Cargo.toml`, `libs/cua/crates/cua-telemetry`, `libs/images/sandbox-images.json`, `libs/cua/crates/cua-teleport/src/ux/targets.json`, and `LICENSE.md`. Only regular source files and their ancestor directories are retained. Tar entries are path-sorted, with zero mtime/uid/gid and empty owner names; source file modes are preserved and directory mode is 0755. The PAX tar is compressed with Python gzip, empty filename, mtime zero, and compression level nine. No build artifacts or unrelated repository files are included.

## Required local cleanup patch

The exact release still spawns untracked browser/grant session-end work and returns from SDK shutdown without awaiting it. The four-file patch retains the previously reviewed cleanup2 implementation: runtime-owned task handles, cancellation-safe joining, completed-handle reaping, sticky abnormal-completion failure, and shutdown drain after session revocation. It does not change authorization predicates, Cargo dependencies or generated bindings.

`patches/session-cleanup-join.patch` is the inspectable diff against this release. `patches/session-cleanup-join.json` binds the original and patched file hashes and archive hashes. The previous 0.38 cleanup2 provenance, diff and manifest are retained under `history/`; its native archive remains in Git history. Prior qualification does not automatically qualify this newer build.

## Build and qualification

Build the CLI and SDK together with Rust 1.97.1, `--release --locked --jobs 2`, and `CUA_DRIVER_GIT_SHA` set to the complete release commit. Build helpers verify and restore the exact source archive. No published native binary is substituted into the custom distribution. See [`../../docs/upstream/cua-driver-build.md`](../../docs/upstream/cua-driver-build.md).

The published macOS universal2 wheel used only for ABI comparison has SHA256 `80b1be9b9a6aca20d733b10f221f9e478e862cfbcac4ce413ce5af7c141aa46c`. Its successful import establishes matched published bindings, not the required cleanup guarantee. Final qualification must use the custom wheel and retain its checksum.
