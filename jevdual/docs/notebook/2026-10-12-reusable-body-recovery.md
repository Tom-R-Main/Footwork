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
