# Linux runtime qualification — 2026-10-30

This extends the prerequisite-only [initial report](../report.md). The native CUA driver builds on Linux; a pure Python product wheel avoids building Footwork's optional Rust accelerator on the consumer. Pure Python does not replace CUA.

## Artifacts and environments

The amd64 builder extends the cached ExecuFunction Ubuntu 24.04 workspace image. Its exact CUA source built with Rust 1.97.1, installed as a binary wheel, and controlled an owned Mousepad under Xvfb/D-Bus. Rosetta reports the emulator as the process executable, so browser and document ownership checks correctly refused. Those checks were not relaxed.

Full native desktop qualification uses arm64 Ubuntu 26.04/Python 3.14.4 in the same local Docker Linux VM, extending the cached desktop image. Task containers have two CPUs, 3 GiB memory, 512 MiB shared memory, a 512-process limit, dropped capabilities, no-new-privileges and no host desktop or credential mounts. The final repeat adds Docker `--init` to reap exited processes. The initial container disabled swap; the repeat inadvertently used Docker's default 6 GiB combined memory/swap ceiling. CPU, RAM, process and shared-memory limits matched. The earlier process-limit hits and their disappearance support the lifecycle diagnosis, but this was not a perfectly controlled single-variable comparison. The builder image is `sha256:616d7e9baf59cec34adcde325478d982e6b423d7e96bf013d20b00b8e4912932`.

| Artifact | SHA256 |
| --- | --- |
| Portable product wheel | `edf0a82d319f5072df922faf9b8f747cd429f2a6e8a018623612e1646630571d` |
| Installer | `1e8e012253ad3c73e858fc4ebd5d3a94419059756e122add10a1ab9d89705b57` |
| CUA Linux x86_64 | `bd7d92848622d96ec295870bbdea001909ea327efb3472e0f79c02e5e99dc67d` |
| CUA Linux aarch64 | `b8be0241d35aeb67fbcb742b8e416be62810c833b4c58629146fab0aa665ce94` |

Both CUA wheels use pinned source `d5373879e9e0baf5a63999ac4d26902340c0ce20`, version `0.38.0+footwork.d5373879`. [Bundle manifests](bundle-aarch64.json), [x86_64 manifest](bundle-x86_64.json) and [archive identities](archives.json) retain the checksums. Other binary dependencies are downloaded during installation unless cached; these are not complete offline dependency archives. The Ubuntu 26.04 arm64 wheel does not establish compatibility with older glibc distributions.

The source suite ran from a real copied Git checkout at container snapshot `3ba3963470e5935b4d4022b3b62d8e06c55d346f`. [Selected source hashes](source-snapshot.json) identify its implementation, tests and build scripts; later documentation and the optional qualification harness are separately recorded in [checked files](checked-files.json). No checkout under the user's active primary branch was changed.

## Observations

[Final installed-wheel identity](installed-wheel-identity.json) matches all 191 packaged files. The clean-container [final receipt](installed-runtime.json), [restart status](restart-status.json) and [saved-artifact check](saved-artifact.json) passed, retaining 109 exact characters with SHA256 `4c833c0e33e3cc5bde92d43db38d935f65dce6918d78e0ee88f4eec72edb7d3c`.

The installed public CLI observes an owned Chrome page and appends exact text in Mousepad. The public MCP server binds an explicit document, appends once, returns the retained result for a repeated token and preserves the result after restart. Current agreement is reported separately from the historical receipt. The harness then dispatches Control-S through the native bridge in an exclusive desktop and independently checks the expected file SHA through the public artifact checker. The MCP receipt itself correctly says disk persistence was not checked. This does not establish a provider-backed save journey.

[Direct text evidence](exact-text.jsonl) retains Unicode/trailing-whitespace append, stale-value refusal and a complete 5,014-character value beyond CUA's preview cap. The adapter bounds reads at 65,536 codepoints and binds process incarnation, X11 geometry, bus identity, unique object owner/path and ancestry. These checks do not claim an oracle for arbitrary accessibility object replacement with all observable identity fields preserved.

[Optional runtime evidence](optional-runtime.json) records installed direct and mirrored synthetic OCR, unchanged original images, exact fixture candidates, digest-bound acceptance, repeat acceptance and independent saved-artifact checks. Both notes have SHA256 `74abfe1124bc7970940069519ef7a38579a8669d5d69e07ea0ab183a514af11e`. OCR reconstruction remains reviewable text, not a general guarantee of exact original spacing. The camera inventory had no devices; the explicit missing device refused without capture. Physical acquisition was not tested. [Simulator discovery](simulator-discovery.json) checks installed discovery and initialization/status.

## Validation and failures retained

- [macOS full suite](macos-tests.txt): 2,405 passed, 70 skipped.
- [Initial final-source Linux full suite](linux-tests.txt): 2,402 passed, 72 skipped, one browser page-readiness timeout. A subsequent browser-only repeat exhausted process capacity because the original container's `sleep` PID 1 did not reap browser descendants. Its cgroup recorded process-limit hits and no OOM events. This is why reproduction now requires `--init`; production predicates and deadlines were not weakened.
- [First final installed rerun](qualification-final-initial.txt) stopped after MCP dispatch when independent text qualification could not bind a field. It did not produce a success receipt. Earlier successful runtime and restart receipts are explicitly named `*-prefinal.json`; they are not substituted for final-wheel qualification.
- The clean-container [agent-loop browser repeat](linux-browser-reaped.txt) passed all 11 tests, including the sole full-suite failure. The [remaining two browser-marked tests](linux-browser-other-reaped.txt) also passed. All 13 browser tests passed without product/test changes; process-limit hits stayed zero. [Resource diagnosis](browser-resource-diagnosis.txt) retains the prior process-limit evidence.
- Camera adapter conformance: 29 passed. [Linux inbox/workbench conformance](linux-optional-tests.txt): 38 passed, 23 subtests, with the installed `FOOTWORK_EXECUTABLE` explicitly supplied. The initial copied-checkout invocation lacked that executable path and failed; it was not a product OCR failure.
- [Ruff](ruff.txt) passed. Packaged tool resources matched all 103 source files. Notebook validation passed before the evidence commit.

The earlier Linux suite also found synthetic macOS fixtures using the host platform, a missing fixture argument, and a visual timeout test whose setup could consume its 15 ms dispatch budget. Narrow explicit macOS-contract fixtures and the preregistered timeout conformance fix resolved those failures. Production timeout behavior is unchanged.

## Scope

Qualified scope is browser automation and native X11/AT-SPI text control, an explicit Mousepad document contract, deterministic CLI/MCP execution/replay/restart, synthetic OCR and optional-tool refusal behavior. Shared foreground coexistence refuses; exclusive-desktop foreground input is explicit. Arbitrary Linux saved-document discovery is unavailable, so persistence requires an explicit file/artifact check.

Wayland, physical cameras/robots, the actual Meta sandbox, provider-backed planning and hosted CI were not exercised. Existing macOS benchmark results are not Linux performance claims. No cloud VM, PR, merge, publication or paid provider evaluation was performed. Reproduction steps and platform requirements are in [the Linux guide](../../../docs/linux-support.md).
