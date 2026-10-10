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

## RRU2 · update · 2026-10-10 12:14
Resolves: RR3 = held
Observed: detached owned child 17255, its own process group, appended once with confirmed driver effect and exact independent AX agreement. Spawn-to-import 0.0574 seconds; spawn-to-dispatch 1.8597 seconds; total 2.2170 seconds. Public baseline with final journal write loss remains unknown after fresh backend/service despite matching text; one insertion and resource busy. Initial baseline teardown double-close was a harness error, corrected without changing the expectation. The first notebook append used the wrong working directory and failed; this entry corrects that omission before implementation.
Inferred: existing Accessibility authorization works for a detached child on this host. Fresh binding costs dominate startup; this is a latency tradeoff, not evidence for broad platform/TCC support.
Next: implement immutable operation-bound receipt consumption and independent fixed-action worker; qualify process boundaries and counterexamples.
Refs: /Users/thomasmain/projects/footwork/output/restart-detached-20261010/report.json; scripts/capability_restart_probe.py; /Users/thomasmain/projects/footwork/output/capability-restart-baseline-v2.log; tests/test_session_scenarios.py; dcc0ed4

## RRU3 · update · 2026-10-10 12:23
Observed: first public durable scenario pass found current_recovery accepted a moved sole field because ax.resolve ignores frame when only one role candidate exists; explicit exact frame qualification fixes the failing scenario. Claude independently identified NSDocument safe-save inode instability and missing worker deadline. The parent deadline had already landed during his snapshot review; worker deadline was still absent.
Changes: prereg/plan amended before safe-save/deadline tests; strict file identity before input, live document/process/field after, disk metadata informational; synchronized watchdog admission fence; bounded parent wait. Generic readback CapabilityError after input must remain unknown, covered by worker scenarios.
Next: challenge these corrections and controlled real native/MCP interruption phases, then final Claude review.
Refs: /Users/thomasmain/projects/footwork/output/capability-recovery-public-dev-v1.log; /Users/thomasmain/projects/footwork/output/capability-recovery-public-dev-v2.log; mailbox 1791649305616318000-claude-codex.md

## RRU4 · update · 2026-10-10 12:31
Observed: focused native/recovery coverage includes actual fixed worker execution over simulated Mac boundaries; both real subprocess watchdog cases pass after correcting the synthetic frame mismatch (the initial after-input case refused before reaching its deadline). Deliberately moving invoked before the input_started write fails the no-input storage-failure test; removing the post-dispatch CapabilityError guard fails the uncertainty test. Original worker source hash was restored exactly after both mutations. Caller audit found the existing host verifier reads top-level evidence.readback.passed; normal/recovered results now preserve that historical summary without editing frozen C1/host runners.
Inferred: the critical branch tests discriminate plausible false no-send changes. This does not qualify a hung real TextEdit process or power loss.
Next: freeze source/harness, full checks, real owned MCP/native interruptions and final Claude review.
Refs: results/restart-reconciliation-20261010/mutations.json; /Users/thomasmain/projects/footwork/output/capability-recovery-public-dev-v4.log; tests/test_session_scenarios.py; tests/test_capability_recovery.py

## RRU5 · update · 2026-10-10 12:35
Observed: frozen 8a407f1 native/MCP v1 passed the first ten cases. The file_replacement case stopped before replacement because the fixture was created in results while that trial safety guard permits replacement only inside project output. delayed_identical was not attempted because the runner stops on an invalid case. No product failure or replacement input occurred; original v1 remains retained.
Inferred: the fixture placement violates a harness prerequisite, not the restart contract. RR2 remains open; v1 does not satisfy the full required matrix.
Next: close only the owned v1 fixture, create a new owned fixture inside permitted output, and rerun all twelve cases without product/harness source changes or retries of individual cases.
Refs: /Users/thomasmain/projects/footwork/output/restart-native-20261010-v1/summary.json; scripts/capability_restart_trial.py; 8a407f1

## RR4 · prediction · 2026-10-10 12:35
Hypothesis: v1 replacement stopped solely because the owned fixture path was outside the harness replacement boundary; recreating the fixture in permitted project output will make the same unchanged frozen matrix reachable.
Test: fresh owned output fixture, unchanged 8a407f1, full twelve-case actual MCP/native matrix v2; preserve v1, cleanup and source hashes.
Predicts: file_replacement reaches the replacement and worker strict pre-input identity guard refuses with no append; delayed_identical also runs and stays unknown while active, then known refusal after its exact guard rejects the changed field. Other ten rules remain as observed in v1.
Against: same placement guard rejects output fixture, required stage remains unreachable, any incorrect applied/no-send result, external edit overwritten or input repeated during collection.
Refs: docs/experiments/R1-restart-reconciliation.md; scripts/capability_restart_trial.py
