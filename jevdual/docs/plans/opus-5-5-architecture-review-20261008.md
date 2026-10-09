# Independent Opus 5.5 architectural review

Fresh read-only architectural consultation. Requested and provider-recorded canonical model: `claude-opus-5-5`; effort: `xhigh`. No fallback. This is a model review of a frozen copied-source packet, not implementation verification or empirical proof. The five hypotheses and human selection remain separate.

**Reviewer title:** Independent design review: five Footwork browser/native architecture hypotheses (H1–H5) against Legible Loop v6 and the retained v5 obligations A1–A4, E1–E5 and M1–M3 (Footwork baseline 88325d1)

## Are these genuinely different?

The five are not cosmetic, but they are also not five independent ways of owning progress. They vary along three different axes that the comparison table (candidates.md:50-56) merges into one.

**(a) Who advances the job.** There are three genuinely different owners:
- the caller or driver (H1, H4);
- a runtime plan scheduler (H3);
- a level-triggered controller over observed resource state (H5).

**(b) Trust and distribution boundary.** H4 differs from H1 here, not in scheduling. H4 assumes untrusted, varied hosts calling over a protocol, with the broker holding custody. H1 is an in-process library, and its own 'optional local RPC later' (candidates.md:52) leads to H4.

**(c) How surfaces are attached.** H2 sits mostly on this axis: long-lived attachments, mailboxes, push invalidation and machine-level posture. Its coordinator 'owns task intent and multi-surface dependencies' (candidates.md:104), but nothing names what decides the next action on an unfamiliar site. If an LLM planner runs on each event, H2 becomes H1 driven by events. If a precompiled dependency graph runs, it becomes H3 with actors.

**H5's overlap.** For multi-resource tasks H5 needs a coordinator for dependencies (candidates.md:192), which is H3-like. For one-shot effects it needs typed commitment records (candidates.md:200), which is H1's operation journal. Its distinct contribution is three-state level reconciliation (satisfied, unsatisfied, unknown), which could also serve as a recovery strategy under any other owner.

**H3's overlap.** LangGraph re-executes a node from its start when resuming after an interrupt (references/langgraph/types.py:908). So every effectful H3 activity must embed an H1-style operation journal. The H3-versus-H1 question is therefore only the value of the stage layer.

**Shared floor.** All five depend on the same unbuilt floor: durable intent before dispatch, an effect-unknown state, task-level budgets, a machine-level posture lease and custody records. If prototypes are built before that floor, the comparison mostly measures how well each re-implements the floor.

**Recommended revision.** Restate the table with three columns (progress owner, trust/distribution boundary, surface-attachment model). Then combinations such as 'H3 owner + H2 attachments + H4 protocol' are visible as combinations, and any hybrid can name exactly one primary owner.

- H1 and H4 share the same progress owner (the caller) and the same owner of each operation's lifecycle. They differ in trust/distribution boundary and in who holds custody when the caller is gone. H1 plus local RPC converges on H4.
- H2's coordinator has no named decision-maker for open-ended tasks. Naming one makes H2 either H1 driven by events or H3 with actors. Its actors are an attachment and concurrency layer that could sit under any of the other four.
- H5 reintroduces an H3-like coordinator for dependencies between resources (candidates.md:192) and H1-like commitment records for one-shot effects (candidates.md:200). Only three-state level reconciliation is unique to it.
- H3 must embed H1's operation journal inside each effectful activity because interrupts re-execute nodes (langgraph types.py:908). The thing to test is the stage layer's value.
- All five rely on the same missing floor: durable intent before dispatch (session.py:963-1013), an effect-unknown receipt (receipts.py:35), task-level budgets (crossloop.py:150-153), a machine-level posture lease (posture.py:173-188) and custody records.
- The reference sources don't discriminate between candidates. pi is cited for H1, H2 and H3. arc-cua's runtime states that the external agent owns intent (runtime.py:68-73), which is closer to H4's split than to H1's.

## Findings before selection

### F1 — blocking — shared

The operator path doesn't write durable intent or an operation identity before an effect. cmd_do bumps the step counter only in memory, dispatches, and only afterwards writes state.pending, the 'do' log record and session.json. No operation ID or payload fingerprint exists. A crash during or right after dispatch leaves no record of the attempt, apart from a grant use already spent. Shared invariant 6, v5 §6.1 and v5 E2 can't be tested in any prototype until this exists.

Source: footwork/source/session-819-1024.py → session.py:963 (step += 1), 967-984 (dispatch), 996-1013 (pending/log/save after dispatch); session.py:66 (pending 'awaiting its receipt'); v5:331-337; candidates.md:40

Recommended correction: Define the floor semantics once and use them in every prototype: prepared → started → observed/unknown records with a stable operation ID and payload fingerprint, committed before dispatch. Leave storage placement (one journal, per-actor log, workflow ledger, broker store) to each architecture, but make the transition semantics and kill-point tests identical.

### F2 — blocking — shared

Receipts and errors can't express 'effect unknown'.
- The receipt vocabulary has five words and none for an unknown outcome.
- Native exceptions raised during a dispatched call, including timeouts after the input was sent, become 'refused'.
- Browser tool errors become 'refused'.
- In the operator command, a RuntimeError becomes 'not dispatched'.
So the shared shell's sentence 'Save outcome unknown; checking the selected file before trying again' can't be produced truthfully today. Reconciliation in every candidate depends on this distinction.

Source: receipts.py:35; native-589-770 → native.py:728-745 (_effect maps a raised exception to 'refused'), 747-771 (_foreground); browser_driver-247-445 → browser_driver.py:354-359; session.py:992-994; v6:54 ('remote outcomes after a timeout are not modelled'); v5:333-335

Recommended correction: Add an unknown-outcome state at the driver adapter boundary. For each route, classify every exception as raised before or after input was sent; treat timeouts and transport loss after sending as unknown (E2). Add mutation tests showing an unknown outcome never becomes 'refused' or 'not dispatched' and blocks dependent commitments.

