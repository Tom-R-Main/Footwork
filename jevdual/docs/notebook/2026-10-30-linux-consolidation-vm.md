# Cloud-base Linux consolidation

## LCON1 · prediction · 2026-10-30 17:47
Hypothesis: cloud cleanup's numeric individual-signal loop can outlive its captured process identity; a pidfd acquired with custody and before/after identity validation prevents later delivery from following PID reuse without claiming process-tree authority.
Test: commit the pre-registration, run an owned-child pidfd check on this actual Debian kernel, reproduce the stale-recipient regression, then adopt pinned individual delivery with explicit unsupported/denied/exhausted outcomes and no numeric fallback. Test acquisition-time replacement, replacement after pinning, stable neighbors, direct-child wait ownership and orphan cleanup separately.
Predicts: the retained descriptor addresses only its referenced child; exited fds return ESRCH and a sentinel survives. Unknown/denied acquisition cannot claim pinned delivery; incomplete inventories retain uncertainty and cannot claim complete cleanup.
Against: a replacement reaches the signal sink, pidfd availability silently downgrades to numeric delivery, descriptors/children leak, or incomplete inventory is reported as a complete no-survivor result.
Refs: docs/linux-consolidation-learning.md; source bd6f185; handoff 0634a06; results/linux-consolidation-vm-20261030/

## LCON2 · prediction · 2026-10-30 17:47
Hypothesis: waiting for an invocation-owned Chrome singleton helper to finish and be reaped before unique-root rediscovery fixes the grounded live-helper failure while preserving unrelated-root and incarnation refusals.
Test: reproduce using the actual root predicate, then challenge delayed/exited/failed helpers, an unrelated second persistent root, replaced root identity and cancellation. Repeat native zero-window recovery through the installed CLI.
Predicts: a delayed owned forwarding helper completes before binding; unrelated roots remain ambiguous and cancellation stops only the invocation's own helper/launch.
Against: arbitrary matching roots are excluded, a helper acknowledgement substitutes for window readback, or a reused persistent browser is terminated.
Refs: results/linux-repo-learning-20261030/models.json; python/jevdual/browser_driver.py

## LCON3 · prediction · 2026-10-30 17:47
Hypothesis: cloud-owned bus/ongoing health plus Xvfb displayfd allocation and WM selection/EWMH self-reference checks provide one stronger readiness contract without widening input authority.
Test: preserve the cloud state machine and packaged supervisor; transfer only compatible native allocation/EWMH mechanisms. Test selection-only WM, stalled handshake/allocation, partial inventories, marker invalidation and bus replacement. Freeze one combined source revision, build/verify one wheel and run installed refusal/save/replay/restart/recovery plus constrained lifecycle tests under init/512 PIDs.
Predicts: each failed or uncertain stage invalidates readiness, cleanup outcomes carry coverage/signalling uncertainty, and the combined installed artifact passes the existing exact-target and independent saved-byte journey.
Against: readiness relies on liveness/selection alone, failed startup retains started, imported competing runners diverge, or earlier green wheels are substituted for combined-build evidence.
Refs: docs/linux-consolidation-learning.md; docs/linux-support.md; results/linux-consolidation-vm-20261030/

## LCONU1 · update · 2026-10-30 18:13
Observed: the actual Debian kernel and installed pin_signal primitive passed owned-child/sentinel checks. Grounded source tests reproduced stale numeric delivery and live-helper ambiguity; corrected focused tests pass. A further partial-inventory regression exposed direct-child identity lookup through the bounded census; f16cc54 records direct-child custody independently and preserves unknown coverage. The f16cc54 source suite passes 2511 tests with 28 skips. Installed no-WM save correctly refuses with no dispatch, zero delivery, no readback and unchanged bytes; pinned cleanup reports complete inventory and no survivors/zombies.
Next: diagnose remaining native acceptance failures without changing the source or treating CLI JSON success as process success. The first constrained run completed installed save/replay and observed the live ambiguous helper, then its public CLI process exited nonzero with a native exception-not-rethrown message after printing success. A fresh repeat failed bounded target readiness before any ready marker; cleanup was complete. Repeat with explicit probe/exit diagnostics and preserve both failures.
Refs: results/linux-consolidation-vm-20261030/final-full-tests.txt; results/linux-consolidation-vm-20261030/container-acceptance.txt; results/linux-consolidation-vm-20261030/container-repeat.txt; results/linux-consolidation-vm-20261030/container-refusal.txt

## LCON4 · exploratory · 2026-10-30 18:13
Question: is the repeat's native target timeout a probe-budget issue or a persistent CUA observation failure, and does the post-success CLI native abort recur with exit diagnostics?
Test: unchanged f16cc54 installed wheel and fixed container limits, fresh private state; explicitly allow ten-second probe subprocesses under the same thirty-second startup deadline and enable Python fatal-signal diagnostics via an interpreter flag. Preserve typed SDK, process exit, readiness and cleanup evidence; do not retry a mutation or alter identity/receipt predicates.
Refs: results/linux-consolidation-vm-20261030/; CUA remains pinned

