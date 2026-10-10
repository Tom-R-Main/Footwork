# Five complete Footwork architectures — revision 2

Design alternatives after the [independent Opus 5.5 review](opus-5-5-architecture-review-20261008.md). The original [five-candidate packet](five-architecture-hypotheses-20261008.md) remains unchanged, along with its frozen review inputs. This revision sharpens the alternatives and closes design omissions; it implements nothing and resolves no empirical hypothesis.

Opus correctly identified three axes: who advances the job, where enforcement is trusted, and how surfaces stay attached. Five complete configurations can differ on those axes without claiming five unique scheduling algorithms. H1/H4 share caller-driven progress but have materially different trust/deployment contracts. H2 now explicitly places reactive planning in a resident goal actor and bounded local planning in surface agents. H5 now has only qualified resource controllers and no hidden general-purpose planner.

The latest located full standard remains [Legible Loop v6](/Users/thomasmain/Desktop/the-legible-loop-v6-draft.md), September 26, 2026, plus its retained v5 obligations. Current implementation is Footwork `88325d1`, not the draft's historical conformance table. This is a design decision packet, not evidence of working continuity, stronger containment or new visual authority.

## The five configurations

| ID | Primary owner of job progress | Enforcement boundary | Surface lifecycle | Expected product |
|---|---|---|---|---|
| H1 Embedded session engine | Current trusted local caller/planner | In-process application service | Attach/observe for an operation; no required service | Attended local workspace |
| H2 Reactive actor agents | Resident goal actor with scoped surface-agent assignments | Process-separated actors; shared task reservations and machine arbitration | Persistent surface agents with explicit event/poll invalidation | Responsive background computer assistant |
| H3 Compiled workflow runtime | Versioned workflow interpreter | Governed activity execution boundary | Per-activity attachments; reused only with qualification | Jobs with stages, hand-backs and durable continuation |
| H4 Capability microkernel | External host plans; broker settles governed operations/custody | Authenticated protocol and scoped capability handles | Broker-owned driver sessions | Portable governed tools for heterogeneous agents |
| H5 Resource controllers | Desired-state resource controller runtime | Qualified resource mutation strategies | Bound resource observations acquired for reconciliation | Output-oriented automation for registered resource families |

These are mutually selectable complete configurations for the first product. They can borrow techniques, but cannot secretly change primary owner or trust boundary while being scored as the same candidate.

## Shared contract for comparison

All five use the same visible task shell and the same browser-to-native demonstration: read the total from a selected browser invoice, update a selected report, save a new copy in a selected folder, show the saved result, and never submit/pay. A typed contract separates desired effects from prohibitions. Regexes over task prose do not define prototype success. The actual saved-copy identity, destination, content and preservation of the original are independently checked.

Use identical **semantics, test cases and independent oracles**, not a mandatory identical store/engine implementation. Otherwise building one shared kernel first would predetermine the architecture. Each candidate must show how its state placement preserves the same requirements.

