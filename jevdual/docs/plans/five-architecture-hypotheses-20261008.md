# Five architectural hypotheses for intuitive browser and computer use

Design candidates for human selection. These are structurally different hypotheses, not measured winners, five implementation branches or permission to replace current runtime defaults. Prepared October 8, 2026, against Footwork `88325d1`. The earlier full-refactor proposal supplies one candidate; it is not the selection criterion.

## Source and objective

The latest complete Legible Loop draft located on this device is **v6, dated September 26, 2026**: `/Users/thomasmain/Desktop/the-legible-loop-v6-draft.md`. The copy at `/Users/thomasmain/Documents/Codex/2026-09-24/aud/outputs/the-legible-loop-v6-draft.md` is byte-identical. SHA-256: `fba1eda246d87c38` (prefix; the review packet retains the full digest). Spotlight filename search across indexed device locations and filename search in Desktop, Downloads, Documents and projects found no later complete draft. This establishes the latest located version, not proof that an unindexed/renamed draft cannot exist.

v6 is a design standard for the harness, independent of any architecture. Its objective is dependable task accomplishment with less avoidable effort imposed on whoever drives, while preserving granted authority, honest claims and the person's control. Its six questions are: outcome owed; currently permitted moves; observed effects; pending/unknown state; completion conditions; decision ownership. Its nine rules cover useful declarations, truthful receipts, working routes, uniform authority, changed-target refusal, evidence-based completion, execution posture, retained decisions/resume and parity between drivers.

v6 explicitly retains v5 obligations it does not yet exercise. Read v5's A1–A4, E1–E5 and M1–M3 alongside it: replanning within an existing grant, non-expanding delegation, conserved reservations/budgets, actual effect-boundary checks, unknown-outcome reconciliation, durable result/delivery custody, recurring-work limits and continuity across model/worker turnover. Both drafts are external reference documents; do not change them or turn their historical status table into a current conformance claim.

Current Footwork adds evidence after that draft: [the repository overlay](legible-loop-evidence-20260926.md), native/cross-surface evidence, and [native advisory visual checks](../visual-checks.md). The visual package is implemented and has retained mechanics/loopback/native verification; independent perception quality, browser visual capture, live pixel preconditions and crop/save execution remain separate qualifications. This supersedes the prior refactor note's observation that its implementation prediction was open at the earlier review time.

User objective: **Footwork should adapt to browser and native computer use and be intuitive for a person and an external agent.** A usable default must avoid requiring the caller to learn internal backend names, repeat task configuration after a pause, manually reconstruct progress, or infer a successful save from an input acknowledgment.

## Equal product brief for all five

Use the same visible shell and task semantics when comparing architecture. Otherwise an attractive UI could win a runtime comparison for the wrong reason. This document describes interaction contracts, not generated visual mockups or implemented commands.

One entry point accepts a goal and scoped resources. A person selects a tab/window/folder using a picker or explicit names; an agent supplies typed handles. A task card presents the goal, selected surfaces, permitted changes, execution posture, progress, unresolved evidence and the next useful move. Relevant detail appears when needed. The shell provides run, inspect, pause, continue, correct and stop; the CLI/SDK expose equivalent operations. Natural language is input to a contract proposal, never silent authority to select every open window or rewrite acceptance conditions.

Demonstration task for every hypothesis:

> From this selected browser tab, copy the displayed invoice total into the selected local report document and save a new copy in this selected folder. Show the saved result. Do not submit or pay anything.

Browser observation supplies a source-bound value. Native observation identifies the destination document and current revision. Routine navigation and editing stay within the granted envelope. Save creates a scoped copy, whose actual bytes/value are independently read back. A person editing the destination mid-task invalidates dependent work. A pause retains the task and recorded progress. Image checks, if invoked, remain advisory and disclose their exact scope.

The shared shell might say: "Total read from the selected invoice. Report edited. Save outcome unknown; checking the selected file before trying again." It offers a meaningful next action rather than a generic error or an invitation to repeat a potentially duplicative operation.

