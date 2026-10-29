# One implementation plan: dependable operations across different apps

**Implementation progress:** the [dispatch correction](../../../results/operator-dispatch-20261028/report.md) and [native admission/replay](../../../results/durable-admission-20261028/report.md) are committed. [Structured evidence and qualified reconciliation](../../../results/structured-evidence-20261028/report.md) add retained runtime receipts, exact bounded AX facts and coverage-aware observations. Reconciliation resolves only validated retained returns; missing or ambiguous receipts remain blocked. Installed Finder/Preview/Chrome qualification remains pending. See [durable native usage and limits](../../durable-native-operator.md).

**Qualification attempt:** [the diversified app run](../../../results/app-portfolio-20261028/report.md) added independent oracles, a durable ticket fixture and interrupted handoff tests, then exercised installed apps. The installed portfolio did not pass: Finder delivery remained unknown, Preview was blocked and Chrome scope evidence was incomplete. The release gate stays open; offline passes are not substituted for nominal UI success. [Harness usage](../../app-qualification.md) records the boundaries and next gaps.

Prepared October 28, 2026 against `5d494c6a22921d092e67399badce708e8418bf2a`. This is the proposed implementation sequence, synthesized after independent subagent review of all five original plans and Claude's critiques and three syntheses. It incorporates the user's subsequent requirement to diversify applications and where Footwork is exercised. It does not record implementation approval or completed qualification.

**Build a durable operator path, then qualify it on Finder file organization, Preview image transformation, and a stateful browser application.** Use independent outcome checks and a static report to show precisely what happened. TextEdit remains regression coverage; it is no longer the main workflow, release demonstration, or evidence of general application support.

The deliverable is one stronger capability system for an existing host agent. The host continues to plan. This work does not create a workflow scheduler, public verification SDK, interactive console, or separate research product.

## What survived the critiques

| Source | Keep in this plan | Defer or correct |
| --- | --- | --- |
| [1: Execution core](01-execution-core.md) | Intent before input, atomic authority reservation, immutable token replay, explicit recovery | Reuse journal primitives; qualify each route instead of promising immediate CLI/MCP/SDK parity |
| [2: Workflow product](02-workflow-product.md) | Complete installed jobs, independent outcome checks, separate operations for mutation and persistence | Replace the TextEdit-centered job with the three-app portfolio below; capability qualification is distinct from demand |
| [3: Verification SDK](03-verification-sdk.md) | A small typed evidence contract and narrowly scoped artifact predicates | Keep it internal until real producers and a named external integrator justify extraction |
| [4: Operator console](04-operator-console.md) | Legible outcomes, target identity and uncertainty | Generate an offline report; defer action UI, server and purported human-only approvals |
| [5: Evidence lab](05-evidence-lab.md) | Independent behavioral oracles, fault injection, complete attempt accounting and portable evidence | Build only the development harness needed for this release; recount is not regrading |
| Claude's [A](synthesis/A-durable-operator-core.md), [B](synthesis/B-auditable-workflow.md), [C](synthesis/C-evidence-contract.md) | Reservation/replay design, persistence as a separate operation, static reporting, unknown measurement handling, deliberately broken adapters | Correct recovery, resource identity, save semantics, crash tests, packaging and demand claims before using them |

The detailed [review index](review-20261028/README.md) maps all reviewed material to three independent reports. Their findings are source-based hypotheses unless expressly described otherwise. No runtime tests, live apps or model evaluations ran for this synthesis; Claude's reported probes are not independently reproduced evidence here.

## Corrections that change the implementation

