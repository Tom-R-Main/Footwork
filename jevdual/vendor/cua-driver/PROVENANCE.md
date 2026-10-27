# CUA Driver source provenance

Source repository: https://github.com/trycua/cua
Reference commit: `d5373879e9e0baf5a63999ac4d26902340c0ce20` (2026-10-27).
Source directory: `libs/cua-driver/python/src/cua_driver`.
Python/native version: `0.38.0`. License: upstream MIT (`LICENSE.md`, copied as `LICENSE`).

The six Python files below are copied byte-for-byte from the reference. `README.md` is the upstream Python package README. Packaging metadata and `hatch_build.py` are Footwork-owned; the hook follows upstream `build_wheel.py` asset naming/tags and pins its release checksums instead of downloading them at build time.

| Source file | SHA256 |
| --- | --- |
| `__init__.py` | `056de6967110bf78c147c72eea4feedf230a38c682479afdaf07509cacb411ef` |
| `__main__.py` | `bcb78a6283dc6da69f3338879ae34a0f2dbeea3b444e4c3dd43f170d2922a387` |
| `_daemon.py` | `f6ce97a08ab5c124ba0210b00e44bd652b41cca5a9ae20a511a6409093e8f01e` |
| `_native.py` | `68def87c546974165ce31af18df499898cccc4d560606893d67e2315594de260` |
| `_native_contract.py` | `bc7ba740b00b7be3cb2279c4a68aafdde8be7ef924142031684839df67c8c8ca` |
| `wrapper.py` | `cfd7abe6215aab7c1d8f66f2c15e6cd6ab7f150918de7b301b73c253e90a61d6` |

Native checksum source: https://github.com/trycua/cua/releases/download/cua-driver-rs-v0.38.0/checksums.txt (retrieved 2026-10-27). Exact accepted hashes are recorded in `build_support.py`; no native asset is committed.

Workflow: [`../../docs/upstream/cua-driver-build.md`](../../docs/upstream/cua-driver-build.md).
