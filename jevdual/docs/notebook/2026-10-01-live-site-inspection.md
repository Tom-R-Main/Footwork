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

## LI3 · prediction · 2026-10-01 16:05
Question: can the same isolated recorder explain a multi-page commercial site's public conversion flow without mistaking marketing copy for product behavior?
Hypothesis: a public get-started page behaves as a demo-request form with required-field validation, while pricing and product navigation lead to public informational pages; the existing capture will preserve step-linked navigation and form-validation evidence without submitting contact data.
Alternatives: the form is a self-service signup, navigation relies on a mechanism the recorder misses, or the page's background requests create enough gaps to make even public-flow ordering uncertain.
Test: add a bounded, privately configured lead-generation scenario to the disposable Playwright runner, load and settle before capture, snapshot the blank form, press Submit without data, inspect focus or validation, follow pricing and product links, and record rendered route/readback and sealed coverage. Keep all site-specific configuration and artifacts private.
Predicts: a sealed packet with step/action/navigation ordering, no form POST caused by the blank submission, and public route readbacks; the written product note separates these observations from documentation claims and ExecuFunction hypotheses.
Against: a contact request is sent on blank submit, navigation/readback fails while the runner reports success, the packet has unreported gaps, or any shareable summary contains a dynamic URL/token.
Refs: tools/inspection-experiments/live-public-smoke.mjs

## LI4 · update · 2026-10-01 16:14
Resolves: LI1 = held
Observed: three public trial types produced hash-verified sealed packets with step intervals. The client-local item survived reload without a corresponding server write. The named public GraphQL query returned HTTP 200 and an allowed operation envelope; that packet reports two body-unavailable gaps. The echo packet recorded four unnamed plain-text frames and accessibility-snapshot readback. The combined focused suite later passed 63/63.
Inferred: the bridge can calibrate heterogeneous public flows, but a sealed packet alone does not prove full target or worker coverage, and unknown frame protocols remain unknown.
Next: LI2 and LI3; keep private run artifacts out of Git.
Refs: output/inspection-public-smoke/; tools/inspection-experiments/coverage.mjs

## LI5 · update · 2026-10-01 16:14
Resolves: LI2 = held
Observed: the redaction regression rejects synthetic data/blob URLs and long mixed-token path segments while preserving ordinary routes. A later public lead-generation packet contains four non-network URL placeholders and no raw data-image URL. The combined focused suite passed 63/63.
Inferred: the observed non-network leak path is closed. The exact earlier challenge response did not recur, so the mixed-token path repair has synthetic rather than repeated live confirmation.
Next: retain the sanitizer regressions and inspect future private packet audits for new URL shapes.
Refs: tools/browser-inspection/redaction.mjs; output/inspection-public-smoke/leadgen-20261001200952-d7a9c3e1/

## LI6 · update · 2026-10-01 16:14
Resolves: LI3 = held
Observed: after correcting a hidden repeated-link locator and replacing an unreliable focus assumption with native required-field validity, the private-config public funnel trial completed blank form validation and two navigations with rendered readback. No contact-form POST appeared in the blank-submit interval; one third-party analytics POST did. The packet has 733 events, zero reported gaps, two orphan terminal events and twelve unclosed requests, so the coverage audit labels it limited.
Inferred: action-linked public UX evidence is achievable without filling or submitting contact details; a POST count alone would have falsely implied form submission. The packet does not establish any authenticated product behavior.
Next: keep site-specific configuration and evidence private; reuse only the generic runner and coverage lessons.
Refs: tools/inspection-experiments/live-public-smoke.mjs; output/inspection-public-smoke/leadgen-20261001200952-d7a9c3e1/

## LI7 · summary · 2026-10-01 16:14
Established: isolated public-browser calibration exercised client-local persistence, named GraphQL, plain-text WebSocket echo, and a lead-generation form/navigation flow. The generic runner now takes a private site configuration for the last case. Hash-verified packets, action intervals, native validity checks, accessibility readback and lifecycle audits make the observations reviewable. The combined focused suite passed 63/63 and the notebook check passed.
Uncertain: browser targets outside the selected page, workers, stream content, authenticated application behavior, and network requests outside the capture interval remain unmeasured. Two network lifecycle orphans limit the final public packet despite zero reported gaps.
Decision: keep the generic Footwork instrumentation; store named-site findings in private research systems, not versioned GitHub-facing code or documentation.
Refs: tools/inspection-experiments/live-public-smoke.mjs; tools/inspection-transport/playwright-cdp-bridge.mjs; output/inspection-public-smoke/