### F3 — blocking — shared

Under current completion code, the demonstration task's own success conditions would be read wrongly:
- required_effects runs a regex over the task text. It matches 'submit' inside 'Do not submit or pay anything', so the task would require a 'submitted' effect. 'pay' isn't recognized at all.
- 'saved' evidence is limited by comparing only the file's basename with the window's document name. That can't express 'a new copy in this selected folder': it can't check the folder, the new-file identity, or that the original was left alone.
- 'Edited again after this save' is computed only from the session's own receipts, so a person's edit after the save doesn't limit the evidence.
Any comparison on this task would partly measure how each candidate works around the completion code.

Source: footwork/source/completion.py:172-183 (_NAMED regex, required_effects), 186-202 (floor), 75-76 (basename limit), 77-85 (later edits from own receipts only); candidates.md:25; overlay legible-loop-evidence-20260926.md:54 ('oracles come first')

Recommended correction: Before prototyping, write the demo's contract as a validated typed contract: source binding, destination folder scope, new-file identity, prohibited effects (submit, pay) and the readback oracle. Use the same contract compiler and oracle for all candidates. Prohibit requirements derived from regexes over task text in prototype scoring.

### F4 — blocking — shared, H2

Nothing owns the machine as a whole.
- Execution posture is a per-session ExecutionPolicy held by each bridge.
- CrossLoop starts each surface with its own session and defaults Surface.mode to foreground_permitted, while the operator default is background_only.
- In the cross-surface demo, two sessions therefore decide independently whether to take the foreground and keyboard.
- Only H2 names a machine-level posture owner (candidates.md:108).
Without one shared owner, comparisons of coexistence are confounded and 'broken posture promises' (a disqualifying guardrail) can arise from architecture rather than from the shell.

Source: posture.py:173-188; native.py:614; browser_driver.py:265-267; crossloop-94-260 → crossloop.py:101 (mode default 'foreground_permitted'); session.py:70 (posture 'background_only'); v6:39,117 (Q15 claims limited; reattachment across commands not exercised); candidates.md:108, 239

Recommended correction: Add to the shared invariants a single machine-level lease for foreground, keyboard and clipboard, with fencing and expiry, implemented the same way in every candidate. Add a scenario where two tasks contend for the foreground, and state that the person can take over during a hand-back.

### F5 — blocking — H2, H5

Neither H2 nor H5 says what decides the next action on open-ended work.
- H2's coordinator owns intent and dependencies, but the packet doesn't say whether an LLM planner runs on each event or a dependency graph is compiled up front.
- H5's controllers 'choose supported route strategies'. For unfamiliar sites and apps that requires a local planner inside each controller, plus a coordinator for dependencies between resources.
Until these are named, a reader can't tell whether H2 and H5 are distinct from H1 and H3. That breaks the packet's own rule against adding a scheduler or planner without saying how it changes the option's identity.

Source: candidates.md:104-106 (H2 ownership/demo), 192 (H5 coordinator and strategies), 196 (browser UI state partial), 58 ('Renaming modules is not an alternative hypothesis')

Recommended correction: Revise H2 and H5 to name where the planner is called, what triggers it, and whether that makes the option event-driven H1 or actor-backed H3. Keep only the residual differences as H2's and H5's hypotheses: push attachment for H2, three-state reconciliation for H5.

### F6 — major — shared, H2, H3, H4

Budgets are neither durable nor scoped to the task.
- CrossLoop's max_steps, max_seconds and done-refusal limits live in process memory.
- The visual-check ledger is scoped to a session, and 'a new session must represent a new scoped workflow'.
- If an architecture maps 'session' onto something smaller than the task (an H2 actor, an H3 stage, an H4 host connection), it can reset budgets just by creating new sessions. That violates A4.

Source: crossloop.py:150-153; footwork/jevdual/docs/visual-checks.md:63; v5:162 (A4); candidates.md:45 (invariant 8)

Recommended correction: Make a durable reservation ledger keyed by task ID part of the floor, and move the visual recovery budget up to task scope. Add an A4 test: replace the worker, actor or host mid-task, keep an unknown outcome reserved, and check that the remaining budget is preserved.

### F7 — major — shared

Using a grant isn't atomic and isn't linked to an operation.
- grants.consume loads JSON, mutates it and writes it back, with no lock and no atomic rename.
- It runs before dispatch, and nothing ties the grant use to an operation ID.
- session.json is also rewritten in place.
Concurrent callers (several H1 callers, H2 actors, several H4 hosts) could both spend a single-use grant, and a torn write can't be told apart from an absent grant. The packet asks for local persistence failures to be explicit.

Source: footwork/source/grants.py:111-112, 115-127; session.py:944 (consume before dispatch), 85-86 (session.json write_text); v5:323 (atomic local checks), 337 (local storage writes are effects too); candidates.md:40

Recommended correction: Reserve grants, budget and the prepared operation in one transaction, record grant use against the operation ID, and never refund on an unknown outcome. Add a persistence-failure case (torn or failed write) to the floor tests.

### F8 — major — shared, H2

There is a gap between checking a target and acting on it.
- cmd_do observes, then awaits a remote destructive judgment, consumes a grant, and only then dispatches.
- The native live recheck of target identity runs only when live_check is enabled.
- The browser's _fresh compares snapshot IDs, not live state.
GUIs offer no compare-and-swap. v5 E1 requires rechecking after awaited work and documenting the race that remains. H2's 'actors check their bound resource/generation at dispatch' is local knowledge, not a GUI fence.

Source: session.py:849 (observe), 893-920 (judge and authorizer), 944, 967-984; native.py:590-595, 605 (live_check), 680-710 (_live); browser_driver.py:345-352 (_fresh); v5:321-325; candidates.md:104

