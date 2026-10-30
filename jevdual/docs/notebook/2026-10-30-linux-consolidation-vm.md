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
