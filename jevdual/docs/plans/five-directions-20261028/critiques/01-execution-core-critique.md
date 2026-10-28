# Critique: Plan 1, one durable execution core

Reviewed October 28, 2026 against `5d494c6`. Read-only; no tests or applications run.

**Verdict.** The diagnosis is sound and the plan is honest about uncertainty. But it proposes a new `execution/` store when most of that store already exists in `capability/journal.py`. Its first slice (native append) also barely touches the grant defect that motivates it. Keep the direction, re-scope the first slice, and build by extending the journal.

## 1. Factual claims

| Claim | Status | Evidence |
|---|---|---|
| Grant consumed before dispatch, pending saved after | **Holds** (line numbers off by about 3) | `grants.consume` at `session.py:966`; dispatch `try` at `:989`, calls at `:991`/`:1002`; `state.pending` at `:1018`, `state.save()` at `:1035` |
| Grant consumption rewrites a JSON file | **Holds, understated** | `grants.py:111-124`: unlocked load, decrement, then `write_text` (no temp file and rename, no `flock`). A torn write makes `load` raise at `:105`, and concurrent `do` calls can lose a decrement. `SessionState.save` has the same pattern (`session.py:86`). |
| Effect evidence recovered from presentation strings | **Holds, and is worse than stated** | `_NAVIGATED`/`_HOLDS` at `completion.py:33,35`, parsed at `:139`. The producer truncates with `repr(x[:80])` (`session.py:344-351`), so `field_holds` for a value longer than 80 characters carries a prefix, not the field's value. The plan misses this concrete defect. |
| Capability service persists intent and checks tokens and unresolved operations | **Holds** | `service.py:42-90`; `journal.begin` at `journal.py:227` |
| Service is "append-specific" | **Overstated** | The journal is generic over `move`/`args` (`journal.py:37-62`). It has `BEGIN IMMEDIATE` (`:425-431`), a process `flock` (`:160-162`), a unique token index, `Busy` blocking, `dispatching→unknown` on reopen (`:196-207`), and `prepared`-stage no-send recovery (`:209-225`). Only `backend.py` and `recovery.py` packets are append-specific. |

The plan's own records (`Attempt`, dispatch-start marker, unknown blocks successors, "only qualified no-send evidence releases a reservation") restate what `journal.py` and `test_capability_recovery.py:193-236` already implement. The plan should say so. As written, it invites a second store.

## 2. Feasibility and sequencing

- **The first slice does not exercise grants.** `append` is gated only by the keyword rule or the `extra` hook (`authorize.py:195-210`). It is not in `JUDGED_ROUTES` (`:44`) and does not replace content. A durable *native append* slice therefore rarely touches `grants.consume`, which is the defect cited as the reason for the work. The defect lives on gated `click`/`menu`/`hotkey`/replacement routes.
- **The failure is reproducible today without a crash harness.** `cmd_do` catches only `NativeBridgeError`/`RuntimeError` (`session.py:1014`). A `CancelledError`, a `KeyboardInterrupt`, or a browser-bridge `TimeoutError` propagates past the pending save. The result: the grant is spent, `grant_used` is logged (`:968`), and there is no `do` record. `test_session_scenarios.py:770` already shows the monkeypatch pattern (`NativeBridge.act = boom`).
- Milestones 2 and 3 are not independently shippable. "Typed evidence" needs attempt identity, and parity needs both. Milestone 2 could start first by having the producer emit a structured field next to the prose. That needs no execution core.
- Milestone 4 ("one operation family per change") has no count or exit.

## 3. Acceptance criteria

Falsifiable: "zero additional dispatches for replay of a recorded token", "zero accepted stale grants", "display wording cannot change the verdict", and "a crash test establishes only its injected boundary". The disconfirmation paragraph is a real decision rule.

The weak ones:

- "Crash at each boundary must retain a recoverable attempt." The boundaries are never listed.
- "Equivalent dispositions … through CLI, MCP and SDK" has no definition of equivalence. Session `do` has grants and label authorization. MCP has resource scope and no grants. These differ by design.
- "Zero additional dispatches" conflicts with the existing first-press `-25204` auto-retry (`native.py:1141-1150`). The plan must state whether a refusal followed by a retry counts as a dispatch.
- No notebook prediction is drafted. AGENTS.md requires one, committed before the test.

## 4. Risks and blind spots

- **Format readers.** `session.jsonl` is read by `completion.py`, `cli.py`, `scripts/m1_offline.py`, `scripts/m6_offline.py` and five test modules. A "compatibility view" must cover the offline eval scripts, or historical results stop recounting. CONTRIBUTING says numbers come from run directories.
- **Mislabelled no-send.** `NativeBridgeError` is turned into `"not dispatched"` (`session.py:1015`). Downstream code treats that as non-delivery (`completion.py:37,73`), which preserves earlier `field_holds`. The core must not inherit that label as qualified no-send evidence.
- Browser `bridge.act` with a `route` argument (`session.py:1001`) and browser-use private hooks are deferred to milestone 4. The browser is where non-`RuntimeError` exceptions are most likely.
- **User value.** No caller gains a capability before milestone 5.

## 5. Strongest ideas to keep

1. **A grant reservation in the same transaction as the intent row.** Add a `reservations` table to `journal.py`, holding grant id, uses, and operation id. Reserve at `begin`, commit on `sent`, release only on `not_sent` backed by a qualified no-send phase, and leave it held while the operation is `unknown`.
2. **Typed field readback.** The producer emits `{producer, resource, attempt_id, label, value_sha, value_len, truncated}` beside the prose. `completion.py` reads that structure, and the regex parsing becomes a versioned legacy reader for old sessions. Test: rewording the prose leaves the `Effect` list unchanged, and an 81-character append yields no prefix-valued `field_holds`.
3. **Token replay returns the recorded operation**, never a redispatch. `service.py:52-61` already does this; extend it to session `do`.
4. **Migration rule.** New sessions use the new store. Old sessions are read-only. A converted historical dispatch with no receipt becomes `unknown`, and conversion never invents evidence.
5. **The stop rule.** If the core needs surface-specific branching throughout, keep the shared records and journal and keep per-adapter services.

## 6. Ideas to drop or shrink

- A new `execution/` package with its own storage. Extend the journal instead.
- Seven record types up front (`SurfaceBinding` … `Result`). Start with `Attempt`, `Reservation` and `Evidence`, and add others when a second adapter needs them.
- The SDK `observe/perform/reconcile` surface. It is a third API before the two existing ones agree.
- The installed-adoption milestone. That is release work that Plans 2 and 5 own better.

**Suggested first slice:** a notebook prediction that a `CancelledError` raised from `bridge.act` on a granted `click` leaves a spent grant and no `do` record. Then a scenario test showing that failure, then a fix that routes session `do` through `Journal.begin` with a reservation.
