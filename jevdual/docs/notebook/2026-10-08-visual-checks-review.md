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