1. **Effect lifecycle:** stable operation ID/payload fingerprint; prepared and started persisted before dispatch; proven refusal distinguished from uncertain delivery. A transport exception after possible delivery stays unknown. Local persistence failure also has a named uncertain/corrupt/refused state.
2. **Atomic local commitment:** grant use, task-level budget reservation and prepared operation are coordinated transactionally or by a recoverable protocol. Unknown effects cannot refund a grant or reset reservations. Actor/stage/session/connection creation never resets task consumption.
3. **Machine arbitration:** cooperating Footwork tasks share foreground/keyboard ownership, and clipboard ownership if they use the clipboard. A person's activity remains independently respected. Fences constrain local dispatch owners; they do not make external GUI operations atomic. Do not hold a global lock across a model call.
4. **Identity:** selected resources carry real surface incarnations and observation generations. A browser URL is evidence, not stable tab identity. Navigation, duplicate tabs, window replacement, incomplete candidates and last-recheck race windows are explicit tests. If the pinned driver cannot establish identity, refuse the route or keep the capability unavailable.
5. **Source policy:** a copied value is either the value at its recorded observation, or required to remain current at commit. The demonstration initially uses the recorded-observation policy and displays its timestamp/source. A freshness requirement is an explicit different contract. Changes to the destination still invalidate dependent mutations.
6. **Resume:** refresh bound resources and relevant source/destination conditions; recheck authority, posture, budget and pending operations; preserve settled work. Attribute human changes only where evidence establishes their origin; otherwise mark them externally changed/unknown, never fabricate actor attribution.
7. **Delivery:** name the recipient and discharge criterion. A shell result owes delivery to its task's human principal and is discharged by a committed presentation receipt under the chosen contract; this proves presentation, not that the person read/accepted it. A CLI result uses an acknowledged task-result retrieval where required. SDK/protocol clients fetch a durable result ID and acknowledge receipt when that is the contract's condition. Queue/transport acceptance alone never becomes recipient acknowledgment.
8. **Succession:** every pending effect/result has a custodian independent of the producer's process. The architecture defines when a successor can assume scoped rights. With no authorized custodian available, the task visibly waits and preserves obligations; it does not claim completion.
9. **Admission:** required missing verification/judgment cannot certify fulfillment or admit a dependent effect. Routine method changes inside the envelope require no repeated approval. Scope changes, retained decisions and exhausted bounds remain explicit.
10. **Coverage:** independent host tools are outside the mediated-effect assurance claim unless separately contained. External changes must invalidate dependent state where detectable; absence of detection is an exposed assurance limit. Readable correct state can support a state claim without proving which actor caused it; action-provenance claims require their own evidence.
11. **Modalities:** current visual checks remain opt-in, advisory and native-only; native System Two is text-only. OCR enrichment and browser visual capture are proposed/qualification-gated here. Image-only invoice totals produce a concrete missing-evidence escalation until a qualified source-extraction role exists.
12. **Measurements:** first use contract/fault prototypes to falsify invariants. Only a separate preregistered paired study can assess avoidable effort and representative human usability. Model roles, drivers and settings remain fixed while architecture is compared; declarations are tested separately from enforcement.

These requirements incorporate Opus findings F1–F19 and F21–F25 as design obligations. They are not a declaration that all cited source risks have been reproduced. Some original review claims are broader than its excerpts establish: an upstream driver may already fence an operation; a helper's optional-verifier path does not prove every configured entry point bypasses verification; unavailable screen-lock evidence is a specific degraded-path question. Actual enforcement and residual races need route-level verification.

## H1 — Embedded session engine

**Complete architecture.** One trusted local app/planner drives a synchronous Python session API. It selects the next action using current task context and returns control after each operation. The engine owns authorization, attempt settlement and evidence; the caller owns progression. Canonical task state is a transactional local journal with projections. Drivers remain implementation details inside the application.

```text
trusted local planner -> session API -> guarded browser/native operation
                              ↕
                       local task journal
```

**Intuitive use.** Select the tab/document/folder, describe the job, see the last established change and next available move. The person can intervene in the same task. A local agent uses the direct API. Ordinary commands hide backend names and preserve task configuration.

**Continuity policy.** H1 promises attended work and reliable continuation on the next authorized invocation. When the caller disappears, it durably marks waiting-for-caller, with pending operation IDs and owed results. It does not promise unattended progress. The next caller first settles pending effects with scoped observation/readback, then continues. Reconciliation that navigates or opens a resource needs the relevant effect authority, not a fiction that every read is inert.

**Adaptation/planning owner.** The trusted caller chooses bounded goals; code resolves resource-scoped qualified routes. There is no resident scheduler or independent planner worker. Adding unattended progression changes this configuration and invalidates its simplicity claim.

**Hypothesis.** Attended one-off work gains parity and clear resume with the lowest coordination overhead. **Falsifier:** continuation still needs transcript reconstruction; task/grant accounting races; or ordinary jobs force a resident scheduler. Waiting while no caller is available is the stated mode, not itself failure.

