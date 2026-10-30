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