### Shared invariants, not a sixth architecture

Every candidate must implement these semantics using its own ownership model:

1. Task scope and exact-effect approvals remain distinct; method changes do not reset authority or require routine reapproval.
2. Every mutating route, including setup/navigation, Enter, scripts, key/menu, recovery and compatibility helpers, has an explicit enforcement boundary.
3. Task authority, credentials and mutation ownership have separate lifecycles. Remote calls or local leases do not manufacture stronger external guarantees.
4. Closed proposals bind to real observations/resources. Browser DOM, browser AX and native AX capabilities remain explicit; identical numeric IDs do not identify the same subject across them.
5. Delivery, UI change, resource persistence, semantic judgment and task fulfillment are distinct records/decisions.
6. Record stable operation identity and durable intent before an effect attempt. Unknown external outcomes reconcile before retry; local persistence failures are also explicit.
7. Retained decisions and result/delivery obligations survive caller/worker turnover, with an identified current custodian and bounded recovery. A finished producer is not proof of received fulfillment.
8. Shared spend/call/time/quantity reservations survive delegation, restart and uncertainty. Cancellation does not imply a refund.
9. Preserve foreground/background promises, secrets and disclosure rules. Fallback may choose only a declared supported route within the envelope; it cannot silently take the foreground, widen capture or switch documents.
10. Preserve qualified Jev text roles/settings and provider-native provenance. A low text confidence alone does not authorize images or a new model. Missing required answers cannot inherit old positives.
11. UI and prompts are projections, never the canonical authority/evidence store. Refused claims retain their content with an honest status.
12. Keep evaluation independent, pre-register empirical comparisons and keep sealed adoption data untouched. Structural plausibility and reviewer agreement are not conformance measurements.

### What makes the five genuinely different

| Hypothesis | Unit that owns progress | Canonical state | Scheduling | Distribution boundary |
|---|---|---|---|---|
| H1 Session kernel | Session service called by one current driver | Task/session journal and projections | Caller-driven, sequential operations | Python library; optional local RPC later |
| H2 Surface actors | Long-lived actor per bound surface plus coordinator | Per-actor generations/events plus coordinator obligations and shared reservations | Mailboxes and events | Explicit local workers/service |
| H3 Durable workflow | Versioned stage graph and current activity | Workflow checkpoints and operation/evidence ledger | Workflow scheduler | Durable executor plus UI activities |
| H4 Capability broker | External client owns planning; broker owns governed tool operations and custody | Broker action/task receipts and delivery obligations | Requests, subscriptions and bounded reconciliation | Protocol boundary first; SDK/CLI clients |
| H5 Desired-state controllers | Controller for a scoped desired resource outcome | Desired/observed resource records and one-shot commitment records | Reconcile loops triggered by actual state/invalidation | Controller runtime plus resource-specific strategies |

All require durable records and adapters. They differ in which component advances the job, how the job is represented and what integration boundary the product exposes. Renaming modules is not an alternative hypothesis.

## H1 — Session kernel: one coherent workspace

**Hypothesis.** A small session service provides enough adaptive browser/native behavior with the least runtime complexity. Its direct API makes uniform authority and intuitive receipts easier to maintain than coordinating independent services.

```text
shell / operator / S1 / S2 / workflow caller
                   ↓
       Session.observe / perform / verify / reconcile
                   ↓
       observation and guarded execution ports
              ↙                 ↘
       browser adapter        native adapter
       [one transactional task/session journal]
```

**Ownership.** A task owns named surface bindings; the session service owns one operation's lifecycle. The calling planner decides what to do next. Canonical task/session records hold state, exact grants, carried evidence, pending attempts and outstanding fulfillment/delivery. A serialized mutation reservation prevents cooperating callers from racing the same surface. Pure renderers supply CLI, task cards and model context.

