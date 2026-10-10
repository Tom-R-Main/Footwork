# Durable restart reconciliation

## RR1 · prediction · 2026-10-10 12:07
Hypothesis: the current restart failure is loss of process-local validation/execution evidence; a durable admitted packet plus independently owned completion receipt can reconcile a killed MCP parent without repeating input, while preserving unknown when execution custody or identity is unsupported.
Test: public native capability scenarios and real child-process parent SIGKILL cases, with an independent one-action worker receipt. Reproduce the missing restart evidence before product edits. Counterexamples cover delayed worker, identical external write, worker death before receipt, original app/process/document/field replacement, bad receipt and legacy records.
Predicts: a qualified completed execution receipt plus matching fresh original-scope postcondition resolves applied after parent death; prepared-only proves not_sent; started/no receipt and identity mismatch remain unknown and busy. Text alone never resolves. Repeated token retrieves only one attempt.
Against: status sends input, a repeated token launches twice, matching text alone clears uncertainty, a stale/replaced target resolves, a legacy journal silently acquires authority, or an unattested process is killed/adopted.
Refs: docs/plans/restart-reconciliation-20261010.md; docs/experiments/R1-restart-reconciliation.md; python/jevdual/capability/service.py; tests/test_session_scenarios.py

## RR2 · prediction · 2026-10-10 12:07
Hypothesis: the same record/custody split holds on the actual scoped macOS native surface, rather than only in a simulated process ledger.
Test: committed frozen implementation; owned browser/TextEdit fixture; actual MCP parent death before send, while independent native dispatch executes, after durable receipt and after final commit. Independent exact AX oracle checks both content and no additional mutation from repeated status/token collection. Delayed/absent receipt and target replacement are counterexamples. Record stage, held reply, process identities, durable artifacts and cleanup. Preregister required cases before running.
Predicts: supported completed receipts recover read-only after parent crash; truly uncertain or replaced attempts remain blocked; no duplicated append or interference outside the owned resource.
Against: any wrong applied claim, duplicate, unresolved required runtime case, unsupported custody/readback promoted to qualified, or unverifiable owned cleanup.
Refs: docs/experiments/R1-restart-reconciliation.md; scripts/capability_interrupt_trial.py; scripts/capability_fixture.py

## RRU1 · update · 2026-10-10 12:10
Observed: Claude independently reviewed the plan and identified that fresh current-state gating would falsely block an affirmatively completed historical append after a subsequent edit. No resolving test has run yet.
Changes: dated prereg/plan amendments adopt receipt-only historical resolution and separate current agreement; flock custody with conservative launch-gap handling; same receipt-consumption path in normal and restart calls. Detached AX feasibility precedes implementation. RR1/RR2 remain open and are interpreted with these amendments.
Next: feasibility probe and public-boundary baseline, then implementation if detached AX works.
Refs: docs/plans/restart-reconciliation-20261010.md; docs/experiments/R1-restart-reconciliation.md; mailbox 1791648499247640000-claude-codex.md

## RR3 · prediction · 2026-10-10 12:10
Hypothesis: a detached child using the installed Python/Cua/AX route retains existing Accessibility authorization and can execute the same scoped append without global permission changes.
Test: model-free owned fixture; spawn start_new_session child that binds only destination, validates and appends once; independent AX oracle checks exact prefix/separator/payload; retain process identity, import/startup/total timing and cleanup evidence.
Predicts: detached child reports confirmed exact readback and independent oracle agrees; startup cost is measured rather than assumed negligible.
Against: detached child lacks TCC permission, cannot resolve the owned field, inserts incorrectly or requires unapproved configuration changes.
Refs: scripts/capability_restart_probe.py; scripts/capability_fixture.py
