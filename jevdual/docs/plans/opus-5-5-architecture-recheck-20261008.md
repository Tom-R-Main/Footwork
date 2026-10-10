# Opus 5.5 focused architectural recheck

Fresh `claude-opus-5-5` session at `xhigh`. This second review received revision 2 and the prior critique as text, with tools disabled. It did not re-inspect source or execute anything. The original source-grounded review remains separate.

## Distinctness

Yes, as complete configurations, not as five scheduling algorithms. There are four distinct progress owners:
- **Caller-driven:** an attended trusted caller (H1); H4's external hosts drive progress the same way.
- **Resident reactive:** a resident goal actor that delegates bounded subgoals to surface agents (H2).
- **Compiled graph:** a deterministic interpreter over a versioned stage graph (H3).
- **Level-triggered:** resource controllers that react to observed state (H5).

H4 differs from H1 on trust and custody, not on scheduling: authenticated untrusted hosts, broker-held custody, and broker-owned settlement when no host is present. That is a real architectural difference, but choosing between H1 and H4 is a product and trust decision that invariant prototypes cannot settle.

The separation is still partly cosmetic in two places:
1. The surface-lifecycle and enforcement-boundary columns barely separate H1, H3 and H5. All three attach to surfaces on demand and gate actions in code.
2. H3 and H5 never say whether they run as a resident process. That hides where they sit on the packet's own first decision fork, attended versus unattended.

Three boundaries still depend on rules that aren't written down:
- **H2 vs H3:** who decides after a subgoal succeeds. If H2 follows a cached plan, it becomes H3 with actors.
- **H5 vs H3:** the 'report revision' resource re-encodes the step order.
- **H4 vs H1:** whether local host authentication is real or just a convention.

## Remaining design obligations

### B1 — shared

The shared contract promises 'identical semantics, test cases and independent oracles', but each prototype section lists a different, partly self-selected set of tests:
- Look-alike output and delayed writes are tested only on H5.
- An unmediated edit is tested only on H4, although H1's 'local agent uses the direct API' has the same exposure.
- Process kills around intent and dispatch are tested only on H1.
- Hand-back appears in none of the five prototype lists.
Cross-cutting hazards therefore land wherever each candidate's framing puts them.

Needed correction: Publish one scenario matrix and run it against all five with the same oracle and the same expected outcomes. It should cover:
- kill points around intent, dispatch and save;
- an unknown outcome after a timeout, and a torn persistence write;
- a missing verifier or judge;
- an external edit to the destination, and a source that changes after copying;
- tab navigation and duplicate tabs;
- contention for the foreground, and a sign-in hand-back;
- an unmediated host edit;
- a total that appears only as an image;
- look-alike or preexisting output, and a delayed write.
Keep candidate-specific scenarios only for each hypothesis's own claim. Before scoring, decide which failures are floor-implementation defects and which are architectural falsifiers.

### B2 — shared, H1, H2, H3, H4, H5

The revision says it incorporates F1–F19, but none of the 12 shared items restates F9: every mutating route crosses the candidate's declared enforcement boundary, and planners hold capability handles, never drivers. The routes at stake:
- setup and attach;
- recovery;
- reconciliation reads that navigate or open resources;
- compatibility helpers;
- H2's local loops in surface agents;
- H4's broker reconciler;
- H5's strategies.
Without this item, no test checks the 'enforcement boundary' column.

Needed correction: Add a shared item that lists these routes. Each candidate maps every route to its boundary, and one enforcement-mutation test per route per candidate can falsify the mapping. Frame it as a verification obligation; it does not assert that current helper paths bypass verification.

### B3 — shared, H5

The contract leaves two things undefined.
- **State or provenance claim.** The demo says 'save a new copy', and item 10 separates state claims from claims about who acted. Yet H5's prototype treats preexisting correct output as a case that may satisfy the job. Which kind of claim each clause makes is never declared, so the preexisting-output scenario has no defined expected result. H5's 'avoids redundant edits' benefit exists only under one reading.
- **Who writes and approves the typed contract.** H3 and H5 each describe their own 'intent compiler', so the candidates may start from different inputs.

Needed correction: Declare each clause as either a state claim or a provenance claim. For example: this task must create the new file, the original must remain byte-unchanged, and no submit or pay may occur. Apply the same expected outcomes to all five.

Hold one contract compiler fixed as a model role, and derive H3's graph and H5's resource spec from the same typed contract.

State when the person confirms the contract: only for prohibitions, ambiguous bindings or scope, not on every routine job.

