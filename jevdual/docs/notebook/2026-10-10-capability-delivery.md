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

## DPU2 · update · 2026-10-10 18:20
Resolves: DP2 = held
Observed: frozen2ea6ff9 final wheel checks pass on3.12.6/3.14.7 and separate empty-cache dependency profiles each resolve115binaries with exactly U1's selected versions and strictdoctor0. ZIP comparison proves all runtime/resource bytes unchanged, with only METADATA/RECORD differing. The existing26.3 parser is direct; lock freshness passes offline and58 affected tests pass. Full offline lock regeneration initially lacked cached metadata; only the existing resolution's two direct dependency entries were updated. An exploratoryv3 wheel check ran before final metadata staging due a relative-path staging error; frozenv4 checks replace that as final artifact evidence and v3 remains retained. Claude confirms both review follow-ups closed and approves2ea6ff9.
Next: consolidate the qualified source and records into one draft PR, observe hosted CI and address any actionable feedback. DP1's local entry-point boundary is checked; hosted Linux/macOS execution is still unavailable here.
Refs: results/capability-delivery-20261010; Claude mailbox1791670667746229000; output/delivery-parser-lock-check.log

## DPS1 · summary · 2026-10-10 18:20
Established: standalone consumer artifact/CLI checks, two final fresh dependency profiles, direct parser contract, isolated automation guidance and independent final review pass. Native runtime bytes and all selected dependency versions match U1, whose original limits remain visible.
Uncertain: hosted CI execution is pending at this preparation boundary; fresh-OS/TCC onboarding, direct worker __main__ diagnostic origin and arbitrary app/persistence/whole-goal behavior remain unqualified.
Decision: hand off the clean committed source and sanitized records to one draft PR and finish its hosted-check/review loop. Registry publication and merging remain separate decisions. Native input and persistent sleep/lock settings were not changed.
Refs: results/capability-delivery-20261010/report.md; 2ea6ff9