Recommended correction: Each candidate states its last recheck point per route and the race window left after it. Prototypes inject a person's edit between the judgment and the dispatch and record whether the action is refused or whether the race is disclosed.

### F9 — major — shared, H1, H4

There are several paths to mutation today.
- desktop.execute calls itself 'the only path to the bridge's mutating methods'.
- But the operator command builds its own Authorizer and calls bridge methods directly.
- The browser agent has a third gate, where authorization is a label/keyword match.
- Setup (browser_prepare with existing_profile) is not shown passing a boundary.
- v6 L9 says the three paths behave differently.
Shared invariant 2 requires every route, including setup, recovery and compatibility helpers, to cross an explicit boundary.

Source: desktop-414-500 → desktop.py:464-468, 492; session.py:904-984; agent-264-435 → agent.py:404 (is_authorized on label/keyword), 423-431; browser_driver.py:289-292; v6:93 (browser grants are keyword scopes), 133; candidates.md:36

Recommended correction: In every candidate, planners only receive capability handles; driver objects are never exposed. Run one enforcement-mutation test per route: click, type, Enter, key, menu, navigate, setup/attach, recovery, compatibility helper. H1 and H4 claim they centralize this naturally; make that claim falsifiable.

### F10 — major — H4, H1

Footwork can only vouch for effects that pass through its own boundary. Hosts like Claude Code or Codex have shell, AppleScript or their own browser tools and can change the bound document without going through Footwork. MCP annotations such as readOnlyHint are metadata, not enforcement. H4 already says uncontrolled host tools are outside its assurance claim, but no scenario tests whether the broker notices such changes or refuses to certify on them.

Source: references/chrome-devtools-mcp/ToolDefinition.ts:86-89; candidates.md:167, 177; v5:281 (enforcement boundary includes subprocesses and delegates)

Recommended correction: Scope the assurance claim to effects mediated by Footwork. Add a bypass scenario: the host edits the destination through a tool Footwork doesn't mediate. The change must invalidate the bound generation, and fulfillment can't be certified on an unattributed change.

### F11 — major — H4

The timeout and reconnect semantics aren't specified. chrome-devtools-mcp gives up on a tool call after 60 seconds and forgets its cached browser handle so the next call reconnects, which is a fast clear error but says nothing about whether the in-flight effect happened. H4 needs operation identity that stays stable across host reconnects and fresh conversations. Otherwise a new host can't recognize its predecessor's unknown operation and may retry it.

Source: references/chrome-devtools-mcp/ToolHandler.ts:30-40; candidates.md:171; v5:257-263 (M2, M3)

Recommended correction: Specify broker-issued operation IDs and a reconnect response that lists pending and unknown operations, owed results and remaining budget. Test a retry with the same ID against a fresh host without it.

### F12 — major — shared

Nobody is named as the recipient of the result, and 'delivered' isn't defined. 'Show the saved result' could be discharged by a task-card render, a person viewing it, an external host fetching it, or a host acknowledging it. v5 E4 requires a named recipient, discharge evidence and a fenced current custodian. The candidates mention custody but don't name recipients or acknowledgement rules per entry point. H1 admits its continuation owner is missing.

Source: v5:353-359 (E4); candidates.md:41 (invariant 7), 83 (H1), 163 (H4), 112 (H2 outbox)

Recommended correction: For each entry point (shell, CLI, SDK, protocol host), define the recipient, the evidence that discharges delivery, and the succession rule. Test that 'producer finished' never counts as fulfillment.

### F13 — major — shared

Handing control to the person and resuming afterwards isn't built anywhere.
- A browser-agent pause rewrites the action as a done with success=False ('Nothing was clicked'), which ends the run.
- v6 marks L8 resume 'no' on all three surfaces.
- No candidate says what resume re-validates, such as posture, grant expiry, every surface's generation, the carried value's source and budget.
- No candidate says how changes the person made during the hand-back are attributed, so they aren't later mistaken for the agent's effects.

Source: agent.py:423-431; v6:56, 125, 165; candidates.md:27, 135

Recommended correction: Add a shared resume contract: a fresh observation of every bound surface, the person's actions during the hand-back attributed to them, grants and posture re-checked, and settled effects never replayed. Test it with a sign-in hand-back in every prototype.

### F14 — major — shared, H2

In the browser, the session identifies 'its' tab by URL. Tab handles are new on every driver connection, so each command rebinds by URL key and refuses if no tab or several tabs show that page. A selected tab that navigates (for example an invoice reached after sign-in, or a single-page-app route change) or that is duplicated loses its identity. Keeping real tab handles alive is H2's most concrete advantage. The other candidates need a stable driver-level target identity instead.

Source: browser_driver.py:283-331 (attach), 285-287 (handles new on every command); session.py:71-73 (browser_tab); v6:101

Recommended correction: Decide the subject-identity mechanism as part of the floor. Add scenarios where the bound tab navigates and where two tabs show the same invoice URL.

### F15 — major — shared