1. **D1/D2 need reproduction, but are sufficiently concrete to investigate first.** Grant consumption precedes input, while the operation log follows input. A post-press exception can become `refused`, which completion treats as no-send. Diagnose these through the existing observable command behavior before adding assertions about a new journal API. A granted click exercises the authority defect; append alone does not. See the [runtime review](review-20261028/runtime-review.md).
2. **The existing journal is reusable, not already a universal executor.** It has transaction, replay and unresolved-operation machinery, but its restart packet validation has append-specific assumptions. Its lock owns a database, not an application across arbitrary session databases. Lifecycle validation and admission must be extended deliberately.
3. **An unchanged screen cannot authorize retry.** Remove the unqualified `-25204` retry. A second input requires qualified no-send evidence or a separately authorized new action; an invisible or delayed effect remains possible. Count underlying input calls independently from logical operations.
4. **A save check is narrower than task correctness.** Current `save_readback` compares decoded disk text with window text. That is useful evidence for that predicate. It lacks intended content and full destination binding, and completion's basename comparison is insufficient. Do not rename this evidence into a stronger claim. Generalize persistence through app-specific predicates; PNG rotation is not text or byte equality.
5. **Unknown can be resolved, but cannot be wished away.** A qualified retained execution receipt can resolve an attempt; matching current state alone does not prove who changed it. Preserve the original unknown and append the resolution. A user's assertion is recorded as an assertion, never manufactured verification.
6. **Source coverage must be recorded before truncation.** The browser producer slices text before downstream code checks its length. Carry original coverage, clipping and normalization metadata from the producer. This matters to browser observations beyond the old quotation task.
7. **Verification layers are different.** The atom matcher can miss polarity; the full verifier also performs semantic checks. Likewise schema validation, packet integrity, arithmetic recount, regrading and fresh execution answer different questions. Do not replace the semantic verifier or claim independent reproduction from a manifest check.
8. **Crash accounting and measurement need real producers.** `finally` cannot record SIGKILL. Persist admission/running state beforehand. Unknown spend must remain unavailable through producer, aggregation and display; known zero remains zero, and cost per success is undefined when there are no successes.

## The application portfolio and environments

These are concrete qualification candidates, **not claims that the current build supports them**. Existing source offers related seams, but some historical Finder work used direct filesystem substitution and Preview rotation has not been qualified. Each route must earn its own status.

| Workload | Application and location | Footwork's permitted work | Independent outcome oracle | Principal negative case |
| --- | --- | --- | --- | --- |
| F1: organize an asset | Finder, native macOS, owned scratch directory | Rename and move one seeded non-text asset within two allowed directories | Old-path absence, exact destination, unchanged file digest, untouched siblings | Same filename in another directory; changed selection or window; effect followed by lost reply |
| P1: transform an asset | Preview, native macOS, owned asymmetric PNG copy | Rotate the specified image 90 degrees and save that copy, with separate operation identities | Independently decoded pixels/dimensions match the prescribed transform; original remains unchanged; exact destination bound | Wrong window with similar image, wrong rotation, unsaved image, changed path, external edit |
| W1: submit and recover | Chrome's dedicated profile, local stateful ticket application | Fill and submit one synthetic record, then recover after a lost response | Durable server row has exact fields and request identity; independent ingress/input counters reveal duplicate attempts; data survives fixture-server restart | Click delivered without effect, response loss after commit, stale document, duplicate input, origin/context change |

The browser fixture must not hide duplicate input behind server-side deduplication. One final row is insufficient: retain the independent request ledger and input-call count. Finder checks must not mutate files to make the agent's run pass. Preview's oracle decodes the saved artifact independently; it cannot simply repeat the adapter's own success judgment. Use exact finite fixtures to make pixel equality well-defined; separately check permitted encoding, orientation and color handling rather than claiming universal image fidelity.

Run each workload independently before connecting them into one **prepare-and-register asset** scenario: Finder organizes a seeded image → Preview rotates and saves the selected copy → the browser records that artifact's declared name and orientation. Bind handoffs to the actual artifact identity and verified state. This connected scenario measures cross-app targeting and recovery, not demand for this synthetic workflow.

Diversification covers several axes without running a full Cartesian product:

- **Execution location:** deterministic simulated driver; actual installed native apps and dedicated browser; independent clean onboarding environment later.
- **Interaction context:** background-capable actions and explicit foreground actions; multiple windows; changed focus; app/browser restart; denied permission.
- **Effects:** filesystem identity changes, visual document transformation and persistence, and a stateful browser submission.
- **Use:** isolated operation, sequential jobs, cross-app handoff and interrupted recovery.

