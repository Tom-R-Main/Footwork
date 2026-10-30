# Pre-header transport attribution and qualification

## PH1 · prediction · 2026-10-30 00:15
Hypothesis: Chrome transport replays a plain form POST after the fixture closes without response headers; Footwork dispatch itself occurs once.
Test: fresh owned loopback fixtures, direct HTTP and isolated Chrome controls; correlate native action, browser lifecycle, connection and ingress. Repeat normal, truncated and disconnect cells twice each; retain uninstrumented comparison.
Predicts: disconnect duplication can occur without Footwork while a single native activation is retained; supported response modes retain one ingress.
Against: duplication requires repeated native activation, server accounting fabricates rows, or controls cannot attribute the second request.
Refs: docs/experiments/preheader-20261030.md
