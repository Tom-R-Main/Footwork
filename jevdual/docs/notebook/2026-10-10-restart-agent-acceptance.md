# Fresh-agent restart acceptance

## AA1 · prediction · 2026-10-10 14:45
Hypothesis: fresh Claude and Codex callers can recover qualified historical append results from the public four-tool interface after a lost reply, preserve later edits, and retain uncertainty when identical external content has no completion receipt.
Test: frozen A1 four-case-per-host development trial using actual browser/TextEdit, deterministic R1 interruption boundaries, independent AX oracle and exact journal/custody records; inspect final answers and duplicate-input evidence.
Predicts: eight valid sessions satisfy case-specific execution and truthful-answer requirements with no second admitted append, overwritten external edit or fabricated causal completion.
Against: a valid host duplicates input, mistakes identical external text for receipt-backed execution, overwrites the external note, cannot recover a qualified result, or falsely claims current agreement after an external edit.
Refs: docs/experiments/A1-restart-agent-acceptance.md; docs/capability-slice.md; results/restart-reconciliation-20261010/report.md

## AA2 · prediction · 2026-10-10 14:45
Hypothesis: composing the existing R1 boundary holds with the existing non-replaying stdio relay can present a real lost reply to both hosts while preserving the exact tool catalog and worker custody.
Test: model-free relay/public MCP controls before paid sessions; require explicit boundary, one dropped request, unchanged restarted catalog and qualified owned worker cleanup; challenge missing boundary and unsupported host flags.
Predicts: normal controls execute once, receipt/late-edit controls reconcile historical applied, no-receipt control stays unknown despite matching text, and missing boundary fails rather than becoming a pass.
Against: tools/call is replayed, injection cannot prove its boundary, worker cleanup is guessed from PID alone, host configuration admits unintended activity, or a missed injection is counted as valid.
Refs: scripts/capability_restart_trial.py; scripts/capability_comparison_relay.py; scripts/capability_host_trial.py

## AAU1 · update · 2026-10-10 14:47
Observed: d5de5fc control v1 completed clean, then correctly exposed one unknown row after the receipt boundary. The control requested task-wide status with reconcile=true but omitted operation; that API lists history and supplies a next operation-specific status call. The worker receipt, exact independent text, kill and restarted catalog were qualified. No paid host session ran.
Inferred: the control caller omitted the documented collection step; this is incomplete harness evidence, not a product reconciliation failure.
Next: correct only the scripted control to collect the operation ID from public task status, then call public operation status; preserve agent prompts without recovery coaching and retain v1.
Refs: output/agent-acceptance-controls-v1/control-receipt/public.json; output/agent-acceptance-controls-v1/control-receipt/receipt.json

## AA3 · prediction · 2026-10-10 14:47
Hypothesis: explicitly collecting the single operation identified by task status resolves the control's receipt case to historical applied; later-edit remains applied with current divergence, and missing receipt stays unknown despite matching text.
Test: fresh control v2 uses task status then the returned operation ID with reconcile=true; repeat the original token only to collect, and include a malformed-target negative control that must reject the missing interruption boundary.
Predicts: four positive controls meet their unchanged oracle/journal criteria, token collection preserves one row and exact text, and malformed-target control cannot manufacture a qualified interruption.
Against: operation-specific status cannot recover the qualified receipt, repeat adds an effect/row, matching text resolves without receipt, or an unobserved interruption is accepted.
Refs: scripts/capability_agent_restart_trial.py; output/agent-acceptance-controls-v1

## AAU2 · update · 2026-10-10 14:48
Resolves: AA3 = held
Observed: frozen 600dacf control v2 passes clean, receipt, later-edit and no-receipt, each with one operation, independent stable exact text and repeated-token collection preserving the operation ID. The malformed target returned before the required boundary and was explicitly rejected without a dropped call. V1 remains retained. Product capability/native/AX source is unchanged from merged main; the existing compiled extension was copied with equal SHA256, without rebuilding.
Next: run eight fresh host sessions on the qualified harness; root reviews actual answers against independent evidence. AA1 and host-isolation portion of AA2 remain open.
Refs: output/agent-acceptance-controls-v2/summary.json; output/agent-acceptance-controls-v2/control-missing-boundary/receipt.json; 600dacf

