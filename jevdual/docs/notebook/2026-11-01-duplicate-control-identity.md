# Duplicate native-control identity

## DCI1 · prediction · 2026-11-01 01:27
Question: can two indistinguishable native controls reorder or replace one another without Footwork refusing the stale selection?
Hypothesis: reobservation matching by role, label, section and same-key peer ordinal/count can choose a different backing control when peer count and states remain unchanged.
Test: extend the existing simulated-Mac session scenario harness with independently identified backing controls; select one, reorder or replace same-label same-state controls without changing peer count, then invoke the public command and inspect the independent dispatch ledger. Compare an unchanged unique-control positive control and owner replacement.
Predicts: the current code dispatches to a different backing identity in at least one same-count counterexample; a narrow identity qualification or conservative ambiguity refusal prevents that dispatch without weakening fresh-observation checks.
Against: the existing boundary already refuses all counterexamples or the harness cannot independently distinguish backing identities; a proposed fix refuses unchanged supported unique controls or authorizes stale objects after owner restart.
Refs: native.py NativeBridge._live; tests/test_session_scenarios.py; tests/fixtures/native_world.py; source baseline7852bb7; repo-learn native-rebinding-needs-discriminating-identity-v1