There is no policy for a source that changes after its value was copied. The copied dispatch path loads the carried value and prints where it came from, but shows no re-check of the source surface (carry.py isn't in the packet). The candidates handle a changed destination in detail but are silent on a changed source: whether the invoice total is the value at observation time or must still be current when the report is saved. Only H5's desired state mentions the source revision.

Source: session.py:827-837 (carry load/provenance); candidates.md:38 (invariant 4), 194 (H5 source revision)

Recommended correction: Make it a contract field: the value as observed at a recorded time, or the value required to be current when it is committed. Every candidate implements the same choice, and a scenario changes the total after it is copied.

### F16 — major — H2

H2 assumes drivers can report changes; the packet has no evidence for that. No copied source shows Cua or the browser route offering change subscriptions. Footwork currently pulls: it notes drift at the next command and re-observes at dispatch. Watchers also add the liveness, ownership and progress distinctions of v5 §4.4.

Source: session.py:854-860 (drift note at next command); native.py:680-710; v5:238; candidates.md:112, 116

Recommended correction: Before building any actor runtime, run a probe of whether and when each pinned driver signals a person's edit, a tab navigation and a window replacement, including missed signals. Gate H2 on the result.

### F17 — major — H5

Reconciling against partial GUI observation can mistake 'not observed' for 'absent', the blind spot v6 already records for absence. That leads to duplicate appends or extra copies. Pre-existing look-alike output can falsely satisfy a predicate, and a delayed file write can look like a missing save.

Source: v6:108; completion.py:75-76 (basename-only binding); candidates.md:196, 200, 204

Recommended correction: Require predicates with three states (satisfied, unsatisfied, unknown) and forbid mutation on unknown. Add look-alike, delayed-write and source-changed cases to H5's prototype.

### F18 — major — H3

Resuming re-executes the node, and declaring stages may change driver behavior. LangGraph resumes from the start of the node. Footwork's Q11 and Q11b show that declaring requirements changed what the driver did and raised no-fact refusals. Putting stage context into prompts could repeat that. Each effectful stage still needs the operation journal, so H3 must be judged on what the stage layer adds over that journal.

Source: references/langgraph/types.py:908; v6:33, 70; overlay:67-71; candidates.md:141, 145

Recommended correction: Compare H3 against a free session that shares the same operation journal, drivers and shell. Run a declaration ablation (stage context shown versus withheld) separately from enforcement tests, as v6 §4 requires.

### F19 — major — shared

Some components accept completion when a check is missing.
- Native System Two accepts a done when no verifier is configured.
- arc-cua's runtime returns True when no verify function is given; Footwork's own arc-cua audit flags this as a transfer hazard.
- In the operator path, the destructive judge is built only when an API key is present. Authorizer behavior without a judge isn't in the packet.
Any architecture that borrows these defaults breaches 'no claim of completion beyond the evidence'.

Source: desktop_s2-250-370 → desktop_s2.py:338; references/arc-cua/runtime.py:195-198; footwork/jevdual/docs/arc-cua-decisions-reference.md:28; session.py:893-903

Recommended correction: Floor rule: fulfillment requires a declared fulfillment owner, and a missing verifier means unverified. A missing judge withholds effects that need judgment. Include an enforcement-mutation test that removes the verifier and the judge.

### F20 — major — H1, H4

H1 and H4 aren't separated as architectures. Both are caller-driven with one service owning each operation's lifecycle. Selecting between them is a product and trust decision (in-process trusted planner versus heterogeneous hosts, and who holds custody when the caller is gone), not a choice between scheduling models.

Source: candidates.md:52, 55, 75, 83, 163, 171

Recommended correction: Merge them as one ownership model with two deployment variants, or sharpen them: H1 is a trusted in-process caller with custody resumed by the next caller; H4 is untrusted hosts with broker-held custody and host authentication and delegation (A3).

### F21 — minor — shared

Some observation limits aren't stated precisely enough.
- The routing contract names local OCR enrichment, but no copied Footwork source implements it.
- Visual checks are opt-in, native-only and advisory, and browser operator sessions are unsupported.
- Native System Two is text-only.
- If the invoice total appears only in a PDF viewer or canvas, every candidate must escalate rather than carry a value inferred from pixels.
- The native visual capability has been built and its mechanics tested, but it is not qualified for autonomous visual execution or for perception accuracy.

Source: candidates.md:210, 214; visual-checks.md:3, 59, 69, 73; desktop_s2.py:285-291; footwork/jevdual/docs/notebook/2026-10-08-visual-checks.md:20, 26

Recommended correction: Mark OCR as unbuilt or unqualified in the packet. Add an insufficient-observation scenario (total only in PDF or canvas) whose expected outcome is a structured escalation.

### F22 — minor — shared

One observation fails open: the screen-lock check returns False when the probe raises ('unknown is not locked'), so an observation failure reads as unlocked.

Source: footwork/source/posture.py:123-129

Recommended correction: Represent the lock state as unknown and let posture policy decide, consistent with honesty about insufficient observation.

### F23 — minor — shared

The reference attributions aren't discriminating, and several can't be verified from the packet.
- pi is cited for H1, H2 and H3.
- arc-cua's runtime puts intent with the external agent (closer to H4) but is cited for H1.
- browser-use, Cua and controller-runtime sources aren't in the packet.

Source: candidates.md:85, 114, 143, 173, 202, 251-261; references/arc-cua/runtime.py:68-73; references/pi/session.ts:54; references/pi/task-graph.ts:58-61

Recommended correction: Map each reference to the specific claim it supports, and don't use reference fit as evidence that the candidates are distinct.

### F24 — minor — shared

The evaluation section mixes two things. A single-task prototype can't measure the primary metric (avoidable effort per verified checkpoint) or human burden, which needs representative users. Prototypes can only falsify invariants and show large ownership costs.

Source: candidates.md:237-241; v6:139-147

Recommended correction: Split prototype falsifiers (pass or fail on invariants and kill points) from the later preregistered burden study, and say so explicitly.

### F25 — minor — shared

The cross-surface loop today shells out to the CLI for every step and parses its prose output, and carried values from different surfaces are keyed by name only, so a later surface can overwrite an earlier one. This is a shared current limitation, not something that distinguishes H1.

Source: crossloop.py:128-138, 253-260

Recommended correction: Give all candidates a typed result API in the common shell so this isn't credited to any one architecture.

## H1 — viable_hypothesis

**Strongest case:** It is the closest fit to how the code works now. The operator command and CrossLoop are both caller-driven (session.py:819-1024; crossloop.py:128-138), and SessionState already holds a pending action awaiting its receipt (session.py:66). One transactional journal on one mutation line (pi session.ts:54: 'one mutation line… Only committed state is observable') makes grant use, reservation, prepared-operation records and custody a single local transaction. That is the cheapest way to meet v5 E1's local-atomicity clause (v5:323) and A4. It has the fewest coordination components, its typed API replaces parsing CLI prose, and a single port is the most direct route to the uniformity L4 and L9 ask for.

**Main failure mode:** Progress, reconciliation and custody stop when the caller stops. A library has no resident custodian, so an unknown save or an owed result sits unreconciled until a caller returns. H1 says that an obligation ledger without an owner of continuation is insufficient (candidates.md:83), but doesn't name one. Arbitrating the foreground across processes and serializing concurrent callers needs a lease that a library alone doesn't provide. Once those are added, H1 becomes H4 (a resident broker) or gains a scheduler (H3-lite). Per-command attach and URL-based tab rebinding also remain (session.py:844, 1020; browser_driver.py:283-331).

**Human intuitiveness:** High for attended, one-off tasks: one task, named surfaces, the last verified change, and 'continue' reloading the journal. Weaker once the person walks away. A card saying owed work is waiting for a driver is less clear than a job that keeps going, and live updates need a resident process that H1 defers.

**External-agent ergonomics:** Good for in-process Python callers, which share the typed operation and result grammar. For Claude Code or Codex hosts it is deferred: today they get CLI prose. Without RPC, a reconnecting agent rebuilds context from its transcript. With RPC, H1 converges on H4.

**Authority and recovery:** Best structural fit for atomic local governance, provided grant use moves out of load-modify-write JSON (grants.py:115-127) into the journal transaction and is linked to an operation ID. Crash recovery is correct only if intent becomes durable before dispatch, which the current path doesn't do (session.py:963-1013). E2 reconciliation is triggered by the caller, and E4 and M2 custody need a named continuation owner. The race left between the last GUI recheck and dispatch must be disclosed per route, as for every candidate.

**Adaptive routing:** A capability resolver chooses a route for each bound resource and operation, and never rebinds on refusal. That is the simplest to audit for L5 and A1. It doesn't fix browser subject identity across connections (browser_driver.py:285-287). When observation is insufficient, it returns a structured escalation to the caller; with no caller present, nothing re-routes.

**Minimum experiment:** The prototype in candidates.md:89 plus four cases:
- kill the process between prepared and started, and between started and recorded, around a real save;
- two callers race for one single-use grant and the foreground on the same machine;
- the caller exits after the save, and a different caller with fresh context must see the unknown or verified save, the remaining budget and the owed result without reading transcripts;
- the bound tab navigates or is duplicated mid-task.
Use the same drivers, shell and oracle as the other prototypes.

**Falsifier:** Without adding a resident scheduler or mailboxes, H1 is falsified if:
- an unknown save or owed result stays unreconciled after the caller is lost;
- concurrent callers spend the same grant or reservation twice, or both take the foreground;
- resuming requires reconstructing context from a transcript.
If fixing these needs a resident service with succession, record that H1 has become H4 or H3, not that H1 succeeded.

## H2 — needs_revision

**Strongest case:** It is the only candidate that names machine-level posture ownership (candidates.md:108) and long-lived attachments. Today every command attaches and shuts down the driver (session.py:844, 1020). Browser tab handles are new on every connection, so sessions rebind by URL (browser_driver.py:285-287). v6 reports roughly 1 s for look and 4–6 s for do (v6:132). Resident per-surface attachments could keep real tab and window handles, avoid cold attaches, and push invalidation as soon as a person edits beside the agent, which is the case that sets a personal app apart (Q15 limits: v6:39, 117). Committed-state subscriptions (pi task-graph.ts:58-61) give live task cards without polling.

**Main failure mode:** Two dependencies are unproven.
- Nothing names what decides the next action on an unfamiliar site: the coordinator owns intent and dependencies, but runs neither a stated planner nor a stated graph. An LLM on each event makes it H1 driven by events; a dependency graph makes it H3 with actors.
- The benefits depend on driver change signals that no copied source shows. Today invalidation is pulled at the next command (session.py:854-860) and re-checked at dispatch (native.py:680-710).
Without push signals, actors poll while adding fencing, deduplication, gap detection, an outbox, succession and backpressure (candidates.md:112), with no gain in verified outcomes. The same-process keyboard ambiguity serializes actors anyway.

**Human intuitiveness:** Potentially the best while a person is watching: live per-surface status, why an action is waiting, and what changed. The risks are more concurrent state to read and degraded watcher states the person must understand. Actor and incarnation names must stay hidden in ordinary use.

**External-agent ergonomics:** Subscriptions suit long-running hosts but sit awkwardly with turn-based LLM hosts, which need a pull form such as 'changes since this cursor' plus the current task projection. Returning a fresh observation for a stale command (candidates.md:110) already matches the operator's behavior today (session.py:879-886), so the gain is mostly latency.

**Authority and recovery:** Needs the most new mechanism: transactional shared reservations, per-actor fencing tokens tied to each incarnation, reservations invalidated when an actor dies, and a transactional outbox for cross-actor results (a good E4 fit, v5:355). No global lock may be held across driver or model calls (v5:301). An actor's generation check is local knowledge, not a GUI fence: a person can edit between the check and the keypress, so the remaining race still has to be documented under E1.

**Adaptive routing:** Each surface advertises its current and degraded capabilities live, which answers 'what may I do now?' well. Route changes that cross surfaces, such as a native file opened in the browser, cross actors, so the coordinator must keep resource identity separate from actor identity. Replacing a surface creates a new incarnation.

**Minimum experiment:** Before building any actor runtime, probe the pinned Cua and CDP routes: inject a person's edit and a tab navigation, and record whether and when each route signals it, the missed-signal rate, and how this compares with pulling at dispatch. Only if signals exist, run the prototype in candidates.md:118 plus two tasks contending for the foreground and a coordinator that dies between the save and receiving its event.

**Falsifier:** If the probe finds no reliable signals for the demo's surfaces, stay with a pull model. H2 is also falsified if push invalidation doesn't reduce refused stale dispatches or planner calls compared with pulling at dispatch on the same drivers, if a warm attachment ever dispatches on a generation that a cold attach would have refused, or if verified end-to-end time including cold start and restart doesn't improve.

## H3 — viable_hypothesis

**Strongest case:** It gives the clearest answer to the open L8 obligation (resuming after a hand-back is built nowhere: v6:125, 165) and to repeated jobs. The scheduler, not the caller, owns pauses, budgets and custody, so work and obligations outlive the caller (M2, E4, A4) without a separate custody service. Stage boundaries are natural points to hand back and correct, and the person sees milestones rather than a transcript. pi's phased scheduler, where the scheduler itself writes 'faulted' or 'orphaned' outcomes (scheduler.ts:106), is precedent for scheduler-owned terminal accounting.

**Main failure mode:** Unfamiliar GUI work doesn't break into stages reliably. Generated graphs need validation and frequent revision, and displayed stages can become false milestones. Q11 and Q11b showed that declaring requirements changed driver behavior and raised refusals (v6:33; overlay:67-71), and putting stage context into prompts risks the same. Interrupts re-execute node logic (types.py:908), so each effectful stage still needs H1's operation journal. H3 wins only if the stage layer adds value beyond that journal.

**Human intuitiveness:** Best for repeated jobs: named inputs, outputs and milestones, and resuming where it stopped. For one-off exploratory tasks, it is intuitive only if the ad hoc path hides graph authoring completely. Corrections ('dependent stages are revised; history stays') are understandable if shown as before and after.

**External-agent ergonomics:** Very little burden for hosts that hand over whole jobs: start, inspect the current stage, submit a decision, continue. More friction for hosts that want step-level control or revise plans often. The protocol must still expose per-operation receipts for debugging.

**Authority and recovery:** The natural owner of task-level budgets and custody. Effects must sit in their own stages, with stable operation identity and reconciliation on entry. A workflow engine's default retries must never be used to retry UI effects. Revising the graph must be checked against A1 and A2 so it can't widen a stage's scope. Keeping old graphs compatible is a real ongoing cost.

**Adaptive routing:** Stages state outcomes and activities choose qualified routes within the stage's bounds (candidates.md:133, 137), which keeps adaptation local. When a route is unavailable, the activity escalates or the graph is revised; over-revising is the main risk. Unknown sites remain an activity planner's job, which is effectively H1's caller loop running inside a stage.

**Minimum experiment:** candidates.md:147 plus a deliberately wrong generated graph (the invoice is behind a sign-in or in a PDF viewer) and an interrupt immediately after the save. Compare against a free session that uses the same operation journal, drivers and shell, and count revisions, authoring or correction actions, and any repeated effect.

**Falsifier:** H3 is falsified as the primary owner if any resume repeats a settled effect, or if one-off tasks need more graph revisions or human corrections than a preregistered limit. It is also falsified if resuming after a hand-back is no cheaper than continuing a session with the same journal; that would mean the stage layer adds burden, not clarity.

## H4 — viable_hypothesis

**Strongest case:** It is the best fit for being intuitive to an external agent and for portability. One governed grammar returns structured receipts and next moves. The broker can be the only route to the drivers, which centralizes L4, and task, pending-operation and custody records live apart from any host conversation (M2, M3, E4). chrome-devtools-mcp shows schema-defined tools, mode availability and bounded connection handling (ToolHandler.ts:40, 56-91). arc-cua's runtime states the same split: 'The external agent owns intent… This runtime owns observation, fast decision-making, freshness checks, native UI execution, and bounded termination' (runtime.py:68-73).

**Main failure mode:** Its assurance covers only effects routed through the broker. Hosts can also act through shell, AppleScript or other tools, and annotations like readOnlyHint (ToolDefinition.ts:86-89) are metadata, not enforcement. Each host would reimplement planning, pause/resume and context reconstruction unless the broker returns a task projection when a host reconnects. Tool-call timeouts produce unknown outcomes that hosts tend to retry (ToolHandler.ts:30-40). If useful continuation needs the broker to schedule, H4 becomes H1 or H3 (candidates.md:171).

**Human intuitiveness:** Indirect. The broker is invisible, and the person experiences whatever bundled client planner drives it. A task card can be drawn from broker records, but on its own it can't say what happens next when no host is connected.

**External-agent ergonomics:** The strongest of the five, if three conditions hold:
- discovery is scoped to the bound resources and kept small;
- a host reconnecting in a fresh conversation gets the current task projection (pending and unknown operations, owed results, remaining budget, retained decisions) without replaying history;
- operation IDs stay stable across reconnects.
Tool descriptions must also avoid Q11-style standing manuals (v6 L1).

**Authority and recovery:** A natural reference monitor for mediated effects, with grants, reservations and operation identity held in the broker. It needs things the current code lacks: host identity and authentication, delegation between hosts that never expands authority (A3), and a reconciler limited to reads. If reconciling requires navigating or opening a file, that is an effect needing its own authority (E3).

**Adaptive routing:** Resolving an operation against the declared handle and generation is clean. The risk is a unified grammar that hides surface limits; the browser route, for example, has no key, hotkey, menu or scroll operations (browser_driver.py:411-443), and hiding that pushes surface reasoning back onto the host model. Degraded capabilities must be stated, never silently substituted.

**Minimum experiment:** candidates.md:177 plus three cases:
- a timeout after dispatch where the same host retries with the same operation ID, compared with a fresh host that never saw it;
- a bypass where the host edits the bound document through a tool Footwork doesn't mediate, which must invalidate the binding and block certification;
- a disconnect after the save, with the owed result retrieved by a different client.

**Falsifier:** H4 is falsified as the product core if:
- a reconnecting host with fresh context can't finish without reconstructing the transcript;
- a retry after a timeout duplicates the effect;
- a refused operation succeeds through a fallback the broker offers;
- the two client adapters need materially different recovery logic.
Its assurance claim is falsified for any deployment where in-scope effects can bypass the broker undetected.

## H5 — needs_revision

**Strongest case:** It answers the demo's hardest moment, 'save outcome unknown', most directly: read the file, compare it with the desired content, and act only on the difference. That is v5's reconcile-before-retry stance (v5:335-339). Footwork already has this kind of convergence test for files: save readback compares the named file with the window's text (overlay:15-19). Separating method from outcome means replanning needs no new authority (A1), and correcting the goal changes the desired spec while keeping the operation history.

**Main failure mode:** GUI observation is partial and has no version counter like Kubernetes' resourceVersion. 'Not observed' is easily mistaken for 'absent' (the absence blind spot at v6:108), producing duplicate appends or extra copies, and existing look-alike output can falsely satisfy a predicate. Writing predicates for each resource family takes app-specific engineering. One-shot effects fall back to commitment records (like H1's journal), and multi-resource tasks need a coordinator (like H3). For unfamiliar apps, route strategies need a local planner, so most planning happens outside the controller.

