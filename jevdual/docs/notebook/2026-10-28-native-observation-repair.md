# Native observation and installed CLI repair

## NO1 · prediction · 2026-10-28 00:18
Hypothesis: the reported capture-binding failure comes from a mismatch between Footwork's native observation request and the pinned CUA capture contract, rather than stale persisted session state.
Alternatives: CUA cannot qualify Muse's window or screenshot geometry even with a correctly constructed request; the installed artifact differs from the source checkout.
Test: trace the installed request through the pinned Python and native sources; reproduce against an owned fixture and model the discriminating failure in the native session scenarios before changing the integration.
Predicts: a specific input/contract mismatch explains fresh-session failure, and correcting it restores an observation without weakening binding or action gates.
Against: the request already satisfies the contract, the owned fixture cannot reproduce the failure, or a correctly bound request still fails in the driver.
Refs: python/jevdual/native.py; tests/fixtures/native_world.py; tests/test_session_scenarios.py; vendor/

## NO2 · prediction · 2026-10-28 00:18
Hypothesis: missing native acceleration is an intentional pure wheel condition with misleading import diagnostics, while empty permission-denied observations and missing session errors lack explicit operator-level classification.
Test: inspect both installed artifact and wheel build paths; reproduce denied Accessibility and absent-session commands through the real CLI, then verify typed failures and concise JSON output alongside acceleration/fallback tests.
Predicts: pure wheel discovery works without an import warning, doctor exposes actual acceleration availability, missing permissions prevent successful observation, and missing sessions return an actionable diagnostic without a traceback.
Against: the pure wheel is meant to include the extension, denied Accessibility is already classified before observation, or error repairs change underlying command/effect semantics.
Refs: python/jevdual/_native.py; python/jevdual/agent_cli.py; python/jevdual/session.py; scripts/build_capability_wheel.py

## NOU1 · update · 2026-10-28 00:24
Resolves: NO1 = held
Observed: installed pre-fix desktop start fails on an owned TextEdit fixture with the exact reported capture_binding_failed error despite granted host permissions. Pinned CUA tool.rs initially supplies an implicit session, then screenshot-file authorization rebuilds the request without that binding. A named public session survives reconstruction. The new real-CLI scenario fails before the repair and passes afterward, including a simulated click bound to its fresh observation session. The rebuilt portable wheel starts and reobserves both the owned fixture and Muse successfully; Muse exposes 20 controls in each observation, and the owned fixture PNG is 1312 by 844. Driver revision and pin are unchanged.
Inferred: Footwork's unnamed screenshot-file requests trigger this driver authorization-path defect; per-bridge explicit sessions repair the integration without relaxing capture identity or dispatch gates.
Next: complete broad regression checks and independent review before publication.
Refs: output/native-observation-repair/live-before.json; output/native-observation-repair/live-installed-start.json; output/native-observation-repair/live-installed-look.json; output/native-observation-repair/muse-installed-start.json; output/native-observation-repair/muse-installed-look.json; vendor/cua-driver/native-source.tar.gz (tool.rs:1835-1845,2047-2063,3431-3507); tests/test_session_scenarios.py

## NOU2 · update · 2026-10-28 00:24
Observed: the portable wheel intentionally omits optional Jev acceleration; explicit module import removes the misleading circular-import warning while tests retain warnings for genuinely broken extensions. Doctor exposes acceleration separately from CUA and emits parsed JSON only once. Denied/unavailable Accessibility scenarios and a missing initialized session now stop with named diagnostics; denied startup preserves an existing session. The first broad run exposed four subprocess fixture failures: TextWorld replaced ApplicationServices without replacing the newly observed permission boundary. Updating that OS fixture restores all 117 recovery/session tests; no production gate was weakened. Focused CLI/native tests passed 194 before the additional fixture checks. Owned browser, listener and TextEdit fixture window cleanup is confirmed, with the fixture file unchanged.
Next: run the final broad suite, inspect the final diff and review, then publish the repair under the existing CLI completion request.
Refs: output/native-observation-repair/cli-backend-before.txt; output/native-observation-repair/cli-backend-after.txt; output/native-observation-repair/scenarios-before.txt; output/native-observation-repair/scenarios-after.txt; output/native-observation-repair/full-tests.txt; output/native-observation-repair/recovery-after.txt; output/native-observation-repair/installed-doctor-after.json; output/native-observation-repair/installed-missing-session.json; output/native-observation-repair/live-fixture/cleanup.json

## NOU3 · update · 2026-10-28 00:26
Resolves: NO2 = held
Observed: final local non-browser suite passes 1696 tests, with 26 skipped and 12 browser tests deselected. Ruff, notebook validation and resource drift checks pass. Installed discovery, schemas and simulator checks pass outside the checkout. The final repair scenarios pass seven cases, and independent same-session-model source review finds no blocking issue. The portable wheel and new install-once bundle contain identical product bytes with SHA256 9802b64e7d80eeaa3d7dc2099bf39b4564675c718ac1f346a71a80ca9203f5a8; the existing delivered environment uses that wheel.
Next: push the candidate and require hosted checks and review resolution before an authorized merge.
Refs: 0f31660; output/native-observation-repair/full-tests-final.txt; output/native-observation-repair/scenarios-final.txt; output/native-observation-repair/installed-tools-check.json; output/native-observation-repair/bundle.json; output/footwork-cli-20261028/

## NOS1 · summary · 2026-10-28 00:26
Established: named CUA sessions restore the reported native screenshot path on the installed CLI, including Muse; missing permissions and failed initialization have actionable errors; optional acceleration and JSON diagnostics are explicit. Prediction 7a9cf57 precedes reproductions and the repair.
Uncertain: hosted CI remains pending. Muse observation does not prove a file transfer or GUI action outcome. Hermes's separate executable and transport were not investigated or modified; no model/provider qualification is claimed.
Decision: retain the verified local candidate and publish the bounded corrective PR under the existing tests, CI and merge authorization.
Refs: 7a9cf57; 0f31660; docs/unified-cli.md; output/native-observation-repair/
