# Browser inspection streamed-response probe

## IS1 · prediction · 2026-10-01 14:59
Question: can a page-local fetch wrapper measure streamed-response cadence without retaining response text or changing the response delivered to the page?
Hypothesis: cloning only same-origin streamed responses, consuming the clone under byte/chunk caps, and emitting size/timing metadata can record first-chunk latency and chunk cadence while leaving the application's response untouched.
Alternatives: clone consumption delays or alters the page's reader; a slow/never-ending stream outlives the capture interval; an error path leaks payload text or cross-origin metadata.
Test: build a standalone injectable probe with synthetic streaming Response fixtures for successful chunks, cross-origin exclusion, cap cancellation, fetch failure, uninstall and concurrent requests. Verify returned response bytes match the unwrapped case and sentinel contents never enter emitted records.
Predicts: only same-origin stream metadata is emitted, measured chunk count/bytes and bounded timings are correct, capped streams report truncation and cancel, uninstall stops new interception, and application-visible bytes are unchanged.
Against: sentinel content reaches a record, a cross-origin stream is cloned or reported, a reader remains active after cap/uninstall, or the page response differs from control.
Refs: tools/inspection-transport/stream-probe.mjs; Best-Edit output/symbolic-recon/inject/recon.js
