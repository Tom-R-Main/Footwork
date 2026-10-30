# Linux installation and runtime qualification

## L1 · prediction · 2026-10-30 00:24
Hypothesis: the portable Footwork wheel can avoid its optional Rust core on a constrained Linux consumer, but the bundle installer and runtime still require explicit native CUA and graphical-session prerequisites; pure Python does not replace CUA.
Test: inspect the cached ExecuFunction Linux image without network access, exercise consumer installation and public diagnostics, then qualify browser and native actions where the available runtime permits. Challenge missing prerequisites, incompatible wheels, stale identities, and macOS regressions.
Predicts: installation can use prebuilt wheels without a consumer compiler; missing native or desktop capabilities are reported before input dispatch rather than mislabeled as working Linux desktop support.
Against: a compiler is unavoidable for a prebuilt consumer bundle, or diagnostic success still conceals a missing action route.
Refs: docs/unified-cli.md; docs/upstream/cua-driver-build.md; scripts/build_agent_bundle.py

## L2 · exploratory · 2026-10-30 00:24
Question: which browser and native primitives in the pinned CUA Linux implementation preserve Footwork's exact-value, identity, and delivery guarantees on an available Linux desktop?
Test: inspect the pinned source and qualify the actual Linux driver before selecting platform adapters; retain unsupported capabilities and uncertain dispatch as refusals. No provider calls or cloud allocation are part of this probe.
Refs: vendor/cua-driver/PROVENANCE.md; python/jevdual/ax.py; python/jevdual/posture.py; python/jevdual/session_operations.py

## LU1 · update · 2026-10-30 00:35
Observed: the cached ExecuFunction Ubuntu 24.04 amd64 image runs the dependency-free probe and builds the portable product wheel offline. Its Python can seed pip 24.0 into a new venv without network access. The generated installer installed synthetic product/CUA wheels and ran their entrypoint in that Linux container with no uv/base pip/compiler. Installing the real product wheel without dependencies exposes discovery and strict prerequisite blockers, not native control. The pinned Linux CUA build still lacks a toolchain and desktop bus packages.
Inferred: consumer compilation is avoidable, but the complete real dependency bundle and native platform behavior remain unqualified; L1 stays open.
Next: obtain approval for the prepared isolated dependency build, then qualify the actual Linux CUA runtime before porting native helpers. Preserve the macOS capability refusal meanwhile.
Refs: results/linux-support-20261030/execufunction-host-probe.json; results/linux-support-20261030/linux-installer-fixture.txt; results/linux-support-20261030/linux-installed-discovery.json; docs/linux-support.md

## LU2 · update · 2026-10-30 00:35
Observed: the default full suite in this unbuilt worktree passed 2212 tests but failed the native-backend expectation. The explicit pure-Python rerun passed 2212 tests but exposed an existing test that expects the lazy-UUID patch even when pure mode deliberately disables it. This is conformance work: preserve the normal repr/hash checks and assert refusal plus unchanged upstream class in pure mode. No production patch behavior changes.
Next: rerun the corrected pure-mode test and full suite; retain both initial failures as environment/test-contract evidence.
Refs: tests/test_patch.py; results/linux-support-20261030/pytest.txt; results/linux-support-20261030/pytest-pure.txt

## LU3 · update · 2026-10-30 00:39
Resolves: L1 = inconclusive
Observed: final pure-Python suite passed 2213 tests, with 70 skips and 13 deselected browser cases; final focused checks passed 60 tests. Ruff, resource snapshot checks, notebook validation and offline consumer package verification passed. The real portable product wheel has identical SHA256 on the local host and cached Linux image. The generated installer also ran offline in Linux using synthetic wheels and Python bundled ensurepip. No complete Linux CUA bundle or native action route was exercised.
Next: native dependency downloads need the pending user approval required by the supplied AGENTS.md. After that, build and load the exact CUA wheel, then qualify Linux actions before changing native authority boundaries.
Refs: results/linux-support-20261030/report.md; results/linux-support-20261030/checked-files.json

## LS1 · summary · 2026-10-30 00:39
Established: consumer installer can use uv, external pip or bundled ensurepip without compiling dependencies; incompatible CUA OS/architecture is refused before creating a venv. Host diagnostics run with Python alone and never claim runtime readiness. Browser discovery supports explicit Linux binaries and checks exact process ownership. The scoped Mac capability still refuses unsupported Linux authority.
Uncertain: full real Linux dependency installation, CUA observation/actions, native exact-value and restart adapters, shared-desktop guarantees, Wayland, camera/OCR and the actual Meta sandbox remain unqualified. The Docker recipe is prepared, not built.
Decision: retain the reviewed local work on codex/linux-support, keep native scope gates intact, and resume at the approved isolated dependency build. No PR, publication, merge or cloud change was performed.
Refs: docs/linux-support.md; results/linux-support-20261030/report.md

## L3 · prediction · 2026-10-30 00:42
Hypothesis: the pinned CUA Linux source can supply an X11/AT-SPI observation and action route in the approved ExecuFunction-derived image; the remaining incompatibilities are in Footwork's platform helpers rather than an absent upstream Linux driver.
Test: build the prepared image and exact source wheel, install a fresh real dependency bundle, then observe and change an owned editor/browser in an isolated Xvfb/D-Bus session. Record build failures and native refusals before changing adapters.
Predicts: the library loads and provides window/tree observations and at least one target-bound input with independent readback; Footwork's macOS-specific seams can be isolated from those working primitives.
Against: the pinned source cannot build or load on this host, the driver cannot bind a Linux app, or delivered input lacks reliable target identity/readback.
Refs: scripts/linux/Dockerfile; vendor/cua-driver/PROVENANCE.md; docs/linux-support.md
