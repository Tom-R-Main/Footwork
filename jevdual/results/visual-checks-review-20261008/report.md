# Native visual capability review and remediation

Observed: the independent review and root boundary probes found actionable defects in the previously committed advisory package. All reproduced code defects are fixed and checked on 9148c2e. Full offline suite: 1,031 passed, 26 skipped; focused integration: 157 passed. Independent rechecks found no remaining blocker in the changed code. Final native requalification passed after the Mac was unlocked: fifteen selected scenarios, seven loopback requests, zero action dispatches.

## Findings and corrections

| Finding | Trigger and consequence | Correction and proof |
|---|---|---|
| Interrupted ledger resets budget | A charged budget.json truncated to zero bytes was initialized as new and allowed another request | Exclusive creation distinguishes new state; existing empty state refuses. Offline regression failed before repair and passes after; native review1 blocks both interrupted ledgers without another HTTP request |
| Stale owning bridge survives handoff | Passed pre-action menu retained a positive even after owning bridge.last was invalidated | Require owning observation and a retained workflow source/generation guard. Both result locations lose probability on invalidation |
| Final visual metadata bypasses redaction | Raw result/escalation overwrote the redacted nested summary, leaking a synthetic credential in request identity | Redact the final assembled packet. Synthetic-secret regression and actual native message-builder readback pass |
| Pending effect baseline overwritten | A visual capture remembered the new menu before reconciling the previous action, corrupting later effect comparison | Shared finish_observation resolves the pending receipt first. Stateful CLI scenario confirms the historical change exactly once |
| Capture ignores operational deadline | A delayed native snapshot completed after the deadline and returned invalid_deadline | Cooperative timeout around capture; delayed-driver scenario returns capture_timeout before completion and preserves baseline |
| Publication prints known-stale positive | Source changed during receipt I/O; storage guard detected it but stdout and receipt retained p | One output packet and post-I/O reconciliation update receipt, nested result, escalation, stdout and summary consistently. Regression and independent recheck pass |

The library source-validity gap is also closed: NativeAgent.check_visual requires is_current=workflow_guard and retains it for System Two consumption. Omitting the guard refuses before dispatch. Stored hashes/guards remain correlation evidence, not proof that live pixels or external files stay atomic after the last check.

Every product reproduction had a failing regression before correction. One publication probe initially needed a missing pathlib import repaired before it demonstrated the product failure. Predictions were committed before probes; the notebook records the disconfirming results and follow-up corrections.

## Verification and scope

[checks.json](checks.json) binds counts to source hashes and commits. [Native review1](../visual-checks-native-20261008/review1/verification.json) passed fourteen selected scenarios on real task-owned document/crop AppKit windows through the CLI/Cua SDK and production transport into loopback. Six loopback requests, zero actions/effects/grants; bridge invalidation and synthetic-secret redaction were checked. Owned processes and listener were cleaned up.

The publication correction followed that first native pass. [Native review2](../visual-checks-native-20261008/review2/verification.json) was blocked at its first look by screen_locked; both fixture processes were terminated and the listener closed. After the user unlocked the Mac, [native review3](../visual-checks-native-20261008/review3/verification.json) passed on 9148c2e: twelve receipt scenarios and three early refusals, seven loopback requests. The publication-time source change invalidated stdout, receipt and both result locations consistently. Source hashes match; owning-bridge invalidation and synthetic-secret redaction pass; zero action dispatches/effects/grants and cleanup are confirmed. The captured document and crop scenes were visually inspected. Fixed predicates qualify transport and boundary mechanics only.

No paid provider or System Two calls, key creation, dependency installation, model activation, admission-setting change, PR, push or deployment occurred. Unrelated refactor planning files were preserved. Provider accuracy, calibration, complete recovery, browser capture and reviewed execution remain unqualified.

Recommendation: retain the corrected advisory boundary and require independent visual quality/speed evidence before adding execution authority or changing model routing.
