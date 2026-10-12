# Mid-job restart and explicit browser recovery

## SIM11-P1 · prediction · 2026-10-12 13:56
Hypothesis: a pending browser stage and single-send command journal survive independent workbench and body restarts without resending an uncertain action; historical body receipts can settle the same stage after its boot epoch changes.
Test: freeze a fresh owned process harness, interrupt two actual image-guided browser jobs at planning and uncertain-dispatch boundaries, recover through the UI and independently score native/SQLite/contact records after cleanup.
Predicts: all four stops/restarts preserve body/application identity and client send counts, planning interruption cancels and reaps its model process, uncertain commands remain blocked until exact receipt lookup, and explicit Resume uses a fresh TCP image before completing both jobs.
Against: a replay, lost pending command, silently resumed planning, orphan model process, body reset or independent verification failure.
Refs: docs/experiments/SIM11-workbench-restarts.md; tools/physical-workcell/qualify_workbench_restarts.py; tools/physical-workcell/score_workbench_restarts.py; results/workbench-restarts-20261012/

## SIM11-EPOCH · prediction · 2026-10-12 13:58
Hypothesis: a changed body boot epoch can preserve running state when its outage is missed, because health and lease acquisition verify stable identity without invalidating the old decision. Binding epoch changes to Pause before command admission will cancel stale planning without disturbing historical receipt recovery.
Test: reproduce on real sockets by rebooting the same body while a model decision waits, avoiding an outage poll; release the old decision after the new epoch is read. Cover health-first and admission-read-first paths, then rerun with epoch invalidation. Separately retain uncertain historical dispatch recovery across reboot.
Predicts: the original fast-reboot path admits the old decision; the repaired path pauses with no successor command, requires explicit Resume and a fresh observation, and retains exact unknown command identity for read-only recovery.
Against: original code already pauses, repaired code sends the old decision, permanently blocks historical receipt lookup, or silently rotates authority while a command remains uncertain.
Refs: tools/physical-workcell/network_operator_runtime.py; tools/physical-workcell/test_network_operator.py; docs/experiments/SIM11-workbench-restarts.md

## SIM11-U1 · update · 2026-10-12 14:03
Observed: four new real-socket checks failed on the original runtime. Health-first reboot let the old waiting model decision advance generation to one; acquisition-first reboot also admitted that decision under boot two. Historical uncertain dispatch stayed single-send across body reboot, but its recovered job remained labelled unknown. Graceful workbench restart left an unfinished job labelled running while its host was paused. Before-fix output is retained. The original completed product roots and source snapshot were preserved before stopping its verified idle owned processes.
Inferred: boot identity alone does not invalidate a model decision, and runner recovery needs a consistent unfinished-job status. The original historical receipt mechanism remains useful.
Next: repair the runtime epoch boundaries and labels, rerun affected real-socket checks, then freeze the actual browser restart trial.
Refs: tools/physical-workcell/output/sim11-epoch-before-fix.log; tools/physical-workcell/output/sim11-preserved-baseline/preserved.json; tools/physical-workcell/test_network_operator.py

## SIM11-U2 · update · 2026-10-12 14:09
Resolves: SIM11-EPOCH = held
Observed: all nineteen runtime socket checks passed after epoch invalidation and job-status corrections. The old decision is withheld on health-first and lease-read-first reboot paths, exact unknown history stays recoverable once, and a later outage preserves the last verified epoch. Eighty core/adapter/link/HTTP regressions and four restart-harness control/ownership checks also passed. Ruff, JavaScript syntax and diff checks passed. The harness now records exact roots, ports, stopped processes, boot epochs and command digests; its scorer requires actual browser recovery evidence and final native/SQLite/contact proof. No actual-model restart trial has run yet.
Inferred: the epoch diagnosis is supported by failing and resolving socket evidence. The 103 mechanical checks establish readiness for the frozen browser trial, not its result.
Next: commit all measured source, then interrupt two actual image-guided jobs at the four preregistered process boundaries.
Refs: tools/physical-workcell/output/sim11-epoch-after-fix-runtime.log; tools/physical-workcell/output/sim11-core-network-regression.log; tools/physical-workcell/output/sim11-harness-tests-v1/unittest.log; tools/physical-workcell/qualify_workbench_restarts.py; tools/physical-workcell/score_workbench_restarts.py

## SIM11-U3 · update · 2026-10-12 14:25
Resolves: SIM11-P1 = held
Observed: all four graceful process restart boundaries and ten visible recovery states passed the independent scorer on the first actual-model trial at frozen d707210. Two jobs completed with native/SQLite/contact proof, continuous generations zero through twenty and 83 single-send command records. Workbench and body each stopped during planning and with a distinct uncertain dispatch. The five-command and 46-command recovery intervals added no sends. All seven trial processes exited before scoring. Three cancelled model calls were reaped and withheld: two planned interruptions and one additional health-timeout pause during reset. That extra pause required explicit Resume and a fresh observation; its cause remains unresolved. Reload preserved results without a command. Paused handoff retained identities, history and 83 commands at body boot four. An abbreviated-SHA launch was refused before process creation; its corrected full-SHA launch started the one actual-model attempt. An unmeasured helper fixture moved into owned output without changing measured source hashes.
Inferred: exact historical receipt recovery composes with graceful body/workbench restarts in this loopback product. Fast epoch invalidation is supported separately by socket regressions. The observed health timeout limits reliability claims even though guarded recovery worked.
Next: hand off the paused connected product and retained recovery evidence; leave sudden power loss and health-timeout diagnosis to separate work.
Refs: results/workbench-restarts-20261012/report.md; results/workbench-restarts-20261012/restart-score.json; results/workbench-restarts-20261012/qualification-score.json; results/workbench-restarts-20261012/health-timeout-observation.json; results/workbench-restarts-20261012/attempt-ledger.json; results/workbench-restarts-20261012/handoff.json

## SIM11-S1 · summary · 2026-10-12 14:25
Established: graceful workbench/body restart during actual planning and uncertain dispatch preserves one body, retained queue and command identity. Recovery reads exact historical receipts once, stays paused until Resume, and uses fresh TCP images. Two independently verified jobs and all four visible restart cases passed with measured source unchanged. Fast boot changes now invalidate old decisions before successor admission.
Uncertain: an additional health timeout paused reset and cancelled a model call; its cause is unresolved. Sudden power loss, forced kill during native persistence, physical hardware and authenticated remote access remain untested.
Decision: adopt the qualified restart behavior, retain the previous product and failing development evidence, and leave the current product connected and paused with both completed jobs visible.
Refs: docs/experiments/SIM11-workbench-restarts.md; results/workbench-restarts-20261012/report.md; tools/physical-workcell/NETWORK_WORKBENCH.md
