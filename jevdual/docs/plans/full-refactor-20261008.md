# Full Footwork refactor: a shared verified execution core

Design-only source review, October 8, 2026. Source baseline: `bd98fdb`; during review `9613204` added the advisory visual implementation prediction. This proposal accommodates that work without taking ownership of it. No runtime changes, new experiments, paid calls, dependency changes or live-app tests were performed for this review. Reference findings below are observations of local source, not reproduced performance or qualification.

**Recommendation: organize Footwork around a small Python execution core, with a transactional session journal, typed evidence and explicit adapters. Preserve the existing guard, upstream drivers, qualification boundaries and evaluation discipline. Migrate one caller at a time.**

The most valuable change is making authorization, dispatch accounting, reconciliation and completion obey the same contract regardless of who drives. A person, Jev, a System Two model and a cross-surface workflow should propose commands to the same runtime. Their planning loops can remain different. A full refactor should improve the reliability of that contract and the ease of adding a qualified capability; file relocation alone would not achieve it.

## 1. What the current app actually contains

Footwork has three related systems:

1. The browser-use integration: `DualProcessAgent`, speculative Jev policy, arbiter, destructive gate, completion verifier, ledger and receipts.
2. Native/operator execution: Cua native and browser bridges, persistent operator sessions, native autonomous loop, shared-machine posture, carried values, grants and cross-surface orchestration.
3. The browser inspection lab: dependency-free JavaScript capture, transport, coverage, comparison and findings utilities.

These share an evidence philosophy but do not yet share one execution implementation. The lab is an instrument and should retain its separate transport and privacy contract. Its observations can become evidence inputs; its network events do not automatically become verified outcomes.

Concrete source findings:

| Observed seam | Why it matters | Refactor destination |
|---|---|---|
| `session.py` combines command handlers, file persistence, bridge creation, secret scrubbing, gate wiring, dispatch, receipts, carries, grants, completion and HTML inspection rendering | Changes to one capability touch several unrelated responsibilities | Thin command handlers over application services; independent store, projections and inspection renderer |
| `SessionState.save()` writes a whole JSON file; grants use a separate JSON read/modify/write; `cmd_do()` dispatches before persisting `pending` | There is a source-level crash window after an external effect but before durable intent/result recording; state and grant accounting have no shared transaction in these functions | Transactional intent journal and action reconciliation; transactional grant reservation |
| `completion.effects()` extracts field/navigation facts from prose using `_HOLDS` and `_NAVIGATED` regular expressions | Presentation wording participates in completion evidence semantics | Structured evidence producers; prose generated from records |
| `CrossLoop.footwork()` spawns `uv run footwork`, receives combined stdout/stderr, and the loop reads session files and private completion helpers | Orchestration depends on process startup, human output and storage layout | Typed session API; structured CLI bridge during transition |
| Browser gates/receipts/completion live in `agent.py`; native dispatch/gating in `desktop.py`; operator dispatch/gating in `session.py` | Parity relies on multiple implementations staying aligned | One application execution protocol, with provider-specific observation/dispatch details |
| `DualProcessAgent` overrides private upstream lifecycle methods, with explicit contract tests; `patch.py` mutates upstream implementation objects | This is a deliberate compatibility seam, not accidental code to delete | One isolated browser-use compatibility package, pinned and tested |
| `native.py` combines observation projection, capture metadata, dispatch, app/window discovery, navigation and save readback | Surface mechanics and app-specific outcome verification have different change rates | Cua adapter plus observation projection, capture and resource verifier modules |
| `policy.py` imports TypeSafe answer/question types; `decisions.py` provides a separate text-only shadow transport | A common semantic interface is possible, but active roles are not interchangeable by evidence | Narrow role contracts and adapters; preserve Jev defaults and provider-native provenance |

These are source observations. The persistence gap and coupling are architectural findings, not newly reproduced incidents. The existing scenario suite is valuable evidence of intended behavior; its reported past pass count is not a current run by this review.