**Demonstration.** The task starts with invoice and report handles. `observe(invoice)` returns the total and provenance. `perform(report, append(carried_total))` verifies current destination state, gates the exact mutation, dispatches and records readback. Save and saved-copy verification use production resource verifiers. A refused changed document returns a fresh observation and a named next move. Continue reloads durable state rather than invoking a new unrelated run.

**Adaptation.** The service's capability resolver chooses a qualified browser/native adapter for the explicitly bound resource and desired operation. It does not rebind to another surface when a driver refuses. A cross-surface caller sequences operations in-process instead of parsing CLI prose. Existing model policies can remain separate clients; the core does not become a planner.

**Intuitive surface.** One current task, its named resources and the last verified change. Ordinary use hides backend/version names. Advanced inspection reveals them. An external agent uses the same operation/result grammar and receives contextual continuation suggestions, not a standing policy manual.

**Recovery and risk.** Durable prepared/started attempts and grant reservations are committed before dispatch. A crash after started may be uncertain; a successor checks the actual bound resource. The service records local refusal and unknown delivery separately. Long-lived cross-surface result custody must be explicit even though the first delivery is a library; an obligation ledger without an owning continuation policy is insufficient. A later daemon is possible but changes ownership and restart semantics and must be separately tested.

**References.** arc-cua's backend/policy split and snapshot/subtask records; pi's separation of loop, versioned session entries and projections; current Footwork operator scenarios. Borrow boundaries while preserving stricter completion and temporal validity. This is closest to the previous proposal.

**Prediction and counterevidence.** H1 should deliver parity and understandable resume with few coordination components. It loses its advantage if meaningful browser/native work repeatedly needs persistent event ownership, or if making it dependable requires adding a scheduler, surface mailboxes and a service anyway. A library API alone does not prove L8.

**Smallest discriminating prototype, later.** One task/session API, two existing driver adapters, carried-value and saved-copy readback, and a kill-before/after-save scenario. Compare direct task resume and caller turnover, including delivery custody. Do not build a daemon to rescue the first result.

## H2 — Surface actors: a responsive local control service

**Hypothesis.** Computer use is naturally a collection of changing surfaces. Giving each bound tab/window a long-lived actor can improve responsiveness, invalidation and coexistence, especially when a person and agent work simultaneously.

```text
                         task coordinator
                         /       |        \
             browser actor   native actor   delivery owner
             event mailbox   event mailbox  fulfillment mailbox
                         \       |        /
                    shared authority/budget store
```

**Ownership.** Each actor owns driver attachment, observation generation, its mutation queue and current pending attempt. The coordinator owns task intent, multi-surface dependencies and result custody. Common authority and shared consumption are transactionally checked/reserved; actors check their bound resource/generation at dispatch. Durable events have IDs and incarnations. Process restarts invalidate attachments and reconcile pending effects before new dispatch rights can be acquired.

**Demonstration.** The browser actor emits a source-bound invoice value. The coordinator sends the carried reference to the report actor. A destination edit invalidates that actor's generation and pending dependent proposal; the coordinator updates the task card. The report actor saves and emits resource readback. The delivery owner settles fulfillment against the required evidence.

**Adaptation.** Each actor advertises current operations and degraded capabilities. Surface replacement creates a new binding/incarnation, not continuation under an old identity. Independent observations can proceed concurrently. Mutations on shared process/foreground resources still serialize through machine-level posture ownership; per-window actors alone cannot make same-process keyboard actions independent.

**Intuitive surface.** Live task cards show which surface is active, what changed and why an action is waiting. Explicit surfaces persist behind short names. Agent clients subscribe to committed state updates instead of polling full menus. A stale command immediately returns the relevant fresh observation.

**Recovery and risk.** Must prove ownership fencing, event deduplication/order, backpressure, missed-event gaps, actor/coordinator succession and a transactional outbox for required cross-actor results. If the coordinator dies after a save but before receiving its event, the successor discovers the pending delivery and reconciles the file. Event publication does not certify an external effect. Avoid holding global authority/budget locks during driver/model calls. Watcher death is a real degraded state, not permission to trust an old generation.

