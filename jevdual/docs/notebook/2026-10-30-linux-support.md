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

## L4 · prediction · 2026-10-30 00:48
Hypothesis: a bounded direct AT-SPI Text/EditableText adapter can preserve complete exact text and append readback where the pinned CUA Linux snapshot truncates at 4096 characters.
Test: implement at the existing injected native accessibility seam; bind process incarnation, X11 window, accessibility bus identity and unique owner/object path; challenge long text, Unicode, trailing whitespace, changed/replaced targets and uncertain replies against an owned Linux editor.
Predicts: exact before/after strings survive the snapshot cap, append inserts only at the measured end, and lost identity or incomplete reads refuse before input. Uncertain write replies remain uncertain rather than retried.
Against: the editor cannot expose a unique stable window/element binding, reads remain lossy, a replacement object is silently accepted, or the backend duplicates a mutation after a failed acknowledgement.
Refs: python/jevdual/native.py; vendor/cua-driver/native-source.tar.gz; https://jeepney.readthedocs.io/en/latest/api/blocking.html

## LU4 · update · 2026-10-30 01:08
Observed: the approved amd64 image and pinned CUA wheel built; the real generated bundle installed all binary dependencies. The public native CLI observed Mousepad and appended Unicode with exact whitespace readback. Hardened direct AT-SPI reads preserved 5014 characters and refused a stale expected value. Browser ownership and Mousepad document binding correctly refused because Rosetta exposes /run/rosetta/rosetta as the process executable.
Inferred: these executable refusals are an emulation boundary, not proof that native Linux process qualification fails. Do not weaken executable checks to accept command-line claims.
Next: qualify native arm64 apps in a task-owned image on the same local Linux VM, retaining the amd64 build and failed binding evidence separately. L3/L4 remain open pending end-to-end qualification.
Refs: scripts/linux/Dockerfile; python/jevdual/browser_driver.py; python/jevdual/linux_documents.py

## L5 · prediction · 2026-10-30 01:08
Hypothesis: native arm64 Linux execution supplies real executable identities and permits the existing exact process/window/document binding checks without an emulation exception.
Test: extend the cached native arm64 desktop image with the same approved isolated build prerequisites; build the pinned CUA wheel, install the real product, and exercise browser read, scoped editor append/replay/restart and independent saved-file readback on its owned display. Never infer hardware support from this VM.
Predicts: /proc process identity agrees with the actual browser/editor binaries and the public CLI/MCP paths can bind and operate while stale or mismatched resources refuse.
Against: native process identity still disagrees, the CUA arm64 build/load fails, or public operations require a weaker identity predicate.
Refs: python/jevdual/linux_documents.py; python/jevdual/browser_driver.py; docs/linux-support.md

## L6 · prediction · 2026-10-30 01:18
Hypothesis: Linux-specific camera input and OCR engines can reuse the existing literal-request, artifact, review and replay boundaries without changing their meaning.
Test: add explicit V4L2 device selection and Tesseract TSV OCR adapters; exercise missing/malformed prerequisites, device mismatch, no-audio capture arguments, unchanged source bytes, synthetic text images, explicit review acceptance and installed artifact readback. No physical camera exists in this task's container, so device acquisition cannot be established here.
Predicts: Linux OCR produces reviewable artifacts with engine-specific provenance; camera requests either bind a selected real character device or refuse before capture. Existing macOS conformance remains green.
Against: adapter selection silently guesses a device, source pixels are modified, synthetic success is reported as physical capture, or the original review/replay boundary is bypassed.
Refs: tools/camera-capture-experiment/capture.py; tools/desk-inbox-experiment/inbox.py; scripts/sync_tool_resources.py

