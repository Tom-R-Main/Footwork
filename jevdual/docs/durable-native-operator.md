# Durable native operator sessions

Experimental native CLI admission, introduced after the October 28 dispatch correction. Opt in when starting a **fresh** session directory:

```sh
footwork desktop start "Inspect the selected window" --app Calculator \
  --session /absolute/path/session-a --authority /absolute/path/authority.sqlite
footwork desktop status --session /absolute/path/session-a
```

Every participating session must select the same canonical absolute authority database. Existing sessions without `authority`, the browser route, MCP, autonomous loops, older binaries and other authority databases are outside this coordination guarantee. The feature has simulated command and process-crash coverage; installed app qualification remains pending.

## Commands and replay

Use `footwork desktop do ... --token NAME --session ...` for a request whose response may be lost. Repeating that token with the same raw arguments returns the recorded operation status before opening the app, resolving secret placeholders, loading carried values or judging authority. Changing the words, route, source session or explicit authorization flags with the same token conflicts. Omitting the token generates and prints one; retain it before relying on replay. A replay never means “try the input again.”

`status` reports operation IDs, tokens, lifecycle, disposition, delivery phase and reservation state, plus the domain's unresolved operations. It needs no live app. Normal observation commands remain available while an operation is unresolved. An uncertain operation is not successful completion.

Use `status --reconcile` to reconcile this session's operations from retained runtime evidence, or add `--operation OP_ID` to select one owned operation. This command neither binds the app nor dispatches input. It accepts no supplied receipt file, manual outcome assertion or current-text shortcut. Repeating reconciliation is idempotent.

`grant` records exact, session-scoped authority in the database. For an action that requires a grant, admission reserves a use in the same transaction as its intent. Actions already allowed by the existing policy record that basis without an artificial grant. Legacy `grants.json` is not imported as concurrent authority.

## Recovery and ownership

The command owns the database before reloading mutable session state. Competing participating commands receive a typed ownership refusal. A durable intent in `prepared` precedes the committed `started` marker; input cannot begin before that marker. Reopening a qualified prepared-only record establishes no-send and releases its reservation once. A started attempt with no qualified result remains unknown. Exact replay and missing session-log projection repair do not dispatch new input.

Any unresolved operation blocks **all new mutations in this authority domain**, including mutations in other apps. This conservative rule protects cross-app handoffs without claiming concurrent artifact ownership. Observation, status and recovery reads are available. Do not change authority databases or use a legacy executor as a way to retry unresolved work.

Reservation and effect state are separate: unknown delivery holds the reserved use; qualified delivery spends it even if the effect is unknown; qualified no-send releases it. A spent reservation does not unblock an unknown effect. SDK delivery counts are retained separately from attempted input. A visible change, window agreement or matching file alone cannot establish who caused a historical effect.

After the bridge fully returns, the runtime retains an immutable execution receipt before finalizing the operation. Its schema/producer version, request digest, session/operation, resource binding, admitted observation/target, capture interval and settled runtime custody must agree. If finalization or the response is lost after that receipt is committed, reconciliation can finish the operation and settle authority once. Missing, unsupported, contradictory or tampered receipts preserve the unknown block. Interrupted calls that never return cannot manufacture such a receipt. Older unknown operations without a qualified retained receipt remain unknown.

## Structured observations and predicates

Participating sessions record structured observations with capture generation/interval, source binding, producer version, coverage and limits. The operation's admitted target and the native bridge's revalidated target are linked explicitly; live checking does not silently replace one identity with another. Browser semantic coverage is recorded before the text cap and retains separately clipped field-preview flags.

Execution, current-state and persistence evidence remain distinct. A complete exact AX append readback can establish the full field value at its capture interval, beyond the legacy 80-character prose preview. A changed fresh projection limits that current-state claim. Generic SDK previews, incomplete readbacks and secret-redacted values do not become exact facts. Malformed typed evidence cannot fall back to stronger prose interpretation; legacy records remain readable with their existing limits.

A direct AX menu acknowledgement establishes delivery, not its application effect. Disk/window agreement is a separate persistence predicate and does not establish intended destination, task completion, or who caused the save. SDK `confirmed` in a retained execution receipt remains the runtime's observed step effect; it is not an independently verified task postcondition. App-specific oracles are still required for Finder, Preview and browser qualification.

## Current limits

- Binding checks boot identity, process creation time, PID, session generation and window number, followed by existing fresh-target checks. The source supplies no independent window-creation identity; same-number window reuse is not qualified.
- Direct AX append acknowledgement and qualified SDK delivery are retained producer evidence. A menu acknowledgement or other delivered input whose application effect remains unknown still leaves the operation blocking.
- Reconciliation is limited to validated retained runtime returns and prepared-only recovery. A process interrupted before receipt retention, an unknown effect, or matching external state alone cannot release custody. There is no universal app-effect reconciliation producer.
- Durable start binds an existing native window. Browser startup, startup URL navigation and unsupported native navigation are refused. Reusing a session directory preserves its history by refusing replacement. Incompatible participating protocol versions refuse writes.
- Secret replay/status works after an environment value disappears. Fresh binding refuses until previously used secret values are available for redaction; new durable input with a secret shorter than three characters is refused before binding. Restore the original values: the gate checks availability/length, not equality with the earlier value, so observations after secret rotation are unqualified. Secret-bearing snapshots are copied without mutating their frozen objects.
- Process `SIGKILL` tests do not establish power-loss durability, installed Finder/Preview/Chrome support or independent onboarding.

The next stage qualifies app-specific outcomes and persistence in the diversified installed-app portfolio. See the [implementation plan](plans/five-directions-20261028/IMPLEMENTATION-PLAN.md).