## 2. Alternatives and tradeoffs

| Structural option | Benefits | Costs and risks | Decision |
|---|---|---|---|
| Split large files, keep existing ownership | Low migration risk and easy diffs | Does not resolve separate dispatch paths, prose-derived evidence or crash accounting | Useful first extraction, insufficient endpoint |
| Python modular monolith with ports and one execution protocol | Matches existing callers/tests; transactions and authority are explicit; incremental migration | Requires disciplined dependency rules and adapters; less automatic infrastructure | Recommended |
| Move the whole runtime to an agent/workflow framework | Potential scheduling, tracing and checkpoint facilities | Framework owns another lifecycle; GUI effects still need reconciliation; migration changes too many semantics | Reconsider only for demonstrated deployment/scheduling needs |
| Rust-first rewrite | Strong types and potential native distribution | Model/driver/capture time may dominate; FFI and Python upstream integration increase scope; no current evidence for benefit | Keep existing measured Rust kernels |
| Separate services for planner, guard, browser, vision and evidence | Isolation and independent scaling | Distributed consistency, credentials and recovery become harder; unnecessary for a local-first runtime | Defer |

Python remains the control plane. The Rust extension remains optional behind its pure-Python twins. Keep `jevdual` as the import/package identity during migration and `footwork` as the CLI; a simultaneous package rename would add compatibility work without fixing a behavior.

## 3. Intended caller contract

The following is a design sketch, not an implemented API:

```python
session = runtime.open_session(task_contract, surface_binding, execution_policy)
observation = await session.observe()
proposal = planner.propose(observation, session.context())
result = await session.perform(proposal, expected_generation=observation.generation)
completion = await session.verify_completion(answer)
```

For an operator, the CLI supplies the proposal. For dual mode, Jev supplies a bounded operation/target and System Two supplies meaning/text where needed. A workflow coordinates named sessions and carried evidence through the same API. A browser-use adapter translates its action models and lifecycle into this protocol without trying to make browser-use abandon its own observer/history.

`perform` returns a typed refusal, authorization requirement, or action attempt/result with evidence references. It does not return an undifferentiated success boolean. Starting, navigating, typing, Enter, hotkeys, menu operations, browser evaluation and filesystem operations need explicit capability handling. Lifecycle/setup operations must declare their scope instead of becoming a hidden mutation route outside the runtime.

Keep the shared protocol small:

- `observe`: a bound, capability-qualified observation and its coverage limits.
- `propose/perform`: closed action arguments, preconditions, authorization, one dispatch attempt and reconciliation.
- `inspect/check`: explicitly read-only evidence and semantic questions.
- `verify_completion`: deterministic evidence floors plus the qualified semantic verifier.
- `reconcile`: determine what can be established after interruption or uncertain delivery.

Planning, retries of semantic calls, presentation and evaluation grading are separate owners. The runtime must not become a universal planner.

## 4. Types that carry the real invariants

Use immutable domain records and discriminated result variants. Runtime schemas are versioned at persistence and transport boundaries. Domain types must not import browser-use, cua-driver, a model SDK, CLI parsing or eval modules.

| Record | Required meaning |
|---|---|
| `TaskContract` | Goal, typed requirements where available, allowed operations/resources, execution posture and workflow budgets; a legacy adapter preserves existing natural-language contract behavior |
| `SurfaceBinding` | Logical surface ID plus native PID/window incarnation or browser target/tab/document identity; never just a title/URL |
| `Observation` | Generation, binding, capture interval, candidates, declared capabilities, truncation/coverage, source evidence references |
| `TargetRef` | Observation-bound candidate and provider token; visual bounds/geometry only when qualified |
| `ActionProposal` | Operation, exact target/resource and arguments, input provenance, expected generation/preconditions; typed variants for targeted and targetless actions |
| `Authorization` | Exact scope, authorizing source, conditions, issue/expiry semantics and reservation/consumption identity; distinct from model judgment |
| `ActionAttempt` | Stable attempt ID, durable intent, dispatch status, driver route/delivery and uncertainty; terminal refusal can establish that nothing was sent |
| `EvidenceRecord` | Kind, producer, resource/revision, observation/attempt relation, structured observed fact, validity/coverage limits and artifact references |
| `JudgmentRequest/Result` | Role, prompt/settings/model identity, exact evidence digest/generation, native answers, consumed dependencies, refusal/error status, timing and usage uncertainty |
| `CompletionVerdict` | Required evidence checks, semantic judgment and final disposition, with named unmet/unknown requirements |