**References.** pi's durable scheduler/committed task-graph view; browser-use's event-driven browser infrastructure; Cua's rich execution records. They motivate the decomposition, not a measured speed claim for Footwork.

**Prediction and counterevidence.** H2 should reduce repeated attach/observe work and stale-result repair for multi-surface jobs. It fails as the preferred architecture if the service adds material coordination/recovery burden without better verified outcomes, or if actual driver capabilities cannot reliably signal relevant changes. Warm attachments can retain stale state and must earn their benefit.

**Smallest discriminating prototype, later.** Two local surface actors and one coordinator; one unrelated human edit, one disconnect, one duplicate event and one coordinator crash. Measure end-to-end verified time including cold start and restart; test shared foreground arbitration. No distributed cloud bus is needed.

## H3 — Durable workflow graph: the job is the interface

**Hypothesis.** Intuitive cross-application use comes from making the user's job a durable sequence of verified stages. A workflow interpreter provides clearer progress and retained decisions than open-ended session loops.

```text
intent -> versioned stage graph
             ↓
read invoice -> update report -> save copy -> verify file -> deliver result
             [checkpointed workflow + governed operation ledger]
             ↓ each UI activity
        browser/native driver port
```

**Ownership.** The workflow scheduler owns stage advancement, pauses, budgets, custody and completion. A stage declares inputs, allowed resources/effects, required evidence and bounded recovery; its UI activity may use S1/S2 adaptively within those bounds. Graph revisions preserve settled effects and outstanding obligations. The planner may propose replacing remaining stages without erasing the evidence or silently widening authority.

**Demonstration.** The user sees five stages, with source/destination details only when useful. A sign-in or retained save decision pauses the relevant stage. Resume enters through reconciliation, checks which effect already happened and continues remaining work. Human correction of the destination revises dependent stages and their resource assumptions; it cannot invalidate the historical fact that an earlier action happened.

**Adaptation.** Stages speak in outcomes such as "obtain displayed total" or "verify scoped saved copy". Activity adapters choose qualified routes. Unknown websites and native layouts remain the local activity planner's responsibility; the graph is not a fixed list of pixel coordinates. Stages can be generated, but their interpretation and contract compilation need validation.

**Intuitive surface.** A reusable job card has named inputs, expected outputs and meaningful milestones. CLI/agent clients start a job, inspect the current stage, submit a retained decision or continue. Users need not manage a raw target ID for every step. One-off exploratory tasks still need a usable ad hoc path; requiring a YAML graph for every task would defeat the objective.

**Recovery and risk.** Checkpoint replay is not external-effect replay. LangGraph's interrupt implementation explicitly resumes from the start of a node. Non-idempotent UI actions require stable operation records, separated effect stages and authoritative reconciliation. A graph checkpoint cannot certify that a saved/submitted result is absent. Compensation is separately governed. Preserving arbitrary old graphs across version changes introduces its own compatibility work.

**References.** LangGraph's state graph/checkpoints/interrupt contract; pi's durable phased task scheduler; durable-workflow principles from the earlier reference review. [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) explains repeated node execution; use that caution, not implicit exactly-once UI claims.

**Prediction and counterevidence.** H3 should reduce reconfiguration after hand-back and make repeated jobs legible. It loses if unfamiliar work produces excessive graph revisions, template authoring or false milestones, or if stage context causes the model to narrate unverified requirements as in Footwork's declaration experiments. More displayed structure can increase burden.

**Smallest discriminating prototype, later.** The five-stage example with one reusable template and one ad hoc generated graph, an interrupt after an effect, and a mid-task destination correction. Compare verified outcomes, interruption recovery and authoring burden against a free session with the same shell.

## H4 — Capability broker: Footwork is a portable governed tool system

