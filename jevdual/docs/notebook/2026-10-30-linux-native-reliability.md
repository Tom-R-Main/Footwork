# Linux native lifecycle reliability

## LR1 · exploratory · 2026-10-30 19:56
Question: which native phase fails in repeated target admission and post-success public browser recovery, and does explicit shutdown leave work alive until interpreter teardown?
Test: preserve main 52601b1 as the new branch baseline. First add bounded, redacted per-attempt phase timestamps, separate JSON result and diagnostic channels, and parent-owned numeric exit/signal/wait records. Challenge timeout, cancellation, success-then-signal and shutdown stalls before native use. Inspect the pinned archive and actual callers; use the cached exact x86-64 CUA wheel and existing init/512-PID/two-CPU/3-GiB/zero-swap harness. Capture native backtraces with a task-scoped debugger when reachable. Initial native exploration is bounded to 40 fresh minimal driver processes and 10 public recovery attempts; retain every attempt and distinguish explicit shutdown return from OS exit. No timeout changes or mutation retries during a batch.
Refs: results/linux-consolidation-vm-20261030/report.md; results/linux-product-release-20261030/report.md; docs/linux-consolidation-learning.md; python/jevdual/linux_session.py; vendor/cua-driver/native-source.tar.gz

## LR2 · prediction · 2026-10-30 19:56
Hypothesis: independent phase and parent wait records can distinguish application non-readiness, work/shutdown stalls and post-result abnormal exit without widening admission authority.
Test: deterministic subprocess cases emit phase events and JSON independently, then return, stall or self-terminate by signal. Retry a failed stage and inspect all attempt records; cancel a live child and retain termination/escalation/final wait outcomes.
Predicts: only valid ready JSON plus normal zero process exit admits readiness. Every attempt remains available with last phase and numeric wait status; malformed or bounded-overflow channels refuse. Diagnostic output contains fixed phase names and monotonic times, no environment or document text.
Against: early JSON masks a nonzero/signal exit, a retry overwrites evidence, a killed child loses its last phase/final wait, or diagnostics corrupt the result JSON.
Refs: tests/test_linux_session.py; results/linux-native-reliability-20261030/

## LR3 · exploratory · 2026-10-30 19:56
Question: after a demonstrated repair, does one exact installed artifact sustain a finite repeated native qualification under the existing resource boundary?
Test: freeze product/native artifacts and timeout policy before measurement. Count all 30 fresh lifecycle cycles and all 10 complete installed public journeys, without replacement attempts. Include repeated driver creation, normal shutdown, cancellation, delayed helper recovery, component failures and unchanged-byte refusal/identity controls. Record phase, process exit and cleanup for every attempt; retain original failures and any reproduction gap. Run full required regression/browser/lint/resource/notebook checks and byte-verify a fresh consumer. A failure prevents a zero-failure reliability claim and requires a new pre-registered artifact batch after repair.
Refs: results/linux-native-reliability-20261030/