## LU5 · update · 2026-10-30 01:20
Observed: native arm64 CUA built and the complete bundle installed. Its process executable identity is /usr/bin/mousepad. Public explicit-PID startup still refuses: Linux app discovery names the process Mousepad with desktop ID org.xfce.mousepad, while its window snapshot reports Org.xfce.mousepad. The fixture retained this failure before any input.
Inferred: the current equality check conflates a desktop app ID with its display name. Normalize only a unique same-PID discovery record whose name or desktop ID matches the observed identifier; preserve all PID/window and unrelated-name refusals. Add a regression before changing this path.
Refs: python/jevdual/native.py; python/jevdual/session.py; scripts/linux/qualify.py
Next: rerun the corrected app-ID regression and installed CLI/MCP journey, then validate optional Linux adapters and the final source snapshot.

## LU6 · update · 2026-10-30 01:31
Observed: the final installed Linux bundle completed the public CLI/browser/MCP journey, repeated tokens and restart agreement, direct native save, and independent public artifact verification. Direct and mirrored synthetic OCR produced exact reviewed text and saved artifacts; a missing camera refused. Linux full-suite failures narrowed to a fixture caller not forwarding its new Mac-contract dependency, an unnecessary app-list query for ordinary display names, and a 15 ms visual timeout test expiring before dispatch under the constrained VM.
Next: preserve strict same-PID normalization for desktop IDs, forward the explicit synthetic-Mac fixture dependency, and isolate the visual test's intended in-flight timeout from setup scheduling. Then rerun both platform suites and retain checked artifact identities.
Refs: scripts/linux/qualify.py; tests/test_bounded.py; tests/test_visual_decisions.py; python/jevdual/native.py

## L7 · prediction · 2026-10-30 01:31
Hypothesis: the visual timeout failure is test setup crossing its 15 ms pre-dispatch deadline, rather than a lost timeout or retry in production.
Test: the drafted test freezes only the producer's monotonic clock during preparation while retaining asyncio's real 15 ms timeout around a 50 ms simulated response. Rerun this contract and both platform suites without changing production deadlines.
Predicts: the request dispatches once, times out, and retains an unsettled cost reservation; the independent pre-dispatch expiry tests keep their existing refusals.
Against: the request retries, returns a probability, releases its cost reservation, or still fails after setup scheduling is isolated.
Refs: tests/test_visual_decisions.py; python/jevdual/visual_decisions.py

## LU7 · update · 2026-10-30 01:45
Resolves: L4 = held
Observed: the direct Linux adapter retained Unicode and trailing whitespace, read the complete 5014-character fixture, and refused a stale expected value. Conformance checks cover identity changes and uncertain write replies without retries. Observable identity checks cannot detect every hypothetical object replacement that preserves all exposed identity fields.
Next: retain the bounded guarantee and final installed-bundle evidence separately from adapter conformance.
Refs: results/linux-support-20261030/runtime/exact-text.jsonl; tests/test_linux_ax.py; tests/test_linux_native.py

## LU8 · update · 2026-10-30 01:45
Resolves: L6 = held
Observed: installed direct and mirrored synthetic OCR retained original bytes, produced the exact expected fixture candidate, accepted its approved digest and passed saved-artifact checks on replay. Camera inventory and explicit missing-device refusal passed without opening a device; no physical acquisition was established. Mac camera receipt replay compatibility and both platform adapter conformance passed.
Next: qualify a real explicitly selected camera only on a host that provides one; do not promote inventory or synthetic-image evidence into hardware claims.
Refs: results/linux-support-20261030/runtime/optional-runtime.json; results/linux-support-20261030/runtime/linux-optional-tests.txt; scripts/linux/qualify_optional.py

## LU9 · update · 2026-10-30 01:45
Resolves: L7 = held
Observed: both platform suites pass the intended visual dispatch timeout and independent pre-dispatch expiry contracts after setup scheduling is isolated. The final Mac suite passed 2405 tests with 70 skips. The final-source Linux suite passed 2402 with 72 skips and one unrelated browser readiness timeout.
Next: preserve production deadlines and investigate the browser execution environment before reporting a clean Linux browser group.
Refs: results/linux-support-20261030/runtime/macos-tests.txt; results/linux-support-20261030/runtime/linux-tests.txt; tests/test_visual_decisions.py