Do not count TextEdit or extra hosts running the same append as additional app coverage. Keep Calculator's existing fixtures as useful native baselines, not substitutes for these three workloads. No Windows, Linux, cloud desktop, personal browser-profile or remote-service support is implied. A later platform adapter needs its own identity, permission, delivery and cleanup qualification.

## Chosen architecture and guarantees

**One operator authority domain.** Extend [`capability/journal.py`](../../../python/jevdual/capability/journal.py) and put operator policy in a small proposed `SessionOperations` service. All participating CLI sessions use one explicitly configured canonical authority database and retain its identity with their session UUID. Do not create a new operations database per session. Reuse the existing schema/transaction/replay machinery with versioned admission records; keep append recovery compatible.

Acquire database ownership before loading mutable session state, matching a grant or admitting input. Hold it for the bounded command, then release after durable outcome and projection. Contention returns a typed busy result. Durable unresolved rows provide exclusion after the owner exits; a lock alone cannot. This conservative database serialization is a Footwork ownership rule, not a machine-wide job guard.

For this first release, **any unresolved admitted mutation blocks new mutations throughout the participating authority domain**. Observation, status and qualified recovery remain available. This deliberately coarse barrier covers the same artifact moving between Finder and Preview, where a process-only lock would miss an outstanding save or rename in the other app. Require settled execution custody and the relevant postcondition before every cross-app handoff. Finer concurrency needs durable multi-resource/artifact claims and alias qualification in a later change; do not imply it exists now. This rule affects participating Footwork operations, not unrelated machine jobs.

For native apps, use boot identity, PID and process-start identity as the initial conflict key, intentionally covering every window in that process. Keep stricter window/document/target incarnation separately for grant validity and evidence. Display names, titles, PID alone and window numbers alone are insufficient. If a required identity cannot be qualified, refuse the relevant new admission. Safe-save inode replacement is evaluated under the document binding rule; it is not automatically a different document.

The initial guarantee is explicitly **across supported native CLI sessions enrolled in the same authority domain**. It excludes older binaries, alternative authority roots, MCP's existing separate journals and detached workers, the autonomous agent loop, and unrelated tools. Do not advertise detection of those writers. Before W1, add a browser admission adapter to the same domain, with context/tab identity and document generation. Browser and native routes to the same Chrome process must conservatively share a conflict scope or one must be refused by the supported entry points.

MCP keeps its existing narrow authority and recovery contract. Cross-runtime coordination is a later adapter: both mutation entry points would need durable claims in the same domain, linked to operation and worker custody. A shared temporary lock is insufficient. No daemon or new public transport is needed for this plan.

**Operation lifecycle.** Every admission records its authorization basis. When the existing policy requires an exact grant, validate authority, match the grant, reserve one use and commit an immutable request in `prepared` in one transaction. Otherwise record that reservation is absent; this plan does not silently require a new grant for every ordinary input. Commit `started` before invoking any input. Persist a qualified outcome before projecting session JSON, text or a report. Recovery may classify `prepared` as no-send only for a versioned protocol that proves input cannot precede `started`; a nullable column is not proof. Recover started/unresolved work conservatively as unknown.

Grant conservation is explicit: available → held on admission; held remains unavailable while delivery is unknown; qualified no-send releases once; confirmed delivery spends once even when its effect is uncertain. Settlement of the grant does not finalize the operation: sent input with an unknown effect remains unknown/blocked with a spent reservation; ambiguous delivery remains unknown/blocked with a held reservation. Replay and reconciliation cannot charge or refund twice. Token replay retrieves the original immutable request before fresh observation/authorization and returns its current recorded status with zero new input. New arguments with an existing token conflict. Resolved secret values are never serialized into the request or evidence.

**Evidence contract.** Extend existing receipt/effect structures rather than creating a parallel general framework. A versioned record carries operation/attempt and session IDs; resource and target identity; observation generation and time interval; producer/check version; input phase; existing delivery and effect/disposition values; evidence references, completeness and limitations. Distinguish four predicates in completion and presentation: input delivery, observed effect, persisted artifact state, and task postcondition. A field can be unmeasured while another is established.

