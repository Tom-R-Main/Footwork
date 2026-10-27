# CUA Driver source provenance

Source repository: https://github.com/trycua/cua
Reference commit: `d5373879e9e0baf5a63999ac4d26902340c0ce20` (2026-10-27).
Source directory: `libs/cua-driver/python/src/cua_driver`.
Python/native version: `0.38.0`. License: upstream MIT (`LICENSE.md`, copied as `LICENSE`).

The six Python files below are copied byte-for-byte from the reference. `README.md` is the upstream Python package README. Packaging metadata and build helpers are Footwork-owned. Distribution version `0.38.0+footwork.d5373879` distinguishes this exact native source snapshot from the earlier upstream 0.38.0 release. The unchanged upstream Python `__version__` remains `0.38.0`.

| Source file | SHA256 |
| --- | --- |
| `__init__.py` | `056de6967110bf78c147c72eea4feedf230a38c682479afdaf07509cacb411ef` |
| `__main__.py` | `bcb78a6283dc6da69f3338879ae34a0f2dbeea3b444e4c3dd43f170d2922a387` |
| `_daemon.py` | `f6ce97a08ab5c124ba0210b00e44bd652b41cca5a9ae20a511a6409093e8f01e` |
| `_native.py` | `68def87c546974165ce31af18df499898cccc4d560606893d67e2315594de260` |
| `_native_contract.py` | `bc7ba740b00b7be3cb2279c4a68aafdde8be7ef924142031684839df67c8c8ca` |
| `wrapper.py` | `cfd7abe6215aab7c1d8f66f2c15e6cd6ab7f150918de7b301b73c253e90a61d6` |

## Native source snapshot

`native-source.tar.gz` SHA256: `606d8c8696aa54afcff32f285f8f6730a8eef1b6c2b4730372f5ce2b0fe426b1` (5,887,584 bytes).

Created from the same exact commit with this path selection, then compressed with Python `gzip.GzipFile(fileobj=buffer, filename="", mode="wb", mtime=0, compresslevel=9)` (empty gzip filename, fixed timestamp and OS-neutral header):

```sh
git -C /path/to/reference/cua archive d5373879e9e0baf5a63999ac4d26902340c0ce20 \
  libs/cua-driver/rust libs/cua-driver/wayland-helper \
  libs/cua/Cargo.toml libs/cua/crates/cua-telemetry \
  libs/images/sandbox-images.json \
  libs/cua/crates/cua-teleport/src/ux/targets.json LICENSE.md
```

These are unmodified upstream source files, including `Cargo.lock`, `rust-toolchain.toml`, the Rust workspace's `THIRD_PARTY_NOTICES.md` and bundled asset notices. The archive contains no compiled CLI or shared library, no Cargo target directory, and no files from the reference working tree outside Git. The source hash is verified before every build and each extracted cache member is restored from the archive; unexpected members and links refuse the build.

The hook runs Cargo 1.97.1 with `--release --locked --jobs 2` and embeds the exact commit through `CUA_DRIVER_GIT_SHA`. No old release native binary is used. Build prerequisites and consumer installation: [`../../docs/upstream/cua-driver-build.md`](../../docs/upstream/cua-driver-build.md).
