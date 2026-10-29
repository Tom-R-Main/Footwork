# Control state and advisory blockers

## CTL1 · prediction · 2026-10-28 20:36
Hypothesis: state normalization, session persistence and duplicate indexing lose observable control transitions or manufacture progress when state becomes available.
Test: deterministic adapter and saved-session round trips, duplicate and unknown-state effect comparisons, real command scenarios, and a disposable browser fixture where available.
Predicts: mixed state and expanded baselines fail before repair; repairs preserve known transitions without confirming unknown or ambiguous comparisons.
Against: existing paths preserve these states and comparisons already distinguish missing evidence.

## CTL2 · prediction · 2026-10-28 20:36
Hypothesis: an opt-in bounded diagnostic at existing blocked/stalled handbacks can explain page conditions without changing the selected operation or authorizing another dispatch.
Test: fake-provider boundary tests for eight categories, invalid/empty/timeout responses, observation binding, and disabled-path regression checks.
Predicts: failures return unavailable and retain the original stop; diagnostics never dispatch actions.
Against: a diagnostic changes routing, retries a mutation, or treats unavailable evidence as a negative finding.

## CTLU1 · update · 2026-10-28 20:50
Observed: source at 515d0f0: neither session producer (native menu_from_snapshot, CUA menu_from_semantic) sets href or expanded, so the session baseline dropping them loses nothing today; menu_from_semantic drops the Driver's selected, expanded and pressed states and reads checked "mixed" as False; build_menu and native read "mixed" as False and None respectively; effects._index keeps the first of same-key controls; native _prune drops repeated toggles; no Candidate field carries pressed.
Inferred: the expanded-baseline loss in CTL1 is latent: it bites once a session producer reports expanded, which the repair adds, so the round trip must land with it.
Next: CTL3.

## CTL3 · prediction · 2026-10-28 20:50
Revises: CTL1
Hypothesis: false no-ops come from three losses (mixed folded into False, pressed/selected/expanded dropped by the CUA adapter, repeated controls collapsed in the diff and native pruning); false progress would come from comparing a state observed on one side only.
Test: new unit tests in test_effects.py, test_menu.py, test_browser_driver*, test_native*, test_session*, run once against the 515d0f0 sources (PYTHONPATH override) and once against the repair.
Predicts: against 515d0f0, mixed -> unchecked, a pressed toggle, a CUA expanded disclosure and the second of two same-label toggles all read as no effect, and a saved-session reload loses expanded/pressed; after the repair each is a named transition, a one-sided state is inconclusive (receipt unverifiable, stall run neither extended nor reset), and the existing suite stays green.
Against: any of those cases already reads as changed on 515d0f0, or the repair turns an unchanged reload into progress or an inconclusive step into a suspected no-op.
