# Linux installation and runtime qualification

## L1 · prediction · 2026-10-30 00:24
Hypothesis: the portable Footwork wheel can avoid its optional Rust core on a constrained Linux consumer, but the bundle installer and runtime still require explicit native CUA and graphical-session prerequisites; pure Python does not replace CUA.
Test: inspect the cached ExecuFunction Linux image without network access, exercise consumer installation and public diagnostics, then qualify browser and native actions where the available runtime permits. Challenge missing prerequisites, incompatible wheels, stale identities, and macOS regressions.
Predicts: installation can use prebuilt wheels without a consumer compiler; missing native or desktop capabilities are reported before input dispatch rather than mislabeled as working Linux desktop support.
Against: a compiler is unavoidable for a prebuilt consumer bundle, or diagnostic success still conceals a missing action route.
Refs: docs/unified-cli.md; docs/upstream/cua-driver-build.md; scripts/build_agent_bundle.py

## L2 · exploratory · 2026-10-30 00:24
Question: which browser and native primitives in the pinned CUA Linux implementation preserve Footwork's exact-value, identity, and delivery guarantees on an available Linux desktop?
Test: inspect the pinned source and qualify the actual Linux driver before selecting platform adapters; retain unsupported capabilities and uncertain dispatch as refusals. No provider calls or cloud allocation are part of this probe.
Refs: vendor/cua-driver/PROVENANCE.md; python/jevdual/ax.py; python/jevdual/posture.py; python/jevdual/session_operations.py
