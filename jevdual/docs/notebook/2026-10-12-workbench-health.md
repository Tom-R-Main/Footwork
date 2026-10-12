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