The following remain separate: dispatched input; delivered input; visible state change; persisted resource change; correctness of the intended outcome. One receipt can report several axes. A `confirmed` driver effect is preserved as the driver's claim, not promoted to task correctness.

Likewise, frozen image binding, temporal validity and permission to execute are separate. Identical image bytes identify content; they do not establish that the live window still has the relevant state. An observation can be incomplete even when its offered target is known. Unsupported geometry, missing pixel capability and withheld evidence are explicit variants.

An initial evidence vocabulary can be small: `FieldReadback`, `NavigationObserved`, `SavedArtifactReadback`, `CarriedValueRead`, `VisualCapture`, `NetworkEventObserved`, `CoverageGap`, and `SemanticAssessment`. A network response alone does not create a `SavedArtifactReadback`. Current-state records invalidate on relevant subsequent edits/navigation; event records and answer provenance retain their distinct semantics.

## 5. Durable execution and honest recovery

Use a local SQLite store, with transactions for journal events, session projections, grant reservations and usage reservations. Store private image/body artifacts outside the database and refer to them by bounded IDs/digests. Use atomic publication and explicit artifact states so a crash leaves an unavailable/incomplete artifact rather than a trusted dangling reference. Durability settings, locking and crash behavior must be tested on the supported filesystem; a database choice alone proves none of them.

The journal is logically append-only. Session state is a versioned projection. JSON/JSONL become export and compatibility formats, not separate authorities for each module. Do not retain all raw observations forever: retention, artifact deletion and redacted projections need explicit ownership. A digest can remain after an artifact is deleted, with the artifact marked unavailable; a digest is not an authenticated source or a substitute for readable evidence.

Action lifecycle:

```text
proposal
  -> refused / awaiting_authorization
  -> prepared (intent + grant reservation committed)
  -> dispatch_started (committed before calling the driver)
  -> driver_result / delivery_unknown
  -> reobserve + reconcile
  -> receipt + effect evidence
```

Persisting `dispatch_started` before the driver creates a conservative uncertainty window: after a crash the action may or may not have happened. This is preferable to losing its identity. Resume must reconcile the bound resource before deciding whether another attempt is safe. Do not replay a save/send/delete merely because its receipt is missing. A negative UI observation may also be insufficient to establish that an external submission did not happen.

Reserve a one-use grant transactionally with the prepared attempt. A refusal that proves no dispatch can release the reservation under a documented rule. An uncertain attempt keeps it reserved/spent until reconciliation or explicit renewed authority. Do not reset budgets, authorization use counts or duplicate-effect protection on restart.

Only one active mutation owner per session/surface is allowed. Host-local locks and attempt fencing prevent cooperating Footwork processes from dispatching concurrently; the driver still performs live precondition checks. They cannot stop a person or another app from changing the window. Expired ownership cannot authorize a second dispatcher while an earlier attempt remains uncertain. Store transactions should be brief; do not hold a database transaction over a provider request or driver call.

Record provider requests before dispatch as well, including conservative unknown-usage reservations. A timeout/cancel does not establish that a paid request was unbilled. Late results remain historical unless their exact generation and request validity still hold. Semantic-call retry policy remains role-specific and explicit; transport retries never imply retry permission for UI mutations.

A warm, single-owner driver service can later reduce process/attach overhead. Begin with a library core and short-lived CLI invocations. Add local RPC/daemon support only after lifecycle, ownership, restart and live preconditions are demonstrated. Do not require a daemon to make the first refactor useful.

