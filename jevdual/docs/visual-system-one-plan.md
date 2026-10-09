# Visual System One: reviewed invocation and escalation plan

Plan review and remediation, 2026-10-08. Updated implementation status: the native advisory service in Units 1–4 is **built and checked locally** for explicit operator/workflow invocation and the native System Two message handoff. Full autonomous System Two recovery and real-provider perception qualification remain unavailable. Browser capture and reviewed execution remain separate gates. No default model routing or admission setting changed.

## Implementation status

The new [visual-check command](visual-checks.md) supports both typed families, private native captures, explicit disclosure, bounded/persisted provider reservations, final source/generation invalidation and redacted question/result handoff. [Post-implementation review and native requalification](../results/visual-checks-review-20261008/report.md) fixes six reproduced defects and a library source-validity gap. Its final native pass exercises fifteen selected scenarios in task-owned document/crop scenes through Cua and the production adapter against a loopback contract server. Full offline checks pass 1,031 tests with 26 skipped. The fixed server probabilities prove mechanics, not perception accuracy or real OpenAI performance; no paid provider calls were made. Normal action policy does not invoke the service automatically.

## Recommendation and scope

Build a read-only visual question/result boundary and structured escalation first. Initial families are **match an offered document preview to a supplied reference** and **assess whether an explicitly supplied crop retains a specified subject**. They are distinct roles with distinct evidence recipes and qualification. Keep Jev active for current text roles. Treat visual answers as advisory until independent family-specific evidence permits a subsequent reviewed-execution package.

Observed: D3 adds useful document/crop perception in authored fixtures but produces a wrong toolbar effect at p=.99. D4 marked/region views improve authored variants; the original failure does not reproduce, so repair attribution is inconclusive. Inferred: precise visual questions merit implementation and independent qualification; generic visual action admission and universal backend interchangeability do not. Independent real-app accuracy, calibration and end-to-end speed are unavailable. Sources: [D3](../results/d3-dev-20261008/report.md), [D4](../results/d4-dev-20261008/report.md).

| Structural option | Assessment |
|---|---|
| Images on every System One step | Inferred: unnecessary disclosure and capture work for text-sufficient steps; no demonstrated workflow benefit. Not chosen |
| Call vision whenever Jev declines | Inferred: conflates missing pixels with planning, authority, transport and freshness failures, and risks confidence-seeking fallback. Not chosen |
| Explicit role service invoked by workflow/System Two | Chosen: bounded evidence and callers make invocation, cost, abstention and qualification inspectable without refactoring all text policies |

“System One” here means a bounded semantic check, not a proven latency advantage. Visual capture may dominate request time; the workflow earns the fast path only through qualification.

## Review findings and corrections

| Finding in the preceding proposal | Consequence | Remediated plan |
|---|---|---|
| “Needs pixels” had no accountable caller or typed criterion | An opaque router could invoke images on every difficult step or bypass a text refusal | System Two or an explicit workflow issues an allowlisted question family; code checks capability and missing evidence. Low Jev confidence alone never enables vision |
| A single target/action envelope was used to describe document matching and crop assessment | Reference provenance, subject definition, crop coordinates and resource ownership were absent | Add typed multi-asset question evidence around immutable captures; preserve the existing inspection envelope and its read-only meaning |
| A fresh binding was positioned close to action approval | AX/pixel capture is sequential; hash equality does not observe current state | Distinguish receipt binding, temporal validity and a future live action precondition. Reject stale generations and visual target remapping |
| Native System Two was assumed able to receive pixels | Current chat and prompt are text-only; a local path is not a remotely readable image | Add a structured text handoff first; qualify an optional multimodal transport separately. Report image capability unavailable when absent |
| Pixel privacy was implicit in screenshot capture | Local storage permission and remote disclosure are different operations | Check source/purpose disclosure before capture/upload; preserve secret withholding. Do not substitute a wider capture after refusal |
| Visual selection implied a complete candidate domain | Native AX projection proves presence, not absence or global uniqueness | First version judges one offered candidate. Any later choice is explicitly among supplied IDs, with ambiguity and incomplete-coverage states |
| Visual true flowed toward execution without a defined evidence combination | Vision might overwrite a missing/negative required check | Required checks are conjunctive and version-bound; no probability averaging, score multiplication or inherited positive. Keep authority and completion in code |
| Browser and crop action paths were assumed available | Browser inspector lacks qualified geometry; current operator routes do not provide a qualified crop workflow | Qualify browser capture separately. First crop capability assesses a supplied rectangle; it does not draw, drag, resize or save |
| “Bounded recovery” and “quality and speed” lacked operational definitions | Repeated requests could hunt for a positive answer; adoption could be justified by medians alone | Set bounded recovery defaults, preregister independent qualification and count wrong effects, abstention burden and full verified-outcome latency |

