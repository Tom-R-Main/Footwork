# Browser inspection coverage diagnostics

## IC1 · prediction · 2026-10-01 14:45
Question: can a sealed CDP capture report its own observable blind spots without equating missing events with absent product behavior?
Hypothesis: a deterministic offline coverage audit over the four verified journals can separate explicit transport gaps, incomplete request lifecycles, body-policy omissions, and unobserved protocol families using only bounded metadata.
Alternatives: CDP event ordering and redirects make lifecycle gaps indistinguishable from real capture loss; an aggregate count conceals intervals where the browser recorder was paused; the report leaks private URLs or body values.
Test: build a Footwork coverage CLI with synthetic redirect, orphan, missing response, body omission, capture-gap and step-interval fixtures, then inspect two already sealed Symbolic calibration packets read-only.
Predicts: synthetic lifecycle states remain distinct, explicit gap packets are marked limited, zero-gap packets say only "no reported gaps," output excludes sentinel values, and the two calibration packets reproduce their manifest-verified gap-count distinction without browser interaction.
Against: a truncated packet is labeled complete, an orphan or missing response is reported as successful behavior, redirect reuse creates a false duplicate, secret sentinels reach output, or a tampered run is analyzed.
Refs: tools/inspection-experiments/coverage.mjs; tools/browser-inspection/summarize.mjs; devtools-protocol pdl/domains/Network.pdl

## ICU1 · update · 2026-10-01 14:48
Resolves: IC1 = held
Observed: 38 offline browser-inspection and inspection-experiments tests passed. The coverage tests preserve redirect hops, optional ExtraInfo, orphan responses/terminals, explicit gaps, body-policy counts, privacy sentinels and tamper rejection. Read-only analysis of manifest-verified Symbolic packets reported two explicit gaps for `projects-route-calibration-20261001/` (778 events, 146 request hops) and zero reported gaps for `cached-route-calibration-20261001/` (334 events, 50 hops). The former was marked limited; the latter was labeled only no-reported-capture-gaps. No browser action occurred in this package.
Inferred: the tool preserves the distinction between partial and gap-free recorded intervals without claiming full browser coverage or product behavior. The orphan terminal/data events in the partial packet are compatible with its truncation gap; they do not prove a Symbolic failure.
Next: use the report before paired workflow comparison, and calibrate any proposed persistent transport separately against a live bounded run.
Refs: tools/inspection-experiments/coverage.test.mjs; Best-Edit output/symbolic-recon/projects-route-calibration-20261001/manifest.json; Best-Edit output/symbolic-recon/cached-route-calibration-20261001/manifest.json

## ICS1 · summary · 2026-10-01 14:48
Established: verified private journals can produce a value-minimized capture-quality report and a protocol capability census; the two available calibration packets retain their different explicit-gap outcomes.
Uncertain: zero reported gaps cannot establish capture before attachment, worker/OOPIF coverage, unattended bridge continuity, or body completeness.
Decision: keep coverage analysis independent of the active recorder and browser lane. Prefer protocol-backed CDP evidence for a future persistent transport, with Playwright HAR as private cross-check and proxy capture reserved for measured blind spots.
Refs: tools/inspection-experiments/REFERENCE_FINDINGS.md; tools/inspection-experiments/coverage.mjs
