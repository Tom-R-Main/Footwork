# Browser inspection evidence package

## BI1 · prediction · 2026-10-01 14:09
Question: can the prepared browser evidence recorder be reused across sites without coupling it to Footwork's browser launcher or changing the authority of an existing driver?
Hypothesis: an injected tab/CDP interface, explicit allowed origin, and caller-owned domain lifecycle can collect bounded evidence independently of browser launch and model judgment.
Alternatives: the Symbolic prototype depends on its exact origin, output layout, or browser state and cannot support another site safely without a new control path.
Test: generalize the standalone ESM recorder under tools/browser-inspection; exercise two synthetic origins and rejected origin changes, numeric tab identities, redirect reuse, event paging/eviction, redaction, failure draining, and artifact hashes using mocks only.
Predicts: the same recorder supports both authorized synthetic origins, rejects a change outside the declared origin, preserves target identity and redirect evidence, redacts before writes, and needs no browser attach, provider call, install, or driver/gate modification.
Against: either synthetic origin needs site-specific core code, outside-origin body retrieval occurs, target identities merge, a sentinel credential reaches disk, or collection bypasses the injected driver boundary.
Refs: tools/browser-inspection; Best-Edit docs/research/symbolic/reconnaissance-plan.md

Identifier correction, 2026-10-01 14:17: the notebook check found A1 already used by another package. Only the identifier was changed to BI1; the prediction text was committed before verification in cb2a814 and is unchanged.

## BIU1 · update · 2026-10-01 14:17
Resolves: BI1 = held
Observed: node --test tools/browser-inspection/*.test.mjs passed 16 offline cases, including two declared synthetic origins, numeric source identities, redirects, redaction, eviction, failed actions, duplicate-step refusal, and integrity checks. Best-Edit's sibling adapters imported successfully. These runs used mocks and synthetic files only.
Inferred: the injected recorder is portable across declared origins without launching a browser or modifying Footwork's driver and gates. This establishes the offline interface contract, not live capture fidelity.
Next: inspect the actual browser bridge on the already loaded Symbolic page; keep body capture, navigation survival, stream values and workers unverified until observed.
Refs: tools/browser-inspection/capture.test.mjs; tools/browser-inspection/summarize.test.mjs; tools/browser-inspection/README.md

## BIS1 · summary · 2026-10-01 14:17
Established: optional dependency-free ESM capture and digest tools accept an existing tab/CDP adapter, scope bodies to an explicit origin, redact before journal writes, and hash a sealed evidence packet. No browser attach, model call, install, CLI behavior change, or gate change was introduced.
Uncertain: live extension command support, body retention, long-running stream coverage, worker/OOPIF visibility and uninterrupted collection across turns remain untested. The recorder uses explicit bounded drains and does not claim continuous background subscription.
Decision: retain the reusable utilities under tools/browser-inspection and keep site-specific plans/fixtures in Best-Edit; live workflow observation follows preparation and calibration.
Refs: tools/browser-inspection; Best-Edit docs/research/symbolic/execution-runbook.md

## BI2 · prediction · 2026-10-01 14:20
Question: can continuous collection coexist with step marks and snapshots without losing cursors or sealing files before pending writes finish?
Hypothesis: serialized drain operations and fsynced journal writes, with an explicit polling lifecycle and stop barrier, can collect through long UI waits while preserving an ordered evidence packet.
Alternatives: simultaneous step and poll operations overwrite cursors or duplicate events; shutdown hashes incomplete files; the browser bridge cannot continue between tool invocations.
Test: mocked concurrent polling/mark/snapshot/stop and write barriers, followed by an observation-only live bridge calibration on the loaded Symbolic Home page. No workflow navigation or account writes are part of the live calibration.
Predicts: mocks preserve exactly-once event sequences, stop terminates polling and waits for pending writes before hashing, and the live bridge can save a marked Home snapshot and cleanly report supported or rejected observation commands.
Against: cursor regression, duplicate events, missing writes after stop, leaked credential sentinels, outside-origin body acquisition, or background operations continuing after stop. Live polling between tool invocations may be inconclusive even if the offline contract passes.
Refs: tools/browser-inspection/capture.mjs; tools/browser-inspection/capture.test.mjs