## Caller and invocation

The caller supplies the task criterion, question family, evidence/source scope and, where relevant, an offered proposal. It cannot put arbitrary page instructions into the trusted criterion. Rendered text, OCR, images and document contents remain untrusted evidence. Initial roles are `document_reference_match` and `crop_subject_containment`; generic icon approval, arbitrary screenshot reasoning, freshness judgment and completion replacement are unavailable roles.

The first operator entry point is a proposed read-only `footwork visual-check` command that takes an explicit typed request manifest in the active session. Its manifest includes versioned family-specific arguments, scoped reference/source IDs and required postcondition where relevant. It obtains current candidate evidence through the capture service; arbitrary local paths are resolved only within the task's explicitly allowed resources. No `--act` switch in this package. System Two integration calls the same service, rather than duplicating capture or provider code. Exact CLI flags are an implementation detail to settle against existing parser conventions before coding.

Routing is deterministic over the request family and available evidence. “Text inadequate” is a recorded condition such as an unlabelled observed preview plus an explicit reference-match task, not the model's generic lack of confidence. Initially the operator/workflow declares the family; an automatic missing-evidence classifier is outside scope.

| Condition | Result |
|---|---|
| Text/resource evidence is sufficient and the question is not visual | Existing text/code path; do not add an image call |
| Allowlisted inherently visual question, qualified capture and permitted disclosure | Invoke visual S1 directly; no obligatory Jev pre-call |
| Explicit visual criterion unresolved by ordinary labels/DOM/AX/OCR | Invoke the same visual service after recording the missing evidence |
| Stale/missing target, invalid geometry, withheld pixels or unsupported role/surface | Return a typed unavailable result before provider dispatch |
| Planning, composing arguments, deciding user intent or selecting a workflow | System Two owns the reasoning |
| Missing authority or unresolved user preference | System Two escalates to the user; a model probability cannot resolve it |

Parallel text/visual requests are a later optimization only for independent required checks on one frozen generation. A dependent question waits for its prerequisite. Do not run unused speculative heads merely to fill a batch.

## Data shape and ownership

These are proposed types, not product stubs:

| Type | Required content and owner |
|---|---|
| `VisualCheckRequest` | Workflow-owned request ID, session/observation generation, allowlisted role and criterion version, family arguments, required evidence/check names, disclosure policy, deadline and budget |
| `CapturedAsset` | Capture-service-owned source scope, image hash/dimensions, viewport/transform, capture interval and receipt time, provenance/coverage limitations; reference assets also carry resource revision/hash and page/render identity |
| `VisualCheckEvidence` | References to immutable assets, candidate ownership, exact offered target/region and relevant context, ordinary accessible text, derivation receipt, complete evidence digest |
| `VisualCheckResult` | Request/evidence identity; valid answer, refusal, unavailable, timeout, invalid response or invalidated status; native probability/distribution and separate confidence where supplied; requested/returned model, prompt/schema version, usage and phase timings |
| `VisualEscalation` | Unresolved question, safe evidence references, source/coverage limits, typed reason, required-check results, failed precondition, last action/receipt, recovery budget and suggested next observation |

Keep capture integrity in `visual_evidence.py`; preserve version 1's `inspection_only` contract. Add a question-oriented wrapper rather than force a pure perception check to invent an action or postcondition. New types must validate at construction/serialization boundaries and prevent mutable mappings from changing a request after hashing. The provider adapter never owns authorization, candidate creation, live screen checks or execution.

Observed production `decisions.py` accepts text input and rejects a whole batch on refusal; image transports currently live in evals. The plan requires a bounded production image adapter behind the new role contract, retaining strict parsing and budgets rather than importing an eval runner into runtime. Start with one predicate per check, so refusal/error is scoped to that check. An envelope failure invalidates the request; a refused required check stays refused. If later batching is added, validate every consumed answer and preserve unused-head refusals separately without relaxing envelope validation.