## LCONU2 · update · 2026-10-30 18:17
Observed: unchanged f16cc54 diagnostic primary acceptance completed installed saved-byte checks and the delayed live-helper public recovery with process exit 0, unchanged root identity and no cleanup survivors/zombies. Its later multi-session batch timed out during a different fixture's target probe even with ten-second probe bounds, so a simple three-second-budget explanation is unsupported. The native selection-only WM gate, partial inventory gate and unsupported/denied/exhausted capability policies all passed in a separate constrained run; partial coverage remained explicitly uncertain with no known live survivors. All thirteen browser tests pass.
Next: keep the batch failure distinct from its completed primary receipts. Isolate native lifecycle fault cases in fresh containers rather than interpreting a later startup failure as validation of a component-death gate. Make one standalone primary repeat and retain the initial post-success native abort as an unresolved observed event; no source or mutation predicates change.
Refs: results/linux-consolidation-vm-20261030/container-diagnostic.txt; results/linux-consolidation-vm-20261030/container-faults.txt; results/linux-consolidation-vm-20261030/browser-tests.txt

## LCONU3 · update · 2026-10-30 18:24
Resolves: LCON1 = held
Observed: kernel and installed primitive tests deliver through the referenced child fd, retain an exited-fd ESRCH result and preserve a sentinel. Acquisition-time replacement, unsupported/denied/exhausted paths and descriptor closure pass. The stale numeric-recipient and direct-child truncation regressions fail before their corrections. Native partial coverage retains cleanup uncertainty with no known live survivors; the supervisor uses no numeric individual fallback and no global competing wait owner.
Next: preserve the bounded observable-custody and pinned-individual claim; do not generalize to complete trees, unseen escaped descendants or other kernels.
Refs: results/linux-consolidation-vm-20261030/pidfd-kernel.json; results/linux-consolidation-vm-20261030/installed-pidfd.json; results/linux-consolidation-vm-20261030/first/faults.json

## LCONU4 · update · 2026-10-30 18:24
Resolves: LCON2 = held
Observed: actual predicate controls reproduce delayed-helper ambiguity and retain unrelated/late-root and replaced-incarnation refusals. The installed native fixture observed the live owned helper satisfying that predicate while independent discovery correctly refused ambiguity. After helper completion/reaping, public startup recovered the same persistent root identity/profile and exited 0. Cancellation tests preserve reused roots.
Next: keep the helper lifetime contract distinct from persistent-root authority; preserve the first post-success native-abort observation as a separate reliability limit.
Refs: results/linux-consolidation-vm-20261030/primary/acceptance.json; results/linux-consolidation-vm-20261030/helper-controls.txt; results/linux-consolidation-vm-20261030/first/browser-recovery.txt

## LCONU5 · update · 2026-10-30 18:24
Resolves: LCON3 = held
Observed: one combined f16cc54 product wheel matches 193 installed package files and source verification. Native displayfd chose a free display with another actual server retained. Selection-only WM, partial inventory and explicit unsupported/denied/exhausted capability policies refused appropriately. Fresh isolated Xvfb/bus/editor death and accessibility replacement invalidated readiness and cleaned up with no observed survivors/zombies or signal uncertainty. Installed normal save/replay/restart and no-WM refusal controls pass. Final full source suite passes 2511 with 28 skips; all thirteen browser tests pass; 55 process/readiness/resource tests pass under init/512 PIDs. Repeated native startup reliability remains unestablished: a target timeout recurred even with ten-second probe caps, while a standalone primary repeat passes.
Next: publish the exact combined source/artifact and retain failure records without asserting universal native reliability. Continue independent review of interpreter teardown and repeated-session observation outside this bounded consolidation acceptance claim.
Refs: results/linux-consolidation-vm-20261030/report.md; results/linux-consolidation-vm-20261030/installed-identity.json; results/linux-consolidation-vm-20261030/final-full-tests.txt

## LCONS · summary · 2026-10-30 18:24
Established: the VM-tested cloud state machine is consolidated with validated individual pidfd delivery, explicit inventory uncertainty, independent direct-child custody, native displayfd/EWMH readiness and helper completion before strict root rediscovery. One exact installed wheel passes primary/refusal and isolated negative/fault acceptance under the same 512-PID/two-core/3-GiB/zero-swap constraints. Prior branch evidence remains historical. Source changes are 40f96b1, 6f9d699 and f16cc54; no competing runner, provider authority or upstream bump was imported.
Uncertain: one post-success nonzero native teardown and intermittent repeated-batch target timeouts remain unexplained. A passing standalone repeat does not resolve those events. Visible start/custody checks are not a standalone universal identity oracle; pinned fds protect their acquired referent, not an entire tree. Missing/hidden process coverage, escaped unseen descendants, other kernels, physical seat/shared foreground and Wayland remain outside the claim.
Decision: retain the exact combined source and successful/failed acceptance receipts on the cloud branch, push for independent review, and explicitly keep native repeated-session reliability open.
Refs: results/linux-consolidation-vm-20261030/report.md; docs/linux-consolidation-learning.md; docs/linux-support.md
