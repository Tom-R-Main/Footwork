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

## HTW3 · update · 2026-11-11 03:45
Resolves: HTW1 = held
Observed: owning Rust ranking/target tests failed with two behavioral assertions before the classifier; unknown competitors already remained blocking. Final exact-source checks pass five HelpTag/CFArray/settable tests and fifteen pure foreground-observation tests (overlapping three classification tests). The ordinary comparator now removes only exact owned unique passive HelpTags while the requested key window is observed. Every error/unknown/action/focus/dialog case stays blocking; HelpTag targets refuse before activation. Activation order, independent process/key/per-display visibility predicates and host partial refusal remain unchanged. Root independent review requested timeout-setting return checks; both reads now abort unknown on timeout-configuration failure.
Next: retain the exact additive source/archive patch and qualify the separate project overlay/frozen wrapper, without treating a simulated SDK reply as coverage of Rust internals.
Refs: results/helptag-ordinary-window-20261111/rust-red.txt; results/helptag-ordinary-window-20261111/rust-green-final.txt; results/helptag-ordinary-window-20261111/rust-observation-final.txt; vendor/cua-driver/patches/ordinary-helptag.json

## HTW4 · update · 2026-11-11 03:45
Resolves: HTW2 = held
Observed: canonical offline native/wheel build from final source 938800555df9485aa4ed800a74ef795d05575efdbdea9c5f4ce6f6dd61b02fda succeeded. New project overlay imports exact version cleanup2.focus1.helptag1; wheel SHA256 is 69a8fe983985c99f083438c7d985bcc31f65dce03a72407385219401805b2ad0. Installed native executable/library bytes match wheel and build target. Six generated binding files and the historical focus1 overlay hashes remain unchanged. Default project pin/lock/canonical archive remain focus1; only two explicit runtime versions are accepted. All 780 new-overlay focused Python/ABI/authority/CLI/contracts pass, plus Ruff/Rustfmt/notebook checks. A pre-hardening intermediate candidate was never installed or qualified and was overwritten only in the owned new wheelhouse.
Next: freeze source and provide a new wrapper using only this overlay and archived source; parent owns one public live qualification and the single final full Python suite.
Refs: results/helptag-ordinary-window-20261111/runtime.json; results/helptag-ordinary-window-20261111/build-wheel.txt; results/helptag-ordinary-window-20261111/overlay-focused.txt

## HTW5 · summary · 2026-11-11 03:45
Established: generic positive AXHelpTag classification fixes the owning ranking seam without broadening unknown/modal/interactive eligibility or admitting HelpTag activation targets. Final source, wheel/native bytes and ABI are bound to additive provenance, with a separate project-only overlay; activation and input safety predicates remain strict.
Uncertain: no worker UI/activation calls were made. Actual scheduled-run recovery remains parent-owned, and the new SDK is not the default/global installation. Rust activation tests were explicitly skipped; pure tests and ABI imports do not prove live application delivery.
Decision: hand off the frozen candidate and artifact; preserve historical overlays and use only the new manifest-qualified wrapper for the next live check. One full Python regression remains for the parent after this freeze, without a redundant mid-build run.
Refs: results/helptag-ordinary-window-20261111/report.md