## Evidence recipes

**Document/reference match.** Bind the supplied reference's resource revision/hash, selected page and rendering recipe independently from the current candidate preview. Record the preview's observed target and owning document/resource identity when the application exposes it. Missing ownership is explicit: a valid appearance match can remain advisory, but cannot prove which file a click opens. Preserve OCR/accessible labels. The answer is about one offered candidate, not global uniqueness. Later bounded selection must allow no supplied match, insufficient evidence and multiple plausible matches; a singleton candidate is not evidence of a match.

**Crop/subject containment.** The caller supplies the subject criterion and a proposed rectangle in declared source-image coordinates. Record source resource/revision, orientation, display-to-source transform and the region's bounds. Include enough image context to see the entire relevant subject and crop boundary; a control's bounding box alone is insufficient. The model judges containment, not coordinate generation. Unspecified subject or ambiguous hidden extent returns insufficient evidence. Actual dragging/resize/save requires a separately qualified app route and independent output checks.

Retain a canonical source capture. Each region/marked view records parent hash, derivation method, transform, bounds and context extent. A direct driver clip is a distinct capture; do not claim it is bitwise identical to a slice of the original. Full-frame, contextual region and marked evidence remain alternatives to compare, not a universally winning recipe. D4 region request p95 was worse despite fewer tokens. Evidence expansion must answer a stated missing-evidence condition and pass the same disclosure/budget gates.

## Temporal validity, disclosure and asynchronous results

Observed: native AX collection precedes screenshot capture, and `NativeVisualCapture.captured_at` is a Python receipt-time stamp. Do not advertise an atomic snapshot. Future captures record monotonic start/end/receipt and the structural observations bracketing capture where available. Source identity mismatch, unstable geometry or incomplete required evidence returns unavailable. Bracketing reduces uncertainty; it does not prove visual semantics remained unchanged throughout.

Assign a session observation generation. A result is consumable only by the exact request, evidence digest, role/prompt/settings version and generation that issued it. Navigation, action, source/target/region change, invalidation or deadline expiry makes an outstanding answer historical. Cancellation does not assume the provider request was unbilled; retain uncertain usage reservation and ignore late answers. Identical image bytes alone do not establish current validity.

Any future reviewed action must re-establish source identity, exact target/arguments and the relevant visual precondition immediately before dispatch through the existing guard. Native semantic remapping to another ID must invalidate a visual judgment, even when role/label/section match. Do not compare a fresh complete binding hash directly to the old hash: capture IDs/timestamps normally change. Compare explicit live preconditions while binding the eventual action to the new observation. Define family-specific pixel/context comparison and allowable changes empirically before enabling the action path; unsupported or unstable preconditions withhold execution.

The capture service and provider boundary separately enforce the task's allowed source/purpose. Preserve secret-session refusal before capture, as applicable on each entry point. It is not a general detector of sensitive pixels. If the selected capture cannot be disclosed, return `pixels_withheld`; do not silently widen, redact by assumption or switch providers. Logs contain safe IDs/digests/status/usage, not raw images, tokens or secret-bearing diagnostics. Local evidence, uploads and escalation media have explicit retention and cleanup ownership. A cached answer is reusable only for the identical request/evidence/model/prompt/settings within the same valid generation; persistent cache and cross-generation reuse are outside the first package.

## Results, escalation and recovery

Separate a native probability from the local interpretation of that answer. The D3/D4 .80/.20 bands are diagnostic experiment settings, not qualified runtime admission settings. Initial advisory output retains the probability and uncertainty/refusal status; family-specific interpretation is preregistered and calibrated before any reviewed-execution gate. Do not convert a timeout, absent answer or refusal into probability zero.

| Outcome | Owner and next action |
|---|---|
| Valid advisory positive | Return bound result to caller/review; grant no action or completion authority |
| Valid negative | Reject this offered proposal; select a different observed candidate if scope permits. It is not inherently a user interruption |
| Valid uncertain or ambiguous answer | System Two chooses an identified additional observation, another candidate or an intent question |
| Conflicting required judgments | System Two investigates the conflicting predicates/evidence; no majority vote or overwrite |
| Capture, geometry, coverage or identity failure | Capture/workflow repair first; do not seek a more confident model answer |
| Disclosure refusal or unavailable provider/image capability | Return the concrete limit to System Two; text-only recovery when sufficient, otherwise user-visible blockage |
| Invalid response, timeout, budget exhaustion or expired generation | Preserve receipt; stop this check. No blind retry or late-result admission |
| Uncertain execution/delivery | Reconcile current resource/effect state before retry, irrespective of visual probability |

