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

## MCU2 · update · 2026-11-11 06:28
Resolves: MC1 = held; MC2 = held
Observed: frozen implementation d34cdd8 passed2988 offline source tests with23 skips and67 deselections; one deselection is the installed CUA version assertion already observed failing against the unpatched0.46.0 environment. The real invocation-owned Chrome catalogue probe pinned the original page and refused its same-URL replacement after closing the original. Repository lint,103 resource snapshot files and97 Node checks passed. GitHub authentication recovered; origin/main still matches the implementation base f5d41c4.
Inferred: the exercised cross-process, cancellation, exact-target and readback boundaries hold in source fixtures; the real catalogue test establishes page-ID conservation independently of the CUA handle mapping.
Next: publish the PR, inspect CI and merge after required checks succeed.
Refs: results/desktop-coordination-20261111/pytest-final.txt; results/desktop-coordination-20261111/catalogue-probe.json; results/desktop-coordination-20261111/ruff.txt; results/desktop-coordination-20261111/resources.txt; results/desktop-coordination-20261111/node.txt

## MCS1 · summary · 2026-11-11 06:28
Established: shared per-user coordination spans session state, app/window transactions, foreground claims, whole-take reservations and the native capability worker. Explicit tokens fence cancellation and delayed cleanup; active transactions retain ownership through readback/shutdown and orphaned desktop owners require explicit input recovery. New ordinary-browser sessions pin the original process/page; native reconnects refuse missing original windows.
Uncertain: no live macOS foreground coexistence, CUA filmed capture, native window-birth identity, independent macOS Screen Sharing desktop, cross-user ownership or control over nonparticipating software is established. Cancellation cannot interrupt inside an already admitted opaque SDK RPC. The exact patched CUA runtime is unavailable locally; CI must qualify that installation.
Decision: implementation is ready for CI and merge with these limits documented. The broad initial mechanism held, but review exposed wrapper compatibility and entrypoint gaps that required fixes; the native-window-loss counterexample failed before its repair. Keep the successful real headless catalogue probe distinct from native/filmed qualification.
Refs: docs/desktop-coordination.md; results/desktop-coordination-20261111/report.md; d34cdd8

## MC3 · prediction · 2026-11-11 06:53
Hypothesis: normalizing only X11 screen zero lets two screens on one X server acquire distinct desktop claims despite sharing its core pointer. The coordinator must key the X server rather than its screen suffix.
Test: hold the desktop with DISPLAY=:0.0 and request it with DISPLAY=:0.1; test canonical local Unix/loopback host aliases and verify distinct X server display numbers remain independent.
Predicts: the current screen-one request is incorrectly admitted; stripping every numeric screen suffix and canonicalizing local aliases blocks it while :0 and :1 remain independent.
Against: screen-one already conflicts, or the repair merges distinct local X servers. This tests cooperative resource identity, not live X11 or macOS coexistence.
Refs: python/jevdual/coordination.py desktop_id; tests/test_coordination.py; PR21
