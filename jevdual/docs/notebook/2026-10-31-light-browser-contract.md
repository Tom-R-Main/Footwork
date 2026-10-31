# Light profile L1b: owned browser contract

## LBC1 · prediction · 2026-10-31 11:01
Question: can BrowserBridge stop speaking CUA's `call_tool` JSON wire without changing what reaches the browser or what callers read back?
Hypothesis: a typed CUA browser adapter (prepare, bind, snapshot, click, type, navigate) returning Footwork-owned reply and refusal records preserves every wire request and every WebMenu/BrowserEffect field current callers read, while carrying refusal detail (delivery, retryable), hint and next_call that the bridge drops today.
Alternatives: some caller or test depends on the raw reply dict or on `driver.call_tool` being invoked by the bridge itself, so the seam cannot move without a visible change.
Test: characterization tests that record each bridge operation's tool name and decoded arguments and its resulting effect against wire doubles, written and passing on unchanged 701fd32 first. Replies are modelled on the vendored CUA constructors: the refusal envelope (refusal.rs:238), the acknowledged-but-unknown trusted click (tools.rs:1567, detail delivery=unknown, retryable=false) and top-level hint/next_call (recovery_hint.rs). Then refactor and rerun them with the existing browser session, evidence, authority, launch, coverage, scenario and effector-boundary suites; AST check that browser_driver.py no longer calls call_tool.
Predicts: identical requests, effect words, summaries, error codes and dispatched flags before and after; the session still maps a dispatched refusal to unverifiable rather than not sent; the new fields are carried data only, never an agent-callable surface; the binding reports context, document generation and persistent target identity as unavailable.
Against: any request argument or effect field differs; a delivery-unknown refusal becomes not sent or dispatched=False; hint or next_call is rendered as a callable tool; or the binding claims persistent identity.
Refs: docs/plans/light-profile-20261030.md (L1a / L1b); python/jevdual/browser_driver.py; python/jevdual/effectors/cua.py; vendor/cua-driver/native-source.tar.gz at d5373879 (cua-driver-core/src/browser/refusal.rs, tools.rs, recovery_hint.rs)

## LBCU1 · update · 2026-10-31 11:12
Resolves: LBC1 = held
Observed: the nine characterization tests from dbd14d4 pass on base 701fd32 and on 390fda1: identical tool names, decoded arguments, effect words, summaries, error codes and dispatched flags; the CLI test still reports the delivery-unknown refusal as unverifiable, never not sent. Nine added tests fail on base and pass after: delivery/retryable/hint/next_call carried on BrowserEffect, payload kept read-only with extension fields, unreadable replies without status, BrowserBinding with connection-scoped tabs and no context, document generation or persistent identity, no call_tool or dispatch tool name left in browser_driver.py, and a non-CUA operations object accepted. Full suite 2512 passed against 2503 on base, with the same single environmental failure (cua-driver version pin vs the borrowed venv's pre-cleanup2 wheel).
Inferred: the bridge no longer depends on CUA's wire, so L3a can supply a second BrowserOperations without touching the bridge's authority, posture or effect logic. Edge difference, deliberate: an empty refusal message now falls back to the reply text in attach/observe errors, as act() already did.
Next: hosted CI on the PR. Live CUA browser tests, an installed wheel and Linux were not run here. The CLI renders none of the new fields yet; whether a delivery=unknown refusal should be worded differently in receipts is a separate, predicted change.
Refs: results/light-browser-contract-20261031/report.md; tests/test_browser_contract.py; source 390fda1

## LBCS · summary · 2026-10-31 11:12
Established: BrowserBridge acts only through the Footwork-owned BrowserOperations protocol; the CUA adapter sends unchanged requests and translates replies without dropping fields. The effector's unknown-delivery and recovery advice are now retained as data, and the binding states which identity it lacks.
Uncertain: live CUA browser behavior on this branch; whether other CUA browser replies carry fields the bridge should read. Native records remain SDK records behind L1a by design.
Decision: ship L1b as its own PR after hosted CI. Next is L3a, a direct-CDP BrowserOperations, opt-in and nondurable. CUA stays in base metadata until L3a and L3c qualify.
Refs: docs/plans/light-profile-20261030.md; results/light-browser-contract-20261031/report.md

## LBCU2 · update · 2026-10-31 11:24
Observed: a fresh-context read-only review accepted 390fda1 with no defect. It diffed raw args_json strings old against new across nine calls including a non-ASCII replace and found them identical, and ran 13 malformed-reply cases against both. Differences appear only on replies the CUA wire does not produce: a null or non-dict body after dispatch was an AttributeError reaching the command's interrupted-outcome branch and is now an unverifiable dispatched effect; malformed attach refusals raise RuntimeError instead of AttributeError/TypeError; a non-string refusal code becomes None. No caller relies on the old exception types. coexist's Q15 record (asdict of BrowserEffect) gains four keys. Added tests for the is_error refusal path and attach by page (one, two and no matching tabs); the behavior assertions pass on 701fd32.
Changes: LBC1's identical-behavior claim holds for well-formed CUA replies; on malformed ones the new path is no less conservative and never reports not sent.
Next: hosted CI on PR 15.
Refs: tests/test_browser_contract.py; results/light-browser-contract-20261031/report.md