### B4 — H3, H5

Only H1 (attended) and H2 (resident) say whether anything runs when no caller is present. H3 promises 'durable continuation' and 'resume the same job later', and H5 promises that controllers 're-read actual state after restart'. Neither says who runs the interpreter or the controllers after a crash or logout, or whether they act unattended. This hides each one's position on the packet's first decision fork.

Needed correction: For H3 and for H5, declare one of two modes:
- a resident service that acts unattended (then compare it with H2 on unattended progress, and state the posture for unattended actions); or
- invocation-driven, with waiting semantics like H1's.
If both modes are allowed, score them as separate configurations.

### B5 — H1

H1's custody is a passive journal, which leaves four gaps:
- An in-process caller that crashes cannot write 'waiting-for-caller', so that state has to be derived when the task is next opened.
- There is no task-level claim on progression. Two local callers, which H1's own prototype includes, could both 'continue' the same task. Atomic grants and the foreground lease don't prevent this split-brain planning.
- With no service, machine arbitration across H1 processes has no named home.
- Reading back to settle an unknown outcome may need authority that the spent single-use grant no longer provides.

Needed correction: - Add a task claim lease with an epoch. It fences local dispatch only, not the GUI.
- Define a takeover rule for stale claims.
- On open, derive the crashed state from records that were started but never settled.
- Name the cross-process lease file for foreground and keyboard.
- Define a scoped settlement and readback authority, bound to the pending operation ID, that neither consumes nor refunds the effect grant.
- Disclose that stranded obligations surface only when the task is next opened.

### B6 — H1, H4

'One trusted local app/planner' conflicts with 'a local agent uses the direct API'. If coding agents such as Claude Code or Codex import the session API in-process, H1 becomes H4 without authentication. Those agents' own shell and AppleScript tools bypass the boundary exactly as they do in H4. The in-process boundary only protects against mistakes a planner makes through the API; it doesn't constrain a caller that can reach the drivers directly.

Needed correction: Either limit H1's caller to the first-party planner, or state that external agents using the API fall under item 10's coverage limit. Say explicitly what the in-process boundary does and doesn't protect against, so H1's assurance isn't scored as equal to H4's.

### B7 — H2

H2 replans on 'materially new progress/blockage events', and H3 also revises its plan on blockage. If H2's goal actor follows a cached multi-step plan after subgoals succeed, H2 becomes H3 with actors. 'Bounded subgoal contract' is not defined. After the goal actor is replaced, nothing stops a surface agent that is still running under the dead actor's assignment.

Needed correction: - State that every subgoal result is a decision point for the goal actor. Count planner calls and give them a budget.
- If plans may be cached, give the cache a stated bound that keeps H2 distinct from H3.
- Type the subgoal contract: bound resource incarnation, permitted effect classes, a budget slice drawn from the task reservation, termination and evidence conditions, and escalation.
- Put the goal-actor epoch on each assignment so a stale agent stops at its next local dispatch. This fences local dispatch, not the GUI.

### B8 — H2

The shared demo runs in sequence, and item 3 lets foreground arbitration serialize the agents, so H2's claimed gains (faster multi-surface response, unattended progress while the person works elsewhere) are barely exercised. If editing the native report needs the foreground, 'continue while the person works elsewhere' conflicts with the background_only default and with respecting the person's activity.

Needed correction: Add a scenario that can tell H2 apart, using the same oracle, and run it against H1 with its pull-and-recheck behaviour:
- The person is actively using another app under background_only posture.
- H2 must either progress through routes that work in the background or visibly queue for the foreground.
- An external edit or a navigation must trigger replanning.
Measure end to end, including restart and the cost of planner calls. Keep the gate on the change-signal probe that the revision already states.

### B9 — H5

Four gaps in H5's resource model:
- **'A report revision' as a controlled resource.** It re-encodes the step order (value, then revision, then copy). It also conflicts with preserving the original across Save As, where the window's document identity may move to the new file. A level-triggered controller watching the original could then apply the edit to it again.
- **No release rule.** Nothing says controllers stop owning resources once a one-off task settles, so later edits by the person could be 'reconciled' away.
- **'Narrow model checks may answer a declared semantic question'.** This has no boundary that keeps out hidden local planning.
- **Unknown has no exit rule.**

Needed correction: - Put the desired state on the output artifact, and put a preservation predicate on the original.
- Make the in-app edit and the save an operation-bound commitment inside the artifact strategy.
- Release ownership when a one-off task settles. Ongoing ownership needs the explicit standing-work authority.
- Limit model calls to extracting or classifying among targets the strategy enumerates; they never emit action sequences.
- Bound re-observation when a state is unknown, then escalate to the person.

