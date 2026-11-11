# macOS desktop-coordination qualification

Target: merged PR21, ac892a75211900ca6e252a46bca4f0da2362af6b. This is a bounded compatibility/behavior qualification, not a performance adoption experiment.

Hypothesis: participating public commands on one macOS console honor session/app/desktop ownership through readback and cleanup, preserve filmed reservations across command gaps, admit unrelated background work, and stop new input after revocation. A suspected fairness inversion may block a valid take owner behind a waiter that its own reservation blocks.

If true: conflicting dispatch never overlaps, independent background work proceeds with exact readback, handoff is token-specific, and the reservation holder can continue while an external request waits.
If false: the owner stalls, conflicting input enters, independent input is blocked, exact targets drift, or cancellation releases ownership before cleanup.

Design: (1) focused/default source suites on macOS using exact installed cleanup2 dependencies, (2) deterministic real-kernel reservation/waiter counterexample with a negative control, (3) fresh local native fixture and background document through the merged public CLI, including actual pointer rehearsal when the desktop is unlocked and idle. Use independently read fixture state/AX and OS pointer state as postconditions. Retain all attempts; no paid calls or heldout tasks. Existing offline tests model native input; label them accordingly.

Primary metric: required macOS criteria passed / required criteria attempted. Preserve each criterion independently; any wrong-resource input, cancellation breach or valid-owner circular wait fails the broad qualification.

Guardrails: use only run-owned fixture processes/files; observe exact target before any action; preserve normal posture checks; do not touch Suno or signed-in browser state; no SDK/global installation; no automatic orphan recovery after actual input unless release state is independently checked. Default per-user coordination use is through the public CLI only. Retain run-owned reservations until explicit cancellation/yield and confirm no live owned requests remain. Original installed Footwork is not upgraded, so old executables remain nonparticipants.

Decision rule: qualify only the tested source/runtime/host and successful criteria. A blocking defect or unavailable desktop leaves broad qualification failed/unverified. Propose product repairs separately unless authorized. Source-level predictions are committed before the resolving test. Capture quality needs actual capture evidence; pointer positions or session screenshots alone do not qualify a recorded take.
