# Journal-validated completion and packaging

## HC1 · prediction · 2026-10-10 15:38
Hypothesis: checking structured host reports against the full durable task ledger and publishing only a deterministic summary prevents unknown attempts from becoming completed, independent of matching text or optimistic raw model prose.
Test: A2 public MCP/CLI adversarial and positive cases, readonly retained A1 counterexample replay, then four frozen native Codex host cases through an enforced final-output adapter.
Predicts: forged/omitted/foreign/duplicate/stale or unchecked-persistence reports are rejected; unknown never renders completed; actual all-applied reports remain usable; validator performs no input or ledger transition.
Against: any trusted completed output lacks a complete final/applied ledger, raw model prose is published on failure, validation changes operation state/effects, or qualified historical action is erased by later current text.
Refs: docs/experiments/A2-host-completion-validation.md; results/restart-agent-acceptance-20261010/report.md

## HP1 · prediction · 2026-10-10 15:38
Hypothesis: the existing pure-Python fallback can support an offline installable capability wheel without a consumer Rust toolchain or provider account, while preserving exact driver pins and the qualified operation boundaries.
Test: after HC1's adapter gate, inspect wheel contents/RECORD/license/metadata, install offline into an owned isolated target, run server/report/doctor/config outside source, and qualify installed detached worker discovery on the owned native fixture.
Predicts: installed modules and worker entry resolve from the wheel, required resources and declared dependencies are present, research/secrets/compiled caches are absent, and diagnostics explain unsupported routes or prerequisites without changing permissions/configuration.
Against: runtime resolves repository source, wheel omits required data/dependencies, consumer must compile Rust, broadening imports changes driver/model semantics, forbidden files ship, or doctor creates/changes a resource.
Refs: docs/experiments/A2-host-completion-validation.md; pyproject.toml; python/jevdual/_native.py; local chrome-devtools-mcp artifact verifier

## HCU1 · update · 2026-10-10 16:05
Observed: Claude's read-only mailbox review identified safe no-input retries and run identity as missing cases. Amendment above narrows the trusted statement to historical effects, accepts honest host downgrades and includes refused/not_sent attempts without treating them as uncertain effects. Packaging will generate a durable per-run task ID, reused across reconnects; reusing a task explicitly means reporting its full history.  Initial focused checks exposed a test fixture blocked by a real unresolved-resource guard and a four-tool catalog assertion; no product reporting failure was established by those fixture failures.
Next: before native trials, qualify safe retry, downgrade and abrupt-owner-exit readonly cases.
Refs: docs/experiments/A2-host-completion-validation.md; output/a2-completion-checks-v1.log; Claude mailbox 1791661308184549000-claude-codex.md

## HCU2 · update · 2026-10-10 16:10
Observed: completion/MCP/service/recovery checks pass75; readonly reads work while the owner is live, after clean close and after SIGKILL with WAL retained. Retained A1 Codex optimistic claim is rejected as unknown and its original DB hash is unchanged. The first update heading reused HC1 and omitted required field labels; this commit repairs formatting without changing the recorded observation. Offline uv resolution lacked cached cross-version metadata; only the root dependency declaration for already-resolved MCP2.1.1 was synchronized, preserving the full resolved package graph.
Next: run four native structured Codex sessions on frozen code, then open packaging if the published adapter gate qualifies.
Refs: tests/test_capability_completion.py; output/a2-retained-replay.json; scripts/capability_completion_trial.py
