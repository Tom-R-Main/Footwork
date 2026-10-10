# Fresh dependency installation and setup

## UI1 · prediction · 2026-10-10 16:34
Hypothesis: the current pure wheel and pinned driver seams resolve as binaries in a fresh macOS arm64 environment without borrowing installed dependencies or compiling Rust, and the installed capability worker remains usable.
Test: U1 empty-cache default Python3.14 and Python3.12 dependency installations, consistency/origin probes and owned real native consumer flow on a supported profile.
Predicts: at least one profile resolves full declared dependencies, all product/dependency imports originate fresh environment or stdlib/system frameworks, and actual installed append/restart-token/report evidence passes. Any unsupported profile is explicitly retained.
Against: no profile can resolve pinned binary dependencies, an undeclared runtime prerequisite is needed, code needs source/borrowed environment or effect/recovery/report semantics regress.
Refs: docs/experiments/U1-clean-installation.md; results/capability-packaging-20261010/report.md

## UIU1 · update · 2026-10-10 16:36
Observed: both v1 fresh environments are created with system-site disabled, but install stops before resolution because the installed uv rejects combining --only-binary with --no-build. No dependency/runtime result is established. Reference review recommends isolated binary-only installation, structured doctor blockers/strict exit and exact emitted MCP startup checks. It also flags newer Cua doctor destructive cleanup and an incorrect newer browser-use platform marker; neither will be adopted.
Next: retain v1, use --only-binary :all: alone (same no-source-build policy), freeze and run separate v2 profiles. Reproduce doctor prerequisite reporting before adding opt-in strict readiness.
Refs: output/u1-py314-v1/install.stderr.log; output/u1-py312-v1/install.stderr.log; local reference Cua doctor.rs571; open-codex-computer-use install-config-helper.mjs613

## UI2 · prediction · 2026-10-10 16:36
Hypothesis: structured prerequisite blockers and an opt-in strict exit make incomplete installs diagnosable without mistaking diagnostic success for operational readiness or granting permissions.
Test: public doctor with missing/incompatible dependency or permission/platform/scope prereqs, unknown ledger and normal supported profile; compare diagnostic0 vs strict1, inspect runtime provenance, and require actual emitted MCP command plus bind for resource qualification.
Predicts: strict mode refuses incomplete/unknown prerequisites, normal diagnostics retain their behavior, no resource/input/permission/journal mutation occurs, and prerequisite status never certifies window identity, effects or job completion.
Against: false prerequisite-met output, strict mode accepts a blocker or doctor starts apps/requests permissions/reconciles; startup is checked with a reconstructed command instead of emitted configuration.
Refs: docs/experiments/U1-clean-installation.md; python/jevdual/capability/setup.py; local Cua structured probe mechanism and open-codex-computer-use startup probe
