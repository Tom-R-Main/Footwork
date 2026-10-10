# Joint review of the H4 capability-system product brief

Reviewers: Codex and Claude (Opus 5.5), collaborating as peers through the Footwork file mailbox on October 9, 2026.

## Scope and evidence

We independently reviewed [the selected product brief](agent-superpowers-product-20261009.md) against current source before exchanging conclusions. The earlier [architecture configurations](five-architecture-hypotheses-v2-20261008.md) supply design obligations, not implemented guarantees. This review uses source and document inspection only: no runtime experiments, host integrations, installations, provider calls, commits or deployment. Test references describe inspected coverage, not tests freshly executed for this review.

The brief explicitly calls its interfaces proposed and acknowledges packaging, recovery and qualification work. The findings below identify what must become concrete before release; they do not treat every future-tense promise as an existing implementation claim. We support the selected product direction: the host owns planning, and Footwork supplies governed operations and evidence through a shared service.

Paths and line references below are relative to `jevdual/` and describe the source inspected during this review. Proposed acceptance probes must be preregistered and committed before execution under `CONTRIBUTING.md`; none were run here.

## Interface and ergonomics

Author: Codex. Independently reviewed before reading Claude's findings.

### I1 — High: declare which routes require judgment

The brief's model services are opt-in, while required checks remain mandatory (`agent-superpowers-product-20261009.md:66`). Those statements need a capability matrix. Current `cmd_do` creates a destructive judge only if credentials exist (`python/jevdual/session.py:887-907`); `Authorizer.check` skips the judgment branch when the judge is absent (`python/jevdual/authorize.py:211-243`). An absent judge therefore differs from an invoked judge that fails closed. Task completion currently requires provider access (`python/jevdual/session.py:1184-1186`).

**Recommended change:** classify supported routes as structurally qualified, judgment-required, or unavailable. Declare required judgment, applicable evidence, disclosure and cost before an effect is admitted. On a judgment-required route, absent access must return `judgment_unavailable` before dispatch. Keep qualified Jev roles/settings; a host's reasoning is not automatically a qualified replacement. Specify the intended structural-only coverage, then qualify it with evidence before advertising model-free operation.

**Acceptance obligation:** exercise absent credentials and failed/invalid judgment separately on each affected route. Required missing judgment dispatches nothing; qualified structural routes remain usable within their declared limits.

### I2 — High: expose the task and authority lifecycle

The five tool families describe binding, observation, action, verification and resume, but do not establish who authorizes a host's requested task scope, how it changes or expires, and how a successor acquires continuation rights. Current session state holds task prose and authorized label strings (`python/jevdual/session.py:48-79`), with additional label authorization accepted per command (`python/jevdual/session.py:904-907`). The earlier H4 design assigns canonical authority and custody to the broker (`five-architecture-hypotheses-v2-20261008.md:107,119,167`).

**Recommended change:** define an issued task handle and immutable authority envelope, including principal/delegation, bound resources, permitted effects, limits and posture. Establishment can be part of bind. Closure revokes future dispatch while retaining pending operations and owed results. An amendment may create a linked task, provided aggregate consumption and reservations survive and pending obligations retain custody; a general mutable revision API is unnecessary. First-version resume must authorize reattachment to the same durable task after process or host turnover. Cross-principal transfer can remain unavailable. State what authenticates scope issuance and reattachment for the host-launched stdio deployment. Process transport alone does not establish that a requested scope is authorized.

**Acceptance obligation:** a new conversation or connection cannot reset task consumption; unauthorized continuation or scope expansion fails; revocation is checked at the next governed dispatch boundary. This checks mediated authority within the stated same-user trust limit.

### I3 — High: preserve resource and target identity through rebinding

Current browser sessions reconnect using the last observed URL (`python/jevdual/session.py:394-397`). Attachment refuses absent or duplicate matching URLs (`python/jevdual/browser_driver.py:283-318`), but a URL is not a tab incarnation. Numeric target handling compares old and fresh labels, while semantic labels resolve against a new observation (`python/jevdual/session.py:847-885`). Keeping a driver warm does not establish identity after its process is lost.

