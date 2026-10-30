# Linux save refusal receipt

## SR1 · prediction · 2026-10-30 12:02
Hypothesis: the cloud save reports dispatched=true because the bridge discards the pinned Linux driver's structured foreground_unavailable/effect=none refusal when its ToolResult has no ActionResult.
Test: reproduce a public CLI save with a simulated structured refusal and no key input; add adapter and Linux hotkey tests for malformed, contradictory, opaque and post-dispatch responses. Recognize only the source-qualified no-input shape, preserving uncertainty elsewhere.
Predicts: the refusal becomes effect=refused, dispatched=false, delivered_count=0 with no save readback, while transport failures, mismatched structure and positive input counts remain uncertain.
Against: the CLI already reports no dispatch, the pinned source can return that exact refusal shape after key input, or a legitimate ambiguous response is mislabeled as no input.
Refs: python/jevdual/native.py; vendor/cua-driver/PROVENANCE.md; tests/test_session_scenarios.py; cloud task Test project in VM, local evidence commit bd0acb1