**Prototype.** Two adapters, carried total and actual saved-copy readback; process kills around intent/dispatch; next-caller resume; two callers contending for one grant/foreground. Keep the library boundary and attended promise during measurement.

## H2 — Reactive actor agents

**Complete architecture.** A resident goal actor owns the job until fulfilled, suspended or stopped. It invokes a qualified System Two planner on goal creation and materially new progress/blockage events, then issues bounded subgoal contracts to process-separated surface agents. Each surface agent owns its local observation/action loop, using existing qualified mechanical policy or scoped System Two escalation. Returned results/outbox events advance the goal actor's state. No precompiled stage graph owns progression.

```text
goal actor + reactive planner
          ↙             ↘
browser agent        native agent
 local bounded loop   local bounded loop
          ↘             ↙
      durable results + goal settlement
```

**Intuitive use.** A responsive task card persists while the person works elsewhere. It shows named surfaces, current assignments, conflicts and meaningful hand-backs. It can continue independently within the existing envelope and bounded task budget.

**Continuity policy.** Actor incarnations, inbox deduplication, durable assignment state, outbox custody and shared task reservations survive replacement. Goal-actor succession rehydrates actual obligations and reconciles uncertain effects. Local agents cannot autonomously widen assignments or grant themselves fresh scope. Machine-level foreground arbitration can serialize agents even when their windows differ.

**Adaptation/planning owner.** Global replanning belongs to the goal actor; local mechanical recovery belongs to the assigned surface agent. Planner invocation is event-triggered and budgeted, with bounded polling only when explicitly qualified. A missing change subscription is a degraded capability. Its benefit must be compared with current pull/recheck behavior, not presumed from warm attachment.

**Hypothesis.** Reactive delegated ownership improves multi-surface response and useful unattended progress. **Falsifier:** unreliable change signals, agents planning conflicting changes, excessive coordination/model calls, stale warm attachments or no end-to-end gain including restart. If reduced to a caller loop with passive event wrappers, it has ceased to be this configuration.

**Prototype.** First probe pinned driver change signals. Then one goal actor and two bounded surface agents, coordinator/agent loss, duplicate events, external edit, budget conservation and competing foreground requests. No cloud bus or general swarm is required.

## H3 — Compiled workflow runtime

**Complete architecture.** An intent compiler proposes a validated, versioned stage graph. The workflow interpreter owns advancement, waiting, custody and termination. Each stage executes a governed activity with declared inputs, effects, evidence and bounded local planning. It cannot independently replan the whole job. Revision changes remaining stages through an explicit contract-preserving operation.

```text
validated job graph -> workflow interpreter -> governed UI activities
                         ↕                       ↙       ↘
                    checkpoints              browser    native
```

**Intuitive use.** A job card presents a few meaningful stages and named inputs/outputs. It supports one-off generated jobs and reusable jobs without requiring users to author YAML. Retained decisions pause a stage and resume the same job later.

**Continuity policy.** Workflow checkpoints preserve obligations and task consumption. Effectful activities carry operation identities; restarting a node never implies repeating a click/save/send. Stage completion depends on actual evidence. Result delivery is an owned stage/obligation, not an incidental final message.

**Adaptation/planning owner.** Global planning occurs at graph compilation/revision. Local activity planners adapt to layouts within the stage contract. The interpreter decides the next stage deterministically from verified results and declared conditions. Event watchers may notify it, but do not become peer job owners.

**Hypothesis.** Explicit jobs lower hand-back/reconfiguration burden for repeatable cross-app work. **Falsifier:** recurring graph correction, stage-induced false claims/refusals, duplicate effects on resume, or no burden gain over H1 with the same operation semantics. A permanently open global planner on each event changes it toward H2.

**Prototype.** One template and one generated graph, an incorrect stage assumption, a changed destination and interruption immediately after save. Test stage declaration as a separate ablation before claiming improved usability.

## H4 — Capability microkernel