## 6. Boundaries and repository shape

Proposed structure within the existing package:

```text
jevdual/python/jevdual/
  domain/             contracts, observations, actions, evidence, outcomes
  runtime/            session service, execution, completion, reconciliation
  storage/            SQLite journal, projections, migrations, artifact store
  safety/             authorization/grants, posture, disclosure, secret boundary
  observation/        menu projection, evidence recipes, geometry/capture rules
  judgment/           role contracts, dependencies, qualification/settings
  adapters/
    typesafe/         existing qualified Jev roles and native receipts
    decisions/        shadow/advisory transport; no implied activation
    cua/              native and browser bridges, typed capability mapping
    browser_use/      pinned lifecycle compatibility and optional patches
  planners/           Jev mechanical policy, native S2, browser S2 integration
  workflows/          named surfaces, carries, resource-specific readbacks
  interfaces/         CLI commands, text/JSON rendering, private review previews
  _pure/              existing reference algorithms
jevdual/crates/        existing measured Rust kernels
jevdual/evals/         independent fixtures, experiments, oracles, comparisons
tools/                independent JavaScript inspection instrument
```

This is an ownership map; do not create a module for every noun or empty packages for future capabilities. Begin with a few cohesive files and grow only where actual callers justify it. Preserve old imports with wrappers during migration.

Allowed dependency direction is interfaces/planners/workflows -> runtime services -> domain/ports; adapters implement ports; storage implements store ports. Evaluation imports runtime interfaces and supplies external oracles. Runtime must not import evaluation labels or graders. Resource-specific readback belongs to production workflow verification; independent evaluation oracles remain separate and check the actual output.

Extract app navigation/discovery and save verification from `native.py` carefully. Preserve its driver refusal, delivery, target-token and coexistence semantics. Avoid flattening browser DOM IDs and native AX IDs into a supposedly stable universal integer. The common layer owns opaque references and operation semantics; the adapter owns provider bindings.

Keep patches and private browser-use hooks contained. Remove a patch only when its measured benefit or compatibility cost justifies removal. Import-time global patches merit an explicit integration bootstrap and a recorded active-patch manifest, but migration must preserve the measured configuration. Upstream remains pinned; a refactor is not an upstream upgrade.

## 7. Provider roles and visual work

The narrow model seam is worthwhile. Universal interchangeability is not established. D1 reports five final unsupported completion acceptances for Decisions and none for Jev on that exposed corpus. D3 provides better authored visual coverage but a wrong Rotate effect approved as Crop. D4 target marking/regions help exposed variants, while causal repair attribution remains inconclusive. Preserve those distinctions and current routing. Sources: [D1](../../results/d1-v2-dev-20261008/report.md), [D3](../../results/d3-dev-20261008/report.md), [D4](../../results/d4-dev-20261008/report.md).

Define roles such as `text_completion`, `consequence_assessment`, `bounded_action_choice`, `document_reference_match` and `crop_subject_containment`. Provider capability describes what it can return. Qualification describes the evidence and settings under which Footwork may consume that result. Neither implies action authority.

Move TypeSafe SDK construction into its adapter, preserve existing request builders and settings through compatibility translation, and retain native probability/confidence/distribution provenance. Do not synthesize a common confidence number or transfer a threshold without qualification. Track requested/returned model, prompt/evidence/settings versions and every attempted request.

Retain refusal per answer. Validate the whole envelope and the dependency closure actually consumed by a decision. An unused speculative target refusal need not invalidate the selected operation; a missing required target or safety head must. A missing image answer must not inherit a previous positive text answer. Deterministically forced singleton choices retain explicit code-source provenance.

The [visual advisory plan](../visual-system-one-plan.md) already defines a sensible next slice. The new implementation prediction is open. Let that work complete within its existing ownership; its request/result records can later be adapted into the shared domain. Do not demand that useful advisory work wait for a repository-wide reorganization. Browser capture geometry, multimodal native S2, independent visual qualification and reviewed execution remain separate gates.

