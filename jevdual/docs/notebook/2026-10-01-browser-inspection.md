# Browser inspection evidence package

## A1 · prediction · 2026-10-01 14:09
Question: can the prepared browser evidence recorder be reused across sites without coupling it to Footwork's browser launcher or changing the authority of an existing driver?
Hypothesis: an injected tab/CDP interface, explicit allowed origin, and caller-owned domain lifecycle can collect bounded evidence independently of browser launch and model judgment.
Alternatives: the Symbolic prototype depends on its exact origin, output layout, or browser state and cannot support another site safely without a new control path.
Test: generalize the standalone ESM recorder under tools/browser-inspection; exercise two synthetic origins and rejected origin changes, numeric tab identities, redirect reuse, event paging/eviction, redaction, failure draining, and artifact hashes using mocks only.
Predicts: the same recorder supports both authorized synthetic origins, rejects a change outside the declared origin, preserves target identity and redirect evidence, redacts before writes, and needs no browser attach, provider call, install, or driver/gate modification.
Against: either synthetic origin needs site-specific core code, outside-origin body retrieval occurs, target identities merge, a sentinel credential reaches disk, or collection bypasses the injected driver boundary.
Refs: tools/browser-inspection; Best-Edit docs/research/symbolic/reconnaissance-plan.md
