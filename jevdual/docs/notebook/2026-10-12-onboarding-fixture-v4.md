# Onboarding fixture v4

## UF1 · prediction · 2026-10-12 13:56
Hypothesis: closing the unique fixture document by exact AXDocument identity and its AXCloseButton, with any discard button confined to its observed attached save sheet, removes the Automation grant while preserving unrelated documents.
Test: first reproduce the old cleanup limitation in boundary scenarios; cover exact-path duplicates, same-name other paths, changed identity, attached versus unrelated sheets, unsuccessful AX presses and verified window disappearance. Then run the frozen new helper on the disposable guest with Automation declined and an edited owned document; check its receipt and independent owned-resource absence.
Predicts: the exact owned window closes automatically with only existing Accessibility, no Apple Event/Automation route executes, and ambiguous/changed/unobservable targets refuse without closing another window. Cleanup remains independent of browser/listener shutdown.
Against: another window or app-level dialog is acted on, the helper claims closure without observed disappearance, leaks the owned browser/listener on AX failure, or needs an extra permission.
Refs: results/u2-independent-onboarding-20261011-v1; results/u2-independent-onboarding-20261011-v2-dev; local Arc CUA6b353039 benchmarks/workflows.py:533; Claude1791753660836044000

## UF2 · prediction · 2026-10-12 13:56
Hypothesis: separately bounded owned-browser startup readiness followed by the unchanged unique-window identity deadline classifies slow first launch without weakening resource identity.
Test: first preserve a slow-start/ambiguous-identity failing scenario against the old helper. Exercise delayed readiness, browser exit, startup timeout, missing/ambiguous windows and successful unique identity; freeze packetv4 and run its installed public path after normal Chrome verification. Keep every failure in distinct fresh run directories.
Predicts: delayed startup gets its own phase and bounded typed receipt/exit, identity ambiguity still refuses after its own deadline, a stopped browser never emits ready, and setup failures run bounded owned cleanup without traceback-only reporting.
Against: a late or foreign browser/window is adopted, ambiguous identity becomes authorized, timeout remains unclassified, or launch failure bypasses cleanup.
Refs: scripts/capability_fixture.py; local Chrome DevTools MCPf08dbe152502d66e75fa07fb2588dc0feb42bc20 src/BrowserManager.ts; UO5 in docs/notebook/2026-10-10-independent-onboarding.md

## UF3 · prediction · 2026-10-12 13:56
Hypothesis: a source-frozen packetv4 with the unchanged reviewed wheel permits a separately recorded denied-to-granted guest Terminal journey and fully automatic owned cleanup.
Test: build twice and verify exact inventory/source binding, review the artifact with Claude, then run an independently recorded guest permission journey with denied doctor/refusal, captured authorized grant, host restart, installed append/replay/report and automatic cleanup. Use the existing disposable guest only after an approved supported per-host Accessibility reset; preserve its v1/v2 evidence and label this as fresh permission state on a previously provisioned guest, not a newly cold OS.
Predicts: packet hashes repeat, denied fixture creates no resources, captured same-host grant and post-restart strict doctor pass, native oracle holds one effect/row, and cleanup confirms the exact document/browser/listener/worker without operator close or Automation grant.
Against: packet depends on runtime source/Git, grant remains uncaptured, native effect duplicates, cleanup is manual or needs extra access, or earlier failed evidence is regraded.
Refs: docs/experiments/U2-independent-onboarding.md; docs/independent-onboarding.md; results/u2-independent-onboarding-20261011-v2-dev
