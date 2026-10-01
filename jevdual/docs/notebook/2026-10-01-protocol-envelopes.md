# Browser protocol envelope inspection

## PE1 · prediction · 2026-10-01 15:35
Question: can a capture-time parser reveal useful realtime workflow structure without retaining WebSocket message content?
Hypothesis: strict protocol recognition plus an explicit event-name allowlist can extract Phoenix, GraphQL WebSocket and Socket.IO envelope metadata while discarding topic identifiers, operation payloads and unknown frames.
Alternatives: protocol envelopes are too varied for a bounded parser, or seemingly structural fields carry private values into output.
Test: build a standalone offline parser and synthetic tests with normal, malformed, oversized, binary and secret-bearing frames; leave the active browser recorder unchanged.
Predicts: known protocol and allowed event names, direction, timestamp and byte count survive; dynamic topic suffixes, payload values and unlisted names do not; invalid frames are classified without throwing or persisting raw text.
Against: any synthetic secret sentinel enters serialized output, invalid input produces a named event, or a known supported envelope is misclassified.
Refs: tools/inspection-transport; devtools-protocol/types/protocol.d.ts; Best-Edit output/symbolic-recon/static/STATIC-READ.md

## PEU1 · update · 2026-10-01 15:37
Resolves: PE1 = held
Observed: five synthetic parser tests passed for Phoenix array/object, GraphQL WebSocket, basic Socket.IO, unknown names, binary, malformed and oversized frames. Secret-bearing payload and topic suffix sentinels did not enter serialized results. The combined inspection-transport and inspection-experiments suites passed 27 tests; the notebook checker passed.
Inferred: a fixed-schema parser can add useful structural timing to a future capture without persisting tested payload values. Synthetic conformance does not prove Symbolic's live wire format or completeness of a real CDP feed.
Next: hand the optional parser to the original browser driver for one bounded calibration; compare event counts and drop signals before using it in workflow claims.
Refs: tools/inspection-transport/protocol-envelope.test.mjs; tools/inspection-experiments/SITE-INSPECTION.md

## PES1 · summary · 2026-10-01 15:37
Established: an isolated, offline-tested parser can recognize selected realtime envelopes and retain allowlisted event names, direction, timing and byte counts while omitting message content.
Uncertain: live Symbolic protocol, worker/target coverage, parser recognition rate and integration with the original recorder remain unverified.
Decision: leave browser driving and recorder integration with the original audit; use the generic evidence-led site-inspection guide for future sites.
Refs: tools/inspection-transport/protocol-envelope.mjs; tools/inspection-experiments/SITE-INSPECTION.md
