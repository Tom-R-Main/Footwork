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