Readbacks are immutable observations. A derived claim names its predicate, parameters, input records and rule version. Preserve partial outcomes; do not globally map them to failure or success. Later observations do not overwrite historical ones. Legacy prose remains readable with explicit limits; missing identity, delivery or full text is not invented. One typed producer feeds completion, JSON CLI and report.

## Ordered implementation packages

Each package produces a reviewable PR with a named owner. Shared core files have one owner; app-oracle and fixture work can proceed independently after the envelope is fixed. Before substantive diagnosis/harness work, commit the notebook prediction required by `CONTRIBUTING.md`; a failed prediction changes the plan. Do not merge blanket expected-failure tests as the first deliverable.

### 1. Make dispatch uncertainty truthful

**Owner/files:** native runtime owner: `native.py`, `receipts.py`, the error/receipt path in `session.py`, `completion.py`; existing native and session scenario tests.

Reproduce D1/D2 through real command paths and the simulated driver's independent press ledger. Inject a failure after the press, inspect existing grants/logs/receipts and prior-readback usability, then test a subsequent command. Preserve the before-fix evidence. Repair false no-send classification and remove uncertain automatic retry in this PR; D1's durable custody repair belongs to package 2. Review outer bridge error handlers too, so they do not relabel ambiguous execution as `not dispatched`.

**Exit:** errors returned or caught through the repaired bridge/driver paths preserve post-input uncertainty; earlier readback cannot certify an unchanged surface after those ambiguous mutations; qualified pre-input refusals still send nothing; a logical operation makes no unqualified second input. This package does not close D1's cancellation/process-death gap. Update tests that intentionally pinned the old faulty behavior. If the alleged path cannot be reproduced, record that outcome and revise the mechanism before adding machinery.

### 2. Add durable admission and granted-click recovery

**Owner/files:** core owner: `capability/journal.py`, `grants.py`, proposed `session_operations.py`, session/CLI integration and lifecycle tests. Preserve `capability/recovery.py`'s existing packet validation.

Implement the common authority domain, versioned lifecycle validation, atomic reservation, request identity, projection repair and status/reconciliation. Start with one grant-gated native click in the simulated world, then route every native mutation exposed in the qualified mode through the admission seam. Unsupported routes refuse instead of silently falling back. All mutable session updates participate in ownership; atomic replacement alone is not concurrency control.

**Exit:** the fault matrix below passes, including different session directories using the same authority store, app aliases, process reincarnation and any owned native helper/driver execution that survives the caller. Preserve existing MCP recovery tests separately; this adds neither a generic detached-worker system nor MCP coordination. Same token produces no new input; unresolved work blocks new mutation in the participating domain. Do not add `resolve --applied` as an unverified escape hatch. Acknowledged abandonment may be recorded separately but cannot clear custody, refund authority or certify an effect.

### 3. Record evidence at its source

**Owner/files:** core/evidence owner: `receipts.py`, `completion.py`, `session.py`, `agent_cli.py`, `browser_driver.py`, `capability/observations.py`, `artifacts.py`; contract and completion tests.

Persist typed observation/operation evidence and manifest-bound artifacts. Preserve browser clipping metadata before slicing. Return typed JSON directly from the same result consumed by completion, rather than wrapping prose as if it were evidence. Add bounded artifact checking with explicit path policy and time-of-observation limits. Final-component `O_NOFOLLOW` is not a promise about all parent symlinks or future pathname replacement.

**Exit:** long values, clipped text, stale targets, absent fields and contradictory fresh state stay distinguishable. Historical receipts and current checks coexist. A qualified retained receipt can resolve unknown; matching external content alone cannot. Existing TextEdit readback remains a limited regression oracle, not the new generic persistence model.

### 4. Qualify Finder and Preview operation families

**Owner/files:** native adapters/oracle owner: app binding and supported action seams in `native.py`, new narrowly scoped oracle modules and new development fixtures/scenarios. Core state-machine edits stay with the core owner.

