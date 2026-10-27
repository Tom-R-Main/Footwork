# CUA and Browser-use reference refresh

## UR1 · prediction · 2026-10-27 17:02
Hypothesis: Footwork can adopt browser-use 0.13.14 and cua-driver 0.38.0 from the October 27 reference snapshots while preserving its existing policy, delivery authority, receipts and session semantics through bounded integration changes.
Test: compare both reference trees against the pinned seams; update exact dependency pins, browser-use submodule and affected adapters; run contract tests, deterministic suite, upstream reuse tests and local headless browser integration without paid model calls or real desktop dispatch.
Predicts: current reference APIs can express each existing Footwork operation and authorization constraint, and the adapted integration passes those checks without changing policy thresholds or backend defaults.
Against: an existing operation or authorization boundary cannot be represented, a patch no longer preserves upstream behavior, or deterministic/integration checks expose an unresolved regression.
Refs: /Volumes/External SSD/referencerepos/browser-use at 2cc71890e65056b67fdb29d98bb407749c15bb08; /Volumes/External SSD/referencerepos/cua at d5373879e9e0baf5a63999ac4d26902340c0ce20; CONTRIBUTING.md; tests/contract/

## UR2 · prediction · 2026-10-27 17:07
Hypothesis: the installed CLI's Python prerequisite blocker is caused by its hand-written clause parser rejecting valid whitespace in normalized Requires-Python metadata.
Test: preserve the failing doctor output; replace only the Python requirement parser with packaging SpecifierSet and test valid spaced metadata, incompatible interpreters, invalid or missing requirements and missing parser support; rerun the installed public doctor command.
Predicts: valid spaced requirements accept Python 3.12 while invalid, absent, incompatible or unparseable requirements still block; dependency version diagnostics retain their current behavior.
Against: the same blocker remains for valid normalized metadata, invalid or incompatible metadata passes, or another diagnostic contract regresses.
Refs: output/upstream-refresh-doctor-before.json; python/jevdual/capability/setup.py

## UR3 · prediction · 2026-10-27 17:08
Hypothesis: the inherited upstream browser tests stall because Footwork's upstream script discards browser-use's session-scoped asyncio fixture and test-loop settings with `-c /dev/null`, leaving its long-lived browser event bus on a different loop from the test.
Test: run the same unpatched go-back test with explicit upstream session/session loop scope, then the patched counterpart; if both pass, restore those settings in the upstream script and run its full selection.
Predicts: the existing navigation timeout disappears with matched session loops for both pure Python and Footwork's active patches, without changing production code or upstream tests.
Against: either matching-loop run still times out or fails a guard assertion, or the complete inherited selection shows an unresolved regression.
Refs: browser-use/pyproject.toml asyncio_default_fixture_loop_scope and asyncio_default_test_loop_scope; scripts/upstream_tests.sh; output/upstream-refresh-browser-pure-go-back.txt

## UR-U3 · update · 2026-10-27 17:09
Resolves: UR3 = held
Observed: the unpatched go-back test timed out at 30 seconds with the original loop configuration, then passed in 3.00 seconds with upstream session/session loop settings; its patched counterpart passed in 2.88 seconds. Restoring both settings and the formerly deselected navigate test lets the complete inherited selection pass 138 tests in 24.38 seconds. Browser-use contracts, scaffold and packaging checks pass 42 tests on the final dependency versions; selected lint passes. UR3's heading minute was transcribed as 17:08 although the preceding date command returned 17:07; its commit d016e37 precedes both resolving probes.
Inferred: preserving upstream loop ownership fixes the current inherited navigation-test stall without production changes. This does not establish the cause of the historical September timeout on that earlier environment.
Next: retain explicit upstream asyncio settings and all inherited tests; combine with CUA and full Footwork validation before closing UR1.
Refs: output/upstream-refresh-browser-pure-go-back.txt; output/upstream-refresh-browser-pure-session.txt; output/upstream-refresh-browser-patched-session.txt; output/upstream-refresh-browser-session-full.txt; scripts/upstream_tests.sh; tests/contract/test_upstream_seams.py

