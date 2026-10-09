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