For F1, bind source object and allowed destinations before rename/move; record each intended effect separately. For P1, bind the input artifact, specific Preview window and expected transform before input. Rotation and Save have distinct tokens and outcomes. Require explicit save posture, fresh target identity and bounded post-save observation. The postcondition verifies the intended saved artifact, not merely disk/window agreement. An already-satisfied artifact can be recorded without input, but must not be attributed to an unperformed save.

**Exit:** F1/P1 positive and negative oracles pass with independent observations. No direct filesystem rename/image transformation is substituted for a failing Footwork action. If the adapter cannot reach or identify the operation, report a concrete missing seam and fix it or leave that workload unqualified; do not replace it with TextEdit to make the portfolio pass.

### 5. Qualify browser submission and cross-app handoffs

**Owner/files:** browser owner: `browser_driver.py`, shared admission integration, observation/delivery projection; local development fixture and its independent durable request ledger.

Add browser mutation admission to the same authority domain, with qualified context/tab identity, document generation and origin scope. Keep network send, page input delivery and server-committed effect separate. A visible confirmation is not itself a qualified submission event. W1 uses the fixture's retained server receipt to qualify a narrowly defined committed-record predicate; it does not create a universal web submission oracle.

**Exit:** loss after server commit does not cause blind resubmission; request count and exact row are independently checked; stale tabs/origins do not inherit authority; native/browser access to the same Chrome resource cannot bypass the supported conflict rule. Only then exercise the Finder → Preview → browser handoff. Remote origins and personal accounts remain outside this fixture qualification.

### 6. Make evidence reviewable and trial accounting complete

**Owner/files:** reporting/evaluation owner: proposed offline report renderer, existing CLI projection, `evals/runner.py`, `evals/report.py`, `evals/paired.py` where those paths produce the trial metrics, plus installed-trial/packet scripts.

Render a consistent snapshot as a static HTML report with target, attempt, evidence links and the four predicate states. Escape task text, constrain artifact paths and resource loading, bind artifacts to the manifest, and show missing legacy evidence as missing. A report-time recheck is a separate timestamped observation. Do not add a mutation server or approval controls.

Persist the frozen schedule and a `running` attempt before trial invocation. After restart, retain abandoned attempts as interrupted/unresolved; an allowed rerun gets a new identity. Separate contamination eligibility from execution outcome. Carry known zero, estimate and missing cost with basis/coverage through producers and readers; show an unavailable total when required components are missing, optionally a labeled known subtotal. For paired comparisons, compare each field only on matched tasks with known, comparable measurements on both sides; disclose eligible/excluded pairs and repeat coverage. Predeclare treatment of partially measured repeats and do not zero-impute missing components. Do not rewrite historical rows.

Use deliberately broken adapters to falsify the actual guarantees: input on stale identity; illegal retry even when its first input had no effect; invented success; wrong destination; clipped observation reported complete; dropped interrupted attempt; missing usage reported as zero. A defect may correctly fail several checks. Include valid variants and independent call/effect oracles, not merely schema checks.

**Exit:** every planned slot is accounted for; zero-success cost ratios are undefined; report fixtures distinguish delivery/effect/persistence/task success; tampered or missing evidence cannot certify a claim. Use new development packets only—no heldout scans or regrading to debug this work.

### 7. Qualify the installed portfolio and publish a support matrix

**Owner/files:** release/qualification owner: existing bundle/installed-trial scripts, new preregistered development protocol and results packet, support documentation.

Freeze the candidate build, dependencies, OS/app versions, tool catalog, schedule, expected outcomes, wall-time/provider caps and cleanup ownership before execution. First use an already-permitted host, then an independent onboarding environment; permission denial is tested on a disposable environment rather than resetting the user's established permissions. Simulated tests, local installed success and independent first use remain separate evidence levels.

The minimum schedule covers F1/P1/W1 normal completion; one chosen identity/focus failure per workload; the relevant persistence/lost-reply failure per workload; then one connected handoff with interruption. Add the core subprocess boundary cases separately. Fix the exact schedule in the protocol before running; this is coverage, not a statistical reliability percentage. Count setup failures, coaching, blocked outcomes, reruns and cleanup failures. Any false certification or extra unauthorized input blocks the affected qualification; honest unknown is not completion and cannot be relabeled append-only success.

