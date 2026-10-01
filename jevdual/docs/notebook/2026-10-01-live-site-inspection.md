# Live public-site inspection calibration

## LI1 · prediction · 2026-10-01 15:45
Question: do the Footwork capture and envelope helpers retain useful evidence across genuinely different public browser flows?
Hypothesis: a disposable Chromium context can produce sealed, gap-accounted packets for a client-local TodoMVC edit, a public GraphQL explorer query, and a public WebSocket echo exchange; structural parsers will identify applicable GraphQL requests and classify non-application echo frames without leaking sent text.
Alternatives: browser/CDP attachment cannot satisfy the recorder bridge, target websites change or block automation, or the parsers assume request/transport shapes these real sites do not emit.
Test: first inspect sites with cached Playwright CLI; then run bounded, unauthenticated browser trials with one CDP session per site, exact-origin capture, step markers, visible state and readback; save private run artifacts under Footwork output. Use only public demo data and an inert unique text fixture.
Predicts: at least two of three trials yield sealed packets with action and network intervals, TodoMVC demonstrates persisted client state without a corresponding write API, and any parser mismatch is visible as unknown/unavailable rather than a fabricated named operation or event.
Against: fewer than two sealed packets, a synthetic fixture value appears in a shareable metadata report, a capture gap is hidden, or the tool claims server persistence from TodoMVC's client-local readback.
Refs: tools/browser-inspection/capture.mjs; tools/inspection-transport; tools/inspection-experiments/SITE-INSPECTION.md

## LI2 · prediction · 2026-10-01 15:59
Question: why did the live journal retain data-URL content and a challenge-path token despite URL redaction?
Hypothesis: `safeUrl` assumes an HTTP-style URL and its opaque-segment check only catches long uninterrupted word characters; rejecting non-network schemes and long mixed-token path segments will prevent both observed leaks without erasing normal route paths.
Alternatives: the values come from a different serialization path, or the required redaction would erase too much endpoint structure.
Test: add a minimal regression in the recorder redaction tests for `data:`, `blob:`, an HTTP challenge segment with punctuation, and ordinary/static paths; change only `safeUrl`, then rerun the focused and combined suites.
Predicts: synthetic payload sentinels no longer appear in sanitized URLs, while normal `/projects/...` and static asset paths still classify as URLs.
Against: a sentinel remains, common route paths are classified as non-network, or journal serialization bypasses `safeUrl` for the observed request events.
Refs: output/inspection-public-smoke/todo-20261001195227-bb65428d; output/inspection-public-smoke/graphql-20261001195239-ff5bdaf8; tools/browser-inspection/redaction.mjs
