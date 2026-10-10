# Capability delivery preparation

## DP1 · prediction · 2026-10-10 18:08
Hypothesis: a separate dependency-free wheel installation check can protect the consumer artifact without the development environment, Rust build, native permissions or live UI.
Test: build and verify two wheels, install one without dependencies in a fresh owned environment, plant host-directory shadow modules, run the installed CLI, and check missing-journal reporting and missing-prerequisite strict exit. Wire this check into Linux and macOS CI and reuse U1's binary-only dependency installation on the macOS profiles.
Predicts: the two builds match within each interpreter, installed imports and metadata belong to the fresh environment, isolated CLI invocations ignore host-directory shadows, and unsupported prerequisites or unavailable journals cannot certify completion. CI needs no model credentials or native input.
Against: source/development dependencies are required, the installed CLI imports the planted modules, the checker accepts a false completion, or CI implicitly grants permissions or launches input.
Refs: scripts/build_capability_wheel.py; scripts/capability_clean_install.py; results/clean-installation-20261010/report.md

## DPU1 · update · 2026-10-10 18:14
Observed: frozen fc525da local artifact checks pass on3.12.6 and3.14.7 with the unchanged U1 wheel hash,58 focused tests,1473 non-browser Python tests,97 Node tests,19 Rust tests and lint/notebook checks. Claude independently rebuilt and checked the artifact and approved the accumulated change with no blockers. Review recommends declaring the strict doctor's requirement parser directly and clarifying console-script versus isolated automation paths. Hosted CI remains unexecuted.
Next: declare the already-resolved packaging parser, clarify launch guidance, qualify a separate final wheel and retain the initial artifact/results. Keep CI's existing major-tag action convention; broader path-filter optimization is nonblocking.
Refs: results/capability-delivery-20261010; Claude mailbox1791670452579982000

## DP2 · prediction · 2026-10-10 18:14
Hypothesis: making the requirement parser an explicit dependency removes its transitive-only setup assumption without changing native execution/recovery behavior or the selected dependency inventory.
Test: add packaging to project metadata/lock using existing resolution, rebuild separately, check installed CLI and wheel metadata, and run new isolated binary dependency installations for3.12/3.14. Compare all Python runtime module bytes with the prior U1 artifact, and retain that native evidence only for identical runtime modules.
Predicts: the parser is declared directly and installed in both profiles, consistency/origin gates hold with the same package versions, and all product Python runtime bytes are unchanged. Console guidance directs automated hosts to the generated -I paths.
Against: dependency resolution changes unexpectedly, new installs fail, product runtime modules differ or guidance treats the non-isolated console script as equivalent automation.
Refs: python/jevdual/capability/setup.py; pyproject.toml; uv.lock; results/clean-installation-20261010/report.md
