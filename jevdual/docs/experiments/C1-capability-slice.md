# C1: Does Footwork's capability slice beat raw backends for an agent?

A developmental decision about the H4 build order, not a general performance claim. It runs only on a frozen, committed slice implementation. Provider calls and host configuration writes for the runs need Tom's direct authorization (mailbox PROTOCOL rule 5) on top of this preregistration.

## Question and hypothesis

H4 claims that an existing agent does better calling Footwork than calling the browser and native backends directly. The value it claims to add is truthful operation records, recovery without repeated effects, and carried values with readback, not just packaging. If raw backends do as well, the slice's value is packaging and the build order should change.

**Hypothesis.** On the same browser-to-native append tasks, a Claude Code agent using the Footwork MCP slice achieves more verified, non-duplicated completions than the same agent using raw backend MCP servers, and the advantage is concentrated in the interrupted stratum.

**If true:** footwork leads in the interrupted stratum, ties or leads in the clean and stale strata, and has no duplicate appends.
**If false:** the arms tie in the interrupted stratum, for example because raw-backend agents read the document before retrying, or raw leads anywhere.

## Design

- **Host and model:** Claude Code, one pinned model and effort level, recorded per run.
- **Arms.**
  - **footwork:** only the Footwork MCP slice registered: `bind`, `observe`, and `act` with native append as its only move, plus `status`.
  - **raw:** only Chrome DevTools MCP and cua-driver MCP registered, at pinned versions recorded in the run directory.
  - Same task text, fixture page, TextEdit document and starting text. Neither arm has other browser, computer-use, shell or file tools; any such use fails the session.
- **Tasks:** fixed before the run. Each reads a value from a local fixture page and appends it to a scoped TextEdit document.

  | Stratum | Tasks | Condition |
  |---|---|---|
  | Clean | 4 | No interference. |
  | Interrupted | 4 | The serving MCP process is killed once. |
  | Stale target | 2 | The document text changes between the agent's observation and its append. |

- **Interruption mechanism, identical in both arms.**
  - **Relay:** an arm-neutral stdio relay sits between the host and the MCP server that performs the native append (the Footwork server or cua-driver MCP).
  - **Gate:** in interrupted trials the relay holds back the reply to the first mutating tool call.
  - **Kill:** an independent watcher polls the document's accessibility value. When it changes from the starting text, it SIGKILLs that server while the reply is still held, and the relay drops it. The append has been delivered and the host has demonstrably not read its reply.
  - **Record:** each trial records the relay's held/dropped log. In the footwork arm it also records the journal state at the kill: `dispatching` versus `final`.
  - **Labeling:** a kill after a `final` commit is labeled a lost reply; a kill during `dispatching` is labeled an interrupted dispatch. A trial without the held-reply log is inconclusive for this stratum and excluded, and excluded trials are counted.
  - **Fairness:** no arm gets a pause, retry or wait that the other lacks.
  - **Restart:** the host restarts the server and the agent continues.
- **Repeats:** three per arm per task, paired by task: 12 clean, 12 interrupted and 6 stale sessions per arm. Counts are reported, not percentages.
- **Oracle:** an independent script, not Footwork code, reads the document's accessibility text after each session. A completion requires the text to equal the original starting text followed by the expected appended value, exactly once and with nothing else changed. This is observed document content, not proof that anything was saved. Agent claims and Footwork's journal are not the oracle.

## Primary metric

Verified, non-duplicated completions per stratum: the oracle passes and the agent reported completion. The interrupted stratum decides; clean and stale are reported beside it and serve as guardrails. Strata are never pooled into one headline number.

## Outcome classes per session

- **Completed:** oracle passes, agent reports done.
- **Correct stop:** the agent stops and reports an unresolved or unknown outcome, and the oracle shows the value present once or absent. Scored separately; it is not a completion.
- **Duplicate:** value appended more than once.
- **Wrong:** any other oracle failure, or the agent claims done and the oracle disagrees (a false completion).
- **Out of arm:** a non-arm tool was used.

## Guardrails

- **Duplicates:** zero tolerated in the footwork arm.
- **False completions:** no more than in the raw arm.
- **Setup burden:** configuration steps and operator interventions, counted from a fixed setup script per arm.
- **Cost:** time and model cost per verified completion.