**Complete architecture.** A separate broker process exposes authenticated, schema-defined capabilities to heterogeneous hosts. Hosts supply proposals and own planning. The broker owns canonical task authority, per-principal scope/delegation, operations, budgets, evidence, custody and driver attachment. Hosts never receive broker driver objects or raw broker credentials. The broker does no goal planning; its reconciler performs only authorized settlement of pending attempts and delivery obligations.

```text
untrusted host clients -> authenticated capability protocol
                                   ↓
                     broker-owned task/effect state
                                   ↓
                         isolated driver adapters
```

**Intuitive use.** Agents receive stable semantic verbs, resource-scoped discovery and a resumable task projection. A human shell includes a client planner; without that client, the broker is a toolkit rather than a standalone personal assistant. The protocol boundary is the product's defining trust/integration choice, not an optional wrapper around trusted callbacks.

**Continuity policy.** Disconnects do not clear broker state. Reconnect returns pending/unknown operation IDs, current resources, reservations and owed results. A new authorized host claims scoped continuation custody; it cannot recreate the task under a new conversation to reset consumption. With no host, planning pauses while permissible reconciliation/delivery remains broker-owned.

**Adaptation/planning owner.** The external host plans; the broker validates and resolves exact resource-bound operations across browser/native capabilities. Outside tools remain outside the mediated assurance claim unless separately contained. The broker detects changes only to its qualified observation extent and does not certify fabricated actor attribution.

**Hypothesis.** This process/trust contract makes Footwork reusable by external agents with consistent guarded behavior. **Falsifier:** each host rebuilds materially different recovery, reconnection requires transcripts, bypasses are hidden inside its assurance claim, or the broker must add global planning to be usable. That would change the configuration toward H2/H3.

**Prototype.** Two independent host adapters and a human client over one broker; disconnect after dispatch, retry identity across conversations, result acknowledgment and an unmediated host edit. Scope and authority attenuation are tested at the protocol boundary, not assumed from MCP annotations.

## H5 — Resource controller runtime

**Complete architecture.** The user submits a validated desired-resource contract. Registered controllers own reconciliation of resource types: an observed invoice value, a report revision and a saved-copy artifact. Work is scheduled from unsatisfied observed conditions and dependency references; there is no ordered job graph or general-purpose runtime planner. A goal settlement evaluator observes controller results and settles the task; it does not issue arbitrary GUI instructions.

```text
desired resource contracts -> controller work queues
                                    ↓
                     satisfied / unsatisfied / unknown
                                    ↓
                       qualified browser/native strategy
```

**Intuitive use.** Describe the output and preservation conditions; see established state, remaining differences and conflicts. The runtime avoids redundant edits when the desired result already exists and is authoritatively identified. Source-policy changes revise the contract rather than silently refresh copied values.

**Continuity policy.** Controllers re-read actual state after restart. Unknown never means absent and cannot justify mutation. One-shot commitments are separately typed, finite and operation-bound; they never become "keep sending until true." Resource predicates and standing-work authority have explicit versions and aggregate limits.

**Adaptation/planning owner.** Intent compilation produces the resource specification once. Registered strategies adapt within qualified resource/application families; narrow model checks may answer a declared semantic question but cannot invent a general plan. Unfamiliar resources or layouts outside a strategy return unsupported. This is a deliberate coverage tradeoff. Adding free-form planners to every controller would change the architecture toward H2.

**Hypothesis.** Output-oriented registered tasks need less explicit step management and recover well from missing acknowledgments. **Falsifier:** look-alikes/delayed writes yield false satisfaction or duplicate changes; conflict handling overwrites human work; or useful coverage requires hidden ad hoc planners and excessive predicate engineering.

**Prototype.** One report-copy family, preexisting correct versus look-alike output, delayed save, externally changed source/destination and an explicitly unresolved one-shot event. Compare coverage as well as burden so narrow scope cannot masquerade as universal ease of use.

## Human selection remains open

Opus's initial conditional shortlist is H1/H3 for a local app, H4 for a portable toolkit, with H2 dependent on trustworthy change signals and H5 strongest as a narrow artifact strategy. The [focused second review](opus-5-5-architecture-recheck-20261008.md) accepts these as distinct complete configurations, with remaining design obligations. No candidate is selected by rewriting this packet.