Required checks are individually named and conjunctive. A visual positive cannot replace missing artifact persistence, resource identity, authorization or a contradictory required text judgment. Different predicates need not agree numerically: “looks similar” and “is the intended file revision” are separate claims. Never average probabilities across them or inherit a previous text positive for an absent image result.

Proposed initial recovery default: at most one provider call for a request/evidence pair; at most one additional evidence acquisition for the same unresolved question, only when its purpose is explicit and evidence materially changes. Then return control with remaining uncertainty. Configure byte/token/call/spend/deadline caps before dispatch, reserve unknown-cost requests, and maintain an overall workflow recovery budget so changing wording/IDs cannot reset it. These are operational bounds to implement and assess, not measured optimal settings. Timeouts are chosen from registered latency evidence before the trial; no invented deadline is claimed qualified here.

Native System Two and `CrossLoop` currently accept text messages. First handoff therefore adds a structured text summary with safe local artifact references usable by the operator or explicit local inspection tools. A local path is never treated as an image the remote model can see. A multimodal adapter must negotiate image capability, serialize authorized assets and preserve the closed action contract before pixel reasoning is claimed. When capability is absent, the escalation says so and keeps the pixel-dependent question unresolved. Existing browser S2 image behavior must be traced and checked separately; native qualification cannot certify it.

## Dependency-ordered implementation packages

| Unit and owned paths | Depends on | Acceptance evidence | Recovery/release boundary |
|---|---|---|---|
| 1. Typed request/evidence/result and deterministic router: proposed `python/jevdual/visual_checks.py`, focused tests; minimal additions to `visual_evidence.py` | This plan; family definitions | Contract checks reject unsupported families, missing reference/transform, mutated hashed data and mixed generations; ordinary text route makes zero image calls | Read-only, unavailable roles explicit; no existing factory/settings migration |
| 2. Native capture service and operator entry point: `native.py`, `session.py`, `cli.py`, existing inspection scenarios | Unit 1 | Actual CLI on task-owned surface; reference and subject/crop input types; secret withholding; capture failure; changing window/source/target; incomplete domain; correct scaled geometry | Existing `inspect-target` continues unchanged; new entry point defaults advisory; browser remains unsupported |
| 3. Production visual provider adapter: new bounded transport module using `decisions.py` parsing principles, focused contract tests | Units 1–2; disclosed source and configured budget | Fake-transport tests for every status, body limits, required-head refusals, unknown usage, late replies and no dispatch; authenticated contract probe only within a separately scoped experiment | No automatic retry, no eval import; feature off without explicit configuration; no new keys/install required by plan |
| 4. Structured native/System Two escalation: `desktop_s2.py`, `desktop.py`; operator caller; cross-loop only when needed | Units 1–3 | Exercise real caller path; reason and evidence identity survive handoff; absent image capability stays explicit; recovery limits and uncertain-effect reconciliation | Text summary first; multimodal adapter is an explicit additional contract, not an assumed provider feature |
| 5. Browser capture qualification: `browser_driver.py`, browser observation integration and contract scenarios | Unit 1; supported driver route | Actual operator entry point; duplicate URLs/tabs, reconnection/navigation, scroll, zoom, DPR, iframe/viewport coordinates, clipping and stale-result rejection | Separate package; retain explicit refusal if pinned driver cannot supply qualified provenance; no dependency bump silently |
| 6. Independent visual qualification: new preregistration, isolated dev/corpus manifests and run receipts | Native read-only path and adapter; browser only for browser claims | Blinded independent document/crop cases, adequate text/OCR control, source swaps/ambiguity, coverage and full capture-to-answer timings; report every attempt | No activation from exposed D3/D4 data; existing sealed suites untouched; spend/collection scope settled before calls |
| 7. Reviewed execution in one selected app: that app's workflow, existing authorization/dispatch and resource postconditions | Qualified family, actual app action route and live visual precondition | Reviewer approves exact source/revision/proposal; changed-after-review refuses; actual opened/saved artifact confirms identity, content, crop geometry and scoped destination; uncertain delivery reconciled | App-specific, reversible output copy first; automatic visual approval and general crop driver remain outside scope |

