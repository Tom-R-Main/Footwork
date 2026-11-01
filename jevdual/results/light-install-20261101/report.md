# Lightweight installation profiles — November 1, 2026

The base Footwork wheel now declares the light runtime dependencies. The `desktop` extra carries
pinned CUA and platform dependencies; `agent` carries pinned browser-use. Full installs request
both. The portable product wheel is the same for both profiles.

The bundle builder supports explicit `--profile light|full`. Light bundles never build or carry
CUA. Full bundles retain exact CUA pin/host checks and optionally simulator dependencies. The
installer selects the manifest's profile, refuses mismatches before environment creation, retains
binary-only installation and never falls back to compiling. Old schema-1 full bundles remain
readable. The clean-install harness checks installed dependency closure and observed profile.

Catalog and doctor report observed installed optional distributions without importing those
backends. This does not establish what extras a previous installer requested or qualify a runtime.
An absent agent dependency produces the same typed unavailable-effector family as native absence.
Current install guides and full-source/consumer CI recipes request the intended dependencies;
light macOS/Linux jobs and resolver-based installed CDP qualification are configured.

The committed LWI1 prediction preceded the new tests. Baseline wheel/profile checks fail four
assertions for the intended missing behavior; after the change, the selected packaging, optional
effector, onboarding and release-candidate group passes170 with6 skips. Ruff and the offline,
no-build lock consistency check pass. The lock transformation preserves all300 resolved package
versions and artifact hashes. Detailed commands and source-file hashes are in `verification.json`.

The parent independently installed the first candidate wheel through the real fresh-cache
binary-only resolver, observed35 installed packages without CUA/browser-use/native platform
packages, and exercised discovery/doctor and typed native absence. That earlier candidate's
identity is retained in the manifest. The final combined artifact and pinned-engine local fixture
remain the parent's qualification step; no final runtime or hosted result is asserted here.

No native delivery, guard, durable admission, uncertain-operation, typing, external engine pin,
or completion contract was changed. Full installed native runtime and small-host resource
measurements remain separate. Worker edits are uncommitted for parent integration and review.

## Parent final artifact qualification

Source `81d6985791298d151c9610bc10b1b00816137b07` produced wheel `0c777e645947f308e93b01e939eaf964dae5a6e77c81c7d4ef269e7f51d41a4a`. Its217-entry source/RECORD verification passes; all212 installed product files match. A final genuinely fresh-cache binary resolver install passed with35 packages, no desktop/agent distributions and observed profile light. Public tools/schema/doctor pass; native requests report unavailable; the installed CLI's loopback pinned-Lightpanda read preserves semantic text, field privacy, no input authority and independent bounded cleanup.

The generated light installer also succeeds offline using the project-owned cache; profile mismatch and unavailable full binary dependency controls refuse as intended. Both manifests pass hash checks and contain the same product wheel. `final-artifact-verification.json`, `final-clean-receipt.json`, `final-installed-public.json` and `verify_installed_light.py` retain this final evidence.

The combined source suite passes2848 with51 skips and66 deselections after using the exact local CUA pin in a task-owned overlay. The earlier shared-venv mismatch is retained in the [integration report](../duplicate-controls-light-install-20261101/report.md). No new hosted CI, fresh full-native install, live native delivery or small-host resource qualification is claimed.