The first fork is attended versus autonomous continuation. The second is a first-party human app versus a broker for external agents. Repeated jobs and readable output families then determine whether H3/H5 earn their additional structure. A resident process can be acceptable without automatically choosing H2; owning long-lived connections and owning job progression are separate choices.

## Host clarifications after the focused review

These clarifications address recheck B1–B14 as design specifications. They have not received a third independent review, and do not establish feasibility, conformance or measured benefit. The frozen revision-2 text supplied to the recheck and both original reviewer reports remain preserved privately and in the linked reports.

**Lifecycle and claims (B3–B6, B9, B14).** Score one explicit lifecycle per candidate: H1 is invocation-driven and attended; H2 is resident/reactive; H3 is a resident workflow service; H4 is a resident broker with host-driven planning; H5 is a resident controller service for registered families. Proposed resident services are future implementations, not running/installable capabilities established here. They stop/hold on logout, unavailable drivers, invalid authority or exhausted limits; reconnect/restart refreshes scope, posture and actual state. Unattended operations default to qualified background-only routes. Foreground work queues or requests the retained decision required by the task policy; residency alone grants nothing.

One fixed contract-compilation role produces the typed input for all five. H3 derives its stage graph and H5 its resource specification from that input. For the demo, **this task must create a new output copy** at the scoped destination, with source-bound content and the original file byte-unchanged. Those are creation-provenance and preservation claims, not merely existence. Preexisting correct output cannot discharge this task's new-creation obligation. A separately tested existence-only contract may legitimately avoid redundant work; do not credit that benefit under the new-copy contract. Meaningful ambiguity or uncovered scope requires a question; routine compilation or stage revision inside the envelope does not become an approval ritual.

H1's authoritative task journal holds a progression claim/epoch in addition to action reservations. A successor takes over only under its recorded stale-owner/succession rule. On task open, unsettled started records reveal possible caller loss; a crashing process cannot promise to write a final waiting marker. Cross-process task/machine lock records have explicit ownership and expiry; those local fences do not prevent human or external GUI races. Settlement rights are scoped to an existing pending operation and authorized resource observations, independently of its spent effect grant. The next caller surfaces stranded duties; no unattended liveness is claimed. Its in-process API primarily trusts the first-party planner and protects mediated use, not an arbitrary same-user process that can invoke other tools.

**H2 assignment and H3 revision rules (B7–B8, B14).** A goal actor makes a fresh global next-assignment decision after each terminal subgoal result or relevant invalidation; it does not advance a cached multi-stage job graph. Code can recognize a settled terminal state without a new model call. Otherwise qualified planner calls are explicitly charged to the task budget. A subgoal includes assignment ID, goal-actor epoch, bound resource incarnation, allowed effects, shared budget slice, termination/evidence conditions and escalation owner. Old epochs stop at the next local dispatch boundary. Local agents cannot convert their assignment into a new global goal. H3 instead advances its current versioned graph deterministically; a stage blockage may produce a compiler revision proposal validated against the unchanged typed contract. Valid in-envelope revisions apply automatically; scope changes return to the contract owner. Displayed stage projections are informational, not required user approvals.

**H4 identity and unattended settlement (B10).** Proposed authentication is explicit local host pairing with task-scoped capability credentials and recorded principal/delegation identity. A credential holder acts as that principal; protection against malicious same-user credential theft or broker-state tampering is unqualified and requires separate platform isolation. Process separation is not that proof. Aggregate limits per principal and a resource-scoped pending-operation index constrain new tasks; no broker can infer that every newly worded task repeats an old intent. Without a host, only already authorized background observation/settlement can proceed; navigation/opening/disclosure remains governed work. The broker does not autonomously retry effects or create a plan.

