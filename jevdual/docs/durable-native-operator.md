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

`grant` records exact, session-scoped authority in the database. For an action that requires a grant, admission reserves a use in the same transaction as its intent. Actions already allowed by the existing policy record that basis without an artificial grant. Legacy `grants.json` is not imported as concurrent authority.

## Recovery and ownership

The command owns the database before reloading mutable session state. Competing participating commands receive a typed ownership refusal. A durable intent in `prepared` precedes the committed `started` marker; input cannot begin before that marker. Reopening a qualified prepared-only record establishes no-send and releases its reservation once. A started attempt with no qualified result remains unknown. Exact replay and missing session-log projection repair do not dispatch new input.

Any unresolved operation blocks **all new mutations in this authority domain**, including mutations in other apps. This conservative rule protects cross-app handoffs without claiming concurrent artifact ownership. Observation, status and recovery reads are available. Do not change authority databases or use a legacy executor as a way to retry unresolved work.

Reservation and effect state are separate: unknown delivery holds the reserved use; qualified delivery spends it even if the effect is unknown; qualified no-send releases it. A spent reservation does not unblock an unknown effect. SDK delivery counts are retained separately from attempted input. A visible change, window agreement or matching file alone cannot establish who caused a historical effect.

## Current limits

- Binding checks boot identity, process creation time, PID, session generation and window number, followed by existing fresh-target checks. The source supplies no independent window-creation identity; same-number window reuse is not qualified.
- Direct AX append/menu paths without qualified delivery evidence can remain unknown even when a current readback matches. This release guarantees retained custody and no blind redispatch, not universal native completion.
- There is no general reconciliation producer for started unknown operations yet. Status preserves their block; manual assertions cannot certify delivery or release custody. Prepared-only recovery is the currently qualified automatic no-send case.
- Durable start binds an existing native window. Browser startup, startup URL navigation and unsupported native navigation are refused. Reusing a session directory preserves its history by refusing replacement. Incompatible participating protocol versions refuse writes.
- Secret replay/status works after an environment value disappears. Fresh binding refuses until previously used secret values are available for redaction; new durable input with a secret shorter than three characters is refused before binding. Restore the original values: the gate checks availability/length, not equality with the earlier value, so observations after secret rotation are unqualified. Secret-bearing snapshots are copied without mutating their frozen objects.
- Process `SIGKILL` tests do not establish power-loss durability, installed Finder/Preview/Chrome support or independent onboarding.

The next stage adds producer-backed evidence and qualified reconciliation before the diversified installed-app portfolio. See the [implementation plan](plans/five-directions-20261028/IMPLEMENTATION-PLAN.md).
