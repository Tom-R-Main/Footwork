# Browser protocol envelope inspection

## PE1 · prediction · 2026-10-01 15:35
Question: can a capture-time parser reveal useful realtime workflow structure without retaining WebSocket message content?
Hypothesis: strict protocol recognition plus an explicit event-name allowlist can extract Phoenix, GraphQL WebSocket and Socket.IO envelope metadata while discarding topic identifiers, operation payloads and unknown frames.
Alternatives: protocol envelopes are too varied for a bounded parser, or seemingly structural fields carry private values into output.
Test: build a standalone offline parser and synthetic tests with normal, malformed, oversized, binary and secret-bearing frames; leave the active browser recorder unchanged.
Predicts: known protocol and allowed event names, direction, timestamp and byte count survive; dynamic topic suffixes, payload values and unlisted names do not; invalid frames are classified without throwing or persisting raw text.
Against: any synthetic secret sentinel enters serialized output, invalid input produces a named event, or a known supported envelope is misclassified.
Refs: tools/inspection-transport; devtools-protocol/types/protocol.d.ts; Best-Edit output/symbolic-recon/static/STATIC-READ.md