Units 1–4 form the next implementable native read-only package. Unit 5 may proceed independently after shared types stabilize; it must not delay useful native advisory work or be counted as complete from CDP eval captures. Sequence shared-file edits and retain existing native/browser behavior tests. Unit 6 is a new experiment; commit its prediction/preregistration and code/captures before paid calls. Unit 7 is a later authorization and qualification decision, not an automatic consequence of building Unit 3.

## Qualification and decision rules

Before new measurement, freeze prompts, evidence recipes, model/role/settings identity and the criteria against which quality and speed will be judged. Record requested and returned model; an alias is not a guarantee of an immutable provider snapshot. No post-result prompt selection or interpretation change may be passed off as independent validation.

Use independently collected scenes/tasks and blinded labels, with ambiguity, partial subject views, similar-looking pages, source swaps, orientation/scale changes and unsupported app states. Repeated API answers to one scene measure stability, not independent sample size. Keep transport/capture gaps in coverage denominators. A second annotator or resource/geometry oracle adjudicates the outcomes where possible; disputed cases remain disputed rather than becoming tuning targets.

Compare ordinary text/AX/OCR, selective visual checks and an every-step-image reference only if that comparison resolves the routing/product decision. Primary quality metric for subsequent execution qualification is wrong accepted proposals/effects; useful supported coverage, false rejection, uncertainty calibration and operator escalation burden are guardrails. A development gain or zero errors in a small set is insufficient. Choose the tolerated error bound and independent corpus size before qualification; report the uncertainty interval rather than presenting three replays as three independent cases. No numeric acceptance threshold is claimed established by this plan.

Measure routing, capture, AX/OCR, derivation/encoding, provider, validation, escalation/recovery, review, dispatch/settle and independent artifact readback separately. Compare cost and median/p95 time per verified outcome, including failures, cold starts, user review burden and recovery. A lower provider median, fewer image tokens or fewer calls is not by itself a workflow speed gain. Preregister the tolerable workflow latency regression before adopting a family.

The immediate release gate earns only advisory native visual checks: contracts and actual CLI inputs pass, no action/model factory authority changes, disclosure/cost/late-result limits hold, and handoffs expose unsupported capability. Reviewed execution additionally requires independent perception qualification and app-specific live-precondition/outcome checks. Autonomous use additionally needs its own scoped adoption decision. Broader model interchangeability remains role-specific and depends on both quality and verified-outcome speed.

## Current source anchors and unresolved facts

Observed source anchors: [inspection command](../python/jevdual/session.py), [capture and semantic live check](../python/jevdual/native.py), [read-only binding](../python/jevdual/visual_evidence.py), [text-only Decisions transport](../python/jevdual/decisions.py), [native System Two](../python/jevdual/desktop_s2.py), [cross-loop messages](../python/jevdual/crossloop.py), [browser semantic bridge](../python/jevdual/browser_driver.py). The source-grounded [arc-cua audit](arc-cua-decisions-reference.md) supplies narrow seam ideas, not a qualified alternate executor.

Unavailable until implementation/qualification: multimodal support on the chosen System Two transport; exact app crop action/readback; general candidate-resource ownership; browser screenshot provenance across reconnect; a stable visual precondition comparator; independent accuracy/calibration and full workflow performance. These are explicit work gates, not reasons to ask the user to guess implementation facts. Any materially different app/workflow or authority requirement is a product scope decision.

Net recommendation: retain the implemented native advisory checks and independently qualify one document/image workflow next. Keep browser capture separate, Jev active for text, and generic icon/visual action admission disabled. The original review was plan-only; the subsequently authorized native implementation is recorded above. No paid qualification was performed.

## VQ1 machinery status — 2026-10-08

The [qualification guide](visual-qualification.md) describes the new offline corpus validation, frozen schedules, production-image transport smoke, source-group quality/calibration scoring and workflow timing contract. The authored development corpus remains ineligible. Unit 6 now has local machinery; independent real-corpus accuracy and complete workflow speed still require separately scoped measurement. No paid collection or broader model/action activation follows from a passing mock run.