Verify owned effects before cleanup. Retire only owned browser/fixture/host processes and exact disposable artifacts; never quit a shared app to simulate restart. Cleanup uses both normal finalization and a startup ownership audit because process death bypasses `finally`. Retain failed runs and receipts.

**Exit:** the diversified portfolio milestone requires installed nominal and assigned-challenge evidence for **all F1, P1 and W1, plus the interrupted cross-app chain**. Individual bugfix packages may ship earlier, but omitting or substituting an unqualified app cannot close this milestone. Ship a matrix keyed by app/version, route, operation family, context, oracle and evidence level. Each claimed supported cell has its own passing evidence; no generic “works across apps” badge. Before expanding to real services, obtain one volunteered recurring task and ordinary baseline method, then run it under a separate scoped protocol. Synthetic authentication or GUI-only tool restrictions do not establish demand.

## Fault matrix required before installed claims

| Boundary/case | Required outcome and independent check |
| --- | --- |
| Before intent commit | No input and no consumed/reserved use |
| Prepared, before started | Only the qualified protocol can establish no-send; reservation released once |
| Started, before/during input | Unknown if delivery cannot be proved; no automatic redispatch; scope blocked |
| Input sent, effect unknown | Operation remains unknown/blocked while its reservation is spent; settlement does not unblock it |
| Effect occurred, finish absent | Retained independent effect/call ledger survives; no invented no-send |
| Finish committed, projection/response absent | Replay reconstructs result with no new input or charge |
| Two sessions/processes or app aliases | Shared authority domain prevents conflicting admission and lost grant updates |
| Finder/Preview handoff with unresolved artifact operation | Domain-wide barrier prevents the other app from admitting a conflicting mutation; no handoff until custody and postcondition are settled |
| Process/window/document replacement | Fresh binding required; old grants/evidence do not transfer |
| Exact retained execution receipt | Append a qualified resolution; preserve prior uncertainty and separate current agreement |
| Matching current state or operator assertion | May establish a new scoped observation/assertion, not who caused the old event |
| Wrong destination or transform, unsaved artifact | Task postcondition fails or is unknown despite plausible UI/disk agreement |
| Browser commit followed by response loss | Server ledger reveals exact effect and every request; replay sends nothing |
| SIGKILL with no finally | Durable attempt remains accounted for; restart reconciles custody before admitting work |

Use synchronized child-process death with an independent durable fake-driver ledger for process-crash cases. Cooperative cancellation is a separate test. Neither establishes power-loss durability. Report actual observations and test scope rather than a universal exactly-once guarantee.

## Migration, rollout and the first handoff

Preserve old sessions, journals, screenshots and historical results. New sessions get fresh generations and manifests; `start` must not delete unresolved history. Version journal schema and admission protocol; participating version-aware writers reject unsupported versions. Historical binaries cannot be constrained by new metadata, so managed rollback retains a compatible status/recovery reader and never directs old executors at the new store. Back up a database before a qualified migration. Legacy grant files do not become live concurrent authority in the new mode: create fresh scoped grants and retain old files for history. Compatibility readers never upgrade legacy evidence into new guarantees.

Land package 1's classification correction independently. Enable durable admission first for development native sessions, add Finder/Preview qualification, then browser admission and W1. Expose only operations that passed their route-specific qualification. A rollback disables new admissions while preserving status/recovery; it never sends unresolved work through the old path or deletes the authority store. Keep existing MCP and old-result readers compatible, without claiming shared custody they do not provide.

The first implementation handoff is **package 1**, including a committed preregistration/prediction, old-path reproductions, the delivery/retry repair and relevant regression checks. In parallel, the qualification owner can prepare independent F1/P1/W1 fixture and oracle specifications after their own required notebook entry. The core schema has one owner; app diversity is a release requirement throughout, not a post-release wish list.

No runtime behavior was changed to produce this plan. The next work is implementation against these gates, not another round of choosing among five roadmaps.
