# Debian VM acceptance — 2026-10-30

The Linux implementation at **0b1e82c** passed the installed deterministic CLI/MCP journey in this attached Debian 13 x86-64 VM after supplying the missing isolated-desktop prerequisites. Product code, driver predicates and tests were unchanged. The first failed save and its diagnostics are retained.

## Verified behavior

- Fresh consumer installation used the generated bundle and binary packages, including the simulator extra. No Rust compilation occurred in the consumer install. The separate development environment was refreshed with `uv sync --locked`.
- [Installed identity](installed-identity.json) verifies all **191** packaged files against the product wheel. Its SHA256 is `edf0a82d319f5072df922faf9b8f747cd429f2a6e8a018623612e1646630571d`, identical to the handoff's wheel. CUA uses this VM's existing cached native x86-64 build of pinned version `0.38.0+footwork.d5373879`, SHA256 `0595b6042a98538b3c79ddef07301dd9481e477a5fbf64278b6cc63c2ed474c9`; it is a separately built artifact from the handoff's CUA wheel. Installed dependency versions and the [bundle manifest](bundle-manifest.json) are retained.
- The [installed receipt](runtime/receipt.json) covers exact native CLI append, owned-browser read, public MCP append, duplicate-token prevention, server restart and agreement after restart. [Restart evidence](runtime/restarted-status.json) distinguishes historical completion from current agreement.
- Save used the documented direct native bridge on an isolated exclusive desktop, followed by independent public artifact checking. [Saved-byte verification](runtime/saved-artifact.txt) confirms **109 codepoints / 117 UTF-8 bytes**, SHA256 `4c833c0e33e3cc5bde92d43db38d935f65dce6918d78e0ee88f4eec72edb7d3c`. This was not a provider-backed public save journey.
- [Optional qualification](optional-runtime.json) passed direct and horizontally mirrored synthetic OCR, unchanged source-image hashes, exact reviewed candidates, digest-bound acceptance, replay and saved artifacts. Camera inventory found no video nodes; an explicit missing-device request refused without capture.
- Installed simulator initialization/status passed ([init](simulator-init.json), [status](simulator-status.json)); installed schema discovery and Node-module export also passed. This does not qualify physical robots or caller-supplied browser capture adapters.

## Prerequisites supplied in this VM

The base image already supplied Chromium, `/usr/bin/mousepad`, session D-Bus, AT-SPI, FFmpeg, Tesseract with English data, Node and a DejaVu TrueType font. It had no active graphical session and lacked Xvfb/Openbox.

Debian binary packages **xvfb, openbox, libobrender32v5, libobt2v5 and libimlib2t64** were downloaded through the existing signed Debian package configuration and extracted under `/workspace/.footwork-setup/sysroot`, without privileged installation. [Package versions and hashes](added-prerequisites.json) are retained. The rootless session required:

```sh
. /workspace/.footwork-setup/activate.sh
export LD_LIBRARY_PATH=/workspace/.footwork-setup/sysroot/usr/lib/x86_64-linux-gnu
export XDG_DATA_DIRS=/workspace/.footwork-setup/sysroot/usr/share:/usr/local/share:/usr/share
export XDG_CONFIG_DIRS=/workspace/.footwork-setup/sysroot/etc/xdg:/etc/xdg
```

The documented `desktop-session.sh` ran under a new `dbus-run-session`, using Xvfb display `:99`. The qualification harness used the actual ELF browser executable `/usr/lib/chromium/chromium`, preserving executable identity checks. It supplied the documented container-only browser sandbox flags through the fixture harness. The product launcher was unchanged. [The successful orchestration](reproduce-runner.py) records the selected commands and paths; choose new state/output paths before another run.

[Host inventory](host-probe.json) records Debian 13, glibc 2.41, native x86-64 and Python 3.12.14. The visible cgroup grants four CPU cores and 16 GiB memory, with no swap and no finite process limit. This is not the earlier two-core/3-GiB acceptance profile, or proof of performance on the Muse VM.

## Failures retained

1. Before the branch was pushed, this VM contained baseline `f849e16`. Its public browser route failed on the macOS Chrome path; doctor reported `platform_unsupported`. These are baseline observations, not failures of `0b1e82c` ([browser command](browser-start.json), [doctor](doctor.json)). The baseline suite passed 2,253 tests with 28 skipped and one failure caused by a duplicate ID in this session's added notebook. The identifier was corrected before the Linux-branch suite, which passed.
2. An exploratory dummy-Xorg probe found the owned window, but its assertion inspected opaque SDK repr strings rather than snapshot fields. Its negative text result is inconclusive, not a product failure ([probe](native/driver.json)).
3. The first installed Linux journey passed CLI/browser/MCP text and restart checks but failed the saved-file assertion. Rootless Openbox could not locate its theme/config and exited ([window-manager diagnostic](failed-runtime/openbox.txt)). CUA refused foreground input with `foreground_unavailable` and no active window, retaining exact focus checks. The [save receipt](failed-runtime/driver-save.json) reports `dispatched: true` even though the driver summary says no input was sent; this reporting inconsistency remains unchanged. Independent file readback caught the failure ([run](qualification.txt)).
4. Adding the extracted package's XDG data/config search paths kept Openbox running. The unchanged installed wheel then completed the journey on fresh state/output ([run](qualification-ready-run.json)). Openbox's missing Debian application-menu warning remained nonfatal.

## Validation

| Check | Result | Evidence |
| --- | --- | --- |
| Linux-branch non-browser Python suite | **2,434 passed, 28 skipped**, 13 browser tests deselected | [output](linux-pytest.txt) |
| Linux-branch headless browser suite | **13 passed**, no skips | [output](linux-browser.txt) |
| Ruff | Passed | [output](ruff.txt) |
| Packaged tool resources | 103 source files matched | [output](resources.json) |
| Notebook validator and notebook tests | Passed after this session's duplicate-ID correction | [validator](notebook.txt), [tests](notebook-tests.txt) |

The test runs used the branch's existing tests and identity checks. Browser tests disabled optional extensions and used the prepared container mode; extension behavior was not qualified. The consumer environment remains at `/workspace/scratch/footwork-debian-consumer`, and its bundle at `/workspace/scratch/footwork-debian-bundle`. All directly owned temporary desktop/browser/fixture processes were stopped.

Wayland, shared foreground coexistence, physical cameras/robots, provider-backed planning and hosted CI remain untested. Local commits contain only this session's notebook and acceptance evidence; no implementation changes, push, PR or merge were performed.

## Follow-up: save-refusal correction retest

The subsequent [045fc5d VM retest](../linux-vm-save-receipt-20261030/report.md) retains the full real SDK refusal envelope and an offline failing replay. The correction still rejects the enriched reply; the ordinary working-desktop save journey passes. Original acceptance receipts and hashes above are unchanged.
