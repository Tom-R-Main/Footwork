# Foreground intent refusal diagnostics

## FID1 · prediction · 2026-11-11 03:04
Hypothesis: current native foreground activation refusals discard the SDK's bounded structured reason, preventing diagnosis even though application input correctly remains withheld.
Test: public CLI simulated-Mac foreground click receives exact-window activation refusal with structured code/status/request acceptance and observed identity mismatch. Assert retained sanitized metadata identifies the failing checks without any application input, retry or raw private strings. Cover wrong/malformed identity, unknown strings and existing successful activation contracts.
Predicts: baseline has no foreground-intent diagnostic; a whitelist-only record carried through existing native_readback preserves useful reason/match booleans while every original gate and no-input refusal remains unchanged.
Against: diagnostic changes activation behavior, dispatches input after refusal, leaks raw text/error/URL/title/foreign identities, or guesses missing/malformed observations as matching.
Refs: results/foreground-intent-diagnostics-20261111/

## FID2 · update · 2026-11-11 03:07
Resolves: FID1 = held
Observed: both public CLI baseline cases lacked native_readback diagnostics. The repair retains a finite whitelist record through existing NativeEffect/session metadata; public CLI cases now report code/status/acceptance and target-match booleans with one activation request and no application input. Four additional wrong-identity/malformed/unknown/type cases preserve unknowns and omit private strings. All 756 focused native/session/posture/authority/CLI/contract tests pass; Ruff, notebook and diff checks pass.
Next: freeze source for one parent-operated existing public command, then inspect the retained diagnostic. No activation guard change or SDK rebuild is justified by these simulated results.
Refs: results/foreground-intent-diagnostics-20261111/baseline.txt; results/foreground-intent-diagnostics-20261111/scenarios.txt; results/foreground-intent-diagnostics-20261111/focused.txt

## FID3 · summary · 2026-11-11 03:07
Established: native foreground-intent refusal retains known pinned code/status enums, strict acceptance/window booleans, requested identity and observed match booleans. Raw tool/error text, arbitrary strings, URLs/titles and foreign identity values are omitted. Failed intent still stops before native activation/application input; successful exact-activation rules and downstream native focus checks are unchanged.
Uncertain: the worker made no live SDK/UI calls; no actual activation conflict cause is inferred. Unknown/new code strings are labeled unrecognized rather than copied. Diagnostic metadata is not action-success or no-global-effect proof; activation itself may have been attempted before refusal.
Decision: close this instrumentation-only package with 756 focused passing checks, no SDK/runtime changes, automatic retries, installs, network or guard bypass. Parent owns the single live diagnostic invocation.
Refs: results/foreground-intent-diagnostics-20261111/report.md
