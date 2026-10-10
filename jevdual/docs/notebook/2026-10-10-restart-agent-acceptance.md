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
