# Review of verification SDK, evidence lab and Plan C

Reviewed October 28, 2026 against the supplied `main` baseline `5d494c6`. This is source review only: no tests, probes, GUI operations, provider calls, installations or commits. Source references are relative to `jevdual/`; plan references are relative to `docs/plans/five-directions-20261028/`. Claude's reported five artifact tests, 225 combined tests, scratchpad probes, 70/73 recount and file inventory counts have no linked retained command evidence in these plans; treat them as reported, not independently verified here. Their plausibility is not reproduction.

**Recommendation:** contribute a narrow evidence contract and measurement corrections to one durable-operation implementation plan. Defer a standalone SDK and research-lab product. Reliable producers and meaningful checks should determine the contract before packaging determines ownership.

## Ranked findings

### 1. Plan C would prohibit recovery the implementation already supports

C's “unknown is sticky” and “re-reading … cannot raise it” (`synthesis/C-evidence-contract.md:35–38`) are too broad. `CapabilityService._reconcile` resolves an unknown operation from a qualified retained execution receipt, or qualified readback with retained resource incarnation (`python/jevdual/capability/service.py:243–286`). Unattributed matching text remains insufficient. A later qualified current-state observation may also establish a new fact without changing an earlier event's evidential status (`python/jevdual/completion.py:62–69,129–163`).

Preserve immutable observations and append resolution records linking the original attempt, qualified source and decision rule. Do not overwrite history or automatically retry unresolved mutations. Reject blanket unknown promotion **and** blanket unknown permanence. This is directly supported by source; no recovery was reproduced here.

Likewise, “no function takes one kind and returns another” confuses relabeling with derivation. Keep input kinds immutable, but allow a versioned rule to produce a separate derived claim with input references. A saved-state observation can support a scoped answer about that observation without becoming proof of who performed a save.

### 2. Claude overgeneralizes the answer-matcher finding

The “fell 5%”/“rose 5%” issue follows from `extract_atoms`: the numerical atom excludes polarity; `check_claims` grades those atoms (`python/jevdual/verify.py:167–264`). `ClaimCheck.supported` includes narrative, but `is_evidence` excludes it (`:81–96`). The full `Verifier.verify` separately calls the semantic client, computes completion/unmet bands, handles evidence-free answers and applies an effect floor (`:510–592`). Thus the scratchpad observation, even if reproduced, would establish an atom-matcher limitation, not a full-verifier false acceptance.

Keep `atoms_present` explicitly scoped if exposed. Do not rename or replace the qualified verifier on this evidence. A meaningful regression distinguishes atom match, semantic verdict and publication behavior, using controlled semantic responses; a provider qualification would require a separate frozen protocol. C correctly avoids changing existing verifier behavior, but its headline “answer support checks only atoms” needs this correction.

### 3. Plan C's interruption design cannot meet its accounting promise

A `finally`/`BaseException` path cannot run after SIGKILL or power loss (C:68). Current `run_split` persists results only after `run_task` returns and resumes by completed `(task, arm)` keys (`evals/runner.py:721–746`); there is no durable scheduled/running distinction. This supports the inferred interruption gap, not a reproduced crash.

Persist the frozen schedule, attempt identity and `running` transition before invocation. On reopening, account for abandoned running slots as unresolved/interrupted, retain their prior identity, and require an explicit new attempt for any allowed rerun. Atomic writes, ownership and schedule/source binding belong in acceptance. Separate execution status from contamination eligibility: contamination can coexist with a completed or interrupted run and its incurred cost (`evals/adjudication.py`). Do not make it erase the execution record.

### 4. Cost correction must span producers, readers and comparisons

Claude correctly identifies missing-to-zero coercion (`evals/paired.py:47–56`) and zero displayed for cost per verified pass when the denominator is zero (`evals/report.py:157–160`). Merely making two dataclass fields nullable leaves arithmetic and formatting broken (`report.py:71–73,101,148,204`). Producers already default absent usage to zero; Jev's counter logs missing tokens but retains an understated total (`evals/runner.py:242–250,619–630`).

