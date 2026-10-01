# Offline inspection experiments

## IE1 · prediction · 2026-10-01 14:28
Question: can two sealed browser recordings support useful controlled comparisons without presenting temporal association as causal proof or leaking captured values into a shareable report?
Hypothesis: an offline comparator over verified journals can pair named steps, compare endpoint and body-shape fingerprints, and carry capture gaps forward as explicit limits without reading browser state or emitting payload values.
Alternatives: request identity and redirect reuse make per-step comparison ambiguous; a derivative digest or missing capture interval can be mistaken for proof of absence; shape comparison exposes private values.
Test: build a standalone Footwork comparison tool against synthetic sealed runs with changed endpoints, redirects, shapes, repeated background requests, missing steps, gaps, and tampered manifests.
Predicts: matching steps show added or removed endpoint fingerprints and shape changes, duplicate/background traffic remains visible as counts, missing or gapped evidence is marked inconclusive, tampered runs are refused, and synthetic secret sentinels never appear in report output.
Against: a tampered packet is accepted, a missing/gapped step is reported as absent behavior, redirect hops collapse into a fabricated single effect, or a sentinel from a recorded URL or body enters the output.
Refs: tools/inspection-experiments; tools/browser-inspection/summarize.mjs
