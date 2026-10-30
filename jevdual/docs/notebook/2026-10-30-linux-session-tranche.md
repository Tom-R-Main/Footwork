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

## LTU1 · update · 2026-10-30 12:51
Resolves: LT1 = held
Observed: the real Linux fixture reached X11/WM/bus/exact-editor stages with an automatically reserved display. Two private-profile starts cancelled and cleaned up without live known components; missing WM refused before ready. Nine final Linux subprocess tests cover blocked probes, invalid readiness, partial startup, cancellation, component death and TERM-ignoring child/grandchild cleanup. PID/event/swap diagnostics retain per-ancestor observations without summing counters.
Next: retain selected resource/security configurations and scoped cleanup limitations; cloud repetition remains a separate target.
Refs: results/linux-session-tranche-20261030/lifecycle.json; results/linux-session-tranche-20261030/linux-lifecycle-final.txt; results/linux-session-tranche-20261030/host-probe.json

## LTU2 · update · 2026-10-30 12:51
Resolves: LT2 = held
Observed: initial Linux recovery reached the helper but Chrome rejected the restricted container's sandbox configuration. A separate owned container permitting unprivileged namespaces recovered one window through installed public startup with unchanged product flags, the same process incarnation and the reused root still alive. Real installed CLI/MCP replay/restart and saved bytes passed. Real no-WM save now reports no dispatch and unchanged disk bytes.
Next: preserve the failed prerequisite run and sandbox-capable success separately; push for the existing Codex Cloud checkout to rebuild and repeat.
Refs: results/linux-session-tranche-20261030/browser-recovery.json; results/linux-session-tranche-20261030/sandbox-prerequisite-failure.txt; results/linux-session-tranche-20261030/installed-journey.json; results/linux-session-tranche-20261030/refused-save.json

## LTS1 · summary · 2026-10-30 12:51
Established: scoped readiness/lifecycle, safe resource diagnostics and Linux zero-window recovery are implemented. Linux regression lane passed 2437 tests and all 13 browser cases separately; macOS regression lane passed 2433. The final fixture revision passed nine Linux process tests. Installed wheel identity and positive/negative runtime receipts are retained.
Uncertain: fresh Codex Cloud execution, Wayland, physical devices, provider-backed planning and shared-desktop foreground guarantees remain outside these observations. Cleanup covers retained groups/children with explicit unresolved states; orphan reaping requires container init. The successful Chrome sandbox run used a documented container seccomp difference.
Decision: retain reviewable local commits and evidence on codex/linux-support, stop temporary helpers, and publish the branch for cloud repetition. Keep the later app/Wayland gates unchanged.
Refs: docs/linux-next-tranche.md; results/linux-session-tranche-20261030/report.md
