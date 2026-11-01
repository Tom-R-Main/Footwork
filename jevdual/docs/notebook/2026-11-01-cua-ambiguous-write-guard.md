# Candidate guard for ambiguous pinned CUA Linux writes

## IR2 · prediction · 2026-11-01 14:10
Question: can a candidate patch prevent the second mutation observed in IR1 after a pinned CUA EditableText write has applied but its reply is lost or errors?
Hypothesis: propagating a mutation method error as an ambiguous effect through native callers, and terminating fallback on that error, will leave one target-owned effect and an uncertain/error result for the tested post-effect error and shortened-timeout withheld-reply cases. A separate outer-route review will identify any callers that still suppress the ambiguity.
Alternatives: another helper, focus retry, Value path or TypeTextTool route swallows the error and mutates again; a timeout happens outside the patched method; the candidate changes the test boundary or silently drops acknowledged false-before-effect compatibility.
Test: freeze an exact-source candidate patch and the existing private-D-Bus harness, then execute ACK, pre-effect false, post-effect error and declared100ms withheld-reply cases first in the selected Linux cloud chat. Use independent target journals, compile the complete pinned Linux module plus test-only inclusion, and test public retained-reference set_value_ref where reachable. Review outer routes separately and retain scope limits.
Predicts: the candidate retains ACK1/1 and false-before-effect2attempts/1effect where promised, while each tested post-effect error or shortened-timeout withheld reply produces one effect, no alternate mutation and an uncertain/error outcome. The unchanged IR1 receipts remain two-effect positive controls.
Against: any candidate post-effect error/withheld-reply case records a second applied mutation, returns success after a lost first reply, fails to compile the exact production source, or reports an error as proven pre-send despite an effect. A helper-only pass does not establish public TypeText or whole-product safety.
Refs: docs/experiments/IR2-cua-ambiguous-write-guard.md; results/cua-internal-replay-ir1-20261101/cloud-closeout.json; prior IR1 frozen test48f93946b39e9f51f45b291b57152692e0d55033

## IR2U1 · update · 2026-11-01 14:24
Observed: the selected Linux cloud chat was stopped by an automated possible-cybersecurity-risk review during candidate preparation. It reported no IR2 build or resolving test. A recovery-only inspection returned a 13,892-byte draft patch with SHA256c1367501dc3f3eeca7f2f4d8d0afd3dda6c3c64af9542e4690ee3fb6d1f2d6a3 and a manifest; both match the local recovered copies. The user explicitly moved tests to the Mac after this stop.
Inferred: the cloud stop supplies no evidence about candidate behavior. The draft patch is source material for review, not a tested fix or a frozen test package.
Next: check the Mac's existing isolated Linux runtime, review and freeze the candidate package, then perform the first resolving IR2 test there if the exact Linux source can run without an install/fetch.
Refs: scripts/ir2_replay_candidate/candidate.patch; scripts/ir2_replay_candidate/candidate-manifest.json; cloud chat01a18d7f-d0d0-733c-93c9-8f554f4190df

## IR2U2 · update · 2026-11-01 14:41
Resolves: IR2 = held
Observed: the Mac's existing Docker Desktop Linux VM initially refused startup from an earlier disk-full error; after current free space and absent VM/disk handles were checked, the stuck Desktop backend was stopped and the VM started. A first candidate build stopped before compilation on a read-only Rustup shim; the frozen harness was corrected in a separate commit. At frozen head86fece5, the complete pinned Linux source with the candidate patch and test-only child compiled and linked using 40 exact cached dependencies. All14 private-D-Bus cases returned. Both helpers and public native set_value_ref recorded one target-owned effect and typed uncertainty after a post-effect error; shortened-timeout helper withheld cases also recorded one effect and typed uncertainty. ACK and false-before-effect compatibility controls passed; deliberate double write recorded two effects. Parent independently recounted journals and28 explicit fixture waits with no escalation.
Inferred: the candidate prevents the IR1 second mutation at the tested native boundaries while preserving the fixture's acknowledged false fallback. This does not qualify registered TypeTextTool/SetValueTool, current Footwork product or the separate batch retry owner.
Next: keep the installed pin unchanged; require targeted registered-tool and token re-resolution regression coverage before adoption. Preserve the cloud-review flag as unexplained, not a behavioral result.
Refs: results/cua-ambiguous-write-ir2-20261101/report.md; results/cua-ambiguous-write-ir2-20261101/parent-verification.json; frozen harness86fece5898f8f4256432db9718e2158b5fa1cf2d

## IR2S1 · summary · 2026-11-01 14:41
Established: a byte-identified candidate source patch, isolated Mac-hosted arm64 Linux compilation of the complete pinned module, and independently journaled one-effect uncertain outcomes after the tested post-effect failures. All selected controls and owned fixture cleanup completed.
Uncertain: registered tool/desktop/product reachability, explicit false after real effect, ordinary default helper outcome, and batch dispatch guard. The candidate is not installed or released.
Decision: close this native-boundary candidate package and carry the patch forward only as a reviewable prototype pending outer-route tests.
Refs: docs/experiments/IR2-cua-ambiguous-write-guard.md; results/cua-ambiguous-write-ir2-20261101/first/summary.json
