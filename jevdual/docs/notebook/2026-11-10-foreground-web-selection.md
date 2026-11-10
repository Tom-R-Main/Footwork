# Explicit foreground web selection edits

## WSR1 · prediction · 2026-11-10 18:15
Hypothesis: an explicit UTF-16 selected-range edit can safely insert before Suno's AX terminal LF without normalizing it, by requiring exact independent selection and selected-text evidence and preserving the complete raw prefix and suffix in the expected postcondition.
Test: public CLI simulated-Mac scenarios for zero-length insertion before LF, nonempty selection including supplementary Unicode, stale selection/value/identity, unreadable selected text, invalid or unsupported options before binding, uncertain single dispatch, and exact full-value receipts including truncation and trailing-whitespace differences.
Predicts: only an already matching range and selected text permit one positively paced focus-guarded text call; no Select All is sent; exact full readback can confirm preserved prefix/suffix while contradictory, unavailable or changed-identity readback cannot confirm. Existing whole-field replacement still refuses an unselected LF.
Against: a stale or partial selection dispatches, a UTF-16 split is accepted, an uncertain input retries, a preview/whitespace-equivalent mismatch confirms, or the ordinary full-field guard changes.
Refs: docs/notebook/2026-11-10-suno-end-to-end.md; output/suno-20261110/lyrics-parameterized-observation.json