**Hypothesis.** Footwork should make any agent or operator effective through a consistent browser/computer tool contract. Keeping planning in the host gives the smallest integration surface and widest reuse.

```text
Codex / Claude / other agent / human shell
                   ↓ protocol or SDK
observe / act / inspect / reconcile / verify
                   ↓
      governed capability broker and receipt store
                ↙       ↘
          browser tools  native tools
```

**Ownership.** The host owns planning and progression. The broker owns declared tool contracts, current task grants, action identity, reservations, evidence and effect settlement. A durable custody registry names who owes continuation/delivery if the host disappears. A bounded broker reconciler handles uncertain attempts; it does not invent a new plan. With no current authorized host, the job waits with explicit obligations and a succession policy.

**Demonstration.** The host discovers capabilities for the selected invoice/report, reads and carries the total, requests an exact mutation and verifies the saved file. Tool replies include what happened and the next permitted move. A human shell can supply an included client planner; another agent can drive the same protocol without adopting Footwork's agent loop.

**Adaptation.** Capability discovery is resource-scoped. Browser DOM and native AX expose compatible semantic operations where qualified, plus honest surface-specific operations/limits. Tool selection resolves the requested operation against the declared handle and generation. MCP could carry the protocol, but a tool description or read-only hint is not an authorization boundary. The broker is useful only while in-scope mutations actually traverse it; uncontrolled host tools remain outside its assurance claim.

**Intuitive surface.** Familiar verbs and structured replies work across environments. A task-scoped active capability set can reduce discovery burden if measured; it must not hide a needed route. The shell presents one job even though the external host remains the planner. Users should never have to know which MCP server or driver supplies a normal action.

**Recovery and risk.** Client turns, tool-call IDs and disconnects do not define task completion. The broker must retain pending effects and owed delivery independently of the host conversation. A reconnect cannot reset authority or spend. If providing useful continuation requires the broker to own scheduling and planning, H4 begins turning into H1/H3; that is an architectural tradeoff to measure, not hide. Exporting only action tools would fail L8 and delivery custody.

**References.** chrome-devtools-mcp's schema-defined tools, mode/capability availability, page scope and bounded connection behavior; Cua's typed contracts; Footwork's current operator interface and tool integration. Borrow explicit tools and structured results while retaining stronger task/effect enforcement.

**Prediction and counterevidence.** H4 should minimize host integration work and make caller parity testable. It loses as the product core if each host rebuilds substantial context, pause/resume and recovery logic, or if a supposedly unified tool grammar merely moves surface reasoning back to the model. Host portability and human intuitiveness are separate measurements.

**Smallest discriminating prototype, later.** One broker API with CLI and two independent client adapters, not five full planners. Run the same task and a host-disconnect/reconnect case. Compare duplicate effect handling, context reconstruction, tool discovery and preserved custody. Test that a refused operation cannot escape through an ungoverned fallback within the claimed boundary.

## H5 — Desired-state controllers: describe the result, reconcile the world

**Hypothesis.** An output-oriented resource contract lets Footwork choose and revise browser/native methods without forcing the user or planner to manage steps. Reconciliation is especially useful when effects are already satisfied or response acknowledgments are missing.

```text
desired report artifact + source/destination scope
                   ↓
resource controller: observe -> compare -> propose smallest change
                   ↓
guarded browser/native strategy -> fresh state -> reconcile
          [desired/observed records + commitment ledger]
```

**Ownership.** Resource controllers own convergence and satisfaction checks for a narrow family: e.g. a saved report copy containing a source-bound total. The planner/compiler proposes a versioned desired-state specification; the contract owner validates its intent and scope. Controllers choose supported route strategies and execute through an effect boundary. A coordinator handles dependencies between resource objects, with shared reservations and result custody.

