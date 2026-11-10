# Pinned Lightpanda CI asset recovery

## LAR1 · prediction · 2026-11-09 21:58
Hypothesis: the installed Linux browser CI lane fails before qualification because its pinned nightly GitHub asset was replaced or removed; a checksum-verified durable source for the same bytes, or an explicitly recorded stable release replacement, restores provisioning without weakening executable identity checks.
Test: inspect the failed CI receipt and upstream release metadata, verify the selected download digest before execution, update only the provisioner and necessary artifact provenance/contracts, then run focused offline contract tests and the existing installed CI qualification.
Predicts: the previous asset URL returns not found; the replacement provisioner obtains exactly the declared binary and retains checksum refusal. Browser qualification either passes or reveals a separate version compatibility failure without silently floating to nightly.
Against: the asset remains available with the expected digest, the proposed alternate source changes bytes without a new pin, or the replacement passes download but fails the existing browser behavior contracts.
Refs: .github/workflows/cdp-observation.yml; GitHub Actions run42746239548; python/jevdual/effectors/lightpanda/artifacts.py