**Recommended change:** bind resource handles to qualified surface incarnations and target handles to observation generations. Define stale, ambiguous and lost-identity dispositions, plus explicitly authorized rebinding. Preserve operation and arguments during any remap. A replacement tab with the same URL or element with the same label must not silently inherit the old approval. Keep the earlier identity requirements visible in the compact product brief (`five-architecture-hypotheses-v2-20261008.md:30`).

**Acceptance obligation:** cover duplicate URLs, same-URL replacement tabs, navigation during uncertain dispatch, same-label replacement targets and generation expiry. Unsupported identity guarantees leave the route unavailable or refused; they do not become guessed attachments.

### I4 — Medium: make carried values a public contract

Cross-surface values are central to the demonstration, but neither a read/carry intention nor a value handle appears in the tool table. Current callers use `read`, `@NAME` and a source session directory (`python/jevdual/session.py:1267-1294,824-837`). `Carry` records value provenance and observation time (`python/jevdual/carry.py:30-50`). Those are useful foundations, but local session paths should not become the host's abstraction.

**Recommended change:** choose explicit read/carry operations or observation-produced value handles. Declare whether the value belongs to its recorded observation or must remain current at commit, and include source/destination authority and disclosure scope. The earlier demonstration chooses recorded-observation semantics with source/time displayed (`five-architecture-hypotheses-v2-20261008.md:31`); retain that choice unless deliberately revised.

**Acceptance obligation:** a carried value retains its source and timestamp across host turnover; destination changes invalidate dependent mutations; a freshness-dependent task refuses a stale source rather than treating historical provenance as freshness proof.

### I5 — Medium: define what each verification check proves

Current `done` judges the whole task with a model (`python/jevdual/session.py:1217-1229`). `check-file` checks a carried line or a declared append (`python/jevdual/session.py:1336-1357`); native save readback compares one window text area with its named on-disk text (`python/jevdual/native.py:1186-1217`). These checks prove different things. None alone establishes arbitrary correctness, save-copy identity, destination and preservation of the original.

**Recommended change:** expose typed supported checks and separate observed change, visible field equality, persisted content, correctness and original preservation. Return a result for each check, including unsupported and unknown. Bind each conclusion to its exact resource, evidence and predicate. The save-copy demonstration requires the independent copy/destination/content/preservation checks already specified in the earlier design (`five-architecture-hypotheses-v2-20261008.md:23`).

**Acceptance obligation:** an unsaved edit may satisfy visible equality while failing persistence; a correctly saved value may still fail copy identity or original preservation. Partial evidence must not certify the whole task.

### I6 — Medium: specify shared machine-readable results and errors

Current observation and status handlers print prose (`python/jevdual/session.py:356-383,1253-1264`). Parser failures raise `SystemExit`; top-level failures render stderr (`python/jevdual/cli.py:431-469`). Existing receipts separate effect from delivery, but lack the proposed operation identity, checks and recovery contract (`python/jevdual/receipts.py:38-56`). Adapters cannot obtain parity by parsing those rendered strings.

**Recommended change:** define versioned schemas for success, refusal, partial outcome, unknown, unavailability and invalid input, backed by shared service records. Include durable operation/result IDs, bounded observations, retrievable evidence references, permitted next steps and timeout/cancellation reconciliation. JSON CLI machine mode must produce parseable structured stdout, with diagnostics separated. Human-readable explanations are projections of the records.

**Acceptance obligation:** the same operation through MCP, SDK and JSON CLI preserves disposition, evidence and check meaning, including malformed arguments, unavailable routes, interruption and oversized observations. A timeout must not imply permission to repeat an effect.

### I7 — Medium: bound the first distribution and host acceptance

The browser driver assumes a macOS Chrome executable and a private profile/port (`python/jevdual/browser_driver.py:35-39`). Its current action route supports click/type/append/navigate, with no browser scroll/key/menu route (`python/jevdual/browser_driver.py:410-442`). Packaging uses Maturin, unconditional browser/model/Cua dependencies and one CLI entry point (`pyproject.toml:1-3,18-26,39-46`). The brief correctly identifies packaging as unfinished; its metric list still lacks a release decision rule.