### B10 — H4

Three gaps in H4's trust claim:
- **No local authentication mechanism.** 'Authenticated' and 'per-principal scope/delegation' are H4's distinguishing trust claims, but no mechanism for authenticating local hosts is named. Processes running as the same user can usually read another host's pairing token, which would reduce the protocol boundary to a convention, effectively H1 over a socket.
- **An unenforceable claim.** 'Cannot recreate the task under a new conversation to reset consumption' is stronger than the broker can enforce, because it can't link a new task to an old intent.
- **Unattended reconciliation with no posture.** When no host is connected, the broker's reconciliation acts unattended, and no posture is stated for it.

Needed correction: - Specify the host-identity mechanism and its residual risk: any process holding a host's credential acts as that host.
- Add aggregate limits per principal, plus the shared resource-scoped check for pending unknown effects, and narrow the reset claim to what those actually enforce.
- Restrict reconciliation without a host to background-only observation that consumes no effect grants.

### B11 — shared

Items 2 and 8 protect consumption and custody within a single task. A fresh task (a new H1 invocation, a new H4 conversation, a new H2 goal) can still redo an effect that another task left in an unknown state on the same bound resource.

Needed correction: Index unresolved unknown operations by bound resource incarnation and destination. When a new task binds those resources, it must surface them and block dependent mutations until they are settled or the person explicitly releases them. Test this on all five.

### B12 — shared, H1, H3, H5

Item 4 refuses a route when the pinned driver cannot establish stable identity, and the copied browser driver issues new handles on every connection. If stable tab identity needs a persistent connection, the candidates that attach on demand (H1, H3, H5) would fail or refuse the browser route while H2 and H4 pass. The demo would then silently score how surfaces are attached rather than who owns progress.

Needed correction: Before prototyping, settle whether the pinned driver provides a target identity that survives reconnection. If it doesn't, choose one of two options:
- give every candidate the same persistent attachment helper, and state that this concedes part of H2's and H4's lifecycle; or
- record the refused browser route as a declared architectural cost of attaching on demand.

### B13 — shared

The shared items mostly define internal correctness, but several could quietly add prompts for the person:
- changes after a hand-back labelled 'externally changed/unknown';
- refusals because identity can't be established;
- holds on unknown outcomes;
- contract confirmation.
No item says which outcomes proceed automatically and which interrupt the person. The demo also uses one invoice site and one report app, so nothing exercises 'adapting to native and browser use', and neither H5's coverage tradeoff nor H3's template value can show up.

Needed correction: - For each shared item, classify outcomes as automatic or surfaced to the person.
- Label changes made during a hand-back by time window ('changed during hand-back'), never by actor.
- Ask the person only when a change conflicts with the contract or with a pending operation's preconditions.
- In prototypes, count prompts and escalations per run as a cost signal, not as a usability claim.
- Add adaptation variants (an unfamiliar invoice layout, a layout change mid-task, a second report app), and record 'unsupported' separately from 'failed'.

### B14 — H3

'Revision changes remaining stages through an explicit contract-preserving operation' names neither what triggers a revision nor who approves it. If the person must approve every generated or revised graph, H3 adds manual work to every job. If revision happens automatically on every blockage, H3 moves toward H2.

Needed correction: - Define the trigger: a stage blockage produces a compiler proposal, which is validated against the typed contract.
- Apply revisions automatically inside the envelope, and ask the person only when scope changes, consistent with item 9.
- For routine jobs, show the stage projection for information only, not as an approval gate.
- Measure the revision rate as the 'recurring graph correction' falsifier.

## Corrections to the first review

