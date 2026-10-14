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

## CA5 · prediction · 2026-10-14 13:10
Hypothesis: frozen onboarding packet verification must derive its wheel inventory from the requested immutable commit rather than the current checkout, and the existing release verifier can preserve that constraint after camera runtime changes.
Test: reproduce reviewer inventory mismatch using the qualified wheel and source445a348; add a regression with current runtime differing from frozen source, then use committed-source wheel verification before generating packet inventory. Reverify the original205577packet and immutable8dc81c72candidate without rebuilding them.
Predicts: exact old wheel and packet verify against their frozen source; altered wheel bytes or a mismatched commit still refuse; current-source default remains correctly verified.
Against: verification accepts tampering, silently uses current source, introduces circular imports, or changes the preserved packet.
Refs: jevdual/scripts/build_onboarding_packet.py:inventory; jevdual/scripts/build_release_candidate.py:verify_committed_wheel; independent reviewer source445a348 inventory mismatch

## CA6 · update · 2026-10-14 13:22
Resolves: CA4 = held
Observed: the same full physical suite passes 314 tests after the private socket repair, including 10 new long-path and hostile-directory regressions. Controller restart/unknown-effect scenarios and AgentBench fresh output setup pass. Hosted Linux CI remains a separate portability check pending on PR3. The reference chrome-devtools-mcp daemon also uses a short per-user temporary runtime directory because of POSIX socket path limits.
Inferred: coupling the socket location to checkout length caused the startup failures; shortening only its private namespace repairs that constraint while retaining source/controller identity and safety refusals.
Next: complete current CI and independent review, remediate actionable findings, then merge PR3.
Refs: bce67ed; output/consolidation-physical.log; output/consolidation-physical-rerun.log; tools/physical-workcell/test_controller.py:SocketPathTests; chrome-devtools-mcp/src/daemon/utils.ts:getRuntimeHome

## CA7 · update · 2026-10-14 13:22
Resolves: CA5 = held
Observed: frozen old packet verification failed before the change and passes afterwards; 34 packet/release tests pass, including frozen-source divergence and tampering. Approved packet205577 and candidate8dc81c72 retain their original digests. A first new-test assertion mismatched only the existing error wording and is retained separately.
Inferred: immutable source reconstruction resolves the verification regression without changing either qualified artifact.
Next: merge after review/CI; preserve exact original artifacts for the adoption handoff.
Refs: 57ed816; output/consolidation-20261014/packet-before.txt; output/consolidation-20261014/packet-after.json; output/consolidation-20261014/release-after.json; output/consolidation-20261014/packet-fix-tests.txt; output/consolidation-20261014/packet-fix-tests-v2.txt

## CA8 · prediction · 2026-10-14 13:25
Hypothesis: current Linux CI errors arise from a macOS-only import in a synthetic test fixture, and the actionable static-review gaps can be repaired without changing the immutable qualified artifact or weakening fail-closed simulation behavior.
Test: replace only unavailable native test dependencies with explicit fakes while keeping Mac coverage real; correct order-handoff cleanup to the bound socket and freeze source bytes; score adoption by exact ZIP/wheel and manifest commit; snapshot archive bytes once, reject unsafe ZIP metadata and noncommit source objects; privatize measurement database creation and reject nonobject proposals; evaluate planner cleanup findings against declared retirement scope and add bounded regressions where supported. Run original affected suites, full Linux CI, notebook/lint and independent remediation review. Preserve first CI failure and the exact Opus review.
Predicts: all 54 unavailable-module errors disappear without dropping synthetic safety tests; cleanup observes the actual bound socket; dirty qualification is refused; verifier tampering, symlink archive and malformed source/proposal cases refuse; initial artifacts stay byte-identical.
Against: tests are skipped to hide a behavior failure, safety assertions are weakened, archive identity changes, cleanup still targets a stale path, or new regressions appear.
Refs: PR3; output/consolidation-ci-failure.log; output/consolidation-opus-review/response.json; review target57ed816

## CA9 · update · 2026-10-14 13:44
Observed: full source Python rerun passes1594 with27skips/12browserdeselections; frozen0e5a59a physical rerun passes330. Archive hardening passes44 and immutable205577/8dc artifacts verify unchanged. Native fixture56 and controlledLinux-import55 tests pass; actual hostedLinux rerun is pending. Independent remediation scrutiny found qualifier location checks lacked produceridentity; two regressions failed before and pass after integer version/sourcekind/currentcontrollerhash checks. Final affected simulation conformance passes42. Original runs, test-preparation errors and development failures remain retained.
Inferred: fixes close the observed setup, provenance and bounded-input gaps while preserving existing fail-closed semantics. Observed detached planner survivors intentionally withhold closure; signalling retained identities would broaden the tested authority. The15secondhostgrace repairs supported delayed guardian publication without promising universal cleanup.
Next: push one consolidated remediation update, inspect current hostedCI and all review threads, retain qualification commits through a true merge, then consolidate primary checkout. A3 remains gated on user8GiBavailableRAM; no VM or adoption model task has started.
Refs: f34ce57; 0e97555; 9cf0c97; 0e5a59a; output/consolidation-pytest-final.log; output/consolidation-physical-final.log; output/consolidation-20261014/archive-hardening-tests-final-v2.txt; output/consolidation-20261014/qualifier-source-identity; output/release-publication-scan-reviewed.json
