# Reusable body contract and interrupted host recovery

## SIM14-P1 · prediction · 2026-10-12 22:14
Hypothesis: a validated contiguous event tail can be reconciled against the retained manifest without replaying effects or treating an unpublished event as completion proof.
Test: reproduce SIM13 event-fsync-before-manifest SIGKILL, then test the repair, malformed/gapped/conflicting tails and a browser restart followed by explicit Resume; inspect command IDs and wire sends.
Predicts: restart retains the original history, pauses, refuses inconsistent evidence and allocates the next unused journal sequence; explicit Resume obtains a fresh observation without repeating an existing command.
Against: FileExistsError persists, history is overwritten, a tail grants effect completion, a command identity is discarded or an effect is replayed.
Refs: docs/experiments/SIM14-reusable-body-recovery.md; tools/physical-workcell/test_workbench_crash_runtime.py

## SIM14-P2 · prediction · 2026-10-12 22:14
Hypothesis: durable planner process ownership combined with restart fencing prevents an independent child left by host SIGKILL from producing an actionable old decision.
Test: externally SIGKILL an owned host during active child planning; restart its retained root, verify ownership before cleanup, test identity mismatch and partial ownership records, then explicitly Resume with fresh image evidence in the browser.
Predicts: old planner authority is revoked, verified owned children retire before new planning, unresolved ownership fails closed, the job stays paused and the old observation cannot be dispatched.
Against: an unrelated process is signalled, a live old writer survives successful recovery, an old decision dispatches or recovery resumes automatically.
Refs: docs/experiments/SIM14-reusable-body-recovery.md; tools/physical-workcell/codex_policy.py; tools/physical-workcell/network_operator_runtime.py

## SIM14-P3 · prediction · 2026-10-12 22:14
Hypothesis: extracting identity, lease, command-envelope and receipt validation behind an operation-contract seam preserves strict bench behavior while allowing a non-bench operation schema without simulation imports.
Test: shared contract tests with a minimal second operation vocabulary, existing invalid body command tests and the network/client/operator recovery suites; inspect source-pinning closure.
Predicts: wire semantics and existing bounds remain unchanged, unknown bench operations stay refused, generic validation imports no bench implementation and every new authority-bearing source is pinned.
Against: unknown commands are admitted, validation weakens, old roots silently migrate across source changes, or the reusable module still needs MuJoCo/bench operations to import.
Refs: docs/experiments/SIM14-reusable-body-recovery.md; tools/physical-workcell/body_protocol.py

## SIM14-U1 · update · 2026-10-12 22:21
Observed: the pre-fix publication regression reproduced FileExistsError on Resume. The first guardian process regression refused cleanup proof because Darwin temporarily returned EPERM for a dead process group; this stayed blocked rather than granting success. Retrying that transient state while still requiring eventual ESRCH yielded three passing owned-process checks, including a planner and grandchild surviving host-only SIGKILL until the guardian retired them. Seven alternate-operation contract checks and 24 existing body/client checks passed in separate development runs.
Inferred: the selected journal repair and parent-liveness mechanism have initial process evidence; actual image-guided browser recovery and stronger malformed-evidence checks remain required before adoption.
Next: finish negative checks and source-pinning closure, freeze committed source, then run publication and active-planning browser recovery trials.
Refs: tools/physical-workcell/output/sim14-publication-before.log; tools/physical-workcell/output/sim14-runtime-first.log; tools/physical-workcell/output/sim13-host-crash-3b0976e974/; tools/physical-workcell/test_body_contract.py

## SIM14-U2 · update · 2026-10-12 22:25
Observed: extraction review caught a zone-validation mismatch: the storage helper did not include the bench's reachable-region bounds. The bench schema now retains those exact bounds with a regression case. The first legacy network-fault suite was invalidated by a concurrent whitespace edit; that attempt remains retained. A frozen rerun passed all 43 schema/body/client/network checks. The shared transport import test excludes bench, agent_bench, MuJoCo and numpy; the alternate simulated operation vocabulary exercises actual TCP reply-loss/client-restart recovery and incomplete lower-proof blocking. The extraction is committed as ee77644.
Next: complete runtime regressions and independent review, then freeze the combined implementation and live trial sources.
Refs: tools/physical-workcell/output/sim14-body-contract-conformance-v2.json; tools/physical-workcell/output/sim14-body-contract-conformance-v2.log; tools/physical-workcell/test_body_contract.py

## SIM14-P4 · prediction · 2026-10-12 22:30
Hypothesis: a blocking prompt write can prevent the guardian from observing host death if its planner never reads stdin; multiplexing nonblocking prompt delivery with host liveness preserves bounded retirement.
Test: use an owned non-reading planner and a prompt larger than the pipe capacity, kill the host only, then verify group retirement and closed ownership. Run before and after the bounded delivery change.
Predicts: the current guardian cannot publish cleanup proof in the timeout, while bounded nonblocking delivery observes EOF and retires the group; normal policy and crash tests remain unchanged.
Against: the current prompt write does not block under a verified full pipe, or the repaired guardian still fails to retire ownership after host death.
Refs: tools/physical-workcell/planner_guard.py; docs/experiments/SIM14-reusable-body-recovery.md

## SIM14-U3 · update · 2026-10-12 22:28
Observed: the frozen runtime development checks passed 18 focused and 59 existing operator/HTTP/health regressions. Independent review found a blocking stdin write before the guardian liveness loop; it is a potential orphan-retirement availability gap rather than an observed effect replay. The live harness will retain independent process absence and owner-transition evidence in addition to guardian closure.
Changes: SIM14-P4 was committed before its test; its heading time was mistyped as 22:30. The clock command immediately before that commit returned 2026-10-12 22:27; Git records the prediction order.
Next: reproduce and repair the full-pipe case, strengthen the live ownership evidence, then freeze the final source before actual model trials.
Refs: tools/physical-workcell/output/sim14-runtime-final.log; tools/physical-workcell/output/sim14-runtime-regression.log; commit 05f3c0d; commit fbdeb20

## SIM14-U4 · update · 2026-10-12 22:30
Resolves: SIM14-P4 = failed
Observed: the current guardian retired a never-reading planner after host-only SIGKILL with a valid 60000-byte prompt; cleanup completed in the retained pre-change test. The expected blocked write was not reproduced on this Mac.
Inferred: pipe capacity on this host may accommodate the bounded prompt. A multiplexed write still makes the liveness/watchdog check independent of platform pipe capacity, but this run does not prove a prior full-pipe failure.
Next: measure the owned pipe capacity, preserve the passing baseline, implement bounded prompt delivery and run the policy/crash regressions before live qualification.
Refs: tools/physical-workcell/output/sim14-planner-backpressure-before.log
