# October 28 operator review and PR integration

## RV1 · prediction · 2026-10-29 14:15
Hypothesis: integrating main's merged control-state/blocker and installer-diagnostic work with the October 28 native operator preserves both durable custody semantics and complete observed control state.
Test: inspect each merge overlap against both parents, run current key-free unit/CLI/package checks and targeted control-state plus admission/replay/evidence regressions. Bind final review/CI to the actual PR head; retain yesterday's installed evidence as historical proof rather than a claim about changed runtime.
Predicts: unresolved mutation still blocks new admission; original-token replay and qualified reconciliation send no input; repeated controls preserve observed state and strict identity. Current installed CLI/package and source-resource checks remain usable.
Against: integration drops either parent's state/coverage/authority fields, admits or retries uncertain input, falsely qualifies a receipt, or passes only by removing a meaningful assertion.
Refs: base 5d494c6a22921d092e67399badce708e8418bf2a; reviewed target a9b260180980e305ebc414568cf92ab02987f941; main 8de9c9ab797e0daafd8b897df61ec03006bde31f; results/move-submit-20261028/report.md

## RV2 · prediction · 2026-10-29 14:18
Hypothesis: A native fallback must require qualified structured no-send, and Finder rename must recheck owned window/selection immediately before its delayed menu leaf and editor write.
Test: Reproduce opaque/mixed delivered keyboard errors and a focus/selection switch during Rename enablement, then repair the narrow gates.
Predicts: Opaque or positively delivered failures send no second key; switched Finder ownership receives no Rename/write; documented structured no-send can still take its permitted fallback.
Against: A text-only error authorizes retry, or another window/editor receives input.
Refs: independent read-only reviews of a9b260180980e305ebc414568cf92ab02987f941; docs/plans/five-directions-20261028/IMPLEMENTATION-PLAN.md

## RV3 · prediction · 2026-10-29 14:18
Hypothesis: Durable public recovery and completion remain usable after interrupted JSONL projection and when the shared authority contains legacy unknown operations.
Test: Reproduce truncated projection followed by replay/new click/done, reused legacy-journal status, and a verifier accept while own/domain/context custody is unresolved. Keep authority decisions independent from corrupt display logs and provider votes.
Predicts: Status reports conservative legacy unknowns, repaired projection readers remain usable, and done refuses unresolved custody before provider/native work.
Against: Corrupt logs prevent canonical recovery, legacy state disappears or status crashes, or verifier acceptance closes unresolved custody.
Refs: independent read-only reviews of a9b260180980e305ebc414568cf92ab02987f941; docs/plans/five-directions-20261028/IMPLEMENTATION-PLAN.md

## RV4 · prediction · 2026-10-29 14:18
Hypothesis: Ticket qualification must bind a supported completed response boundary and its exact admitted service source into the Chrome handoff.
Test: Pause a handler after first ingress before pre-header disconnect and attempt reconciliation; challenge Chrome completion with another database/nonce. Add explicit producer response provenance and exact scope/oracle binding without diagnosing or suppressing transport duplication.
Predicts: Transient first ingress or unsupported disconnect never seals a success; supported completed response and matching admission may qualify; an unrelated ledger/nonce cannot advance Chrome.
Against: An early snapshot irreversibly qualifies a later-duplicating fault, or evidence from submission B completes submission A.
Refs: independent read-only reviews of a9b260180980e305ebc414568cf92ab02987f941; docs/plans/five-directions-20261028/IMPLEMENTATION-PLAN.md
