# Linux save refusal receipt

## SR1 · prediction · 2026-10-30 12:02
Hypothesis: the cloud save reports dispatched=true because the bridge discards the pinned Linux driver's structured foreground_unavailable/effect=none refusal when its ToolResult has no ActionResult.
Test: reproduce a public CLI save with a simulated structured refusal and no key input; add adapter and Linux hotkey tests for malformed, contradictory, opaque and post-dispatch responses. Recognize only the source-qualified no-input shape, preserving uncertainty elsewhere.
Predicts: the refusal becomes effect=refused, dispatched=false, delivered_count=0 with no save readback, while transport failures, mismatched structure and positive input counts remain uncertain.
Against: the CLI already reports no dispatch, the pinned source can return that exact refusal shape after key input, or a legitimate ambiguous response is mislabeled as no input.
Refs: python/jevdual/native.py; vendor/cua-driver/PROVENANCE.md; tests/test_session_scenarios.py; cloud task Test project in VM, local evidence commit bd0acb1

## SRU1 · update · 2026-10-30 12:05
Resolves: SR1 = held
Observed: source inspection confirms foreground_unavailable precedes the input body and publishes an effect=none structured record. Both the public CLI scenario and adapter regression fail on the original bridge and pass with the strict structured-shape recognition. All 249 focused native/session/SDK/notebook tests pass; malformed, contradictory and opaque responses remain uncertain.
Next: push the correction for a cloud rebuild and repeat; keep old bundle identities and prior cloud acceptance distinct from this local regression evidence.
Refs: results/linux-save-refusal-20261030/report.md; results/linux-save-refusal-20261030/before.txt; results/linux-save-refusal-20261030/focused.txt

## SRS1 · summary · 2026-10-30 12:05
Established: a source-qualified Linux activation refusal reports no dispatch and zero delivered input, and does not add save-readback evidence. Identity and actuator predicates are unchanged.
Uncertain: the corrected build has not yet repeated the real cloud VM failure. The cloud task's evidence commit bd0acb1 remains local to its VM.
Decision: retain the narrow fix and regression record on codex/linux-support; provide the new commit for cloud retesting before further Linux rollout.
Refs: results/linux-save-refusal-20261030/report.md
