# Exact HelpTag classification for ordinary-window verification

## HTW1 · prediction · 2026-11-11 03:25
Hypothesis: a newly visible exact owned nonfocusable AXHelpTag with only AXRaise actions is incorrectly treated as an ordinary same-process front competitor, causing the observed partial activation refusal while the intended window remains key.
Test: owning Rust pure ranking/classification seam with exact target, higher-z HelpTag and checked owner/ID/role/actions/focus facts; baseline must still rank the HelpTag. Cover unknown/error/duplicate/wrong-ID/owner/focus/action/dialog cases and HelpTag target preactivation refusal. Preserve process/focus/visibility/per-display predicates and activation sequence. Build a separately versioned project-local offline artifact and qualify bindings/native hashes; retain Python public partial-refusal behavior.
Predicts: only positively proven non-target passive HelpTags are removed from ordinary ranking while requested key-window proof is present; every unknown or interactive case remains blocking, and HelpTag targets refuse before activation.
Against: ordinary/modal/unknown surfaces are dropped, missing/error action reads count as empty, activation order or success gates weaken, HelpTag targets activate, or native ABI/default runtime changes silently.
Refs: output/suno-studio-20261111/transient-classification.json; output/suno-studio-20261111/helptag-action.json; results/helptag-ordinary-window-20261111/

## HTW2 · prediction · 2026-11-11 03:25
Hypothesis: an additive HelpTag patch atop the exact current focus1 source can build from existing offline caches with unchanged generated bindings and without changing the default/global runtime.
Test: build with cached Rust1.97.1/cargo/Hatchling, canonical native hook and a separate output package/overlay; verify archive/patch/version/native/wheel hashes and Python ABI/contracts. Do not execute native activation tests; explicitly skip own_process_activation.
Predicts: separately versioned cleanup2.focus1.helptag1 artifact is reproducible from its manifest, six Python binding hashes remain identical, old focus1 overlay/default project pin remain unchanged, and both explicit compatible runtimes pass host gates.
Against: network/global installation is needed, cleanup/focus patches disappear, generated bindings differ, the old overlay changes, or source/native provenance cannot be established.
Refs: output/foreground-web-text/runtime.json; vendor/cua-driver/patches/; results/helptag-ordinary-window-20261111/