**H5 controller boundaries (B9).** Desired state belongs to the output artifact; the original has a preservation predicate. In-app edits and save-as form an operation-bound strategy, not an ongoing controller watching and rewriting the original. After a one-off task settles, controller ownership is released. Continuing reconciliation requires explicit standing-work authority and aggregate bounds. Any narrow model call classifies/extracts among a strategy's enumerated candidates or predicates; it cannot emit action sequences. Unknown state permits bounded authorized reobservation, then a concrete unsupported/blockage result or an intent question when the person can resolve it. It never becomes absence or unlimited retry authority.

**All routes and cross-task uncertainty (B2, B11).** Each configuration maps setup/attach, normal actions, Enter/key/menu, scripts, compatibility helpers, local-agent loops, activity retries, controller strategies and reconciliation operations to its actual preventive effect boundary. Planners receive capability handles, not driver objects. An enforcement-mutation scenario removes the required check at each route and must expose the violation. This is a future verification obligation, not a claim that every existing helper bypasses gates. Unresolved operations are indexed by bound resource incarnation and destination across tasks. A new task surfaces that uncertainty and cannot silently redo a dependent commitment; any separately authorized risk/retirement decision preserves the original unknown record and does not invent a known outcome.

**Stable attachment preflight (B12).** First determine whether pinned drivers can preserve target identity across reconnection. If an on-demand configuration cannot qualify continuity, its refusal is an explicit coverage/lifecycle cost; do not hide it by silently giving only that candidate a persistent helper. A separate ownership-only comparison may hold the attachment helper constant, but must record that different experimental question. Historical warm/cold speed claims do not settle either choice.

### Identical floor scenario matrix (B1, B3, B13)

Every candidate runs every row with the same typed contract and independent oracle. Candidate-specific probes come afterwards. A broken implementation of common semantics is scored separately from evidence against an architecture's distinctive benefit; neither is excused as usable conformance.

| Scenario applied to H1–H5 | Shared expected outcome |
|---|---|
| Kill before/after prepared/started/driver result/save receipt | Retain operation identity; reconcile uncertain effects before dependent mutation |
| Post-dispatch timeout, torn/unknown local write | Preserve unknown/corrupt state and reservations; never report proved refusal without evidence |
| Missing required verifier/judge on each mutating route | No certified fulfillment/dependent effect; report concrete unavailable check |
| Two callers/workers contend for one grant/task/foreground | One current local owner; conserved use/reservation; person remains in control |
| Destination edit or source change after copy | Refuse conflicting dependent mutation; apply the declared source-time policy |
| Selected tab navigates, is duplicated or replaced | Preserve qualified identity or explicitly refuse; do not follow a look-alike |
| Sign-in/retained-decision hand-back | Refresh resources and authority, mark changes during hand-back, resume without repeating settled effects |
| Unmediated host edit | Invalidate where detectable; disclose observation/assurance limits; do not invent actor provenance |
| Invoice total exists only in unqualified pixels | Missing-evidence escalation; no fabricated source value or autonomous visual approval |
| Preexisting/look-alike output; delayed saved file | New-creation contract not discharged by existence; unknown does not become absence or duplicate creation |
| Caller turnover/result delivery and new-task retry | Preserve recipient/custody/budget and resource-scoped unknown operations |
| Unfamiliar invoice layout, mid-task layout change, second report app | Preserve scope and invariants; report unsupported separately and include coverage in the denominator |

Automatic actions include fresh observation, supported in-envelope route repair, bounded authorized readback, display of state and validated graph revision. External changes are labeled by observed interval, such as changed-during-hand-back, rather than presumed actor. Interrupt the person only for ambiguous intent/resources, uncovered effects/disclosure/posture, retained decisions or a conflict/unknown condition they can legitimately resolve. Purely unavailable technical routes return a concrete limit rather than repeated approval questions. Count prompts/escalations as prototype cost signals; representative-user usability still requires its own study.

Distinctive probes remain: H1 next-invocation continuity without a resident scheduler; H2 reliable change signals and background progress beside active human work; H3 reusable/ad hoc graph burden and declaration ablation; H4 different host clients, identity and reconnect; H5 coverage/predicate engineering for registered output families. All use the same floor matrix first.