Represent known zero, known estimate and unavailable measurement distinctly, with measurement basis. Propagate unavailable components to an unavailable total; optionally report a labeled known subtotal and coverage. Pair only tasks with comparable known measurements for each field, disclose exclusions and repeat counts, and predeclare handling of partially measured repeats. Zero verified passes means an undefined ratio, even with known zero spend. Preserve old source rows and version readers; do not infer that every historical zero is missing.

### 5. Original Plan 3 is narrower and more defensible than its critique allows

Its deterministic artifact slice is real: bounded reads, mutation detection and digest-bound equality exist (`python/jevdual/artifacts.py:19–67`). They establish current bytes, not authorship. The critique usefully identifies existing `Effect`, carry oracles and packaging seams, but incorrectly treats a light core with optional heavyweight capture adapters as inherently contradictory. Original Plan 3 explicitly allows optional adapters (03:25,41).

Today's history adapter requires Footwork's qualified journal; arbitrary imported prose must not certify execution (`capability/completion.py:86–128,205–224`). That implementation limit does not establish C's universal rule that every supplied event is forever unsupported. Trust must name the authenticated/qualified producer and permitted predicate. A future imported execution receipt would require its own qualification, not a provenance-label shortcut. Reading a file “directly” likewise does not authenticate who wrote it.

C's record also loses operation disposition and lacks explicit evidence/attempt references. `partial` is not universally `refuted`: it may support a partial-effect predicate while refuting exact completion. Preserve raw disposition, predicate parameters, producer/check versions, resource incarnation, observation interval, evidence references and limits. Legacy `Effect` records cannot acquire unknown identity or timestamps through `to_record()`. Keep legacy prose readable and visibly limited; the producer truncates values at 80 characters (`session.py:343–351`).

### 6. Plan 5's strongest contribution is discriminatory evidence, not another lab

Recount validates accounting/integrity, not ground-truth labels. It remains useful but should not be sold as independent grading. Schema compatibility alone permits an adapter to invent success. Claude's independent-effect oracle and mutant suite improve this substantially, but C's fixed diagonal confusion matrix and twenty identical repeats are arbitrary. A defect can appropriately trigger several checks.

Instrument dispatch count independently: duplicate final text catches some retries, not an illicit retry whose first send had no effect. Assert no dispatch on stale observation, independent final content for false success, retained slot accounting after process death, and owned-resource cleanup. Include a positive reference and valid variants; report which defect classes the suite actually distinguishes. Same-author mutants provide no independent-adapter qualification.

C's regrade proposal needs exact scorer/task/checkpoint versions, all grading inputs, eligibility and error/pause/judge policy—not only four `EndState` fields (`evals/runner.py:254–269,326–335`). Redaction can change predicates; bind public redacted bytes separately from private original identity. Missing private evidence means unavailable regrading. Never promise rescoring heldouts or run C's “every committed results directory” survey: use new development fixtures and explicitly permitted development packets only.

### 7. Extraction and publication are premature integration dependencies

The existing builder copies all dependencies; its `--no-deps` install checks isolated imports, not a dependency-free resolving install (`scripts/build_capability_wheel.py:36–78`; `scripts/capability_package_check.py:81–102`). Claude's negative dependency-injection gate is useful. Its two distributions sharing the same installed package files are not a sound long-term ownership contract: upgrades/uninstalls can remove another distribution's files. Choose one owner distribution with an explicit dependency, or defer extraction entirely. Identical source bytes do not solve package ownership.

Reuse `scripts/verify_onboarding_packet.py:12–58` for manifest integrity; keep its current single-wheel assumption explicit. Demand should precede wheel and public-adapter work, not follow five implementation milestones.

## Contributions to the one final plan

1. Producer-backed typed evidence, with legacy compatibility, immutable source kinds and explicit derivation/resolution links.
2. Independent expected-content checks plus mutants that falsify actual behavioral guarantees.
3. Durable evaluation slot accounting and cost coverage, retaining known zero and undefined ratios correctly.
4. Versioned development packets that distinguish integrity, recount, regrading and new execution; missing evidence remains visible.

**Minimum integration order:** first reproduce the operation/save defects under committed notebook predictions; repair authoritative producers and preserve compatibility. Next agree the smallest shared evidence envelope using those real producers, then add positive/negative CLI scenarios for truthful reporting and recovery. Land nullable measurement propagation as a bounded producer-to-report change. Add durable slot transitions only when the next development experiment needs them. Finally package one new development run with retained oracle inputs and independent checks. SDK extraction requires a named integrator and an explicit packaging decision.

