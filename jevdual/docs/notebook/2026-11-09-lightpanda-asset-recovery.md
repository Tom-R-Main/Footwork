# Pinned Lightpanda CI asset recovery

## LAR1 · prediction · 2026-11-09 21:58
Hypothesis: the installed Linux browser CI lane fails before qualification because its pinned nightly GitHub asset was replaced or removed; a checksum-verified durable source for the same bytes, or an explicitly recorded stable release replacement, restores provisioning without weakening executable identity checks.
Test: inspect the failed CI receipt and upstream release metadata, verify the selected download digest before execution, update only the provisioner and necessary artifact provenance/contracts, then run focused offline contract tests and the existing installed CI qualification.
Predicts: the previous asset URL returns not found; the replacement provisioner obtains exactly the declared binary and retains checksum refusal. Browser qualification either passes or reveals a separate version compatibility failure without silently floating to nightly.
Against: the asset remains available with the expected digest, the proposed alternate source changes bytes without a new pin, or the replacement passes download but fails the existing browser behavior contracts.
Refs: .github/workflows/cdp-observation.yml; GitHub Actions run42746239548; python/jevdual/effectors/lightpanda/artifacts.py

## LARU1 · update · 2026-11-09 22:01
Observed: run 42746239548 and a fresh asset lookup return HTTP 404 for asset 694146173. The published stable 1.0.3 Linux asset 712768846 downloads successfully and its 77,403,464 bytes match the upstream SHA256 53eb34da09159dcf8f04865dbfe3e63e9a652062684495aa7ced5ddd7c82e8b0. The release tag currently resolves to b8e234a77259283ff2653d5cc5900249d1d2cea9; upstream does not enable GitHub immutable-release protection. Focused offline contracts pass (101 passed, 6 browser tests deselected), Ruff and notebook validation pass.
Inferred: the failed lane stopped at external artifact provisioning, before browser qualification. Pinning the stable asset ID and digest restores reproducible provisioning; release deletion can still cause an explicit failure. No alternate published asset for the removed bytes was identified in upstream release metadata.
Next: run the installed Linux browser qualification in CI before merging; local macOS cannot execute this Linux binary. LAR1 remains open until that result.
Refs: output/lightpanda-asset-recovery/release-metadata.json; output/lightpanda-asset-recovery/focused-pytest.txt; https://github.com/lightpanda-io/browser/releases/tag/1.0.3

## LARS1 · summary · 2026-11-09 22:01
Established: Linux provisioning, runtime artifact discovery and the public CLI contract now share the stable 1.0.3 byte pin. The downloaded digest was verified independently before execution; no checksum or custody check was removed. macOS asset identity is unchanged.
Uncertain: installed Linux browser compatibility awaits the existing hosted CI lane.
Decision: hand off the minimal pin change for the final CI candidate; retain the existing browser tests as the adoption gate.
Refs: e7e61ff; .github/workflows/cdp-observation.yml; python/jevdual/effectors/lightpanda/artifacts.py; tests/test_lightpanda_cli.py
