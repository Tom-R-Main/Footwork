# Suno end-to-end development exploration

## Preregistration

Question: what prevents Footwork from completing a creation-to-editor-to-reopen journey on the current signed-in Suno desktop UI?

Hypothesis: native Chrome accessibility supports ordinary creation controls, while waveform/timeline targeting and absence of synchronized audio evidence limit editor actions and quality judgment.

Prediction if true: creation controls can be observed and safely operated; at least one timeline or listening step lacks enough evidence to assert the intended result without an added observation or action capability.

Prediction if false: the current CLI exposes and verifies creation, bounded editor changes, listening and persistence without new capability, or an earlier environmental blocker prevents testing this mechanism.

Design: development exploration, one operator, installed Footwork launcher, existing signed-in Chrome Suno window, fresh explicit session directories. Record runtime identity, selected window, command receipts and exact blockers. Use a new draft and preserve existing songs. No publication, purchases, installs, account changes, heldout evaluation or rate claims. Freeze code versions for any measured comparison. Keep private page content and captures under ignored output/suno-20261110; redact any committed results.

Primary metric: number of independently evidenced milestones among create, audition/select, bounded editor change, transition inspection, and save/reopen (0 through 5). Missing prerequisites are unverified, not product failures.

Guardrails: fresh targets, existing action gates, no uncertain submission retries, no unrelated tab inspection, no aesthetic claims from silent screenshots, no paid model-provider activation to bypass missing prerequisites.

Decision rule: resolve locally reproducible Footwork frictions with regression scenarios and re-drive the affected path; record external prerequisites separately. Completion requires all five milestones with preserved originals and persistence readback. Otherwise report the exact reached milestone and missing evidence.

## Result

Development run reached visible Create navigation but no song generation. Primary metric: zero of five song milestones completed; all remain unverified. Title/address changes preceded useful AX form observations, demonstrating a readiness-evidence gap. A source repair adds bounded exact-control observation and passed affected offline plus live read-only positive/timeout checks. The underlying external AX delay remains unexplained; foreground menu attempts were refused because of active human input. Continuing the actual creation/editor journey requires the pending desktop handoff, not a weakened gate. See `results/suno-20261110/report.md` and `docs/notebook/2026-11-10-suno-end-to-end.md`. No paid generation, purchase or publication was submitted.
