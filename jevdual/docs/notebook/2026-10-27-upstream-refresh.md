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
