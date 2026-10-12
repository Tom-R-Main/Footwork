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

## UFU1 · update · 2026-10-12 14:19
Observed: the old Automation-denied main-boundary scenario leaves the exact owned AX window open; the new helper closes that window and preserves a same-name other-path window. Root reviews the worker diff and69focused helper/onboarding/packaging checks pass, with Ruff and notebook valid. Source3d0984d includes review notes on synchronous AX read deadlines, second-SIGINT cleanup protection and bounded actual file snapshots. Both final packet builds match14members and03dc0079; installed3.12/3.14 help/import/member/provenance preparation smokes pass without Git, stopping at an intentional uv stub. Claude approves initial23e5e16f artifact; final03dc0079 confirmation is pending. Guest unlock, SIP/prerequisite provenance and bounded awake hold are observed; no v4 guest effect or permission reset has occurred.
Changes: initial developer validation used a stale editable environment, then a relative source path failed the subprocess CLI check; absolute worktree PYTHONPATH corrected the probe without product/test changes. Guest close-preference defaults key is absent and GUI search yields no result; effective preference remains unverified rather than inferred off.
Next: complete final Claude artifact confirmation, transfer pristine v4, cold-install new guest dependencies, obtain explicit guest Terminal-only reset approval, then capture denial/grant/restart and installed automatic-cleanup evidence. UF1/UF2/UF3 remain open pending their real guest boundary.
Refs: results/onboarding-fixture-v4-preparation-20261012; output/u2-fixture-v4-dev/baseline-automation-behavior.txt; output/u2-packet-v4-final; Claude1791828646123834000; U3-packet-v4-permission-journey.md

## UFU2 · update · 2026-10-12 14:20
Observed: Claude confirms exact03dc0079 artifact for U3 but identifies an N3 API semantic error: AXUIElementSetMessagingTimeout applies only to the supplied element, not new equal application references created by product lookup. Apple documentation independently confirms the system-wide element is required for this process's global AX timeout and setting0 resets its default. Current pre/post checks refuse late identities but the prior inferred one-second native RPC bound is not established. No v4 guest effect/reset has occurred.
Inferred: the process-local system-wide timeout, scoped to identity collection and reset to default during teardown, should cover those internal references without changing OS permissions; this remains under existing UF2 and needs corrected boundary verification before a new freeze.
Next: correct the setter scope and cleanup restoration, retain old artifacts and refreeze the reviewed qualification candidate. Do not claim restoring an unknown previous custom timeout.
Refs: Claude1791829172719781000; https://developer.apple.com/documentation/applicationservices/1459345-axuielementsetmessagingtimeout; source3d0984d; UF2
