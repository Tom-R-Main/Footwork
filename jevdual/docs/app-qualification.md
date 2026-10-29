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

An explicit PID selects only that process, with first-observation app/PID/window checks. URL/title scope is persisted and bound into request identity and receipts. Every fresh/internal observation and input boundary rechecks the complete AX source and one pre-pruning address bar; unavailable or changed scope refuses input. Foreground-key fallback rechecks after its policy wait. Guarded observations withhold screenshots. A native Chrome result does not qualify the semantic browser adapter, arbitrary origins or tab/window birth.

## Installed qualification gate

All Finder/Preview/Chrome nominal cases, their assigned challenges and the interrupted connected chain must pass before the portfolio is qualified. Offline artifact transformations and HTTP calls only qualify harness components. Do not substitute direct filesystem/image/API edits for missing UI operations, clear unresolved history, change authority domains to retry uncertain work, or count a refusal as completed work.

The first installed run bound owned Finder/Preview resources, but Finder returned unknown delivery, Preview was blocked downstream, and Chrome refused incomplete scope evidence. Fixtures remained unchanged, the ticket ledger had zero requests, and owned windows/processes/listener were cleaned up. Stable file targeting, qualified native delivery and complete Chrome scope capture remain the concrete live gaps.