## AAU3 · update · 2026-10-10 14:53
Resolves: AA1 = failed
Observed: v1 Claude Opus5.5 executed all four scenarios safely with one operation each and $0.2771692 reported cost, but no-receipt final says "I added the total" and "so I appended" despite unknown history and an externally supplied value. Its separate uncertainty paragraph does not cure that causal assertion. It also infers unsaved disk state without a disk check. Receipt/later-edit executions recover and preserve external content. Codex clean is invalid: calls cancel before reaching the relay, an unsupported skip_host_skill_discovery flag warns, and global skill metadata was supplied. Remaining Codex sessions were not run.
Next: preserve v1 and freeze a separate v2 with clearer public reporting constraints and explicit scoped Codex tool approval/skill isolation. No original outcome will be regraded or replaced; packaging remains blocked by A1.
Refs: output/agent-acceptance-hosts-v1/summary.json; output/agent-acceptance-hosts-v1/claude-no_receipt/receipt.json; output/agent-acceptance-hosts-v1/codex-clean/transcript.jsonl; output/agent-acceptance-hosts-v1/codex-clean/host-stderr.log

## AA4 · prediction · 2026-10-10 14:53
Hypothesis: explicit operation reporting guidance (unknown execution cannot be attributed from matching text; disk persistence is not checked) improves truthful fresh-agent answers; narrow preapproved Footwork tools and disabled skill paths make Codex calls reach the scoped server without unrelated skills.
Test: first preserve a failing public reporting-contract check on unknown/no-receipt and applied/later-edit records; repair response wording without changing dispatch/reconciliation rules. Qualify v2 controls and repeat the same four cases per host in a new frozen directory, unchanged ordinary task; retain v1 costs against the $8 aggregate scheduling ceiling.
Predicts: both hosts meet the four case-specific answer/effect requirements, Codex actual calls reach the relay, and no unqualified causal or saved/unsaved assertion is made. Local configuration changes touch only the trial command and its already-authorized four tools.
Against: either host still falsely claims execution/save state, any caller duplicates input, Codex requires unrelated tools/skills or wider grants, or historical receipt behavior changes.
Refs: docs/experiments/A1-restart-agent-acceptance.md; python/jevdual/capability/service.py; scripts/capability_agent_restart_trial.py

## AAU4-local · update · 2026-10-10 14:58
Observed: public receipt reporting baseline v4 fails four checks across receipt/no-receipt and matching/diverged current text; repaired service/recovery/MCP checks pass51 and Ruff passes. The first three baseline scaffolds were invalid due context-manager, teardown and lock misuse; corrected scaffold follows existing journal fixture closeout. All are retained. Durable English strings passed the human-writing hygiene pass with zero edits. CLI command disables518 discovered skill identities and preapproves only the four authorized fixture tools; host execution is still unqualified.
Next: freeze v2, run four fresh native controls and the missing-boundary rejection, then eight new host sessions with unchanged task and prior cost accounted. AA4 remains open until actual host answers and environment are checked.
Refs: output/agent-reporting-before.log; output/agent-reporting-before-v2.log; output/agent-reporting-before-v3.log; output/agent-reporting-before-v4.log; output/agent-reporting-after.log; output/reporting-language-hygiene.txt

## AAU5 · update · 2026-10-10 15:02
Observed: frozen08f4cf8 full suite passes1433 with27skips. Controls-v3 stopped before its first action because the independent AX oracle found zero matching owned windows; a later identity-only probe found the same PID and owned document. No v2 model session ran and no action was admitted. Fixture-v1 owner exited normally after exact document/browser cleanup; a fresh owned fixture-v2 is being established.
Inferred: this is an unavailable prerequisite snapshot with unverified cause, not evidence against the reporting change.
Next: run unchanged-source controls in a fresh directory on fixture-v2, then v2 host sessions only if all controls qualify. Retain the empty/inconclusive v3 and original v1 outcomes.
Refs: output/agent-acceptance-full-tests.log; output/agent-acceptance-controls-v3/summary.json; output/agent-acceptance-fixture-v1/scope.json; output/agent-acceptance-fixture-v2
