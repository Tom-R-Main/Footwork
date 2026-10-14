# Consolidation and unassisted local adoption

## CA1 · prediction · 2026-10-14 12:51
Hypothesis: latest main, capability qualification and independently developed camera/workbench branches can form one reviewed main without changing the immutable release artifact or losing private evidence.
Test: preserve exact branch refs and untracked draft context; merge origin/main into a new consolidation branch, retaining only the three documented later capability enhancements in squash-history conflicts; merge e17a49e experimental branch after user explicitly authorizes both. Review the complete netdiff, run full relevant deterministic/runtime-free suites and current hosted CI, remediate concrete findings, merge one PR. Keep VM stopped; qualify physical simulation as simulation only. Preserve ignored output and recoverable refs before linked checkout retirement; no gitclean/history deletion.
Predicts: merged tree includes both disjoint work streams, tests/review/CI pass, existing qualified8dc81c72 remains byte-identical, original experiment/capability records and drafts remain recoverable, and the sole active primary checkout ends clean onmain.
Against: useful data is lost, an unreviewed integration seam lands, preserved artifact identity changes, required checks fail, or unique work is silently dropped.
Refs: origin/main268f0fc; capability5dab496; camerae17a49e; userOctober14authorization includebothafterreview

## CA2 · prediction · 2026-10-14 12:51
Hypothesis: a fresh Codex session given only the exact8dc81c72 package and README can install and complete the bounded task without source coaching on this existing Mac.
Test: user changes separate-Mac requirement to thisMac, with8GiBmemoryheadroom and otherprojectactors idle. Record currentresources; stop only attestedownedidle Footwork actors ifneeded, preserve their state anddo not launchVM. Use one cleanper-run Codexcontext with opaqueexistingauth, package-only consumer instructions, freshownedinstall/job/fixture. Preserve allattempts; verify actualcalls/origins/exactoracle/durableclaims/automaticcleanup independently. Recordsetupfriction and repaironly demonstratedscopedissues in new versions withClaude review. Neverclaim anotherMac/coldOS qualification.
Predicts: actual Codex can follow README-only setup, identify permittedtargets through the publicsurface, completeoneexacteffect andvalidatedreport, and cleanup withminimalmanualsetup.
Against: it requires authorcoaching/manualPIDwindowURLdocumentinput, packageinstructionsfail, hostneedsungrantedaccess, duplicatesinput/misreportscompletion, or requiredmemoryheadroom is unavailable.
Refs: results/release-candidate-20261012; userOctober14thisMacauthorization; docs/installed-agent-host.md

## CA3 · update · 2026-10-14 13:07
Observed: full Python source suite passed 1582 tests; Node suite passed 97; camera synthetic suite passed 18. Initial desk/workbench tests failed because the new checkout's public CLI was not installed; after frozen uv sync, the same tests passed 30 tests and 11 subtests. The physical suite ran 304 tests with 38 failures and 15 errors: initial AgentBench setup lacked its output parent, and retained native startup logs show the owned Unix socket path exceeds the platform bound in this long managed checkout.
Inferred: the physical socket location is coupled to source checkout path length; the fail-closed bound protects the socket but prevents portable installation. The output-parent failure is a fresh-checkout test preparation defect.
Next: preregister a bounded socket-location portability repair, preserve original failed runs, review it and repeat the same suite.
Refs: output/consolidation-pytest.log; output/consolidation-node.log; output/consolidation-camera.log; output/consolidation-inbox-workbench.log; output/consolidation-inbox-workbench-rerun.log; output/consolidation-physical.log; tools/physical-workcell/output/a59ecfcf7/native-1.log

## CA4 · prediction · 2026-10-14 13:07
Hypothesis: deriving a short, per-user private Unix socket directory independently of checkout length, while retaining source/controller binding and owned-private socket validation, repairs fresh-checkout physical conformance without weakening refusal behavior.
Test: add meaningful long-path and adversarial ownership/symlink cases; create fresh test output parents explicitly; run the original 304-test physical suite in this long checkout and hosted Linux CI. Review changes with Claude before merge.
Predicts: long checkout paths work, hostile socket roots are refused, separate controller identities remain separate, restart/replay safety tests remain green, and all original physical tests pass.
Against: shortened paths retarget another controller, tolerate unsafe roots, weaken the existing safety bound, leave broken binding across restart, or original failures persist.
Refs: tools/physical-workcell/controller.py:socket_path; output/consolidation-physical.log