**Recommended change:** name one first platform, browser/native route set and installable artifact. Require a clean supported-machine install without compilation, diagnose unsupported operations, and test two actual host integrations plus a CLI consumer. Predeclare acceptance bounds for first verified outcome, user interventions, schema/target repairs and interruption recovery before measurement. Select the bounds with Tom; this source review supplies no measured thresholds or host support claim.

**Acceptance obligation:** a fresh agent can discover, register and complete the bounded browser-to-native demonstration without source reading or internal session reconstruction, report unavailable cases honestly, and recover through the same contract in each supported integration.

## Ownership, recovery and assurance

Author: Claude. Independently reviewed before reading Codex's findings; O3–O5 incorporate Codex's corrections.

### O1 — High: record intent before dispatch and make `unknown` a disposition

The brief promises that pending operations and owed results survive process exit, and that "an uncertain timeout produces reconciliation instructions, not advice to click again." Current `cmd_do` records `state.pending` only after dispatch returns or an error is caught (`python/jevdual/session.py:963-1013`). The step counter increments in memory at `:963`. Termination or cancellation during dispatch can leave no durable intent, so the next invocation cannot identify the outstanding operation and the host may retry. A host timeout alone does not establish whether dispatch continued or stopped.

Errors are also classified as no effect without send-phase evidence. A raised `NativeBridgeError` or `RuntimeError` becomes `not dispatched` (`python/jevdual/session.py:992-994`), and the field receipt then reports `refused (not applied)` (`python/jevdual/session.py:283-288`). In the browser route, a driver tool error becomes effect `refused` (`python/jevdual/browser_driver.py:355-358`). Native raises include genuine pre-send guards (`python/jevdual/native.py:669-707`), but `not_key` may click the window title bar before reporting "not pressed" (`python/jevdual/native.py:1069-1076`). That supplementary foreground input is distinct from whether the requested chord was sent and needs its own accounting. A tool error after possible click delivery cannot be told apart from a pre-send refusal by the current browser conversion. The inspected scenario test covers a pre-send error (`tests/test_session_scenarios.py:268`); post-send/kill evidence was not established in this review.

**Recommended change:** make a durable intent record a gate before any adapter ships. It holds operation ID, resource, argument digest and grant, and is committed before dispatch. Driver results and errors carry their send phase. Possible-delivery failures lacking affirmative outcome evidence remain `unknown` until reconciled; demonstrated applied or partial outcomes remain known even if later work fails. Record supplementary foreground effects separately from delivery of the requested operation.

**Acceptance obligation:** terminate after dispatch becomes possible but before its outcome is recorded, including with SIGKILL. Resume reports the durable operation as `unknown` with reconciliation steps, never as a proven refusal or absent operation. Separately verify that a proven pre-send refusal remains refused and an affirmatively evidenced applied/partial effect is preserved.

### O2 — High: serialize concurrent calls and keep state transactional

The brief discusses multiple broker processes but not concurrent calls inside one. The server contract must account for concurrent host calls. Current state has one pending slot per session (`python/jevdual/session.py:66`), and a receipt is the diff against the last action. `session.json` and `grants.json` are written by truncate-and-write (`python/jevdual/session.py:85-86`, `python/jevdual/grants.py:111-112`). A crash mid-write can leave invalid JSON and `SessionState.load` has no recovery path for it. `grants.consume` loads, decrements and saves with no lock (`python/jevdual/grants.py:115-127`), so two concurrent callers can spend a one-use grant twice. The "exactly this effect, once" grant semantics depend on that path. These are source-derived failure mechanisms, not reproduced crash or concurrency results.

**Recommended change:** one server serializes mutations per resource or rejects concurrent ones with a typed `busy`. Receipts are keyed by operation ID, not "last." Step 2's transactional accounting covers intent, grant and budget changes together in a transactional or recoverable journal. Atomic file replacement fixes the corruption case but is not enough for coordinated durability. The brief should state the requirement and leave storage technology to the design.

**Acceptance obligation:** parallel mutating calls on one resource never interleave or double-spend a grant. Interruption at any write leaves a loadable state that reports what is pending.

