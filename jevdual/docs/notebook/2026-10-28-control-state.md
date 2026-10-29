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

## CTLU2 · update · 2026-10-28 20:59
Resolves: CTL3 = held
Observed: a behaviour probe using only 515d0f0 APIs, run on 515d0f0 sources: browser-use mixed -> unchecked, aria-pressed toggle, CUA expanded disclosure and the second same-label toggle all read unchanged; native _prune kept [1] of two "Enabled" switches; a saved baseline reloaded expanded as None and an untouched reload read as changed. On 65bb991 each is a named transition and the reload reads unchanged. In real headless Chromium (tests/test_control_state_browser.py) 515d0f0 reported "no visible change" for the pressed toggle and the second switch; 65bb991 names all four transitions and two idle looks stay unchanged. Full suite 1739 passed, browser suite 13 passed at ceea93c.
Inferred: the browser-use path already caught expanded and a mixed -> checked click (False -> True); its false no-ops were pressed and repeated controls. Counting repeated controls also makes a second identical row appearing count as added, which the earlier key set hid.
Next: CTLU3 for CTL2; review before PR.

## CTLU3 · update · 2026-10-28 20:59
Resolves: CTL2 = held
Observed: tests/test_blockers.py and the two new tests in tests/test_s1.py (ceea93c): one request with eight Nouls and no SDK retries; empty observation, deadline overrun, provider error and malformed answers are unavailable; the micro-loop and both S1 handback sites keep their status, dispatch nothing and attach the diagnosis; with no diagnoser the result is unchanged; non-blocking handbacks are not diagnosed.
Inferred: the mechanism is safe to enable; its usefulness depends on Jev's accuracy on real blocked pages, which no run here measured.
Next: a preregistered comparison (current, state fix, state fix plus diagnosis) before any routing change uses the diagnosis.

## CTLU4 · update · 2026-10-28 21:15
Observed: a fresh-context review of 515d0f0..ceea93c reproduced a regression introduced by keeping same-label toggles: after a switch was inserted above two "Enabled" switches, `do click 201` toggled the first one and the receipt read confirmed, because the id and label guards had relied on pruning making labels unique. Also: diagnosis coverage ignored build_menu's budget trimming; S1 diagnoses were not written to traces; a cancelled diagnosis could leave an escalated delegation open; kept repeats could crowd the native cap. d75a7e4 fixes each; test_a_shifted_window_refuses_the_wrong_one_of_two_same_label_switches now refuses with nothing pressed. Full suite 1746 passed; browser suite 13 passed on ceea93c.
Inferred: keeping more controls weakens any guard that assumed labels were unique; position among same-key peers restores identity only while the alike controls keep their order.
Next: summary; PR.

## CTLS1 · summary · 2026-10-28 21:15
Established: control state (checked/pressed incl. mixed, selected, expanded) survives browser-use, the CUA browser adapter, native snapshots, session save/reload and capability rows; the effect diff names transitions, matches repeated controls by position, and reports a state seen on one side only as inconclusive (unverifiable receipt; stall runs neither extended nor reset); real Chromium confirms the pressed and repeated-switch false no-ops are gone. An opt-in advisory blocker diagnosis attaches to blocked/stalled handbacks without changing status or dispatching.
Uncertain: the CUA browser route was checked against the pinned producer's state shape, not driven live; native exposes no pressed or expanded; position-based identity misreads alike controls that reorder; Jev's accuracy on real blocker pages and the latency cost are unmeasured.
Decision: land d75a7e4 with the diagnosis off by default; before any routing change uses it, preregister a comparison of current, state fix, and state fix plus diagnosis with blocker precision and added latency reported separately.