## 8. Inspection lab and evaluation system

Keep the JavaScript lab dependency-free and separate from the Python actuation runtime. Define a versioned evidence-import schema: packet/step/event identity, hashes, exact scope, clocks/cursors and coverage gaps. Python verifies imported manifests and keeps any inference/assessment as an overlay. Cross-language conformance fixtures can validate the schema; no second live tab controller is needed to share evidence.

The existing findings ledger already distinguishes observed, documented and inferred claims. Preserve that and extend evidence consumers rather than rebuilding the recorder. Notebook prediction W1 remains open: local workflow/readback checks do not yet close the scoped live workflow question. Future unattended capture must prove a persistent connection/process, owner scope and gap accounting; a polling method name is not continuity evidence. HTTP 200, a sealed packet and an event within an action interval do not prove persistence or causation.

Reorganize the eval harness around task/capture manifests, runner configuration, attempt accounting, independent oracles and reporting. Parameterize shared provider-call/timing/artifact machinery instead of copying it into every D-number file. Keep each preregistration and frozen result directory immutable. Historical scripts can remain archival entry points; do not rewrite old reports to appear produced by the new runner.

Every new run manifest should identify commit, cleanliness, dependencies/patches, task/corpus digest, prompt/settings, requested/returned model, arm, attempt count and budget state. A structured stage outcome distinguishes invalid capture, provider refusal, transport failure, gate refusal, uncertain dispatch, unsupported claim and wrong verified effect. All-attempt denominators and end-to-end phase timings survive interruption.

Inspect is a useful reference for this organization, not a replacement for Footwork's grading rules. It explicitly documents that checkpoints do not restore running tools or external side effects, and the reviewed checkpoint feature requires its development version. Adoption would be a separate dependency decision. [Inspect checkpointing](https://inspect.aisi.org.uk/checkpointing.html).

## 9. Reference repositories: what to borrow and what to preserve

Inspected local sources, not executed benchmarks:

| Reference | Concrete source observation | Transfer and limit |
|---|---|---|
| arc-cua, `6b35303` | `src/arc_cua/protocols.py`: separate backend/policy protocols; `models.py`: immutable snapshot/elements/subtask; `policies/choice.py`: validates consumed answers; `runtime.py`: bounded settling/execution | Borrow compact boundaries and required-head validation. Its optional completion verifier can default to true, so preserve Footwork's evidence floors. Preserve explicit visual freshness and refusal semantics identified in the existing source audit |
| pi, `ce950d78f` | `packages/agent/src/types.ts`: typed tool hooks, errors and turn decisions; `packages/coding-agent/src/core/session-manager.ts`: versioned entries/projections; `packages/durable/src/session/session.ts`: serialized mutation line and publication of committed state | Borrow the separation of loop, session state and presentation, plus committed-event publication. Do not import the entire TypeScript runtime or treat conversation/session replay as UI effect replay |
| Cua, `9994fc2e4` | `libs/cua-driver/rust/crates/cua-driver-core/src/action_record.rs`: internal execution truth distinct from stable projection, route/delivery/evidence/attempts; contract `outputs.rs` carries typed published effects | Preserve richer driver truth through the adapter rather than collapse it to an effect string. This newer source does not establish capabilities of pinned cua-driver 0.28.2; negotiate the installed contract and refuse unsupported fields |
| browser-use, local submodule `d8110c5` | Agent lifecycle and browser events are upstream-owned; Footwork's contract tests explicitly assert private phase order, signatures and action-model behavior | Keep observer/executor/library value and isolate version coupling. Event-driven observation is useful for future settle probes; it is not permission to bypass guards or change pins |
| Inspect AI, `69ee9ba02` | `util/_checkpoint/sample_runtime.py`: dumps/restores cost, tokens, turns, elapsed time, role/model usage; solver/task state and approval decisions have separate types | Borrow restored cumulative limits, solver/scorer separation and structured intervention. Keep external GUI reconciliation in Footwork; checkpointing is not effect rollback |
| DBOSify local README and Temporal documentation | Durable workflows checkpoint orchestration and activity results; Temporal recommends idempotent activities | Use durable-workflow ideas for recorded intent and attempt identity. A database can transact the local record, not a third-party click/send. A workflow framework is optional later infrastructure, not a substitute for outcome readback |

