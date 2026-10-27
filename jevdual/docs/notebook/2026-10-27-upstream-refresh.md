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
