# Healthy-job health timeout investigation

## SIM12-E1 · exploratory · 2026-10-12 14:38
Question: which boundary caused the SIM11 healthy-job pause: expensive or queued body reads, a stale overlapping health probe, or treating a transport deadline as proof of loss?
Test: compare retained SIM11 event timing with independent source inspection, then use bounded direct-body/link probes and scoped timing instrumentation. Commit a causal prediction before a reproducing test or fix.
Refs: docs/experiments/SIM12-workbench-health.md; results/workbench-restarts-20261012/health-timeout-observation.json; tools/physical-workcell/output/sim11-browser-restarts-v2/

## SIM12-P1 · prediction · 2026-10-12 14:38
Hypothesis: the host can keep a healthy job running while withholding new command admission during a delayed health read, and recover from fresh same-body/same-boot proof without weakening explicit controls or uncertain-command recovery.
Test: after causal reproduction and repair, run outage/epoch/uncertainty/pause regressions and two frozen actual image-guided browser jobs with owned health-delay injection; independently score native results and retained sends.
Predicts: delayed healthy reads cause bounded waiting rather than unrequested Pause; effects still need fresh pinned admission proof; actual loss/epoch/identity/unknown state blocks successors; two jobs complete without health-caused cancellation and with exact receipt recovery.
Against: stale health grants an effect, an unsafe body stays runnable, an unknown command is replayed, explicit Pause is overwritten, or actual-model verification fails.
Refs: docs/experiments/SIM12-workbench-health.md; results/workbench-health-20261012/

## SIM12-U1 · update · 2026-10-12 14:47
Observed: thirty-two sequential pinned body/link reads all succeeded. Direct state median was 92.1 ms and linked state median 94.3 ms; no observed maximum exceeded 136.7 ms. An isolated scan of 83 copied command records performed 249 file reads and 664 canonical request digest builds, with a 20.8 ms median. The warm paused baseline did not reproduce the historical deadline. Independent code review found that one auxiliary deadline cancels the model, full state checks share the body execution lock, and the link may keep its upstream read alive after the caller times out.
Inferred: receipt scanning adds real work but is not sufficient evidence for the original slow response. The confirmed logical weakness is promoting an ambiguous probe deadline to body loss. Bounded auxiliary reads and fresh authoritative admission proof can address that weakness without inferring the historical scheduling cause.
Next: reproduce isolated healthy slow reads, then separate inconclusive telemetry from fresh command admission and bound outstanding probes.
Refs: tools/physical-workcell/output/sim12-diagnosis/summary.json; tools/physical-workcell/output/sim12-diagnosis/timing.jsonl; tools/physical-workcell/network_operator_runtime.py; tools/physical-workcell/workbench_link.py

## SIM12-DELAY · prediction · 2026-10-12 14:47
Hypothesis: a healthy auxiliary read delayed beyond its deadline causes a false control cancellation in the original runtime. Treating that deadline as unconfirmed, while requiring fresh pinned ready state before lease and stage admission, preserves healthy progress and still prevents stale or unsafe authority.
Test: real TCP delay of only an auxiliary identity/state reply while a model decision waits; retain the failing original pause and recheck after repair. Pair with fresh-proof failure, epoch/identity changes, unknown outcomes, explicit controls and stale-probe overlap.
Predicts: the original path pauses/cancels despite a live unchanged body; the repaired path keeps the job running, obtains independent fresh full status before any command and completes the bounded action. Hard faults and explicit Pause continue to suppress admission.
Against: the original path already tolerates the delay, repaired code dispatches from cached health, accepts an old boot, cancels the healthy decision or erases pending uncertainty.
Refs: tools/physical-workcell/network_operator_runtime.py; tools/physical-workcell/test_network_operator.py

## SIM12-FLIGHT · prediction · 2026-10-12 14:47
Hypothesis: tagging only auxiliary identity/state reads and limiting them to one outstanding upstream request per path bounds the two-hop backlog without affecting untagged authoritative reads or any effect command.
Test: delay an actual upstream health response past the caller deadline, issue repeated tagged probes, and assert at most two upstream health reads, bounded inconclusive replies, no late-result reuse and owned worker cleanup. Challenge invalid probe routing and unchanged command faults/reconciliation.
Predicts: delayed auxiliary results never become command proof; full status still reaches the body independently; expired probe callers cannot produce an unbounded read fanout; all workers exit before ownership release.
Against: a probe annotation changes effect semantics, a cached response authorizes admission, outstanding readers grow with retries or workers survive cleanup.
Refs: tools/physical-workcell/workbench_link.py; tools/physical-workcell/test_workbench_link.py
