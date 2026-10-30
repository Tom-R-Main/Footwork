# Linux bounded runtime tranche

## LXRT1 · prediction · 2026-10-30 16:34
Hypothesis: ad60bae recognizes the real pinned SDK recovery-enriched foreground refusal, closing the failed 045fc5d cloud repeat without changing actuator/identity predicates.
Test: rebuild and verify a fresh installed wheel; repeat the isolated broken-WM and fresh-profile working controls with the real SDK recorder and independent file comparison.
Predicts: broken-WM save records refused/dispatched=false/zero inputs/no save readback/unchanged bytes; working control completes CLI/MCP/replay/restart/save/artifact checks.
Against: real enriched replies still fail recognition, refusal claims input/readback, or working control fails exact persistence.
Refs: results/linux-runtime-tranche-20261030/; commit ad60bae; docs/linux-next-tranche.md

## LXRT2 · prediction · 2026-10-30 16:34
Hypothesis: an owned session supervisor with fresh XDG profiles, bounded subprocess probes and staged readiness prevents the startup/modal/cleanup failures seen in this VM.
Test: replace the shell fixture lifecycle with an independently testable supervisor; test stalled/failed readiness, occupied display, absent WM/bus/tree, recovery modal, cancellation, component death and TERM-ignoring owned descendants. Run native fresh-profile repeats and record PID/swap/event diagnostics without changing product input predicates.
Predicts: readiness requires X handshake, live WM, accessibility and exact fixture target; failed startup never publishes ready; cancellation/critical exit ends within probe/cleanup bounds and records forced/surviving descendants distinctly.
Against: a blocked probe or cleanup escapes its deadline, a partial/root-only/modal session is ready, unrelated processes/state are touched, or owned descendants survive without being reported.
Refs: scripts/linux/desktop-session.sh; python/jevdual/host_probe.py; docs/linux-next-tranche.md sections 2 and 3

## LXRT3 · prediction · 2026-10-30 16:34
Hypothesis: Linux zero-window browser recovery can launch the qualified ELF executable into the existing exact profile and bind a new window while preserving the persistent browser's identity and lifetime.
Test: reproduce the macOS-open fallback in a scenario before changing it; add launcher/recovery fault and cancellation tests. Qualify a native owned Chromium process with every visible window closed, then invoke public startup and verify the same process/profile plus scoped target.
Predicts: Linux recovery never invokes macOS open; failed/cancelled attachment reaps only newly owned helpers and closes its driver, preserving persistent browsers and strict ownership/ambiguity refusals.
Against: recovery weakens executable/UID/profile/port/incarnation checks, kills a reused browser, binds unrelated windows, or cannot recover on the native VM.
Refs: python/jevdual/browser_driver.py; tests/test_session_scenarios.py; docs/linux-next-tranche.md

## LXRTU1 · update · 2026-10-30 16:35
Resolves: LXRT1 = held
Observed: the fresh ad60bae consumer matched all 191 installed package files. The real recovery-enriched refusal now reports refused/dispatched=false/zero delivered inputs/no readback, with unchanged independent disk bytes. The fresh-profile working control passes the full public CLI/MCP/replay/restart and independently checked saved-byte journey. Actual SDK envelopes and both receipts are retained.
Next: implement units 2 and 3 independently, preserving the corrected receipt and all identity predicates.
Refs: results/linux-runtime-tranche-20261030/receipt-installed-identity.json; results/linux-runtime-tranche-20261030/ad60bae-refused-profile.json; results/linux-runtime-tranche-20261030/ad60bae-working-profile.json

## LXRTU2 · update · 2026-10-30 16:53
Observed: 26 lifecycle/resource tests and the native f31f7bd CLI/MCP/save journey passed. The outer VM's tail PID1 left four orphan zombies, explicitly reported without live descendants. An init-container repeat enforces 512 PIDs, two CPUs, 3 GiB and zero swap. Its first startup failed boundedly because the fixture UID lacked a passwd entry, with no ready record or remaining descendants/zombies. After supplying only fixture passwd/group records, installed text/save qualification passed. The real zero-window browser recovery then failed when its new-window helper exited; the initial root browser explicitly used the isolated fixture's no-sandbox flag. The d7c3dee full non-browser suite passed 2475 with 28 skips, and all thirteen browser tests passed.
Next: capture the helper's actual startup error before changing recovery runtime-mode inheritance; keep the failed container and exact limits separate from later repeats. Tighten supervisor root-incarnation tracking after code review identified a stale-root PID reuse risk.
Refs: results/linux-runtime-tranche-20261030/lifecycle-native-dev.json; results/linux-runtime-tranche-20261030/container-acceptance.txt; results/linux-runtime-tranche-20261030/container-ready-acceptance.txt; results/linux-runtime-tranche-20261030/full-tests.txt

## LXRT4 · prediction · 2026-10-30 16:53
Hypothesis: the isolated browser root's explicit no-sandbox setting is required for its secondary command-line helper in this container; default helper startup does not reach the existing profile singleton.
Test: capture stderr for the same qualified new-window command in a fresh isolated fixture; if confirmed, inherit only that already-selected flag from the exact existing root with incarnation validation. Challenge absent/different flags and process replacement, then repeat the public zero-window route under unchanged limits.
Predicts: default helper fails with a sandbox prerequisite error, and respecting the exact root's explicit flag recovers the same process/profile without adding it to normal launches or admitting arbitrary arguments.
Against: stderr identifies another cause, the matching-mode helper still fails, or inheritance widens identity checks or implicitly disables a previously enabled sandbox.
Refs: python/jevdual/browser_driver.py; docs/linux-next-tranche.md; results/linux-runtime-tranche-20261030/
