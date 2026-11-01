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
