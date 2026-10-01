# Browser inspection coverage diagnostics

## IC1 · prediction · 2026-10-01 14:45
Question: can a sealed CDP capture report its own observable blind spots without equating missing events with absent product behavior?
Hypothesis: a deterministic offline coverage audit over the four verified journals can separate explicit transport gaps, incomplete request lifecycles, body-policy omissions, and unobserved protocol families using only bounded metadata.
Alternatives: CDP event ordering and redirects make lifecycle gaps indistinguishable from real capture loss; an aggregate count conceals intervals where the browser recorder was paused; the report leaks private URLs or body values.
Test: build a Footwork coverage CLI with synthetic redirect, orphan, missing response, body omission, capture-gap and step-interval fixtures, then inspect two already sealed Symbolic calibration packets read-only.
Predicts: synthetic lifecycle states remain distinct, explicit gap packets are marked limited, zero-gap packets say only "no reported gaps," output excludes sentinel values, and the two calibration packets reproduce their manifest-verified gap-count distinction without browser interaction.
Against: a truncated packet is labeled complete, an orphan or missing response is reported as successful behavior, redirect reuse creates a false duplicate, secret sentinels reach output, or a tampered run is analyzed.
Refs: tools/inspection-experiments/coverage.mjs; tools/browser-inspection/summarize.mjs; devtools-protocol pdl/domains/Network.pdl
