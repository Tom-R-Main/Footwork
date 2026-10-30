# Linux session lifecycle and browser recovery

## LT1 · prediction · 2026-10-30 12:33
Hypothesis: explicit fresh profiles, staged bounded readiness and one process lifecycle owner eliminate the observed rootless-WM and recovered-editor setup ambiguity without changing input predicates.
Test: replace the fixture shell lifecycle with a bounded Python supervisor; exercise missing/stalled stages, cancellation, critical-component death and bounded group cleanup in subprocess tests, then run isolated Linux desktop acceptance with the actual installed driver where available.
Predicts: ready is published only after X11, WM, bus and exact fixture target qualification; partial startup never publishes ready, inherited app state is excluded, and cleanup finishes within its declared bound while recording forced termination separately.
Against: an unusable or modal target passes readiness, a failed component leaves the fixture running, cancellation hangs or an unrelated process is signaled.
Refs: docs/linux-next-tranche.md; scripts/linux/desktop-session.sh; results/linux-vm-save-receipt-20261030/report.md

## LT2 · prediction · 2026-10-30 12:33
Hypothesis: platform-specific new-window creation using the retained exact browser executable/profile can recover an owned Linux browser with zero windows without relaxing attachment identity.
Test: reproduce the unconditional macOS open route in a focused/public scenario, implement bounded exact-profile recovery, challenge failed spawn, changed incarnation and cancellation, and qualify the actual Linux recovery when an isolated browser is available.
Predicts: Linux never invokes open, reopens only the qualified profile, validates process incarnation before binding and leaves preexisting persistent browser processes alive on failure.
Against: a wrong profile or replacement process can attach, recovery blocks indefinitely, or cancellation kills a reused browser.
Refs: python/jevdual/browser_driver.py; tests/test_browser_launch.py; docs/linux-next-tranche.md
