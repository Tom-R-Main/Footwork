# Desktop and session coordination

## MC1 · prediction · 2026-11-11 06:10
Hypothesis: a shared cross-process resource coordinator, entered before session loading and retained through readback and driver cleanup, can prevent competing state updates and foreground transactions without serializing independent apps. Persistent desktop-and-subject reservations can extend that ownership across filmed command gaps.
Test: multiprocess contention and process-death tests, public command integration tests, cancellation and stale-token counterexamples, strict browser target tests, then affected and full offline regression checks.
Predicts: same-session read-modify-write operations and conflicting resources serialize; independent resources overlap; reservations survive process exit and block subject mutations and foreground work while permitting independent background work; cancellation fences later dispatch and does not release active cleanup; stale release cannot remove newer ownership; reconnect never falls back from a missing explicit tab.
Against: any conflicting dispatch/readback overlaps, a canceled waiter dispatches, unrelated background work blocks behind a desktop reservation, cleanup releases newer ownership, or a missing pinned target switches to the remaining tab.
Refs: user-supplied multitasking assessment and five implementation priorities; python/jevdual/session.py; python/jevdual/posture.py; python/jevdual/browser_driver.py. The Mac-only docs/repo-learning/multitasking report is absent from this checkout.