## Decision rule

- **Proceed with the H4 build order as planned** if footwork leads the interrupted stratum by at least 2 of 12 paired sessions, has zero duplicates, and trails raw by at most 1 session in each of the clean and stale strata.
- **Re-plan toward packaging and setup** (less recovery machinery) if the interrupted stratum is within 1 session and raw has no duplicates.
- **Stop and diagnose** if footwork trails in any stratum by more than 1 session or breaches a guardrail.

## Dependencies

CS1 and CS2 in `docs/notebook/2026-10-09-capability-slice.md` hold first. C1 runs on a named commit and is not debugged mid-run; a change starts a new version.

## Result

*(appended after the run)*

## Amendment: not run, raw-backend runtime unavailable, 2026-10-09 16:58
At the time CS2 held, half of the raw arm's runtime was absent: the local Chrome DevTools MCP checkout has no build or node_modules. The cua-driver CLI is available, bundled in the project environment (jevdual/.venv/bin/cua-driver), though not on the shell PATH. Nothing was installed or substituted, because a stand-in proxy would not be the preregistered comparator. C1 stays preregistered and unrun until a reproducible Chrome DevTools MCP runtime exists, in a separately authorized package. The design above is unchanged.

## Implementation clarifications before measurement, 2026-10-09

Tom authorized proceeding with this package. The raw browser runtime is the actual published
Chrome DevTools MCP 1.10.1, installed privately with lifecycle scripts disabled; its npm integrity
is recorded separately from the reference checkout SHA. The native raw runtime is cua-driver
0.28.2 `mcp --direct`, with an immutable tool policy and capability manifest restricted to the
owned TextEdit PID/window. No reference checkout, global host configuration or OS permissions
are changed. This is a developmental comparison on one machine, not a heldout adoption trial.

Execution details are fixed in `scripts/capability_comparison_trial.py` and
`scripts/capability_comparison_relay.py` before measured sessions:

- **Host:** canonical claude-opus-5-5, effort high. Fresh host working directories; strict MCP
  configuration, built-in tools disabled, hooks disabled, setting sources empty, slash commands
  disabled. Footwork offers four tools. Raw offers two browser reads (`list_pages`, `take_snapshot`)
  and five native tools (`get_window_state`, `type_text`, `press_key`, `hotkey`, `set_value`), with
  unchanged backend descriptions/schemas. Both prompts receive identical source URL and exact
  destination PID/window/document metadata. Other browser/desktop/file/shell/configuration tools
  are unavailable to the agent. This compares capabilities permitted by this scoped task, not the
  entire raw-server catalogs.
- **Tasks:** all read the same displayed `17.25 USD` total. The four clean and four interrupted
  tasks vary destination prefix: ordinary newline, no terminal newline, empty document, and
  preserved trailing whitespace. The two stale tasks use the first two prefixes. These are ten
  fixture conditions, not ten distinct websites/apps. The full strings live in the committed
  runner. Expected insertion uses a newline only when the preserved prefix is nonempty and lacks
  a terminal newline. No normalization, trimming or fuzzy matching is allowed.
- **Schedule:** thirty paired blocks, three repeats of every condition. Task order rotates by four
  conditions each repeat; arm order follows ABBA across blocks. The exact schedule is saved before
  execution. Sessions run serially over the same owned resources, with independent exact AX reset
  before each session. No measured session is rerun.
- **Persistent relay:** Claude remains connected to an arm-neutral stdio relay. The relay owns
  backend restart, addressing the unverified assumption that the host reconnects a dead stdio
  server. It serializes requests equally in both arms. Restart replays only initialize and
  notifications/initialized, then checks the complete tool catalog hash. It never replays a
  tools/call. The caller receives the identical generic JSON-RPC error `backend process exited;
  restarted`, without oracle results, journal state, IDs or recovery advice.
- **Interrupt treatment:** arm-native text mutations are Footwork `act`, raw `type_text` and
  `set_value`. Caret-only hotkeys/press_key are not the append being interrupted. A separate
  read-only watcher starts before forwarding the first text mutation, requires the exact starting
  prefix, and SIGKILLs only the owned dispatch process group at the first field change. The relay
  gates the response before dispatch; after kill it records a held/dropped event even if the child
  died before emitting reply bytes. The original first-field-change trigger is retained. A partial
  raw insertion is reported as observed, never silently repaired or normalized; driver routes may
  differ and results do not isolate the journal's causal contribution. No change within ten seconds,
  no held/dropped evidence, or catalog drift makes the treatment inconclusive.
