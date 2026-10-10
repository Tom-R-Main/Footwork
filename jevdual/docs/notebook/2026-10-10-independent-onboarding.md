# Independent onboarding qualification

## UO1 · prediction · 2026-10-10 19:20
Hypothesis: packaging the existing model-free consumer/native helpers with the final wheel and explicit runbook makes the independent qualification transportable without including Footwork's runtime source or development dependencies.
Test: build a frozen packet twice, verify every manifest member and the wheel against source, unpack outside the checkout, and import the documented helper modules with an already qualified installed interpreter. Exercise help only; no fixture/native input, permission change or provider call.
Predicts: packet bytes repeat, runtime source and secrets/evals/results are absent, all helper imports and documented help entry points work from the unpacked directory, and tampered inventory or bytes are rejected. This qualifies preparation, not first use.
Against: a helper imports unavailable source/research code, the manifest accepts tampering, the builder executes a helper or the runbook mistakes existing grants for a denied baseline.
Refs: docs/experiments/U2-independent-onboarding.md; scripts/capability_installed_trial.py; results/capability-delivery-20261010/report.md

## UO2 · prediction · 2026-10-10 19:20
Hypothesis: a new SIP-enabled macOS environment launched through one responsible interactive host exposes a truthful denied-to-approved Accessibility transition and permits the frozen installed native oracle afterward.
Test: U2 independent environment first-use lane, with initial strict diagnostics, human permission decisions, host restart/readback and one-effect/repeated-token/report/cleanup checks.
Predicts: initial missing Accessibility blocks before input, the approved host's installed native flow passes and grants are attributed to that host rather than inherited from the current Mac or a golden seed.
Against: the initial baseline is already granted, the blocked route sends input, host attribution changes, or approved permission still cannot satisfy the actual native oracle.
Refs: docs/experiments/U2-independent-onboarding.md; local Cua macos-lume SIP-on permission-flow lane; local Arc Accessibility-only setup

## UOU1 · update · 2026-10-10 19:34
Observed: frozenf39b76a packet builds match at13members, helpers import outside the checkout on installed3.12.6/3.14.7, four help entries pass, placeholder-resource config stays private/fresh and creates no journal, malformed/reused configs refuse, and modified/extra archive members reject.17 selected tests and Ruff pass. The Claude request remains unread in the mailbox; no independent verdict is available. Self-review finds a missing explicit Chrome prerequisite and a verifier coupling its recorded source commit to currentHEAD, which would invalidate a frozen packet after evidence-only commits.
Changes: UO1/UO2 heading times were entered19:20 while the terminal clock was19:19; preregistration order is established by committed aa6be28 preceding frozenf39b76a and all resolving tests. No prediction text is rewritten.
Next: retainv1, clarify source-checkout/browser prerequisites and qualify explicit immutable source binding in a separate packet version. UO2 remains unexecuted pending environment selection.
Refs: output/u2-packet-smoke-v1/receipt.json; output/u2-packet-v1; Claude request1791674683421027000

## UO3 · prediction · 2026-10-10 19:34
Hypothesis: reading the packet's fixed helper/doc inventory from an explicitly selected immutable Git commit lets a frozen artifact remain verifiable after evidence-only commits without trusting unrecorded working-tree bytes.
Test: verify oldv1 from this later commit with an explicit frozen source ref; build a new version from committed source, verify it against that ref, and reject mismatched refs/member bytes. Keep the reviewed wheel's current source verifier and external archive hash.
Predicts: explicit frozen-ref verification succeeds despite currentHEAD differing; the caller's expected ref, exact allowed Git blobs and wheel/member hashes still reject foreign or altered contents.
Against: verification still depends on currentHEAD, uses dirty payload bytes, silently accepts another ref, or helper/runtime inventory changes outside the declared preparation scope.
Refs: scripts/build_onboarding_packet.py; output/u2-packet-v1/footwork-onboarding-u2.zip
