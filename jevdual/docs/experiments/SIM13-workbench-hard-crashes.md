# SIM13: Hard crashes at command boundaries

Hypothesis: the durable command identity, request, admission and receipt records let the simulated body and workbench recover from abrupt process death without replaying effects. A crash that lacks conclusive receipt evidence must remain blocked, regardless of what the camera appears to show.

Predictions if true: SIGKILL at controlled in-flight and uncertain-command boundaries preserves the original command identity and single send. Completed retained receipts can be read after restart and leave the workbench paused until explicit Resume obtains fresh evidence. Incomplete native/effect persistence cannot silently become successful or autorun. Restart invalidates earlier leases and decisions, owns or fences interrupted child processes and does not reuse cached health or images as authority.

Predictions if false: stage association disappears, requests or outcomes diverge, an action is resent, orphan processes continue writing across restarted ownership, incomplete evidence is promoted to success, a corrupt root starts runnable or the browser cannot explain the blocked recovery boundary.

Design: inspect body and workbench persistence and process ownership first. Commit causal predictions before targeted crash regressions. Preserve the previous paused product. Build an owned diagnostic harness that synchronizes with durable command boundaries, records exact pre-crash expectations and sends SIGKILL only to its registered process or proven owned process group. Retain every meaningful failed attempt. Freeze measured source before actual Codex calls. Drive actual image-guided jobs and crash/recovery through the browser, with an independent post-stop scorer checking exact commands, sends, receipts, native results, child cleanup and visible paused/uncertain/blocked transitions.

Primary metric: every tested hard-crash boundary has zero replayed actions and zero successor admissions before sufficient historical proof and explicit Resume; recovery succeeds only where proof exists.

Secondary checks: retained command identity and request bytes; changed boot invalidates stale lease/decision; no surviving owned planner/native writer crosses the restart boundary; missing or inconsistent proof remains visibly blocked; completed jobs retain measurement and reset evidence.

Guardrails: loopback simulation and fresh owned roots only; no hardware or existing project processes are crash targets; no retries of effect commands; no inferred success from camera position; no relaxed source, identity, freshness, lease or uncertainty checks; narrowly scoped diagnostic synchronization cannot grant authority; no manual pose correction; actual-model runs use committed source; independently score stopped evidence before live handoff appends events.

Decision rule: adopt only independently verified recovery behavior. A safely blocked incomplete command is a valid safety result and an explicit usability limitation, not successful recovery. Do not claim power-loss durability or arbitrary crash-point qualification from a finite set of process-kill tests.

## Result

Held for four selected boundaries on frozen source `4e2dd74d27ec07f0b5a42039e0f30016402cf050`. Three actual image-guided jobs recovered their exact historical receipts after SIGKILL and completed measurement/reset; the saved-native-state-before-receipt case remained blocked. All 127 commands in the qualified runs had one wire send and fresh admission proof; 41 model decisions were bound to exact TCP images and lower intents/results. Twenty-two new conformance checks passed. Two additional native-gap attempts were not qualified and remain reported: a missing-database scorer failure and a capture-root mismatch. An event-publication crash window also remains an explicit recovery limitation. See [report](../../results/workbench-hard-crashes-20261012/report.md).
