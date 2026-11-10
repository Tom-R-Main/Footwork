# Explicit foreground native clicks

## FNC1 · prediction · 2026-11-10 18:37
Hypothesis: an explicit native foreground click can open a web dropdown that the pinned CUA background route refuses, without retrying an uncertain background action or weakening target identity and shared-desktop policy.
Test: public CLI simulated-Mac scenarios for explicit foreground AXPopUpButton click, background refusal with no fallback, human activity, unsupported options before binding, same-window/target/resource drift after activation, and unknown single-call delivery.
Predicts: only the explicit admitted foreground option fronts the exact window, reobserves/rematches and clicks one fresh qualified element token with SDK foreground delivery. Default background remains one background attempt; errors and no-send outcomes never trigger another route.
Against: a stale/ambiguous token dispatches, human activity is ignored, unsupported input binds the driver, a failure retries, or the background default changes.
Refs: docs/notebook/2026-11-10-suno-end-to-end.md; output/suno-20261110/song-more-actions.txt; output/foreground-web-text/source-804aeb8b2ba5/libs/cua-driver/rust/crates/platform-macos/src/tools/click.rs

## FNC2 · update · 2026-11-10 18:41
Resolves: FNC1 = held
Observed: five public CLI cases failed before implementation. The explicit foreground route now passes 16 scenarios, and 686 affected source/contract tests pass. Activation-time target/window/ambiguity changes send no click; unknown replies and SDK refusals do not retry. Ordinary background select refusal remains one uncertain exception receipt without foreground fallback.
Inferred: explicit delivery can cross the existing SDK background-select refusal while preserving Footwork posture and fresh-token targeting gates. The SDK's token-route refusal occurs before cursor animation or AX input, but its lossy Python exception does not retroactively qualify the older receipt.
Changes: the initial song-more-actions.txt reference was not an actual trace path; the parent-owned observed trace is candidate-a-more-menu.txt.
Next: freeze source for parent-owned actual menu observation, then handle range-focus preparation separately.
Refs: results/foreground-native-click-20261110/report.md; output/suno-20261110/candidate-a-more-menu.txt

## FNC3 · summary · 2026-11-10 18:41
Established: explicit native foreground click is opt-in, rejects unsupported/no-judge combinations before binding, retains three-second idle/exact-window/identity gates and sends one fresh-token SDK foreground click. Background behavior is unchanged and no automatic retry exists.
Uncertain: no worker live UI test occurred. SDK acknowledgement does not prove menu opening or whole-task completion; parent must inspect actual menu state. Historical unknown receipts remain unknown.
Decision: freeze the click route with unchanged native SDK bytes; do not combine later focus-preparation changes in this commit.
Refs: results/foreground-native-click-20261110/report.md
