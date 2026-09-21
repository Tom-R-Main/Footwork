# Design notes

## The seam
browser-use's `Agent.step` is prepare, decide, execute, post-process. The decide phase is
`_get_next_action`, whose only contract is to leave an `AgentOutput` in `state.last_model_output`.
`DualProcessAgent` overrides that method and `_execute_actions`; everything else, including the
serializer, watchdogs, history, GIFs and callbacks, is inherited unchanged. Contract tests
(`tests/contract`) pin every seam at browser-use 0.13.10 so an upgrade fails loudly.

## Why not a fork
Upstream moves quickly and its value is the battle-tested observer and executor. A package that
depends on a pinned version keeps the upgrade path a version bump plus a rerun of the eval rig.
Patches to hot paths are installed at import time behind contract tests, with pure-Python twins so
the package works without the extension.

## What each system owns
System 1 decides; System 2 owns meaning. Jev picks an index from a menu code built, never emits a
selector or text, and its "done" is an opinion that verification must confirm. The arbiter's rules
are code, its thresholds live in a TOML file, and every verdict names the rule and the numbers.
Text is composed from a literal in the task, a secret placeholder, or a small helper behind a
strict JSON contract; otherwise the step escalates.

## What the evals taught
- Confidence floors did not bind on the local site; Jev's confidences sit near 1.0. The nouls did
  the work: `stuck` flagged the form loops on 16 of 21 steps, `destructive` stopped the delete.
- Two mechanisms, not thresholds, closed the dev gap: verification must know whether the task asks
  for an answer, and the destructive gate must cover System 2's actions.
- Rig defects can masquerade as agent defects: end-state capture after `run()` returns fails
  silently because upstream closes the session; the serializer's text drops some inline nodes;
  a policy factory bound to the first arm ran two S1-only arms. Each is now a test.

## The Rust rule
Ports paid off where they deleted a Python algorithm (paint order) or an unnecessary Python object
(the per-node uuid), and where the input was already flat (evidence matching). They did not pay
off where the result had to be rebuilt as Python dataclasses for downstream readers (snapshot
lookup). The remaining DOM cost is object construction consumed attribute by attribute; closing it
means changing what downstream reads, which is the decision recorded in
`results/r7-boundary-decision.md`.
