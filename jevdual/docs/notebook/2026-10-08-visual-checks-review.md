# Native visual capability post-implementation review

## VCR1 · prediction · 2026-10-08 20:00
Question: do durable reservation and final-consumption guards remain fail-closed when state is interrupted or changes across the native advisory boundaries?
Hypothesis: the current empty-ledger initialization conflates a new file with an interrupted existing file; source/observation handling may have similarly unchecked transitions outside the provider transport.
Test: fresh independent source review plus bounded offline CLI/ledger/agent probes, focused regressions for concrete findings, and existing native CLI/Cua loopback verification after fixes. Commit this prediction before probes; no paid provider or System Two calls, actions, key creation or installs.
Predicts: an existing zero-byte ledger incorrectly allows a fresh reservation, contradicting the documented fail-closed workflow cap; meaningful regression and first-create distinction can repair this without relaxing capture/disclosure or action guards.
Against: an existing empty ledger is already rejected, reproductions depend on bypassing the public boundaries, or fixes change default model/action authority rather than the failing transition.
Refs: python/jevdual/visual_decisions.py; python/jevdual/visual_native.py; python/jevdual/desktop.py; docs/visual-checks.md; cbd7bf1

## VCR2 · prediction · 2026-10-08 20:09
Question: does the configured visual-check deadline bound an asynchronous native capture, or only the subsequent HTTP request?
Hypothesis: capture_request awaits bridge.observe without a timeout; a slow capture exceeds the caller's deadline before request construction rejects it.
Test: a real CLI scenario with the driver boundary delayed beyond a short deadline, no provider; assert capture_timeout before the delayed snapshot completes and preserve the original session baseline.
Predicts: current code returns invalid_deadline after waiting for the delayed capture rather than stopping at the capture boundary; wrapping the cooperative capture await repairs the operational timeout.
Against: current capture already cancels by the deadline, or a non-cooperative driver rather than the missing async boundary explains the failure.
Refs: python/jevdual/visual_native.py; tests/test_visual_native.py

## U-VCRFIX · update · 2026-10-08 20:17
Resolves: VCR1 = held
Observed: Four initial regressions failed for empty persisted ledger reset, pending-action baseline replacement, stale owning-bridge positive and final handoff secret-metadata redaction. Two library guard scenarios failed for missing source-current validation and absent callback support. The delayed-driver scenario failed with invalid_deadline after waiting for capture. All seven now pass: exclusive creation distinguishes empty interrupted state; shared finish_observation reconciles prior effects; owning bridge and retained workflow guard gate consumption; final assembled payload is redacted; capture awaits have a cooperative timeout. Independent reviewer rechecks 127 focused tests and closes its findings. Root integration set passes 156; full suite passes 1030, 26 skipped, in 67.21 s.
Inferred: Original local verification omitted important failure paths; source review and small boundary probes disconfirmed the blanket failure-handling claim. Remediation preserves the explicit advisory role and current authority settings while closing these measured transitions.
Next: Commit corrected source, then requalify actual native CLI/Cua and loopback with owning-bridge invalidation, redaction and interrupted-ledger cases. Preserve previous proof as historical; no paid calls or live activation.
Refs: tests/test_visual_native.py; tests/test_visual_decisions.py; python/jevdual/session.py; python/jevdual/desktop_s2.py; python/jevdual/visual_decisions.py; scripts/verify_visual_checks.py; cbd7bf1

## U-VCRDEADLINE · update · 2026-10-08 20:18
Resolves: VCR2 = held
Observed: The delayed-driver CLI probe failed before repair: it completed the delayed snapshot and reported invalid_deadline. After adding the cooperative capture timeout, it reports capture_timeout before that snapshot finishes, with original session bytes preserved. The full 1030-test suite and focused regressions pass.
Inferred: The missing timeout around the native capture await was the measured cause. This bounds cooperative capture waits; it does not establish a hard real-time limit for driver startup, synchronous decoding or cleanup.
Next: Include the corrected boundary in native requalification and retain separate provider-quality limits.
Refs: tests/test_visual_native.py; python/jevdual/visual_native.py; docs/visual-checks.md
