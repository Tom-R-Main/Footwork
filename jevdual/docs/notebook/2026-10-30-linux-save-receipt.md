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

## SRU2 · update · 2026-10-30 12:17
Observed: cloud retest at 045fc5d disproves the four-field envelope assumption. Pinned recovery_hint.rs decorates the refusal with hint and next_call. The recorded actual ToolResult and offline replay reject the recognizer, while the four-field control passes. Original SR1's local simulation result did not establish the public envelope contract.
Next: test the captured SDK envelope before another fix; keep code/effect/action/error predicates strict while allowing only the two documented recovery metadata fields.
Refs: results/linux-vm-save-receipt-20261030/045fc5d-refused-profile-sdk.json; results/linux-vm-save-receipt-20261030/sdk-replay.json

## SR2 · prediction · 2026-10-30 12:17
Hypothesis: allowing the pinned core's hint and next_call metadata fixes the captured refusal without granting those advisory fields input authority.
Test: reconstruct the actual public SDK ToolResult from cloud capture in a public CLI scenario; reproduce failure, then permit those optional keys while retaining all existing refusal predicates. Challenge unknown keys and contradictory actions; run focused regressions and the recorded replay without starting a driver.
Predicts: both captured and minimal envelopes refuse with zero input; arbitrary advisory content is never executed; unknown semantics and contradictory delivery remain uncertain.
Against: capture remains unrecognized, advisory content triggers an operation, or unrelated error/delivery shapes become no-input claims.
Refs: python/jevdual/native.py; vendor/cua-driver/native-source.tar.gz; tests/test_session_scenarios.py

## SRU3 · update · 2026-10-30 12:21
Resolves: SR2 = held
Observed: the real captured public ToolResult and advisory-metadata case fail against the previous bridge and pass with only hint/next_call permitted as optional metadata. The public CLI scenario reconstructs the captured SDK class; an input-free replay recognizes it. All 252 focused regressions pass, including contradictory action and unknown semantic-field cases. No advisory call is executed.
Next: push the correction for installed-cloud broken-WM and fresh-profile working controls; local replay is not a replacement for that live repeat.
Refs: results/linux-next-tranche-20261030/sdk-replay.json; results/linux-next-tranche-20261030/envelope-before.txt; results/linux-next-tranche-20261030/envelope-focused.txt
