# Duplicate native-control identity

## DCI1 · prediction · 2026-11-01 01:27
Question: can two indistinguishable native controls reorder or replace one another without Footwork refusing the stale selection?
Hypothesis: reobservation matching by role, label, section and same-key peer ordinal/count can choose a different backing control when peer count and states remain unchanged.
Test: extend the existing simulated-Mac session scenario harness with independently identified backing controls; select one, reorder or replace same-label same-state controls without changing peer count, then invoke the public command and inspect the independent dispatch ledger. Compare an unchanged unique-control positive control and owner replacement.
Predicts: the current code dispatches to a different backing identity in at least one same-count counterexample; a narrow identity qualification or conservative ambiguity refusal prevents that dispatch without weakening fresh-observation checks.
Against: the existing boundary already refuses all counterexamples or the harness cannot independently distinguish backing identities; a proposed fix refuses unchanged supported unique controls or authorizes stale objects after owner restart.
Refs: native.py NativeBridge._live; tests/test_session_scenarios.py; tests/fixtures/native_world.py; source baseline7852bb7; repo-learn native-rebinding-needs-discriminating-identity-v1

## DCIU1 · update · 2026-11-01 01:36
Resolves: DCI1 = held
Observed: the public CLI counterexamples on source baseline7852bb7 with scenario-only fixture additions dispatched to setting-A after a same-count reorder and replacement-C after same-field replacement; the unique-label positive control dispatched once to setting-B. The independent backing ledger is not part of the SDK snapshot. A preliminary run failed only a render-format precondition; that assertion was corrected before the behavioural red. The expanded red also dispatched a pruned retained row from a five-peer group.
Inferred: ordinal, state and snapshot-local token checks do not discriminate these backing objects. The pinned WindowElement Python contract exposes no retained native identity/identifier, so generic action refusal is the bounded repair rather than a pointer/daemon protocol.
Changes: generic native actions now retain pre-pruning collision IDs and raise target_ambiguous with dispatched=False, while duplicate rows remain usable observation evidence.
Next: preserve the same evidence across separate CLI commands and verify affected scenarios, unique controls and existing owner-change/no-replay regressions.
Refs: output/duplicate-controls-20261101/red.txt; output/duplicate-controls-20261101/red-behavior.txt; output/duplicate-controls-20261101/red-pruned.txt; vendor/cua-driver/src/cua_driver/_native_contract.py WindowElement

## DCIU2 · update · 2026-11-01 01:36
Observed: review of the first refusal implementation found a distinct boundary within DCI1: transient NativeMenu collision IDs were lost by session save/load. A new public scenario starts with two identical ordinary native buttons pruned to one; after the original disappears, a same-index singleton lookalike receives the click. This fails against the transient-only repair with backing ledger setting-B.
Inferred: the action must check the prior observation's raw-collision evidence, even when both offered menus have only one row. A fresh singleton cannot establish that the earlier selected backing object survived.
Changes: SessionState persists last_native_ambiguous alongside its observation baseline; numeric selection checks the captured prior evidence before admission. Missing legacy evidence requires fresh selection. Explicit label selection remains a query on the current observation and current live ambiguity still refuses.
Next: complete the save/load, legacy refresh, final-revalidation, hidden-peer and changed-owner checks; retain the normal CLI receipt contract for errors raised after its dispatch attempt boundary.
Refs: output/duplicate-controls-20261101/red-historical-pruning.txt; session.py SessionState.remember and cmd_do

## DCIU3 · update · 2026-11-01 01:37
Observed: final focused source checks passed203 tests in test_session_scenarios.py, test_control_state.py, test_native.py and test_session.py. The backing-ledger cases cover reorder, replacement, unchanged ambiguity, current pruning, historical ordinary-button pruning/save-load, a newly inserted peer during final live revalidation, peer disappearance, unique-label success and legacy-session refresh. The selected existing durable process-change and unknown/no-replay scenarios also pass in that affected suite. Ruff passed all owned Python files.
Changes: the historical collision guard rejects before operation admission and logs no do record. A newly arising collision detected inside act retains the existing CLI contract: exit0 may contain a typed not-dispatched receipt, whose dispatched=False field and independent empty effect ledger are asserted. The old ordinal-success test is replaced by refusal; its duplicate-state observation/diff coverage remains through externally changed persisted observations.
Next: parent commits/integrates with the independent lightweight-install package and runs the final broad checks and installed-artifact qualification. Owned production and test files are frozen for that integration.
Refs: output/duplicate-controls-20261101/affected-persisted.txt; output/duplicate-controls-20261101/expanded-focused.txt; output/duplicate-controls-20261101/source-identity.json

## DCIS · summary · 2026-11-01 01:37
Established: the scenario counterexamples demonstrate wrong backing delivery on the old ordinal path and on a transient-only ambiguity repair. Generic native actions now refuse known semantic duplicate collisions before dispatch; raw collision evidence survives pruning and session save/load. Distinct supported controls, read-only duplicate observation, changed-peer rejection and existing durable process/uncertainty gates remain covered by the203-test affected suite.
Uncertain: no live desktop or native identity protocol was exercised. Positively observed duplicate collisions do not establish global uniqueness when the underlying backend omitted unseen peers. Conservative refusal deliberately removes generic native action support for alike controls, even when their mutable state differs; a future qualified native-identity seam could restore that capability. Shared native/agent effect-diff matching remains observational rather than backing-object proof.
Decision: deliver the bounded refusal and regression scenarios for parent integration; do not claim retained AX identities, arbitrary native uniqueness, overall task completion, or a live-platform qualification from the modeled scenario.
Refs: prediction7b326f2; output/duplicate-controls-20261101/red-behavior.txt; output/duplicate-controls-20261101/red-historical-pruning.txt; output/duplicate-controls-20261101/affected-persisted.txt