## UR-U1 · update · 2026-10-27 17:11
Observed: the fresh binary-only consumer installation and immutable onboarding packet pass on b8c9be1. Supplemental live observation reads the owned TextEdit fixture through the actual CLI. The installed capability trial fails at source bind because CUA refuses a same-Space background attachment while TextEdit is frontmost; no capability append was dispatched. The original UR1 plan excluded desktop dispatch; this supplemental existing conformance harness did reset its owned fixture text before bind. It does not count as the original offline test design.
Inferred: the new CUA background-attachment refusal preserves a stricter visible-effect boundary; complete integration readiness also needs a documented, scope-preserving initial-attachment prerequisite.
Next: test UR4 without changing production delivery authority or policy defaults.
Refs: output/upstream-refresh-clean-install/receipt.json; output/upstream-refresh-packet/footwork-onboarding-u2.zip; output/upstream-refresh-native-menu.txt; output/upstream-refresh-browser-bind-probe.txt; output/upstream-refresh-installed-trial/

## UR4 · prediction · 2026-10-27 17:11
Hypothesis: placing the owned fixture Chrome in front before initial attachment satisfies CUA 0.38's background attach constraint and allows the installed capability read/append/reconnect flow without changing Footwork's background delivery authority.
Test: activate only the fixture's identified Chrome PID, then run the existing installed capability conformance trial in a new owned run against the unchanged consumer wheel. Read the destination's exact value and retained operation receipts; close only owned fixture resources afterwards. No model/provider calls, user-profile writes, permission changes or production policy changes.
Predicts: initial browser attachment and source read succeed; one append has matching destination readback, and reconnect with the same operation token does not duplicate it.
Against: attachment still refuses, delivery requires broader authority, destination content differs, or reconnect duplicates the append. Preserve refusal rather than escalating delivery if the prerequisite is insufficient.
Refs: scripts/capability_installed_trial.py; output/upstream-refresh-fixture/scope.json; output/upstream-refresh-package/build-one/jevdual-0.0.1-py3-none-any.whl

## UR-U4 · update · 2026-10-27 17:12
Resolves: UR4 = held
Observed: placing the owned fixture Chrome in front permits the installed capability trial to pass, including actual installed worker identity, exact destination readback, and restart/replay without duplicate append. Fixture cleanup confirms its document, browser and listener are closed. A final source audit shows the native 0.38.0 release is behind reference HEAD across 75 Rust files even though Python SDK files match; the release-based wheel cannot establish complete native reference parity.
Inferred: the documented foreground prerequisite is sufficient for this fixture on this host; latest published native release is an intermediate validation point, not the full requested source refresh.
Next: build and qualify the native engine from the immutable reference source under UR5.
Refs: output/upstream-refresh-installed-trial-front/receipt.json; output/upstream-refresh-fixture/cleanup.json; trycua/cua cua-driver-rs-v0.38.0..d5373879 libs/cua-driver/rust

## UR5 · prediction · 2026-10-27 17:12
Hypothesis: the native CUA SDK and CLI at reference d5373879 can be built reproducibly into a source-identified dependency wheel and retain Footwork's current integration contract.
Test: build the immutable native reference source in owned ignored output, preserve source/build hashes, package its matching Python bindings with source identity, then rerun contract and installed native conformance checks. Keep published-release evidence separate and document platform build requirements.
Predicts: current reference native sources build on this Mac, import through their exact Python bindings, and pass the existing scoped observation/append/reconnect flow without policy changes.
Against: native build prerequisites cannot be satisfied within authorized dependency downloads, ABI checks fail, or the source-head engine breaks a required integration boundary.
Refs: /Volumes/External SSD/referencerepos/cua at d5373879e9e0baf5a63999ac4d26902340c0ce20; vendor/cua-driver/PROVENANCE.md