Source roots are under `/Volumes/External SSD/referencerepos/`; browser-use's Footwork submodule is local to this repository. The existing [arc audit](../arc-cua-decisions-reference.md) and [inspection reference survey](../../../tools/inspection-experiments/REFERENCE_FINDINGS.md) provide additional transfer limits. See [Temporal activity guidance](https://docs.temporal.io/activity-definition) for the activity idempotency requirement; external GUI behavior must be established independently.

The important synthesis: compact adapters from arc-cua, committed session records from pi, truthful actuation records from Cua, independent evaluation from Inspect, and pinned browser infrastructure from browser-use. Footwork's guard and experimental discipline remain its own.

## 10. Migration sequence, ownership and rollback

These packages are an executable sequence, not an estimate of days. Units touching the same runtime files should be serialized. Each unit needs a concrete acceptance receipt before the next caller migrates.

| Package and owned paths | Dependency | Acceptance | Recovery |
|---|---|---|---|
| A. Freeze contracts: `tests/contract`, `tests/test_session_scenarios.py`, new runtime interface scenarios; notebook/preregistration where required | None | Inventory every public command, mutation route, receipt/terminal state, legacy grant behavior and pin; scenario parity exposes intended differences | No product routing change |
| B. Structured evidence: `completion.py`, `receipts.py`, `delivery.py`, `carry.py`, new domain records | A | New records match current evidence-floor behavior on exposed fixtures; changing text formatting cannot change completion; missing evidence stays limited | Preserve legacy prose parser for old artifacts only |
| C. Transactional store: `SessionState` persistence, `grants.py`, store/migration/artifact modules | A–B | Kill before/after intent, grant reservation, dispatch-start, driver result and receipt; concurrent commands; cumulative budgets; corrupt/incomplete artifacts; unknown outcomes never auto-repeat | Convert a copy; retain original session; refuse downgrade of new active sessions |
| D. Operator session service: `session.py`, `cli.py`, command/rendering modules | B–C | Real CLI scenarios preserve exit codes, target/refusal behavior, secret withholding, grants, carries and completion; JSON and human rendering derive from same result | Select legacy/new per new session; never dual-write or dual-dispatch |
| E. Native loop caller: `desktop.py`, `desktop_s2.py`, Cua adapter extraction | D | Operator and autonomous callers see same gate/receipt outcomes; actual task-owned native runs verify shared-machine posture and saved-resource checks | Preserve old native loop for isolated comparison sessions |
| F. Browser caller: `agent.py`, `bridge.py`, `s1.py`, compatibility package, relevant tools | B–D plus upstream contracts | Account for every action including Enter/evaluate/file operations; sequentialize or prove independence of mutations; browser scenario and upstream tests; guard cannot be skipped through a tool/lifecycle route | Keep pinned adapter; feature selection only for new runs; no upgrade bundled |
| G. Cross-surface API: `crossloop.py`, `carry.py`, workflow modules | D–F for migrated surfaces | Structured results replace output parsing; no repeated uncertain effects; source revision/carry provenance survive; completion checks all required surfaces | Structured CLI bridge remains temporary fallback |
| H. Judgment role extraction and eval consolidation: `policy.py`, `verify.py`, provider adapters, D runners/reporting | A–B; ongoing advisory implementation remains separately owned | Replay preserves request/decision behavior and native scores; required-head refusal and stale result handling; budget restoration; runtime has no eval imports | Preserve qualified Jev role implementations/settings; new adapters disabled without qualification |
| I. Lab evidence import and private review view: `tools/` schema/conformance fixtures, Python importer, renderers | B–D | Sealed integrity and limits survive import; gaps block unsupported claims; review shows exact source/proposal and observed outcome | Lab remains independently usable; imported evidence grants no new authority |