**Human intuitiveness:** Intuitive for output tasks ('the copy in this folder should contain this total'), and showing conflicts with a person's edits comes naturally. Less intuitive for browsing, forms and one-shot actions. A prohibition like 'do not submit or pay' isn't a state at all.

**External-agent ergonomics:** Little back-and-forth when an agent can state a precise outcome; it then reads concrete differences. The burden moves to specifying desired state and prohibitions correctly, and the agent gives up control of method. A wrong spec converges confidently on the wrong result.

**Authority and recovery:** Best E2 behavior for resources that can be read back authoritatively, provided predicates have three states (satisfied, unsatisfied, unknown) and the controller may not mutate on unknown. Level-triggered loops need finite budgets and must not turn into standing authority (E5). One-shot commitments need stable identity and payload fingerprints (v5 §6.1). Reconciliation must never overwrite the person's edits (candidates.md:194).

**Adaptive routing:** Swapping routes is safest here because success is defined by the predicate, not the route. That holds only where a trustworthy readback exists: in the demo, the saved file, but not the browser source. If the source total is visible only in a PDF or canvas, the predicate's input is advisory at best, and the controller must stop rather than converge.

**Minimum experiment:** candidates.md:206 plus three cases:
- a delayed or unflushed write, where the file isn't visible on the first read;
- an existing correct copy versus an unrelated look-alike with the same file name in a different folder;
- the source total changing after it was copied.
Use the same drivers and journal as the other prototypes.