## LU10 · update · 2026-10-30 01:45
Observed: the original container used sleep as PID 1 and accumulated hundreds of unreaped browser descendants. Its cgroup reported process-limit hits and zero OOM events; repeated browser tests failed as process capacity ran out. The first final-wheel installed repeat also stopped without a success receipt when exact text could not be qualified. Earlier successful receipts do not establish final-wheel success.
Inferred: container process lifecycle is a plausible common cause; the prior notebook's phrase final installed bundle referred to the earlier successful bundle, before the last source fixes. Final artifact qualification requires its own repeat.
Next: use a fresh task-owned container with --init under the same CPU/memory/process restrictions, verify installed package bytes against the final wheel, and repeat native qualification and browser tests sequentially without changing product predicates.
Refs: results/linux-support-20261030/runtime/qualification-final-initial.txt; scripts/linux/qualify.py; docs/linux-support.md

## LU11 · update · 2026-10-30 01:46
Resolves: L3 = held
Observed: exact pinned CUA wheels built for amd64 and arm64. The final portable product wheel matched all 191 installed package files, then completed public CLI/browser/MCP append, replay and restart in the clean native Linux container. Independent artifact readback confirmed saved bytes. No consumer compiler was used for the binary installation.
Next: retain the architecture/distribution-specific bundles and explicitly scoped installation requirements; actual Meta sandbox installation remains separate validation.
Refs: results/linux-support-20261030/runtime/installed-wheel-identity.json; results/linux-support-20261030/runtime/installed-runtime.json; results/linux-support-20261030/runtime/saved-artifact.json

## LU12 · update · 2026-10-30 01:46
Resolves: L5 = held
Observed: native Linux process identities passed the existing checks without an emulation exception. In the clean --init container with unchanged resource limits, all 13 browser tests passed unchanged and the final installed CLI/MCP journey passed. The process-limit counter remained zero. The prior full-suite failure and failed installed repeat remain retained rather than rewritten as successes.
Next: require process reaping in repeated container qualification and preserve strict product identity predicates.
Refs: results/linux-support-20261030/runtime/linux-browser-reaped.txt; results/linux-support-20261030/runtime/linux-browser-other-reaped.txt; results/linux-support-20261030/runtime/restart-status.json; results/linux-support-20261030/runtime/browser-resource-diagnosis.txt

## LS2 · summary · 2026-10-30 01:46
Established: Linux X11 browser/native text paths, explicit Mousepad document binding, durable CLI/MCP replay/restart and independently checked saved bytes work in the installed bundle. Linux synthetic OCR/review/replay and missing-camera refusal passed. Both architecture bundles contain prebuilt CUA wheels, and consumer installs use binary dependencies. Mac regression suite passed 2405 tests; Linux full suite retained 2402 passes and one browser failure, followed by all 13 browser tests passing cleanly. Ruff, packaged resources and notebook checks passed.
Uncertain: actual Meta sandbox installation, Wayland, shared-desktop foreground coexistence, physical cameras/robots, provider-backed planning and hosted CI remain unqualified. The arm64 Ubuntu 26.04 wheel does not establish older-glibc compatibility; bundles still download other binary dependencies unless cached.
Decision: retain implementation commits 818d586 and 653ee74, the local bundles and redacted evidence on codex/linux-support. Stop owned temporary Linux helpers. Do not merge, publish, allocate cloud resources or generalize these results to other Linux environments.
Refs: docs/linux-support.md; results/linux-support-20261030/runtime/report.md; results/linux-support-20261030/runtime/archives.json

## LU13 · update · 2026-10-30 01:47
Observed: final Docker configuration inspection found the clean repeat used a 6 GiB combined memory/swap ceiling, while the original explicitly disabled swap at 3 GiB. CPU, RAM, process and shared-memory limits matched. This corrects the earlier same-resource-limits shorthand; successful final bundle receipts remain valid, but the reaping diagnosis is not a perfectly controlled single-variable comparison.
Next: retain both selected container configurations and this limitation with the process-limit counters; do not claim that every environment setting was identical.
Refs: results/linux-support-20261030/runtime/container-limits.json; results/linux-support-20261030/runtime/report.md
