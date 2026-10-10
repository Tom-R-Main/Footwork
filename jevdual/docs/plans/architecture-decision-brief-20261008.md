# Choosing Footwork's primary architecture

**Product direction selected October 9, 2026: H4, an MIT-licensed capability system other agents can configure and call with minimal effort.** The host keeps planning; Footwork abstracts supported browser/native mechanics and returns evidence-backed results. Read the [selected product brief](agent-superpowers-product-20261009.md), [the corrected five architectures](five-architecture-hypotheses-v2-20261008.md) and [the independent Opus 5.5 review](opus-5-5-architecture-review-20261008.md). Implementation details and qualification remain open; the alternatives are not measured product capabilities.

The latest located Legible Loop is [v6](/Users/thomasmain/Desktop/the-legible-loop-v6-draft.md), dated September 26, 2026. Its objective is dependable accomplishment with less avoidable driver burden, subject to authority, evidence, retained decisions, explicit uncertainty and human control. Historical implementation statuses need the current Footwork evidence overlay.

| Option | The product promises | Main design question | Main cost |
|---|---|---|---|
| H1: Session kernel | One coherent workspace with the same execution rules for people and agents | Can a direct session API handle the required continuity without becoming a service/scheduler? | Caller-driven continuation needs an explicit owner |
| H2: Surface actors | Responsive, coordinated work across persistent tabs/windows | Do persistent observers and independent surface workers improve verified outcomes enough to justify coordination? | Ownership, event loss, machine-level arbitration and service lifecycle |
| H3: Workflow graph | Jobs with understandable stages, retained decisions and resume | Are repeatable outcome stages the natural unit of use, including unfamiliar work? | Graph authoring/revision and effect replay semantics |
| H4: Capability broker | A portable browser/computer tool contract for any host agent | Can the host plan without rebuilding progress, recovery and task custody? | Integration boundary limits and external host responsibilities |
| H5: Desired-state controllers | State the output; bounded controllers reconcile current state toward it | Can the relevant resources and output predicates be observed reliably? | App-specific resource semantics, conflicts and one-shot commitments |

All five can present the same task shell: choose scoped resources, describe the outcome, see evidence-backed progress, inspect uncertainty, correct a target, pause and continue. Interface intuitiveness and architecture must be evaluated separately.

A composition should still have one primary owner of progress. An actor can be a driver strategy; a workflow can be a caller; a broker can be a protocol adapter; a reconciler can verify a resource. Adding all patterns as peer controllers creates multiple authorities.

Before selecting implementation, settle product priorities: a human's local workspace, an external agent toolkit, repeated jobs, or simultaneous background work. Then choose the smallest prototype that can distinguish the leading alternatives, with the same drivers, settings, model roles and visible shell.

The proposed common task is browser invoice total -> native report edit -> scoped saved copy -> actual file readback. Its failures include changed destination, retained decision, uncertain save, client turnover and stale visual evidence. Existing qualified behavior and secret/posture boundaries stay fixed.

## What Opus challenged

The first review found that the initial list mixed ownership, trust/distribution boundaries and surface attachment. It did not accept those as five independent progress models. It raised 25 source/design findings, with important source-coverage limits. The review remains unchanged and available in full.

[Revision 2](five-architecture-hypotheses-v2-20261008.md) turns them into five complete configurations and acknowledges common foundations. H2 now specifies a resident goal actor and bounded local planners; H5 has registered controllers with no hidden general planner. H1's attended continuation policy and H4's authenticated broker custody/trust boundary are explicit. The [focused fresh Opus recheck](opus-5-5-architecture-recheck-20261008.md) accepts the five as distinct complete configurations, with four progress models and H4's separate trust/custody variant. It leaves 14 design obligations. The host clarifications in revision 2 address their specification; those clarifications have not received a third independent review and are not implemented guarantees.

The shared design now defines unknown outcomes, task-level reservations, machine arbitration, source-time policy, delivery recipients, resume checks, insufficient-evidence behavior and mediated-effect assurance limits. It also names H3/H5 residency, H1 takeover, H2 assignment epochs, H4 credential limits, H5 ownership release and one identical scenario matrix for every candidate. Those are future implementation obligations, not new runtime guarantees.

## Conditional shortlist after both reviews

- **An attended first-party local app:** H1 is the baseline; H3 earns its structure if repeated jobs and hand-backs dominate.
- **A toolkit for external agents:** H4, with durable broker task projections and scoped assurance.
- **Unattended progression:** compare resident H3 with H2. H2 needs reliable driver change signals and proof that delegated agents earn their coordination cost; residency alone does not qualify background actuation.
- **Predictable saved artifacts:** H5 is promising for registered families; the broader product may instead use its reconciliation pattern inside another owner.

Host observation: H2 also needs to contend with Footwork's [Q9e delegation evidence](../../results/q9e-delegate-fixed.md), where the repaired bounded-delegation arm did not earn adoption. That is counterevidence to assuming delegation pays, not a measurement of the proposed actor architecture.

## The decision to make

The user selected external agents requesting easy, governed tools as the primary use. Refine H4's contracts, setup and recovery around real host integrations. Keep common evidence/authority semantics, pinned drivers and model roles. No full implementation of all five is needed. H1 can organize the internal library; H5 can supply resource verification; neither becomes a competing owner of the host's job.

A readable output predicate is not causal attribution. A displayed result is not proof that a person read it. A source review is not a reproduced bug, a benchmark or a conformance certificate. Those limits apply to both the original proposal and Opus's review.


## Review provenance

The source-grounded review and focused recheck were fresh Claude CLI sessions, both with provider-recorded canonical model `claude-opus-5-5` and requested `xhigh` effort. The first could read only copied packet sources; the second had tools disabled. Input hashes were unchanged and both completed successfully. The focused review judged design text, not new source or runtime evidence. The October 9 user clarification subsequently selects the H4 product direction; the specific new brief is not being presented as independently rereviewed or implemented.
