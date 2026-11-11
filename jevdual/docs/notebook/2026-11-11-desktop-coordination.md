# Desktop and session coordination

## MC1 · prediction · 2026-11-11 06:10
Hypothesis: a shared cross-process resource coordinator, entered before session loading and retained through readback and driver cleanup, can prevent competing state updates and foreground transactions without serializing independent apps. Persistent desktop-and-subject reservations can extend that ownership across filmed command gaps.
Test: multiprocess contention and process-death tests, public command integration tests, cancellation and stale-token counterexamples, strict browser target tests, then affected and full offline regression checks.
Predicts: same-session read-modify-write operations and conflicting resources serialize; independent resources overlap; reservations survive process exit and block subject mutations and foreground work while permitting independent background work; cancellation fences later dispatch and does not release active cleanup; stale release cannot remove newer ownership; reconnect never falls back from a missing explicit tab.
Against: any conflicting dispatch/readback overlaps, a canceled waiter dispatches, unrelated background work blocks behind a desktop reservation, cleanup releases newer ownership, or a missing pinned target switches to the remaining tab.
Refs: user-supplied multitasking assessment and five implementation priorities; python/jevdual/session.py; python/jevdual/posture.py; python/jevdual/browser_driver.py. The Mac-only docs/repo-learning/multitasking report is absent from this checkout.

## MCU0 · update · 2026-11-11 06:03
Observed: the MC1 heading was transcribed as06:10; the clock returned05:59 UTC before commit d2b8d2b. Git order establishes that the prediction preceded implementation and tests.
Next: implement the predicted boundaries and exercise multiprocess counterexamples.

## MCU1 · update · 2026-11-11 06:25
Observed: the first multiprocess coordinator checks passed10 tests; affected session/browser/posture/filmed/authority checks passed209, and expanded target/native/capability checks passed286. Full offline review found an incomplete-browser-metadata regression and a visual-inspection refusal-code regression in the new wrapper, plus environment failures from umask0077, the missing /tmp/.X11-unix fixture directory and unpatched installed CUA0.46.0. The compatibility regressions are repaired; the affected final review passed236 tests. A public native-window-loss scenario dispatched before the repair (window-red.txt) and refuses afterward. Repository lint, resource snapshot verification and97 Node checks pass.
Inferred: command-level ownership needs every production input entrypoint, including independent capability workers and headed browser launch/recovery. URL matching alone cannot preserve a closed ordinary-browser target across CUA reconnects.
Changes: shared resource coordinator with persistent take reservations and fenced cancellation; retain orphaned desktop claims after hard kill; pin new ordinary-browser sessions to the original CDP page ID/process incarnation; revalidate native windows before reconnecting; preserve the existing visual-inspection error contract.
Next: finish the frozen source regression run and probe the page catalogue against an actual owned headless Chrome. The installed CUA version check remains an environment failure; Rust and required native development headers are unavailable in this image.
Refs: results/desktop-coordination-20261111/pytest-before-final-review.txt; results/desktop-coordination-20261111/final-affected.txt; results/desktop-coordination-20261111/window-red.txt; tests/test_coordination.py; tests/test_browser_target.py

## MC2 · prediction · 2026-11-11 06:25
Hypothesis: the bounded /json/list catalogue identifies a page across connections in a real owned Chrome, and closing that ID while keeping a same-URL replacement makes the persisted pin unavailable.
Test: launch an invocation-owned headless Chrome with a private profile and fixed ephemeral debugging port, pin its initial about:blank page, create a replacement about:blank page through a separate test-only CDP connection, close the original and resolve its persisted pin again; terminate only the owned launch afterward.
Predicts: initial pin records the owned PID/incarnation/profile/port and a nonempty page ID; resolution after replacement refuses the original as unavailable rather than selecting the new page.
Against: the catalogue cannot establish the initial owned page, or resolution selects the same-URL replacement. This probe does not qualify native CUA dispatch, shared macOS input or filmed capture.
Refs: python/jevdual/browser_target.py; results/desktop-coordination-20261111/catalogue-probe.py