The shortest valuable delivery is A–D: structured evidence and a recoverable operator session with the current CLI. It can ship before migrating autonomous planners. E–G remove execution duplication. H–I make later visual/workflow work easier. The advisory visual work can proceed independently and adapt after these records stabilize.

Old logs/results stay readable. A legacy reader may conservatively derive the old evidence, but must label its format and limitations; it cannot create evidence that was never recorded. Migration is copy-based and versioned, with a dry-run report. Do not roll back an active session by deleting its new journal or restoring an old projection after effects have occurred; reconcile or start a fresh explicitly scoped session.

Keep old implementation selection only for newly created isolated sessions during rollout. Shadow deterministic planning/evidence projections from recorded exposed fixtures; never shadow by dispatching twice. If a difference exposes a bug, capture the scenario, then land that behavioral fix separately from the structural migration. Removing a broad authorization mode is likewise a separate behavior change, not an undocumented refactor side effect.

## 11. Verification and adoption criteria

Structural acceptance is stricter than a green unit suite:

- Core imports without model SDKs, platform drivers, CLI or evals; adapter imports are explicit.
- Every supported caller reaches the same authorization/execution protocol; optional capabilities declare real support and limits.
- Presentation changes cannot alter evidence or final verdicts.
- No crash/concurrency scenario loses intent, reuses a one-use grant or blindly repeats an uncertain mutation.
- Scope, target identity, secret withholding, posture, required evidence floors and native score provenance survive migration.
- Resume retains calls, cost reservations and recovery limits; late generations cannot supply a consumable positive.
- Existing upstream contracts, pure/Rust equality and route/scenario coverage remain green.

For implementation, use the repository checks: Ruff, appropriate scenario/unit/contract tests, notebook validation, pure/native equality, Node conformance tests for changed lab schemas, browser tests where changed, and actual task-owned native/browser verification for platform claims. Use the configured environment; do not fetch dependencies as a side effect of validation.

Empirical claims need separate preregistered tests, with predictions committed before their resolving run. Useful questions: does a shared session service reduce parity failures; does a warm driver improve end-to-end verified time without retargeting or focus loss; does structured evidence reduce false completion or operator repair burden? Observe failures, all attempts, cold starts, scope gaps and independent resource readback.

Use exposed development data for characterization and comparison. Keep heldout suites sealed and run them only at their required adoption boundary; do not turn this migration into repeated heldout debugging. Freeze measured code/settings first. Compare dangerous/wrong accepted effects, verified coverage, operator intervention burden and cost/median/p95 time per verified outcome. A lower model-call count or faster command return is insufficient. Do not invent a tolerated quality/latency regression after seeing the new result.

The refactor is complete when a supported operation has one authority/evidence lifecycle across callers, active sessions recover conservatively, a new qualified driver/role needs an adapter rather than another gate implementation, and existing result provenance remains readable. Independent visual accuracy, a live pixel precondition and reviewed crop execution are further product capabilities; a cleaner architecture cannot count them as delivered.

## 12. Product consequence and first decision

The user-facing app can stay centered on the existing commands. It gains clearer explanations: what is bound, what is proposed, what was authorized, what was attempted, what is observed, what is verified and what needs reconciliation. A private review view should be a projection of those records, showing source/target/arguments, evidence limits and outcome readback. It should not own execution logic or hide uncertainty behind a single confidence badge.

Start with extraction of structured effect evidence, then the transactional intent store and session service. Preserve the current qualified behavior while making recovery explicit. Let the advisory visual package remain useful on its own. Broader provider routing, driver replacement, a daemon, public UI and autonomous visual execution should each earn a separate measured decision after this core is stable.