**Demonstration.** The desired report specifies the source observation/revision, intended destination, preservation conditions and saved-copy requirement. The controller checks whether an appropriate output already exists, avoids duplicate appends, makes the minimum authorized change, and verifies actual bytes. If the user edits the document, it recomputes from current state within the original envelope or stops on a conflict; it does not overwrite the person's edit merely to restore a desired snapshot.

**Adaptation.** Qualified resource strategies can use a browser page or native app to reach the same permitted output. Browser UI state is partial and often ephemeral, so controllers must expose incomplete observation, unstable identity and unsupported predicates rather than treating them like database rows. API/file strategies could be added later, under explicit capability/authority qualification, not inferred from the phrase "computer use".

**Intuitive surface.** The task card shows the desired result, what is currently established, remaining differences and conflicts. A goal correction changes the desired contract, preserving prior operation history. The agent requests outcomes and reads concrete deviations; the controller handles mechanical recovery where convergence is demonstrable.

**Recovery and risk.** One-shot events such as send/pay/delete cannot be modeled as "keep making state true." They use a separately typed commitment with stable identity, authorized payload and reconciliation. If that event cannot be authoritatively observed, the controller remains unknown and stops dependent commitments. The controller must not turn ongoing desired state into unlimited standing authority; finite task/standing-job budgets and material change rules apply. Distinguish "output now has this value" from "our action produced this value."

