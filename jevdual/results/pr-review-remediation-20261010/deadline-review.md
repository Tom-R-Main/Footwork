# Deadline-test review addendum

This is a bounded test-only continuation of the existing independent review, in the same inherited reviewer/model context. No new reviewer, paid CLI review, UI action, provider call, or production-source edit was used. It does not establish model diversity.

**Verdict: no actionable findings in the inspected delta.** The previous production and CI-remediation conclusions remain unchanged.

Scope: the uncommitted change to `jevdual/tests/test_capability_recovery.py` over `6dd81648090ec3c79c4a6c167b520c8452e730f9`. Checked SHA-256: `d29e100a400c32cec6af4b8053e550151f100e469c8086512c69112183dff797`.

The fixed worker still runs in a real child process. The test Timer runs the unchanged production deadline callback in a real thread only after the intended blocked observation boundary is recorded and its event is set. A missing boundary exits with code 3, which cannot satisfy the required deadline exit code 2 or manufacture a qualified deadline receipt.

The after-input boundary requires an effect file produced by the actual simulated `AXSelectedText` setter and checks its exact content, `Invoice\n17.25 USD`, before signaling the deadline. The before-input boundary requires the unchanged prefix and no effect file. Parent assertions retain the exact boundary phase/content, deadline error, no-send versus unknown disposition, phase, admission flag, effect-file presence/content, and released custody. The added 400 ms pre-boundary delay controls exercise both phases without relying on an assumed startup speed.

Independent check:

```sh
cd /Users/thomasmain/projects/footwork/jevdual
uv run --no-sync pytest -q tests/test_capability_recovery.py
```

Result: **35 passed in 1.98 seconds**.

This verifies the admission fence and uncertainty behavior at the observed simulated boundary, using the real worker process and deadline callback. It does not measure the production 25-second duration, qualify live macOS input timing, or add an OS-call-interior interruption guarantee. No product deadline or worker logic changed in this delta. Root owns final CI and merge verification.
