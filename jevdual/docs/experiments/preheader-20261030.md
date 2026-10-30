# Pre-header duplicate-ingress investigation

Hypothesis: plain Chrome form navigation may repeat a POST after an empty response; agent replay is not necessary.
True prediction: one browser activation can yield two ingresses and correlated network retry evidence, including a control without Footwork.
False prediction: duplication requires multiple activation/dispatch or incorrect service accounting.
Design: two fresh trials per normal/truncated/disconnect cell for direct HTTP and isolated browser controls; two fresh native Chrome disconnect trials, then installed normal and interrupted cross-app qualification. Instrumented browser trials retain network provenance and supplementary submission-event counts; uninstrumented native trials challenge instrumentation bias. No old unknown is replayed or promoted.
Primary metric: independently recorded HTTP ingress count per one admitted native activation (or explicitly labeled diagnostic browser/client activation).
Guardrails: owned numeric-loopback origins, fresh profiles and assets; no provider calls, network installs, personal profiles, arbitrary external endpoints or threshold tuning. Record every slot before invocation; preserve failed/incomplete trials. Observe identity before UI input; no uncertain action retries. Cleanup exact owned helpers only.
Decision rule: only identify a cause when traces distinguish activation, request/retry and ledger accounting. Fix a demonstrated local mechanism; if browser retransmission cannot be controlled under the current route, retain explicit unsupported status and single-ingress gate. Do not weaken qualification or substitute truncated loss. Any new guarantee requires explicit versioned contract decision.
Caps: 120 seconds per action, 30 minutes per live chain, at most two diagnostic reruns after a repaired probe; zero model-provider spend.
Verification: regression red/green, full key-free suite, Ruff/notebook/package checks, independent review, frozen installed nominal/interrupted chain. Record source and wheel hashes and finite support boundaries.

## Amendment: route comparison before execution
Add two fresh isolated Chrome fetch POST controls against the identical pre-header disconnect fault. Same fields/body and one activation, NetLog and handler observations; no fixture/runtime change. A passing diagnostic does not qualify native submission or create new reconciliation authority.

## Amendment: positively sealed fixture contract
Evaluate an optional new preadmitted evidence version whose terminal boundary is an irreversibly closed fixture producer, all request handlers drained, and final ledger snapshot atomically sealed. Same unique-ingress predicate and original fault. No claim of browser/network exactly-once delivery. Existing v1/v2 reads/unknowns retain their contracts. Test active-handler drainage, late input, source restart, tampering, duplicates, wrong operation/source and no retroactive enrollment. Installed schedule adds one fresh native fetch disconnect trial under this new policy, including actual controller kill after ingress, and read-only reconciliation after closure.

## Result
Observed causal evidence, fetch correction, sealed-source v3 qualification and finite limits are retained in results/preheader-20261030/report.md. Twenty-six controls and twelve live slots include failures and probe repairs. No old unknown was upgraded. Final suite: 2269 passed, 26 skipped. Hosted CI/merge remain separate follow-through.
