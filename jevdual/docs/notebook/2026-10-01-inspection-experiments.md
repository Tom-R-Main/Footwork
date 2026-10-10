# Offline inspection experiments

## IE1 · prediction · 2026-10-01 14:28
Question: can two sealed browser recordings support useful controlled comparisons without presenting temporal association as causal proof or leaking captured values into a shareable report?
Hypothesis: an offline comparator over verified journals can pair named steps, compare endpoint and body-shape fingerprints, and carry capture gaps forward as explicit limits without reading browser state or emitting payload values.
Alternatives: request identity and redirect reuse make per-step comparison ambiguous; a derivative digest or missing capture interval can be mistaken for proof of absence; shape comparison exposes private values.
Test: build a standalone Footwork comparison tool against synthetic sealed runs with changed endpoints, redirects, shapes, repeated background requests, missing steps, gaps, and tampered manifests.
Predicts: matching steps show added or removed endpoint fingerprints and shape changes, duplicate/background traffic remains visible as counts, missing or gapped evidence is marked inconclusive, tampered runs are refused, and synthetic secret sentinels never appear in report output.
Against: a tampered packet is accepted, a missing/gapped step is reported as absent behavior, redirect hops collapse into a fabricated single effect, or a sentinel from a recorded URL or body enters the output.
Refs: tools/inspection-experiments; tools/browser-inspection/summarize.mjs

## IEU1 · update · 2026-10-01 14:33
Resolves: IE1 = held
Observed: 31 offline browser-inspection and comparator tests passed. The five comparator cases cover paired count differences, redirect hops, request and response shape fingerprints, missing steps and gaps, secret sentinel exclusion, and tampered manifest rejection. The notebook checker passed. No live Symbolic capture was compared.
Inferred: sealed capture journals can support a privacy-minimized comparison of named observation intervals. The synthetic tests establish the report contract, not real-world capture completeness or causal attribution.
Next: calibrate against a real benign browser action, then compare two deliberately controlled workflow trials and document background traffic and missing evidence.
Refs: tools/inspection-experiments/compare.test.mjs; tools/inspection-experiments/ROADMAP.md

## IES1 · summary · 2026-10-01 14:33
Established: Footwork has an independent, dependency-free offline comparator that verifies packet hashes and emits paired endpoint/shape fingerprints without browser control or raw values.
Uncertain: Symbolic account workflows, live capture completeness, screenshot/DOM fidelity, and any architectural hypothesis remain untested by this work package.
Decision: keep the comparator separate from the active recorder and browser-driving lanes; use it after sealed controlled trials exist.
Refs: tools/inspection-experiments; Best-Edit output/symbolic-recon/COLLABORATION.md
