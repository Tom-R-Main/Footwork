# Explicit foreground native clicks

## FNC1 · prediction · 2026-11-10 18:37
Hypothesis: an explicit native foreground click can open a web dropdown that the pinned CUA background route refuses, without retrying an uncertain background action or weakening target identity and shared-desktop policy.
Test: public CLI simulated-Mac scenarios for explicit foreground AXPopUpButton click, background refusal with no fallback, human activity, unsupported options before binding, same-window/target/resource drift after activation, and unknown single-call delivery.
Predicts: only the explicit admitted foreground option fronts the exact window, reobserves/rematches and clicks one fresh qualified element token with SDK foreground delivery. Default background remains one background attempt; errors and no-send outcomes never trigger another route.
Against: a stale/ambiguous token dispatches, human activity is ignored, unsupported input binds the driver, a failure retries, or the background default changes.
Refs: docs/notebook/2026-11-10-suno-end-to-end.md; output/suno-20261110/song-more-actions.txt; output/foreground-web-text/source-804aeb8b2ba5/libs/cua-driver/rust/crates/platform-macos/src/tools/click.rs