**Falsifier:** H5 is falsified if any duplicate, overwrite or false 'satisfied' results from treating an unknown or partial observation as settled. It is falsified as the primary owner if most demo-class steps need a local LLM planner or commitment records rather than predicate convergence, or if predicate engineering per resource family exceeds a preregistered budget. Even then, its pattern can be kept as a reconciliation strategy under another owner.

## Conditional recommendation

**Personal local app:** Conditional ranking for the primary owner of progress; this is not a selection: H1 ≈ H3 > H5 > H2 > H4.

For one person on one Mac, the app process runs continuously anyway, so H1's advantage of being a library rather than a daemon is small. The real choice is between progress owned by the caller and progress owned by a scheduler:
- **H1:** attended, one-off tasks, the lowest coordination cost and the strongest local atomicity.
- **H3:** frequent hand-backs, a person who walks away, and recurring jobs.

The rest of the ranking:
- **H5** is most useful here as a reconciliation strategy for file outputs, not as the owner.
- **H2** moves up only if the change-signal probe shows reliable push invalidation. Working alongside a busy person is the case where a personal app differs most.
- **H4** is last as primary owner because a person gets nothing from a broker without a bundled planner, though its boundary shape is a good internal interface.

All rankings assume the shared floor (durable intent, effect-unknown, task budgets, machine-level posture lease, typed demo contract) is built first and identically for every candidate.

