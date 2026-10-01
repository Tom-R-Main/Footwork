# Live public-site inspection calibration

## LI1 · prediction · 2026-10-01 15:45
Question: do the Footwork capture and envelope helpers retain useful evidence across genuinely different public browser flows?
Hypothesis: a disposable Chromium context can produce sealed, gap-accounted packets for a client-local TodoMVC edit, a public GraphQL explorer query, and a public WebSocket echo exchange; structural parsers will identify applicable GraphQL requests and classify non-application echo frames without leaking sent text.
Alternatives: browser/CDP attachment cannot satisfy the recorder bridge, target websites change or block automation, or the parsers assume request/transport shapes these real sites do not emit.
Test: first inspect sites with cached Playwright CLI; then run bounded, unauthenticated browser trials with one CDP session per site, exact-origin capture, step markers, visible state and readback; save private run artifacts under Footwork output. Use only public demo data and an inert unique text fixture.
Predicts: at least two of three trials yield sealed packets with action and network intervals, TodoMVC demonstrates persisted client state without a corresponding write API, and any parser mismatch is visible as unknown/unavailable rather than a fabricated named operation or event.
Against: fewer than two sealed packets, a synthetic fixture value appears in a shareable metadata report, a capture gap is hidden, or the tool claims server persistence from TodoMVC's client-local readback.
Refs: tools/browser-inspection/capture.mjs; tools/inspection-transport; tools/inspection-experiments/SITE-INSPECTION.md
