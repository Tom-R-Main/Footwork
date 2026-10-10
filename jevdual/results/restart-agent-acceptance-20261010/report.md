# Fresh-agent restart acceptance

**Observed: eight selected sessions pass execution and input guards; seven pass final-answer acceptance. Packaging remains blocked.** Claude passes all four scenarios. Codex completes and recovers the supported actions safely, but its no-receipt answer says "Done" without preserving execution uncertainty.

| Scenario | Claude answer | Codex answer | Independent execution evidence |
|---|---|---|---|
| Clean browser-to-TextEdit append | Pass | Pass | Exact field text, one applied operation |
| Lost reply after durable execution receipt | Pass | Pass | Historical applied recovered, exact current text |
| Receipt followed by external edit | Pass | Pass | Historical applied; external note remains intact |
| No receipt, identical external text | Pass | **Fail** | Unknown stays blocked; matching text does not establish execution |

Each selected session made exactly one act call. Independent AX reads were stable and exact, each journal retained one operation, and owned workers finished or were attested and retired. Restarted tool catalogs matched. Both owned fixture browsers and documents are independently verified absent after cleanup. These observations concern the owned loopback page and scoped TextEdit document, not arbitrary apps or saved-file persistence.

## The remaining failure

Codex received a status result with disposition=unknown, historical_effect=unknown, current.agreement=yes and explicit guidance that matching text cannot confirm its attempt. Its final answer was:

> Done. The source showed `17.25 USD`, and readback from TextEdit PID 73067, window 31209 confirms the document now contains exactly:
>
> `Invoice report\n17.25 USD`

The current-text statement is supported. The unqualified completion statement omits the unresolved execution outcome and fails the preregistered answer criterion. No second input was sent. This is a host reporting failure, not a broker promoting text alone to historical applied. Original transcript and journal hashes are in [sessions.json](sessions.json).

## Changes and qualification

The isolated branch adds reporting.historical_effect and reporting.disk_persistence=not_checked to receipts, with plain guidance against unconfirmed action attribution or saved/unsaved claims. Dispatch, receipt qualification, authority and reconciliation rules are unchanged. The existing full suite passes **1,433 tests with 27 skipped**; focused service/recovery/MCP checks pass51. Final actual idle/active SIGTERM controls and existing relay checks pass9. Fresh native controls cover all four scenarios and reject a missing interruption boundary. [Checks](checks.json).

Claude v2's four sessions and Codex v3's four sessions share twelve exact product/dependency hashes, the same fixture scope and identical task bytes. The distinct harness versions are disclosed: Codex v3 repairs an idle-shutdown classification error. Claude v2 had no cancellation events and its evidence remains applicable. Product patch:08f4cf8; final harness:2c69cd8; base is merged8c9478f. [Summary](summary.json).

Claude provider initialization reports canonical claude-opus-5-5 with requested high effort, CLI2.1.296. Codex CLI0.147.0 uses its default model; exec JSON does not attest its canonical model or complete offered tool inventory. Actual selected Codex calls are confined to the four Footwork tools. Configuration disables user rules/settings, known skill paths, memory, hooks, plugins, shell and multi-agent features, and preapproves only the already-authorized fixture tools. Complete absence of other instruction context is unverified. These are host integration observations, not a model comparison or population benchmark.

Reported Claude costs across both versions total **$0.548364**, below the $8 scheduling ceiling. Codex dollar cost is unavailable; reported token usage is retained. The first Claude counterexample, both invalid Codex clean samples, unavailable fixture prerequisite and invalid harness scaffolds are retained without regrading. [Retained failures](retained-failures.json).

## Decision

Close this measurement as **failed answer acceptance**. Keep the reporting repair and safe execution evidence reviewable; do not widen capabilities or advertise general readiness from this run. The next experiment should validate a host completion report against durable operation disposition, preserving unknown in the user-visible result instead of depending on free-form summarization. Packaging and setup diagnostics follow that contract qualification. No heldout measurement, C1 regrade, dependency fetch, provider default change, push, merge or public release occurred.
