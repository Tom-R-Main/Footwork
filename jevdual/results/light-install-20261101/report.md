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
