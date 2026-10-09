# The first Footwork capability slice

This local development slice exposes four MCP tools: `bind`, `observe`, `act`, `status`.
An existing agent reads a value from a local browser fixture, appends it to a selected
TextEdit document, and checks exact field content. The host owns the plan. Footwork
records append intent before dispatch and retains an unknown operation after process
death. It never repeats input through `status`.

This is a scoped macOS prototype, not a released installable package. Browser and native
drivers remain at the repository's pinned versions. Live agent acceptance and the raw
backend comparison have separate preregistrations in
[the notebook](notebook/2026-10-09-capability-slice.md) and
[C1](experiments/C1-capability-slice.md). Check their outcomes before treating the slice
as qualified.

## Setup for the fixture owner

Use an existing project environment. Start a loopback HTTP fixture in a dedicated browser
window and open a project-owned plain-text fixture in TextEdit. The fixture owner supplies
the exact application PIDs/window IDs and document path; the agent cannot broaden them.
The server attaches to those resources and creates no browser, app, tab or document.
Required macOS Accessibility permissions must already be granted to the runtime.

Create a scope file in the run directory, using actual fixture IDs:

```json
{
  "task": "fixture-run-001",
  "source": {
    "pid": 123,
    "window_id": 456,
    "url": "http://127.0.0.1:8000/"
  },
  "destination": {
    "pid": 789,
    "window_id": 1011,
    "document": "/absolute/project/run/fixture.txt"
  }
}
```

The source is read-only. Only a destination append is offered. Other URLs, application
selection, generic clicks/keys, saves, shell and driver passthrough are outside this slice.
Scope is trusted startup configuration, not an argument the model can rewrite.

Launch the local server:

```sh
uv run --no-sync python -m jevdual.capability.mcp_server \
  --scope /absolute/project/run/scope.json \
  --journal /absolute/project/run/operations.sqlite
```

Run this from `jevdual/`. A Claude Code registration can invoke the environment's Python
directly; the paths below are placeholders to replace before running:

```json
{
  "mcpServers": {
    "footwork": {
      "command": "/absolute/project/jevdual/.venv/bin/python",
      "args": [
        "-m", "jevdual.capability.mcp_server",
        "--scope", "/absolute/project/run/scope.json",
        "--journal", "/absolute/project/run/operations.sqlite"
      ]
    }
  }
}
```

The prototype does not write the host's global configuration. A temporary MCP config
under the owned run directory can be passed to a fresh host session. Experiments must
restrict the session to these tools; an agent using shell/source or other computer-use
tools has not demonstrated this interface's usability. Provider calls and host configuration
writes follow the mailbox's explicit authorization boundary.

## What the agent does

1. `bind({"name":"source"})` returns source text and a resource handle.
2. Read the requested value from that observation.
3. `bind({"name":"destination"})` returns current document content and an append target.
4. `act({"target":"<offered target>","text":"<source value>"})` records intent, validates
   the target/content and appends. Optionally include a `client_token` for repeat-safe receipt lookup;
   use a new token for each intended effect and reuse it only for that same operation.
5. Inspect the operation's exact readback. `observe({"resource":"<destination resource>"})`
   independently shows current field content.

The target packages its resource, observation and allowed move. Every new observation
expires that resource's previous targets. Ambiguous/stale targets require a fresh observation,
and a changed destination prefix refuses the append before sending it.

Readback checks exact original content plus the intended insertion (with a newline if the
original content did not end with one). It does not prove disk persistence. The slice offers
no save command and makes no saved-file claim.

## Recovery

A matching caller token returns the original operation rather than appending again. Changing
text or target while reusing a token refuses the request. If a reply is lost, call `status`
before deciding to send another append. Unknown operations block further append to the same
logical native window, including after rebind/restart.

`status({"operation":"<operation ID>","reconcile":true})` only reads back an attempt whose
original execution context and live binding are retained. After process death those identities
are lost: status retains `unknown` and asks the operator to inspect. A guessed reattachment
does not settle it. The first slice intentionally favors a truthful stop over blind replay.

Only one process may own a journal. A second startup returns `journal_in_use`; concurrent
surface calls return `busy` rather than queueing a stale append. SQLite and the GUI do not
share a transaction, so this is not an exactly-once GUI guarantee.

State/arguments/readback remain local to the fixture's journal. Use non-secret fixtures and
private run directories. EOF shuts down the server's driver sessions; it does not close the
externally owned browser or TextEdit document.

## Operator CLI judgment policy

The separate missing-judge package is specified in
[MJ1](notebook/2026-10-09-missing-judge.md). The intended correction requires configured judgment
for ordinary `footwork do` click, menu, hotkey, key, enter and navigate routes. An exact effect
grant cannot substitute for a required but unavailable judgment. Explicit `--no-judge` retains
the existing keyword/replacement-only mode and does not qualify those routes as model-free.
Observations and native append remain outside this specific judgment-required route set.
The correction is implemented and reproduced through the simulated-Mac CLI scenarios in MJ3.
This does not qualify a model-free semantic judgment replacement.