- Distinctness, corrected from the first review: version 1 failed because owners were unnamed. Revision 2 names a primary progress owner for each configuration, so the five are now distinct as complete configurations: four progress models plus one trust and custody variant (H4, a variant of caller-driven progress).
- H2 no longer collapses into 'H1 driven by events'. Residency, delegation to fenced surface agents and unattended progress are real differences. The remaining risk is collapse toward H3 if H2 caches plans after successful subgoals.
- H5 is coherent as a planner-free option with deliberately narrow coverage. Dependency references between resources are not an H3 stage coordinator on their own. The 'report revision' resource, however, re-encodes step order and conflicts with preserving the original.
- The prior recommendation to merge H1 and H4 is superseded. Custody while no host is present, broker-owned settlement and authority scoped per principal are real architectural differences. Choosing between H1 and H4 is still a product and trust decision that invariant prototypes can't settle.
- H1's attended custody is enough for its stated promise (attended work, continuation at the next invocation) only with three additions: a task claim with an epoch, a crashed state derived when the task is opened, and a scoped authority for settlement readback. Without the task claim, H1's own two-caller test can produce split-brain planning.
- The revision's narrowing of the prior review is accepted. An optional-verifier helper path doesn't show that every configured entry point bypasses verification, an upstream driver may already fence actions, and the screen-lock fail-open is a specific degraded-path question. All three remain verification obligations, not established defects.
- Accepted as correct in revision 2: item 3 limits fences to local dispatch owners; item 6 forbids inferring human attribution from local state; item 7 treats a presentation receipt as proof the result was shown, not that it was read or accepted.
- Overclaim in revision 2: it says it incorporates F1–F19, but the route-coverage obligation (F9) is missing from the shared items, and the shared contract compiler from F3 is only implicit.
- Overclaim in revision 2: the surface-lifecycle and enforcement-boundary columns overstate how different H1, H3 and H5 are. All three attach on demand and gate actions in code.
- Inconsistency in revision 2: the shared contract says 'identical test cases', but the prototype test lists differ by candidate.
- Sharing semantics, tests and oracles while letting each candidate choose its own store and engine is sound, because a shared kernel would predetermine the architecture. The cost is five separate floor implementations, so floor defects must be scored separately from architectural falsifiers.

## Conditional shortlist

Conditional shortlist, not a selection:
- **Attended first-party app.** H1 is the baseline. H3 earns its extra structure only if repeated multi-stage jobs with hand-backs dominate and its revision rule avoids approval churn. Compare it against H1 with the same operation semantics.
- **Unattended background progress required.** H2, but only if the change-signal probe and the background-posture scenario succeed. If they fail, the alternative is H3 run as a resident service, once that is declared. Adding a scheduler to H1 would make it a different configuration.
- **Governed tools for external agents.** H4, if local host authentication is credible. With a first-party client planner it can also serve the human app, at the cost of running a broker.
- **H5.** Only if the first release deliberately targets registered output families and accepts 'unsupported' everywhere else. Otherwise treat its three-state reconciliation as a technique another owner can adopt; that hybrid would then be scored as a different configuration.

## Decision questions

- Must a job keep progressing when no Footwork caller or window is active (unattended), or is attended work with reliable resume enough?
- Is the first product an assistant for one person, or a governed capability service for external agents such as Claude Code or Codex? Must those agents be treated as untrusted?
- Are the target jobs mostly repeated with recognisable stages, mostly one-off, or mostly defined by an output artifact in a known app family?
- Is broad adaptation to unfamiliar sites and apps required in the first release, or is narrow registered coverage acceptable?
- In the demo, does 'save a new copy' mean this task must create the file (a provenance claim), or only that a correct copy must exist (a state claim)?
- Which outcomes may interrupt the person (contract confirmation, unknown outcome, external change during a hand-back, identity refusal), and how many interruptions per task are acceptable?
- Is a resident background process acceptable on its own merits (permissions, battery, trust), separately from the question of who owns job progression?

## Limits

- This is a focused text-only recheck. Tools were disabled, so I opened no Footwork source, reference repository, v6 or v5 draft, or the original packet in this session. The judgments rest only on the revision 2 text and the prior review as quoted.
- Nothing was executed or verified empirically. Driver change signals, a tab identity that survives reconnection, LangGraph resume semantics, MCP timeout behaviour and macOS mechanisms for authenticating local processes appear here as conditions to settle, not as facts.
- I did not re-check or reproduce the source risks and line references cited in the first review. Current product limitations remain unimplemented and untested.
- I drew no inference about human attribution or external fencing from local state, and treated no optional helper path as proof that all entry points bypass verification.
- Burden and intuitiveness can't be judged from design text. Only the separate preregistered paired study can assess them.
- I did not estimate the cost, schedule or implementation feasibility of any configuration.
- The architecture choice stays with the user. The shortlist depends on how the decision questions are answered.

## Receipt

- Provider-recorded canonical model: `claude-opus-5-5`.
- Effort: `xhigh`; fresh session; tools disabled.
- Complete configurations distinct: true.
- Input integrity: unchanged.
- Wall time: 480.73 seconds.
- Provider-reported cost estimate: $0.879208.
- Private receipt/structured output: `output/architecture-hypotheses-20261008/`.