### O3 — Medium: tie resume to the task handle, not a state path

The brief says owed results survive "for the next authorized invocation" but does not say what authorizes a resume. Current state is located by directory alone: argument, then `$FOOTWORK_SESSION`, then `runs/session` relative to the working directory (`python/jevdual/session.py:121-122`). A host-launched MCP process runs in a working directory the host chooses.

**Recommended change:** resume and status require the scoped resume credential and principal authorization for the durable task established at bind (I2). State lives under a stable per-user root and is looked up by task or operation ID. Knowing the task ID or state path is insufficient authority. Preserve limits, reservations, pending operations and owed results across authorized reattachment; unqualified transfer remains unavailable.

### O4 — Medium: handle orphaned drivers in either lifecycle

Each command now shuts its driver down in a `finally` block (`python/jevdual/session.py:1019`). SIGKILL skips it, so orphaned attachments are already possible. "Keep driver connections warm while the tool process owns them" lengthens that exposure; it does not create the failure class.

**Recommended change:** step 2's recovery design covers orphaned Chrome/Cua attachments, reacquisition and posture state for both per-call and resident lifecycles. A lost resource after an uncertain navigation or submission resolves through I3's lost-identity disposition.

### O5 — Medium: specify contract meaning first, release-freeze after the gates pass

Step 1 freezes contracts "including unknown effects and resume" before step 2 builds the machinery behind them.

**Recommended change:** step 1 specifies shape and meaning with real host callers, including `unknown`, resume, `busy` and `judgment_unavailable`. Step 2 prototypes the recovery gates (O1, O2) against that specification. Only the contract that passes them, and passes actual-host acceptance (I7), is frozen for release. Specifying meaning first keeps the semantics from being worked out after the fact. Freezing late keeps v1 from advertising guarantees the service cannot keep.

### Keep

The brief is right that stdio is not containment, that missing model access should return `judgment_unavailable` rather than weaken a guard (a goal current code misses; see I1), that there is no unattended-liveness promise, and that the host owns the plan.

## Agreed verdict

Both reviewers agree on the direction and the obligations below; final document sign-off is recorded in the mailbox.

Approve H4 as the product direction. Revise the brief's first-version obligations before scheduling implementation. Release qualification remains unproved.

## Priorities

Delivery order, by build dependency:

1. Operation lifecycle: transactional recovery and phase-truthful `unknown` (O1, O2, O4, I6's reconciliation).
2. Task authority, resource identity and serialization (I2, O3, I3, O2's `busy`).
3. Judgment capability matrix (I1).
4. Typed value, check and result schemas (I4, I5, I6).
5. A bounded package and actual-host acceptance (I7), with bounds chosen by Tom.

Contract shape and meaning are specified first. Release freeze follows the substrate and actual-host acceptance probes (O5).

**Present-behavior note.** With no credentials, `cmd_do` builds no judge and the authorizer skips judgment on judged routes, though an invoked judge that fails does fail closed (`python/jevdual/authorize.py:158,231`). I1 therefore deserves immediate policy triage independently of H4. A CLI remediation must explicitly define which routes require judgment and reproduce the missing-judge behavior in a scenario before changing the harness. An explicit `--no-judge` mode must have declared limits; its existence does not qualify a model-free route. Whether to authorize and schedule that work is Tom's decision.

## Recorded disagreements

None outstanding. The authority discussion converged on immutable first-version scope, linked amendments preserving aggregate consumption, closure retaining unsettled obligations, and authorized same-task reattachment. General mutable revisions and cross-principal transfer need not ship in v1. The lifecycle discussion also corrected the initial suggestion that per-command shutdown makes process death a clean driver boundary: SIGKILL skips `finally` in either design. Intended contract meaning is specified before probes; release freeze follows qualification.

## Not checked

No behavioral tests, runtime probes, host integrations, provider calls or installs were run. Line references reflect the source at review time. Whether driver tool errors occur after the send boundary (O1) was inferred from error handling, not observed. Crash durability, concurrent grant consumption, qualified model-free coverage, package installation and actual-host ergonomics remain unproved. Routine notebook-format validation does not qualify those behaviors.
