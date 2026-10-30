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

## LRU0 · update · 2026-10-30 19:53
Observed: the shell clock immediately after prediction commit 2f98dc0 reads 19:53:22 UTC. The initial headings incorrectly estimated 19:56; git ordering establishes that the committed predictions precede probes. This correction preserves the original text.
Next: take all subsequent entry times directly from the clock. The requested tometo-mode, linux, pstack-investigate, repo-learn and pstack-verify skills were searched in the available cloud/executor catalogs and local skill paths; none is available here. Proceed under the explicit task authorization and repository discipline.

## LRU1 · update · 2026-10-30 19:57
Resolves: LR2 = held
Observed: 26 diagnostic/lifecycle tests pass at 5324f6f, including success JSON followed by actual SIGABRT and a TERM-ignoring shutdown stall. The first native harness used fixture HOME=/work; Mousepad abbreviated its exact document title to ~/session-N/document.txt. Phases show completed observe/shutdown and typed AXError at document_bind, not a native stall. An inspection initially omitted the required on_screen_only field; corrected inspection identifies lost_identity from the strict title check. These setup failures remain counted in the ten-attempt batch and do not reproduce the earlier native timeout. The prior harness used /home/agent, outside /work. Pinned runtime.rs and native.rs hashes exactly match the supplied reference hashes.
Next: finish the unchanged initial batch; use the historical /home/agent fixture identity in a distinct native batch. Preserve title guards. GDB 16.3 and libc debug symbols were extracted into the task sysroot; no host service or dependency pin changed.
Refs: results/linux-native-reliability-20261030/diagnostic-tests.txt; /workspace/scratch/fw-reliability-initial/; vendor/cua-driver/native-source.tar.gz

## LR4 · prediction · 2026-10-30 19:59
Hypothesis: a UniFFI continuation can publish its asyncio wake before the native callback has returned; interpreter finalization can therefore race a foreign callback even after the explicit driver shutdown await returned.
Test: inspect the pinned UniFFI dependency and live native thread stacks. Compare the unchanged minimal process batch with a separately labelled controlled scheduling case delaying only the existing continuation after its wake publication, then capture any actual native abort under GDB. This scheduling intervention is a mechanism experiment and cannot by itself identify the historical abort's cause. Independently diagnose zero-window target refusals in fresh sessions with X11 and native window counts.
Predicts: explicit shutdown/result can precede continuation return, and GDB can identify a Python-finalization forced unwind through native Rust/FFI frames in the controlled case.
Against: the FFI free/complete path synchronously joins all callbacks before shutdown resumes, or the native failure stack identifies a different path.
Refs: vendor/cua-driver/src/cua_driver/_native.py:2246; pinned uniffi_core 0.31.0; results/linux-native-reliability-20261030/

## LRU2 · update · 2026-10-30 20:00
Resolves: LR4 = failed
Observed: all 40 unchanged minimal processes completed three create/list/observe/shutdown cycles and normal exit. Three baseline and three delayed-continuation shutdown processes exited normally under GDB. The pinned UniFFI scheduler holds its mutex across the continuation, and RustFuture.free reacquires that mutex, so the proposed missing continuation join is contradicted by the actual caller/dependency path. A public recovery exploration stopped at target admission (window_not_unique) before any recovery attempt. A later inspection of an initial-batch editor returned one native window; no cause for that discrepancy is yet established.
Next: retain the negative mechanism result and avoid speculative callback/runtime patches. Add numeric window count and typed AX refusal classification, then compare live native and independent X11 views during a failed attempt. The LRU1 heading estimated 19:57 before the shell clock read 19:56; subsequent headings are generated directly from the actual clock.
Refs: /workspace/scratch/fw-reliability-minimal/; /workspace/scratch/fw-reliability-callback/; /workspace/scratch/fw-reliability-recovery/; pinned uniffi_core 0.31.0 ffi/rustfuture/future.rs and scheduler.rs

## LRU3 · update · 2026-10-30 20:02
Observed: the isolated public browser fixture reproduced actual SIGABRT (numeric -6) in attempts 7 and 9 of 10. Each recorded explicit shutdown return, public success JSON and unchanged persistent root identity. This fixture admits X11/bus/WM for diagnosis only and never publishes desktop target readiness. It does not substitute for full acceptance. The original minimal driver case lacked the configured Python authorization-host boundary. The first full recovery fixture failed before any recovery at window_not_unique. Native and X11 views agreed in a later fresh successful desktop, so that discrepancy remains under investigation.
Next: capture the reproduced public abort under GDB and compare configured-host destruction with plain drivers. Run ten fresh desktop admissions at the unchanged 30-second startup/3-second probe policy using the historical home outside /work; retain all phases and failures, with no replacement attempts.
Refs: /workspace/scratch/fw-reliability-recovery-isolated/attempts.json; /workspace/scratch/fw-reliability-recovery-isolated/recovery-07.events; /workspace/scratch/fw-reliability-windows/

