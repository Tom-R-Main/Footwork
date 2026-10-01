# Browser inspection streamed-response probe

## IS1 · prediction · 2026-10-01 14:59
Question: can a page-local fetch wrapper measure streamed-response cadence without retaining response text or changing the response delivered to the page?
Hypothesis: cloning only same-origin streamed responses, consuming the clone under byte/chunk caps, and emitting size/timing metadata can record first-chunk latency and chunk cadence while leaving the application's response untouched.
Alternatives: clone consumption delays or alters the page's reader; a slow/never-ending stream outlives the capture interval; an error path leaks payload text or cross-origin metadata.
Test: build a standalone injectable probe with synthetic streaming Response fixtures for successful chunks, cross-origin exclusion, cap cancellation, fetch failure, uninstall and concurrent requests. Verify returned response bytes match the unwrapped case and sentinel contents never enter emitted records.
Predicts: only same-origin stream metadata is emitted, measured chunk count/bytes and bounded timings are correct, capped streams report truncation and cancel, uninstall stops new interception, and application-visible bytes are unchanged.
Against: sentinel content reaches a record, a cross-origin stream is cloned or reported, a reader remains active after cap/uninstall, or the page response differs from control.
Refs: tools/inspection-transport/stream-probe.mjs; Best-Edit output/symbolic-recon/inject/recon.js

## ISU1 · update · 2026-10-01 15:05
Resolves: IS1 = held
Observed: eight stream-probe tests passed; the complete browser-inspection, experiment and transport suite passed 52 tests. Synthetic same-origin SSE/NDJSON streams preserved application-visible bytes while emitting only timing/byte metadata. Cross-origin and ordinary JSON responses were ignored; cap and stop cancelled the cloned reader; the in-page source was idempotent and reinstallable after drain. The artifact writer stripped sentinel values, refused a sealed run, and its artifact was included in a mocked recorder manifest. The Footwork notebook checker passed after the original-owned entries were completed.
Inferred: the probe supplies a bounded metadata-only sidecar that can be sealed with the existing recorder. Synthetic equality does not prove that cloning has zero effect on application buffering or timing, or that the Browser plugin permits the same injection and drain behavior live.
Next: calibrate on a synthetic page through the actual permitted browser bridge, then use a bounded Symbolic workflow only if it stays within the original browser lane and the result includes probe dropped/active status.
Refs: tools/inspection-transport/stream-probe.test.mjs; tools/inspection-transport/README.md

## ISS1 · summary · 2026-10-01 15:05
Established: a standalone stream-cadence sidecar emits no response values and can write a private, manifest-hashed metadata artifact before recorder stop.
Uncertain: live injection, streams begun before installation, cached original fetch references, workers, cross-call continuity and any behavioral perturbation remain unverified.
Decision: offer the sidecar to the original Symbolic audit as an optional calibration; keep Claude's richer raw-preview recorder separate and private for fixture-only runs.
Refs: tools/inspection-transport/stream-probe.mjs; Best-Edit output/symbolic-recon/COLLABORATION.md
