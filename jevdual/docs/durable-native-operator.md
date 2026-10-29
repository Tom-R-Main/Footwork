# Durable native operator sessions

Experimental native CLI admission, introduced after the October 28 dispatch correction. Opt in when starting a **fresh** session directory:

```sh
footwork desktop start "Inspect the selected window" --app Calculator \
  --session /absolute/path/session-a --authority /absolute/path/authority.sqlite
footwork desktop status --session /absolute/path/session-a
```

Every participating session must select the same canonical absolute authority database. Existing sessions without `authority`, the browser route, MCP, autonomous loops, older binaries and other authority databases are outside this coordination guarantee. The [October 28 installed trials](../results/move-submit-20261028/report.md) exercised the owned nominal and interrupted/truncated-response app chains. Those are finite fixture results; the pre-header-disconnect qualification gate remains open. The October 29 review tightens recovery and service-evidence gates without expanding that support claim.

## Commands and replay

Use `footwork desktop do ... --token NAME --session ...` for a request whose response may be lost. Repeating that token with the same raw arguments returns the recorded operation status before opening the app, resolving secret placeholders, loading carried values or judging authority. Changing the words, route, source session or explicit authorization flags with the same token conflicts. Omitting the token generates and prints one; retain it before relying on replay. A replay never means “try the input again.”

`status` reports operation IDs, tokens, lifecycle, disposition, delivery phase and reservation state, plus the domain's unresolved operations. It needs no live app. Normal observation commands remain available while an operation is unresolved. An uncertain operation is not successful completion.

Use `status --reconcile` to reconcile this session's operations from retained runtime evidence or the narrow pre-admitted ticket producer described below, or add `--operation OP_ID` to select one owned operation. This command neither binds the app nor dispatches input. It accepts no supplied receipt file, manual outcome assertion or current-text shortcut. Repeating reconciliation is idempotent.

`grant` records exact, session-scoped authority in the database. For an action that requires a grant, admission reserves a use in the same transaction as its intent. Actions already allowed by the existing policy record that basis without an artificial grant. Legacy `grants.json` is not imported as concurrent authority.

## Recovery and ownership

The command owns the database before reloading mutable session state. Competing participating commands receive a typed ownership refusal. A durable intent in `prepared` precedes the committed `started` marker; input cannot begin before that marker. Reopening a qualified prepared-only record establishes no-send and releases its reservation once. A started attempt with no qualified result remains unknown. Exact replay and missing session-log projection repair do not dispatch new input.

`done` checks unresolved custody in its own domain and explicitly referenced context domains before key loading, app access or verifier calls. Verifier acceptance cannot close an unresolved operation. Legacy pending uncertainty is also a blocker. Context domain locks remain held through completion.

Interrupted JSONL projection bytes are preserved in a private quarantine file before the readable projection is replaced atomically. Valid records remain readable; canonical admission, delivery and replay still come from the authority database. Legacy journal operations without operator evidence remain visible unresolved blockers and cannot inherit operator receipts.

Any unresolved operation blocks **all new mutations in this authority domain**, including mutations in other apps. This conservative rule protects cross-app handoffs without claiming concurrent artifact ownership. Observation, status and recovery reads are available. Do not change authority databases or use a legacy executor as a way to retry unresolved work.

Reservation and effect state are separate: unknown delivery holds the reserved use; qualified delivery spends it even if the effect is unknown; qualified no-send releases it. A spent reservation does not unblock an unknown effect. SDK delivery counts are retained separately from attempted input. A visible change, window agreement or matching file alone cannot establish who caused a historical effect.

After the bridge fully returns, the runtime retains an immutable execution receipt before finalizing the operation. Its schema/producer version, request digest, session/operation, resource binding, admitted observation/target, capture interval and settled runtime custody must agree. If finalization or the response is lost after that receipt is committed, reconciliation can finish the operation and settle authority once. Missing, unsupported, contradictory or tampered receipts preserve the unknown block. Interrupted calls that never return cannot manufacture such a receipt. Older unknown operations without a qualified retained receipt remain unknown.

## Structured observations and predicates

Participating sessions record structured observations with capture generation/interval, source binding, producer version, coverage and limits. The operation's admitted target and the native bridge's revalidated target are linked explicitly; live checking does not silently replace one identity with another. Browser semantic coverage is recorded before the text cap and retains separately clipped field-preview flags.

Execution, current-state and persistence evidence remain distinct. A complete exact AX append readback can establish the full field value at its capture interval, beyond the legacy 80-character prose preview. A changed fresh projection limits that current-state claim. Generic SDK previews, incomplete readbacks and secret-redacted values do not become exact facts. Malformed typed evidence cannot fall back to stronger prose interpretation; legacy records remain readable with their existing limits.

A direct AX menu acknowledgement establishes delivery, not its application effect. Disk/window agreement is a separate persistence predicate and does not establish intended destination, task completion, or who caused the save. SDK `confirmed` in a retained execution receipt remains the runtime's observed step effect; it is not an independently verified task postcondition. App-specific oracles are still required for Finder, Preview and browser qualification.

## Owned ticket service reconciliation

The owned native Chrome fixture may enroll its exact ledger, origin, expected fields and artifact through `--ticket-manifest` before submission. A matching current row alone is insufficient. The v2 producer requires one matching ingress, one durable row and a positive supported response-boundary event tied to that ingress. The response mode is bound before admission; the handler records its event only after flushing headers for normal or truncated-body responses.

A pre-header-disconnect mode cannot qualify, even during the transient first-ingress interval before a duplicate arrives. Missing response evidence preserves uncertainty. This guard does not diagnose or prevent the second HTTP request.

The retained service receipt is distinct from native delivery evidence and supplies no native input count. The Chrome handoff must use that admitted submission's exact source, origin, request fields and artifact identity; another ledger or nonce cannot complete it. Historical v1 final receipts remain readable and replayable, but a v1 unknown cannot obtain new v2 qualification or finalize from an old v1 service receipt. Existing records are not rewritten.

## Current limits

- Binding checks boot identity, process creation time, PID, session generation and window number, followed by existing fresh-target checks. The source supplies no independent window-creation identity; same-number window reuse is not qualified.
- Direct AX append acknowledgement and qualified SDK delivery are retained producer evidence. A menu acknowledgement or other delivered input whose application effect remains unknown still leaves the operation blocking.
- General reconciliation is limited to validated retained runtime returns and prepared-only recovery. The explicitly pre-admitted owned ticket producer is the narrow service exception. Matching external state alone cannot release custody; there is no universal app-effect reconciliation producer.
- Durable start binds an existing native window. Browser startup, startup URL navigation and unsupported native navigation are refused. Reusing a session directory preserves its history by refusing replacement. Incompatible participating protocol versions refuse writes.
- Secret replay/status works after an environment value disappears. Fresh binding refuses until previously used secret values are available for redaction; new durable input with a secret shorter than three characters is refused before binding. Restore the original values: the gate checks availability/length, not equality with the earlier value, so observations after secret rotation are unqualified. Secret-bearing snapshots are copied without mutating their frozen objects.
- Process `SIGKILL` tests do not establish power-loss durability or independent onboarding. Installed app claims require their separately recorded UI trajectories and independent postconditions.

See [app qualification](app-qualification.md) for the exact Finder/Preview/Chrome routes, and the [implementation plan](plans/five-directions-20261028/IMPLEMENTATION-PLAN.md) for the remaining release gates.