- **Stale treatment:** after a successful destination snapshot, immediately before forwarding the
  first text mutation, the harness changes the fixture prefix through independent AX access to
  `prefix + "External note: preserve this edit.\n"`. Expected completion preserves that exact new
  prefix and appends the source total once. Erasing the external edit is Wrong. An unchanged edited
  prefix with an honest stale/unknown stop is Correct stop. This resolves the oracle ambiguity in
  the original "starting text" wording; it does not count the harness edit as agent corruption.
- **Budget:** CLI cap $1 per session, aggregate scheduling ceiling $30. Reserve $2 before starting
  each pair; stop scheduling if cost is missing or the reserve is unavailable. Model-free probes
  and up to three development pairs qualify the runner before measurement. Development sessions
  and independent model reviews are reported separately and do not enter C1 counts. Incomplete
  pairs/exclusions are retained in the report; no decision-rule threshold is prorated. A truncated
  or incomplete comparison is inconclusive. Host cap/timeouts are counted outcomes unless a
  separate harness fault invalidates the session.
- **Claim review:** machine receipts leave claim_review null. Review final messages against their
  actual tool evidence and independent oracle, recording done, stopped/unknown, other and any
  unsupported claim separately. AI review is labeled as such, never described as human sign-off.
  Exact content plus a supported done claim is Completed. Exact/unchanged content plus an honest
  unknown stop is Correct stop. Safe stops never count as completions or trigger the Proceed rule.

The primary metric and numerical decision rule above are unchanged. If Footwork trails because it
honestly stops on unknowns, that is a stop-and-diagnose result: safety without sufficient recovery.
It is evidence for qualified restart reconciliation, not permission to silently promote unknown
to applied or redispatch. No product change occurs during a measured comparison.

## Pre-measurement harness qualification amendment, 2026-10-09 18:52

Development versions v1/v2 are retained and excluded from C1. They exposed a 64KB framing limit
and legacy-only lifecycle assumption, both repaired before measurement. The final relay preserves
32MiB bounded frames and both successful legacy initialize and modern server/discover lifecycle
requests, including the original per-request catalog envelope. Backend-to-client requests retain
their backchannel; no tools/call is replayed. Bind(destination) is a valid snapshot because this
product returns its fresh observation from bind. Observe(source) does not qualify as a destination
snapshot. Interrupted treatment needs the exact independent starting prefix, not a particular
agent observation call; stale treatment still requires a successful destination snapshot.

Every raw write-capable native call (set_value, type_text, press_key and hotkey) is a candidate
until the field first changes. A completed candidate whose independent field read remains equal
to the starting prefix releases its held reply promptly and leaves the kill available. This
prevents caret motion or a refused call from spending the treatment. No observed change during
an unresolved call remains inconclusive. The original first-field-change kill stays unchanged.
Watch evidence records exact detection content and a limited read 100ms after SIGKILL, without
claiming a universal absence-of-late-delivery bound.

The identical task prompt now explicitly requires both specified PID and window ID on native
calls accepting them, including token-addressed calls. This keeps the existing exact-window
manifest intact: development agents following the upstream optional-window schema otherwise
received an application-level authorization refusal. No raw schema, request or response is
rewritten, and no application-wide grant is added. This is a task resource-binding instruction
for both arms, not an outcome/recovery hint. Setup burden includes this configuration nuance.

Before oracle readback/reset, the runner retires attested owned backend groups and requires two
equal AX readings 200ms apart. This proves the observed state over that interval only. Unknown
PID identity, unreadable/changing oracle, catalog drift or transport failure stays unqualified.
Clean-tree status, core/harness/lock hashes and package versions are recorded. Summary rows name
block/task and pair completeness; decision_eligible remains false until complete measurement and
claim review. Missing cost stops scheduling and reserves its session ceiling as an explicitly
uncertain upper bound. Prior qualification/review spend is included in the $30 scheduling ceiling
through --prior-cost. Numerical C1 thresholds, exact oracle and no-retry rule remain unchanged.