**Portable agent toolkit:** H4 > H1 with RPC (which converges on H4) > H3 as a job-level API over the same boundary > H5 for specific resource families > H2.

H4 ranks first only if the broker:
- owns task records, pending and unknown operations, owed results and remaining budgets independently of host conversations;
- returns a task projection when a host reconnects;
- limits its assurance claim to effects it mediates.

If target hosts routinely have unmediated shell or app tools, no candidate can claim full boundary coverage without OS-level containment, and this ranking speaks only to ergonomics.

**Repeated jobs:** H3 > H5 (when outputs are readable artifacts such as a recurring report) > H1 > H4 > H2.

Recurring work also needs:
- v5 E5 standing-grant binding: job revision, identity for each occurrence, aggregate consumption, and policy for missed or overlapping occurrences;
- W3 drain semantics.

No candidate specifies these yet. H3 is the only one whose owner naturally holds them.

**Minimal composition:** A least-commitment hybrid, offered as a hypothesis with its own falsifiers (H1's and H4's), not a recommendation from source plausibility.

- **Primary owner of progress:** the current caller. That is the bundled planner for the human shell, or the external host for agents.
- **One governed operation boundary:** the only path to driver mutations. It holds grants, reservations, operation identity, receipts, the machine-level posture lease, task-level budgets and custody records. It is H1's journal exposed both in-process and through an H4-shaped typed protocol: one object with two front-ends.
- **A bounded custody reconciler:** may only settle unknown outcomes through authorized reads and hold owed results for the next authorized caller. It never plans or retries effects.
- **H5-style three-state resource predicates:** used only inside reconcile() for readable artifacts.
- **H3 templates, if added:** run as a client (a caller), not as a second scheduler.
- **Actors:** none until the change-signal probe justifies them.

Fork: if unattended continuation after a hand-back is required, the primary owner must switch to an H3 scheduler, and callers become planners for stage activities. Never run both as owners.

