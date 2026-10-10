# Fresh dependency installation and setup

## UI1 · prediction · 2026-10-10 16:34
Hypothesis: the current pure wheel and pinned driver seams resolve as binaries in a fresh macOS arm64 environment without borrowing installed dependencies or compiling Rust, and the installed capability worker remains usable.
Test: U1 empty-cache default Python3.14 and Python3.12 dependency installations, consistency/origin probes and owned real native consumer flow on a supported profile.
Predicts: at least one profile resolves full declared dependencies, all product/dependency imports originate fresh environment or stdlib/system frameworks, and actual installed append/restart-token/report evidence passes. Any unsupported profile is explicitly retained.
Against: no profile can resolve pinned binary dependencies, an undeclared runtime prerequisite is needed, code needs source/borrowed environment or effect/recovery/report semantics regress.
Refs: docs/experiments/U1-clean-installation.md; results/capability-packaging-20261010/report.md