**Meaningful acceptance:** cancellation and process-kill tests must distinguish no-send, unresolved-send and qualified recovery; matching external text cannot resolve an event, but a bound retained receipt can. Verify typed and legacy evidence separately, narrative versus atom versus semantic verdict, positive/partial/zero/missing costs, no verified-pass denominator, repeated observations, changed destinations and packet tampering. Preserve historical files and heldout discipline. Exclude a new lab CLI, semantic-backend replacement, universal certification, public release and independent-reproduction claims from this implementation scope.

## Addendum: broaden qualification beyond TextEdit

The subsequent user requirement makes application diversity an implementation constraint. TextEdit stays regression-only. Qualify a small, deliberately heterogeneous development portfolio; do not average its outcomes into “general computer use.” Existing Calculator simulation (`tests/fixtures/native_world.py`, `tests/test_session_scenarios.py`) supplies a reusable starting point, not installed-app evidence. Browser task rules already distinguish observed-state predicates, live sites and judge grades (`evals/tasks/README.md`). Add fresh development cases; do not repurpose sealed fixtures.

Freeze six development rows, each with a nominal case and the assigned challenge below. App availability and version are prerequisites to inspect before implementation; Pages is a proposed target, not an asserted installation. If unavailable, explicitly freeze one installed rich-document editor as its replacement before running, and disclose the narrower scope.

| Row / target | Distinct semantics and oracle | Assigned challenge |
|---|---|---|
| N1 Calculator | Transient arithmetic; independently compute expected numeric output and compare a separately captured display. No persistence claim. | Stale control/observation: zero dispatch when identity is invalid. |
| N2 Finder | Rename/move one owned fixture file within a temporary directory; independent filesystem inventory, exact destination bytes and absence of an unintended duplicate. | Replace the bound directory/resource at the same path; refuse or require fresh binding. |
| N3 Preview | Navigate an owned multi-page PDF and identify a specified page/value; fixture digest and separately observed page identity establish the bounded answer. | Two similar document windows; focus swap must not silently retarget. |
| N4 Pages, subject to prerequisite check | Edit and save an owned rich document; expected content checked through an independent format parser/export oracle and reopening the document. Unsupported format coverage is a gap. | App exit/restart and unsaved-versus-saved distinction; ambiguous dispatch must not cause another edit. |
| B1 Local browser form application | Authorized form submission; independent server-side effect count and payload, with an unauthorized control case. | Tab/origin navigation invalidates approval/target binding; uncertain submission is not retried. |
| B2 Local browser editor application | Editable content in a DOM unlike the form; exact persisted server/store value after reload, independently read. | Browser restart or disconnected session; truthful persistence claim and explicit rebind. |

Each row gets one specific nominal effect predicate, one identity/resource scope, and explicit permitted/refused behavior. A row fails qualification on any wrong target, unauthorized dispatch, duplicate effect, false completion or missing attempt; unsupported capability is reported as unavailable, not hidden by successful rows. Clean refusal proves that refusal boundary only, not task completion. Do not choose an arbitrary percentage or repeat count. Add repeats only when the registered question concerns variability; retain every attempt.

Keep three evidence tiers separate. **Offline/static and simulated:** model each assigned failure, plus permission denial, hard kill, torn-write recovery and missing measurement at shared seams. **Installed-app:** execute the fixed rows through the installed CLI from outside the checkout, record actual app/OS/driver versions, and use owned inputs and independent observations. Do not change global permissions merely to manufacture denial; qualify that on a separately authorized disposable environment. **Real user task:** after these gates, preregister two distinct useful tasks—one native and one browser/cross-surface—selected with the user, with explicit effects, independent final checks and recorded interventions. Fixture success does not establish user value or live-site reliability.

Use an axis coverage table rather than a Cartesian product. Each risk has a designated witness row; shared lifecycle/permission cases run at the shared seam. All six rows use the CLI entry point; an additional representative native row and browser row through the chosen external host establish transport parity without rerunning every app through every host. Defer untested axes explicitly. This diversifies both applications and usage context while keeping failures attributable.