Decision questions:

- Will tasks normally run while a person or agent is present, or must work and owed results keep moving after the caller leaves? This decides between caller-owned and scheduler-owned progress.
- Who is the primary customer: a person in Footwork's own shell, or external agents such as Claude Code and Codex calling Footwork? This decides between H1 and H4.
- Are the most valuable tasks repeated with a stable structure, or mostly one-off exploration? This decides whether H3 is worth its authoring cost.
- Are the most valuable outputs artifacts that can be read back authoritatively (files), or one-shot events (submit, send)? This decides whether H5 is an owner or only a strategy.
- Will a person routinely work on the same machine while a task runs, and do the pinned drivers actually signal changes? This decides whether H2 is justified.
- Must Footwork's assurance cover effects that a host makes through its own tools? If yes, OS-level containment is needed, and none of H1–H5 suffices alone.
- Is a resident local process (menu-bar app or daemon) acceptable to the user?
- For each entry point, who receives an owed result, and what counts as delivered: a rendered card, the person viewing it, a host fetching it, or a host acknowledging it?
- Should a copied source value be the value at observation time, or must it still be current when the destination is committed?
- Will one machine run one task at a time, or several concurrently? This determines how much machine-level arbitration is needed.

## Unresolved assumptions

- BLOCKING (all candidates): the drivers can tell an effect that may already have happened apart from one never sent. Today, exceptions after dispatch become 'refused' or 'not dispatched' (native.py:728-745; browser_driver.py:354-359; session.py:992-994).
- BLOCKING (all candidates): the demo's destination identity can be established ('a new copy in this selected folder', the original untouched) and the saved bytes can be read back authoritatively within a bounded time. The current evidence binds by basename only (completion.py:75-76).
- BLOCKING (all candidates): a machine-level lease on foreground, keyboard and clipboard can be enforced across processes and sessions. Posture today is per session (posture.py:173-188), and CrossLoop defaults to foreground_permitted (crossloop.py:101).
- BLOCKING (all candidates): natural language can be compiled into a validated contract, including prohibitions. The current regex-derived requirements misread 'Do not submit' (completion.py:172-183).
- BLOCKING (H2): the pinned Cua and CDP routes give timely, reliable change signals for a person's edits, navigations and window replacement. The packet has no evidence for this.
- BLOCKING (H4, and H1 with external callers): every in-scope mutation passes through Footwork's boundary. Hosts with shell or other tools can bypass it.
- BLOCKING (H5): demo-class resources have predicates with three states (satisfied, unsatisfied, unknown) that don't mistake 'not observed' for 'absent' (v6:108).
- (H1, H4): a bounded custody reconciler can settle unknown outcomes by reads alone. If settling needs navigation or opening files, those reads are effects that need their own authority (E3).
- (H3): one-off GUI tasks can be turned into stage graphs without excessive revision or false milestones, and showing stage context doesn't reproduce the Q11/Q11b effects.
- (all candidates): a person's changes during a hand-back or while working alongside the agent can be attributed to the person, not mistaken for agent effects or silently overwritten.
- (all candidates): browser subject identity can survive navigation within the bound tab. Today, handles are new on every connection and rebinding is by URL key (browser_driver.py:285-287).
- (all candidates): visual checks stay advisory, native-only and opt-in. No candidate establishes source values or completion from pixels, and browser capture, perception accuracy and visual execution remain unqualified.
- (all candidates): there is a single user and a single machine. Authority with multiple principals is out of scope (v6:169).
- (H2 benefit): per-command cold attach (v6:132: look ~1 s, do 4–6 s) is a meaningful share of verified end-to-end time. This is unmeasured against the costs of capture, model calls, settling and readback.

## Source limits

- session.py, native.py, browser_driver.py, agent.py, crossloop.py, desktop.py and desktop_s2.py were provided only as line-range excerpts (offsets taken from manifest.json). These files were not in the packet: authorize.py (including Authorizer behavior with judge=None), carry.py, delivery.py, ledger.py, progress.py, the native save_readback implementation and session.observe(). Claims about them are limited to what the excerpts show.
- The v6 status table is pinned to afe6d94 and the evidence overlay to 2026-09-26. Where copied 88325d1 sources were available I used them, but I couldn't check every v6 status cell against 88325d1.
- Not in the packet: controller-runtime source, browser-use and Cua source, LangGraph's checkpointer/state.py, pi's transaction and storage modules, arc-cua's models/driver/macos_hybrid, the September full-refactor proposal, and any results directories (Q15, Q17, G3, the visual proof report). Claims about them in candidates.md are unverified here.
- The status of the native visual capability comes from the documentation and notebook text (visual-checks.md; notebook 2026-10-08), not from running anything. It is described as mechanically verified and advisory, and not qualified for perception accuracy, browser capture or autonomous visual execution.
- Nothing was run: no tests, prototypes, probes or measurements. Every risk and ranking here is a design judgment from source inspection, not conformance or performance evidence.
- The MCP specification wasn't in the packet. The point that annotations aren't enforcement rests on the chrome-devtools-mcp ToolDefinition excerpt and on v5:220 and v5:267.
- I didn't examine whether candidates.md and the September draft are complete beyond the copied files. The provenance claims for the v6 hash and the model probe (candidates.md:7, 245) were not independently verified, apart from the v6 SHA-256 recorded in manifest.json matching the prefix given in candidates.md.

## Review receipt

- Canonical model: `claude-opus-5-5`; effort: `xhigh`.
- Copied input files: 34; all input hashes unchanged.
- Candidate IDs: H1, H2, H3, H4, H5.
- Wall time: 688.61 seconds.
- Provider-reported review cost estimate: $2.7561496.
- Read-tool permission denials: 0.
- Private structured output and receipt: `output/architecture-hypotheses-20261008/`.
- No new product tests, paid evaluation corpus, heldout execution, implementation or architecture selection in this review.