## LR5 · exploratory · 2026-10-30 20:04
Question: which native thread/frame causes the reproduced abort, and does a configured Python authorization-host reference survive explicit shutdown?
Test: normal GDB startup changed timing and yielded 0/30 aborts, against 2/10 in the plain public CLI batch. Use a diagnostic-only native SIGABRT handler to stop only after an actual abort has already begun, attach the explicitly permitted task-owned debugger, record all thread backtraces, then restore normal SIGABRT termination. This must not convert an abort to success. Run ten more public recovery attempts with unchanged input/identity/deadline policy. Inspect the NativeAbiDriver shutdown/destroy ownership seam and Python trait-free callback path; do not patch it without the stack evidence.
Refs: /workspace/scratch/fw-reliability-recovery-isolated/; /workspace/scratch/fw-reliability-recovery-gdb/; /workspace/scratch/fw-reliability-recovery-gdb20/; vendor/cua-driver/native-source.tar.gz

## LR6 · prediction · 2026-10-30 20:07
Hypothesis: SDK shutdown revokes sessions synchronously but fails to await browser/protected-consent cleanup tasks spawned by those hooks. Their retained engine/provider can enter a Python foreign destructor on async-compat/to during interpreter finalization and trigger glibc forced-unwind abort through Tokio catch_unwind.
Test: preserve the actual abort-triggered GDB stack (one actual SIGABRT in ten capture attempts; restore and retain -6). Inspect BrowserEngine::new_with_runtime_services session-end spawn and the registry's protected-grant spawn. Add one runtime-owned tracked cleanup queue shared via ApprovalBroker; route those two hook tasks through it and await their completion after revocation in DriverRuntime.shutdown. Native tests challenge pending cleanup, cancellation of a drain, and isolation across brokers. Do not suppress exceptions or terminate the interpreter manually. Apply a reproducible Footwork patch to the verified native source, update provenance/version/hash pins, and repeat the same installed recovery boundary plus final finite acceptance.
Predicts: explicit shutdown cannot return while these owned cleanup tasks retain their captures; cancellation preserves pending joins for a later drain. Public recovery retains its strict root checks and normal process exits through the measured batch.
Against: native tests show early completion/lost cancelled joins, a retained hook task still outlives completed shutdown, or the same public native abort recurs after the patch.
Refs: /workspace/scratch/fw-reliability-recovery-capture/recovery-07.gdb; pinned cua-driver-core/src/browser/engine.rs:696; cua-driver-core/src/tool.rs:1189; cua-driver-sdk/src/runtime.rs:228

## LR7 · prediction · 2026-10-30 20:09
Hypothesis: selection/EWMH publication precedes a fully servicing Openbox startup boundary; an editor mapped in that interval can remain outside WM management, and repeated target children then correctly return zero visible qualified clients. This differs from a single slow AT-SPI observation.
Test: ten corrected-home admissions yielded eight ready and two persistent window_not_unique failures; ten phase-rich admissions yielded nine ready and one zero-window failure. Independent X11 tree at the latter shows the editor directly beneath root at +0+0 instead of a decorated/reparented client. Capture map attributes, WM_STATE, client-list membership and WM process stack in the next ten fresh sessions before changing readiness. Then require an owned temporary normal window to receive WM_STATE plus client-list membership, retaining selection/EWMH identity checks; close the temporary window on every path. Challenge a fake WM that publishes valid EWMH but never services mapping, and repeat fixed native admissions.
Predicts: failed clients lack completed WM admission even though WM selection/EWMH exist. A serviced sentinel before launching the editor prevents this race without increasing deadlines or changing target binding.
Against: failed editor is already managed/mapped in the verified WM list, or the same failure recurs after the serviced sentinel succeeds.
Refs: /workspace/scratch/fw-reliability-admissions/; /workspace/scratch/fw-reliability-windows10/case-03/x11-view.txt; /workspace/scratch/fw-reliability-windows10/case-03/session/probe-target-0001.json

## LR8 · prediction · 2026-10-30 20:18
Hypothesis: cleanup can poll a still-running direct child, then observe its new zombie state and stop the wait loop without a final direct-child reap. This explains a transient editor zombie snapshot without establishing a persistent leak or changing historical snapshots.
Test: a deterministic poll/capture interleaving leaves a direct child as a zombie after the last loop poll. Add a final nonblocking poll of each solely owned Popen child, keep the pre-reap zombie snapshot and numeric direct wait statuses, then take the final process snapshot. Check actual finite acceptance snapshots and follow-up proc identity observations; do not reap non-child processes or install a global reaper.
Predicts: the owned-child race resolves through its existing Popen wait owner, while before/after snapshot truth remains available. Any orphan zombie remains explicitly reported until init reaps it.
Against: the final snapshot still has a reapable owned child, earlier snapshots are erased, or the change calls waitpid for unowned processes.
Refs: results/linux-product-release-20261030/report.md; python/jevdual/linux_session.py:cleanup
