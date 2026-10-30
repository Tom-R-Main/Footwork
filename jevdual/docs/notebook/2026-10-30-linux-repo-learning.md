# Linux consolidation: repository learning

## RL1 · prediction · 2026-10-30 13:27
Hypothesis: cloud cleanup's captured PID/start snapshot can become obsolete between group signaling and its subsequent individual signals; a retained identity handle is a stronger boundary than a pre-signal snapshot.
Test: execute the exact cloud signal_owned method with a synthetic process table and fake signal sinks; replace a member's incarnation after group delivery. Compare a stable neighbor, the unchanged routine and a test-only immediate-revalidation control. No OS signal or reference code runtime is invoked.
Predicts: the unchanged method can address the replacement numeric PID, while the revalidation control skips a replacement and preserves the stable neighbor. The model establishes a specific stale-snapshot transition, not pidfd or kernel correctness.
Against: the exact method already revalidates after group delivery, the replacement cannot reach the individual sink in the model, or the control drops stable recipients.
Refs: docs/linux-next-tranche.md; cloud bd6f185 python/jevdual/linux_session.py:173-189; systemd src/basic/pidref.c:346-360

## RL2 · prediction · 2026-10-30 13:27
Hypothesis: a still-running cloud Chrome singleton helper can satisfy the same executable/profile/port predicate as its owned persistent root, causing unique-root discovery to refuse during recovery.
Test: execute the exact cloud browser discovery/bind functions with synthetic process records and driver/launch stubs. Compare a helper already exited, a helper still initializing and a genuinely unrelated second matching root. No browser or real input is started.
Predicts: exited-helper control binds, live-helper case reaches the multiple-root refusal, and unrelated-root case remains refused. The transfer must distinguish invocation-owned transient helpers without relaxing unrelated-root exclusion.
Against: helper command arguments cannot satisfy the predicate, bind waits for helper completion before rediscovery, or the unrelated-root control attaches.
Refs: cloud bd6f185 python/jevdual/browser_driver.py:104-126,619-654; local65996ad browser helper completion handling

## RL3 · prediction · 2026-10-30 13:30
Hypothesis: the existing local Linux test VM permits pinned single-process signal delivery via Python pidfd APIs, with an exited process remaining distinct from a separate live sentinel.
Test: in the already-owned Linux container, open a pidfd for an owned sleeping child, terminate through that fd and wait through its Popen owner; signal the retained fd after exit and require ESRCH while a separate sentinel remains alive. Close every fd and join owned children. Record kernel/runtime and unsupported or denied states without numeric fallback.
Predicts: supported path terminates only the referenced child, retained fd cannot signal a replacement and the sentinel survives; unsupported APIs remain unavailable rather than silently downgraded.
Against: the wrong child exits, the post-exit fd signal succeeds unexpectedly, a descriptor/child leaks, or unsupported state is reported as a qualified pinned path.
Refs: systemd src/basic/pidref.c:94-123,346-360,406-429; repo-learning Linux consolidation pattern study

## RLU1 · update · 2026-10-30 13:37
Resolves: RL1 = held
Observed: the exact cloud signal_owned function addresses a replacement numeric PID in the model after group delivery changes its incarnation. Stable and immediate-recheck controls behave as predicted. A recheck narrows the race but does not equal pidfd identity pinning; group scope and wait ownership remain separate. No real PID reuse or OS signal was used in this model.
Next: carry that distinction into the consolidation contract and qualify fd support/failure policy on the cloud VM before adopting a pinned path.
Refs: results/linux-repo-learning-20261030/models.json; docs/linux-consolidation-learning.md

## RLU2 · update · 2026-10-30 13:37
Resolves: RL2 = held
Observed: exact cloud discovery/bind functions accept the exited-helper control but reject the live owned helper as a second matching root; an unrelated root still refuses. The first model run had a missing DEVNULL test stub, retained as a harness error rather than a successful negative control.
Next: add a delayed-helper regression when implementing consolidation; preserve unrelated-root exclusion.
Refs: results/linux-repo-learning-20261030/models.py; results/linux-repo-learning-20261030/models.json; results/linux-repo-learning-20261030/initial-harness-error.json

## RLU3 · update · 2026-10-30 13:37
Resolves: RL3 = held
Observed: the local Linux owned-child probe passed pidfd TERM and post-exit ESRCH, with the sentinel alive, fd closed and children joined on aarch64 kernel7.0.14-linuxkit/Python3.14.4. This does not establish the cloud Debian target's syscall policy or a combined product path.
Next: retain target-specific compatibility as a prerequisite; do not generalize the local probe into cloud adoption.
Refs: results/linux-repo-learning-20261030/pidfd-learning.json

## RLS1 · summary · 2026-10-30 13:37
Established: five reusable Linux consolidation pattern families are stored with exact source anchors, counterexamples and target-fit gates. The existing seed export was retrieved read-only; the task SQLite store is /Users/thomasmain/projects/footwork/output/repo-learning/linux-consolidation/library. Fresh-context retrieval found the signal pattern using different vocabulary and rejected payment-retry and leader-fd tree-cleanup misapplications. Two v2 cards repair reproduction metadata while preserving immutable history.
Uncertain: kernel source checkout is absent; cloud syscall compatibility, new consolidated supervisor behavior and full process visibility outside constrained fixtures remain unverified. Source, models, isolated syscall observation and earlier authored acceptance artifacts support different claims.
Decision: retain the cloud supervisor as consolidation base with explicit identity/scope/coverage and helper-lifetime corrections. No product implementation, branch merge, reference edit or memory write was performed in this learning pass.
Refs: docs/linux-consolidation-learning.md; results/linux-repo-learning-20261030/reproducibility.json; results/linux-repo-learning-20261030/verify.json
