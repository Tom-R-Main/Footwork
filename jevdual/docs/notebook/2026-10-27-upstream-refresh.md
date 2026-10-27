# CUA and Browser-use reference refresh

## UR1 · prediction · 2026-10-27 17:02
Hypothesis: Footwork can adopt browser-use 0.13.14 and cua-driver 0.38.0 from the October 27 reference snapshots while preserving its existing policy, delivery authority, receipts and session semantics through bounded integration changes.
Test: compare both reference trees against the pinned seams; update exact dependency pins, browser-use submodule and affected adapters; run contract tests, deterministic suite, upstream reuse tests and local headless browser integration without paid model calls or real desktop dispatch.
Predicts: current reference APIs can express each existing Footwork operation and authorization constraint, and the adapted integration passes those checks without changing policy thresholds or backend defaults.
Against: an existing operation or authorization boundary cannot be represented, a patch no longer preserves upstream behavior, or deterministic/integration checks expose an unresolved regression.
Refs: /Volumes/External SSD/referencerepos/browser-use at 2cc71890e65056b67fdb29d98bb407749c15bb08; /Volumes/External SSD/referencerepos/cua at d5373879e9e0baf5a63999ac4d26902340c0ce20; CONTRIBUTING.md; tests/contract/
