# Reusable body recovery

The two host recovery gaps are fixed, and the shared body contract is separated from bench operations. Three final browser cases passed independent post-stop scoring on `c00c65cf29fb468cbf2c1601d44f0e5d26bf4b54`.

| Final case | AI decisions | Interrupted request | Commands | Outcome |
|---|---:|---:|---:|---|
| Event saved before host manifest | 14 | 0 | 43 | Exact receipt recovered; measurement and contact reset completed |
| Host killed during actual planning, then measurement reply lost | 14 | 1 | 44 | All observed old process identities/groups absent; fresh planning; exact measurement receipt recovered; reset completed |
| Native motion saved before completion receipt | 1 | 0 | 4 | Original command remains uncertain; two receipt checks cannot release it |

All 91 commands had one wire POST. The final runs retained 29 actual image-guided decisions and one interrupted reservation. Both completed jobs have exactly one independently checked SQLite measurement and a verified native contact reset. The missing-receipt case remains quarantined, with no successor command or automatic reset. Evidence is in the three case folders and `summary.json`.

## Implementation

Startup validates the immutable event sequence and retained activity before importing an orphan audit tail. It repairs the index, never the physical outcome. Malformed or inconsistent evidence refuses startup; an unfinished command keeps its identity and requires its exact receipt.

Planning uses a host-liveness pipe, a call ownership lock, atomic proof publication and a new owner after restart. Prompt delivery remains nonblocking while checking liveness and timeout. The guardian accounts for observed child identities and withholds closure if one survives. It never signals arbitrary retained PIDs. Codex shell snapshots are disabled. The final actual planning gate still observed transient node/git processes in other groups; independent qualification accounted for every captured identity/group before continuation.

`body_contract.py` contains identity, epoch, lease and envelope rules. `persistent_body_client.py` supplies durable single-send transport and exact receipt reads with required schema hooks. `bench_body_contract.py` contains reachable zones, movement bounds, bench actions and image/result validation. Existing `BodyClient` callers retain their bench facade. A separate simulated camera-pointing vocabulary exercised the shared client over real TCP without importing bench, MuJoCo or numpy.

The browser shows interrupted history and retired planners. When the host is unavailable, cached job selection keeps actions disabled and the camera explicitly labelled as retained evidence. Recovery stays paused until explicit Resume obtains a fresh challenge.

## Checks and review

The retained logs cover 43 body/client/contract/network checks, 59 existing operator/HTTP/health regressions, 25 final focused planner/journal checks and 25 final native/scorer/trial controls. The unique test identifiers are listed in `checks/test-identifiers.json`. Focused independent review found and closed a blocked-input availability concern, incomplete descendant/leader proof checks, and offline camera provenance drift. Scoped Ruff and notebook checks are recorded separately.

The expected pre-fix stdin stall did not reproduce on this Mac: the original guardian buffered the valid 64 KiB prompt. The revised path was tested under partial-delivery backpressure and retired its child after host death. This is a failed initial prediction, not evidence of a prior reproduced stall.

## Earlier attempts

`attempt-ledger.json` separates the earlier passing publication predecessor from the unqualified planning capture race. The original screenshots, API record and private roots are retained. The failed Darwin cleanup attempt, source-edit-invalidated network test, and partial proof observation are recorded in the engineering notebook. Final metrics exclude the predecessor and failed capture attempt.

## Scope

This qualifies selected process-SIGKILL boundaries in a loopback simulation. It does not establish power-loss durability, arbitrary instruction-level recovery, OS-level containment of unsampled detachment, authenticated remote control or physical device safety. Client event-publication/pre-send windows remain outside this host repair. Identity admission remains simulation-only; a hardware controller must qualify its own operation bounds and evidence. Journal and job budgets remain finite.

The saved scores and snapshots describe stopped trials before live handoff appends administrative restart events. Handoff state and its browser URL are recorded separately in `handoff.json`.
