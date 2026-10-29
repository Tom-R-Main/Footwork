# Diversified app qualification

The October 28 harness covers Finder file organization, Preview image transformation, Chrome ticket submission and interrupted handoffs. **The installed portfolio has not passed qualification.** See [the run report](../results/app-portfolio-20261028/report.md) for separate offline and installed evidence.

## Fixture and independent checks

`jevdual.app_oracles.create_fixture(root)` creates a fresh owned scratch tree with an asymmetric PNG, preserved original, same-basename decoy and sibling sentinels. Keep authority, handoff and server databases outside that fixture subdirectory. `check_finder` verifies exact output path, old absence, unchanged bytes and siblings; `check_preview` independently decodes saved pixels/dimensions against the specified clockwise transform. Neither check performs the UI effect or establishes its author.

Start the owned local form with:

```sh
python -m jevdual.app_qualification --root /absolute/run/ticket-fixture --lose-reply-once
```

It prints an owned PID, loopback URL and database. POST ingress and deduplicated rows are recorded separately in SQLite, so one row cannot hide duplicate requests. `TicketStore.check(expected)` checks exact request ID, filename, orientation and digest. Lost responses and fixture restart retain both ledgers.

`HandoffRun(root, authority, epoch)` dispatches no app actions. Call `begin(stage, session_id=...)` before each stage, then `complete(stage, operation_ids, verify, artifact)` after UI execution. It requires settled retained receipts from the bound session/app and an independent check bound to the same artifact identity. Preview preserves its input path and verifies clockwise rotation; Chrome preserves the entire input identity and rechecks the bound ticket database read-only. Stale/tampered input, unknown custody and unbound success dictionaries refuse advancement. Stage checkpoints survive process death; an interrupted active input cannot authorize blind redispatch.

These gates combine custody and current postcondition evidence. They still require a live trajectory showing the intended UI operations; a generic app click plus matching externally modified bytes is not installed UI qualification.

## Chrome route and scope

The semantic browser route lacks durable tab/document incarnation and remains refused for durable admission. The separate native Chrome candidate supports:

```sh
footwork desktop start "Owned local fixture" --app "Google Chrome" --pid OWNED_PID \
  --window FIXTURE_TITLE --native-url EXACT_HTTP_LOOPBACK_URL --native-title FIXTURE_TITLE \
  --authority /absolute/run/authority.sqlite --session /absolute/run/chrome
```

An explicit PID selects only that process, with first-observation app/PID/window checks. URL/title scope is persisted and bound into request identity and receipts. Every fresh/internal observation and input boundary obtains a separate bounded complete trusted-toolbar capture (`chrome.ax-toolbar/v1`), excluding web-content descendants. Exact PID/window, one real toolbar address bar, readable URL and fixture title are required. An incomplete page capture does not invalidate a complete toolbar capture; an incomplete toolbar refuses. Scope coverage is retained with execution evidence. Foreground-key fallback rechecks after its policy wait. Guarded observations withhold screenshots. A native Chrome result does not qualify the semantic browser adapter, arbitrary origins or tab/window birth.

## Owned Finder targets and native predicates

For the synthetic asset fixture, start durable Finder with `--finder-manifest /absolute/fixture/fixture.json`. Startup finds the unique window containing the exact seeded file, even among identically titled windows. Use `do type file:/absolute/fixture/inbox/asset.png renamed.png` for a rename. Grants accept the same selector. Fresh Foundation-resolved AXURL, retained device/inode, manifest scope, complete bounded AX traversal and current geometry establish the target; stale numeric IDs and basename matching do not. Wrong directories, symlinks, replaced inodes, duplicate windows and unreadable subtrees refuse.

The rename producer selects the sole exact row, opens File to validate Rename, enters the real editor, writes its value and sends one foreground Return. It retains acknowledged input counts as a lower bound and qualifies only an observed same-inode path transition. Name-cell display changes alone remain insufficient. This route currently supports rename, not move.

Preview's first Rotate Left/Right can qualify a new exact Undo Rotate marker on the same bound document. Save qualifies only an observed edited-state or file-digest transition following its acknowledged menu press. A plain menu acknowledgement stays unknown. Preview can autosave independently; saved pixels and persistence require the separate oracle. These narrow native predicates are checked against the admitted operation, arguments, PID/window and producer schema before reconciliation.

## Installed qualification gate

All Finder/Preview/Chrome nominal cases, their assigned challenges and the interrupted connected chain must pass before the portfolio is qualified. Offline artifact transformations and HTTP calls only qualify harness components. Do not substitute direct filesystem/image/API edits for missing UI operations, clear unresolved history, change authority domains to retry uncertain work, or count a refusal as completed work.

The first installed run bound owned Finder/Preview resources, but Finder returned unknown delivery, Preview was blocked downstream, and Chrome refused incomplete scope evidence. Fixtures remained unchanged, the ticket ledger had zero requests, and owned windows/processes/listener were cleaned up. Stable file targeting, qualified native delivery and complete Chrome scope capture remain the concrete live gaps.

The [repair rerun](../results/app-repair-20261028/report.md), on frozen commit `4c2c4cf`, completed installed exact rename and Preview rotation/autosave, plus controller-kill recovery between them. Trusted Chrome scope admission and mismatch refusal passed. The installed Chrome form remained unavailable in the background while foreground setup yielded to user activity. The required Finder move and Chrome submission/reconciliation remain open; the rename-only partial chain does not qualify the full portfolio. All old unknown operations remain retained.