**References.** controller-runtime's level-based reconciliation reads actual state rather than responding by replaying individual events. It is an architectural analogy; GUI state lacks Kubernetes' resource/version guarantees. [Controller-runtime reconciler](https://github.com/kubernetes-sigs/controller-runtime/blob/main/pkg/reconcile/reconcile.go). v5 E2 already identifies this pattern as a recovery precedent.

**Prediction and counterevidence.** H5 should reduce duplicated work and explicit replanning for output-oriented tasks. It loses if reliable source/resource identity and desired-state predicates require extensive app-specific engineering, if conflict recovery harms human work, or if most useful tasks reduce to ad hoc event sequences with no trustworthy convergence test. A falsely satisfied predicate is a guardrail failure.

**Smallest discriminating prototype, later.** One report-copy controller with readable artifact identity and one explicitly non-convergent submission case. Test preexisting correct output, unrelated look-alike output, missing save acknowledgment, human edit and unknown event outcome. Compare useful verified completion, adapter complexity and interventions with H1/H3.

## Common adaptive routing contract

The architectures may schedule differently, but none may solve adaptation by silently broadening scope. A route request states the resource, goal/operation, evidence required, posture and current generation. Resolution proceeds through qualified semantic observation (DOM/AX), targeted text enrichment such as local OCR when appropriate, explicitly scoped advisory visual checks, then a supported action route or structured escalation. This is a capability check sequence, not permission to call all modalities on every step.

When a route fails, return the diagnosed category and a useful alternative if one exists: unsupported route, ambiguous subject, human activity, changed precondition, missing evidence, withheld disclosure, provider failure, unknown effect or exhausted recovery. Semantic uncertainty can justify an identified new observation; it cannot justify searching providers until one is confident. Recovery is budgeted at the task level.

The current image adapter is an advisory option. Native System Two remains text-only, and browser capture geometry is not qualified by the native proof. No candidate may claim that a local file path supplies pixels to a remote model. Acquisition, disclosure, semantic evaluation, admission and dispatch each retain their own boundary.

## Evaluation that can distinguish architectures

Do not score these candidates numerically from intuition. First reject invariant violations; then compare useful outcomes and human/agent burden. The architectures should initially reuse the same pinned drivers, qualified model roles, fixtures, settings and task shell. Changing the driver, model, prompts and architecture simultaneously prevents causal attribution.

Proposed common scenarios, not executed by this task:

| Case | Required distinction |
|---|---|
| Browser read and quote | Source value/provenance versus a model's unsupported answer |
| Browser form fill without submit | Permitted preparation versus retained commitment |
| Browser navigation/download | Page change versus actual downloadable artifact |
| Native append and save-copy | Delivered key/value versus exact file readback |
| Native background operation beside a person | Task progress and preserved human focus/work |
| Duplicate native labels or browser tabs | Offered ID presence versus source identity/uniqueness |
| Browser-to-native carried value | Cross-surface provenance and destination preservation |
| Native artifact opened in browser | Resource identity across route changes |
| Human sign-in/retained decision | Resume remaining work without replaying settled effects |
| Crash/timeout immediately after an effect | Uncertain operation remains pending; reconcile before retry |
| Stale image/text result after a person edits | Invalidated generation cannot authorize or fulfill |
| Client/worker turnover with an owed result | Custody, remaining budget and delivery remain attributable |

Primary candidate metric: avoidable driver/user effort per independently verified checkpoint, reported alongside all-task verified completion and zero-progress cases. Human burden needs representative users, not a model pretending to be a user. Measure interventions, forced backend choices, repeated configuration, invalid target repair, recovery actions and comprehension of unknown outcomes. Agent burden includes tool discovery, schema corrections, context reconstruction and useless requests.

Guardrails: wrong/out-of-scope effects, false fulfillment, lost retained decisions/results, budget resets, broken posture promises and hidden uncertainty disqualify a candidate. End-to-end time/cost per verified outcome includes capture, attach, model calls, settling, readback, review and recovery, including failures/cold starts. UI declaration ablations and runtime enforcement tests are separate interventions, as v6 requires.

First comparison need not implement all five fully. Build the minimum distinguishing ownership/recovery slice, preserve exposed development counterexamples, then preregister the next bounded measurement. Numeric tolerances/sample sizes and deployment authority are later decisions. These proposals are not preregistered paid experiments and do not resolve their own hypotheses.

## Independent review brief and decision boundary

Request a fresh read-only **Claude Opus 5.5 (`claude-opus-5-5`), xhigh** architectural review after freezing this candidate packet. The exact model's structured-output probe succeeded; the retained provider receipt identifies that canonical model. No fallback model is permitted. The reviewer receives copied sources, not the active checkout, credentials, raw traces or home-directory access.

Ask the reviewer to challenge whether the five are truly distinct, test each against v6 plus retained v5 obligations, assess human and external-agent intuitiveness separately, identify missing ownership/adaptation mechanics, preserve current qualification limits and propose the smallest discriminating experiments. Ask for strongest-case and fatal-risk arguments for every option before conditional ranking. Reviewer preference is advisory, not architecture selection or evidence that a runtime works.

The human decision remains open. Possible composition should name one primary owner of progress; simply adding all five produces multiple authorities. Choose what Footwork should principally be: a coherent local session, a responsive surface service, a durable job runner, a portable tool system or an output controller. Compatible secondary patterns can be added only where their ownership and measured benefit are clear.

## Reference source inventory

Local code was read, not installed or benchmarked. Exact copied snippets and full digests will accompany the review packet:

- Legible Loop v6 and selected v5 obligations at the paths above; current Footwork overlay and visual docs.
- arc-cua `6b35303`: `src/arc_cua/protocols.py`, `models.py`, `runtime.py`, `policies/choice.py`; see Footwork's existing [transfer audit](../arc-cua-decisions-reference.md).
- pi `ce950d78f`: `packages/durable/src/session/session.ts`, `harness/scheduler.ts`, `harness/task-graph.ts`, and coding-agent session projection types.
- LangGraph `40a2e6d84`: `libs/langgraph/langgraph/graph/state.py` and `types.py:893` interrupt restart semantics.
- chrome-devtools-mcp `2744afa`: `src/ToolHandler.ts` and `src/tools/ToolDefinition.ts` typed capabilities, page scope and connection limits.
- Cua and browser-use source observations from the earlier proposal remain precedents, with pinned Footwork capability/contract tests authoritative for integration.
- controller-runtime reconcile source and LangGraph interrupt documentation linked above were read as primary-source patterns. Neither proves GUI safety or speed.
