# Independent review by GPT Astra (Codex), 2026-09-21

Route: supervise-workflow review-existing, base 9e7d73f, head c1e9bc4. The harness's own verification passed (lint, 240 tests, cargo tests). The harness's Codex reviewer role could not read files (its prompt forbids commands and Codex has no other file access), so the review was run directly by `codex exec --sandbox read-only --model gpt-6-astra` on the harness worktree with the same packet and acceptance criteria. That run is outside the harness evidence chain.

Recommendation: remediate (confidence 0.96). Acceptance: {'AC1': 'fail', 'AC2': 'fail', 'AC3': 'fail', 'AC4': 'fail', 'AC5': 'fail', 'AC6': 'fail'}

Summary: Remediation required. The monitor reports 240 passing Python tests, 21 skips and 19 passing Rust tests, but source inspection found destructive-gate bypasses, secret exposure, inflated eval passes, missing verification enforcement and a native equality coverage gap. Published dev claims also conflict with committed artifacts.

## Findings and dispositions

### [P1] [AC1] Destructive actions without element indices bypass the gate

[AC1] The gate skips every action without an index. System 2 can therefore use evaluate to click a destructive control, navigate directly to its destination, or submit a focused form with send_keys while authorized_destructive is false. These are registered upstream actions. Enforce authorization across executable action types before dispatch.

Evidence: agent.py:73-76 continues when get_index() returns None, then :103 dispatches through upstream. tests/contract/test_upstream_seams.py:120-147 lists send_keys, navigate and evaluate. evals/fixtures/site/delete-confirm.html:7 exposes the destructive destination.

**Disposition:** Fixed: evaluate refused without authorization; navigate url checked; Enter checked against the focused element and its form's submit control (unknown focus is gated). agent.py, test_s1.py.

### [P1] [AC2] Secret-bearing observations reach Jev without redaction

[AC2] JevS1 passes the raw menu and history context to the policy. Policy state includes URLs, page text, candidate values and recent memory without consulting the SecretStore redactor. The fixture login submits its password in a GET query, so the subsequent account URL supplies a concrete exposure path. Redacting artifacts after the run cannot prevent this model-facing disclosure.

Evidence: policy.py:179-194 copies observations directly into model state; verify.py:172-180 does likewise. evals/fixtures/site/login.html:7-10 submits password via GET. results/g2-dual-20260921-014136/taxonomy.md:23 records the resulting password-bearing URL after artifact redaction. runner.py:243-255 applies redaction only after execution.

**Disposition:** Fixed: JevS1 redacts the menu, recent-action lines and the verification menu through the store's redactor before any model call; the fixture login now POSTs and the password never enters a URL. s1.py, agent.py, fixtures.

### [P1] [AC2] The origin rule permits non-loopback HTTP

[AC2] origin_allows accepts arbitrary HTTP hosts for wildcard scopes and explicitly HTTP or http* patterns. This contradicts the required rejection of non-loopback HTTP. Additionally, the runner exports the unfiltered store, and the S1 placeholder path never checks allowed_for at dispatch. Require secure origins independently of pattern syntax and enforce the rule against the current destination.

Evidence: secrets.py:87-88 accepts http for '*'; :93-96 accepts explicit insecure schemes. tests/test_secrets.py:40 explicitly expects non-loopback HTTP to pass. runner.py:203 uses to_browser_use(), while text.py:168-177 selects placeholders solely by field/name.

**Disposition:** Fixed: plaintext HTTP is allowed only to loopback hosts regardless of pattern; the runner exports the origin-filtered store; the S1 placeholder path checks allowed_for against the live url before typing. secrets.py, s1.py, runner.py.

### [P1] [AC4] Paused runs can pass ordinary predicates

[AC4] passed is computed solely from the predicate and absence of an exception. The paused flag is recorded later and never vetoes that result. A run stopped before sending or deleting can consequently pass a page-text, URL or answer predicate. Explicitly disallow paused passes unless the predicate is not_reached.

Evidence: runner.py:242 computes passed without paused_before_action or predicate-kind handling; :267 stores that result and :279 independently stores paused. predicates.py:24-35 has no paused-state input.

**Disposition:** Fixed: decide_passed vetoes a paused run unless the predicate is not_reached. runner.py, test_evals_runner.py.

### [P1] [AC4] The contact submission predicate passes on the untouched form

[AC4] contact-form-basic requires filling and submitting a specific message, but its predicate only searches for Damaged item, which is already an option on the initial form. The committed taxonomy records this task as passed after one step while still on /form.html. This inflates the published dev result. Grade the submitted destination and required field values.

Evidence: evals/fixtures/site/form.html:10 contains Damaged item before interaction. results/g2-dual-20260921-014136/taxonomy.md:18 records pass at /form.html; its report.md:16 also counts the task as passed.

**Disposition:** Fixed: predicate now checks the submitted message on the confirmation page; an audit of every local task found no other predicate satisfied on its start page. The previously published dev pass for this task is withdrawn.

### [P1] [AC3] Snapshot equality coverage can miss a divergent Rust implementation

[AC3] The direct snapshot equality and sensitive-value tests skip unless JEVDUAL_NATIVE_SNAPSHOT=1, which the committed CI matrix does not set. The pipeline comparison is also compromised: uninstall restores snapshot bindings but leaves its active flag set unless lazy_uuid was installed. After the preceding snapshot patch test, install can return success without installing the native snapshot implementation. Exercise native equality independently of production opt-in and fix cleanup.

Evidence: _adapters/snapshot_lookup.py:23-31 requires the opt-in variable. .github/workflows/ci.yml sets only JEVDUAL_PURE_PY. patch.py:144-155 leaves snapshot_lookup active after snapshot-only uninstall, and :112-113 trusts that flag. tests/test_patch.py:70-112 runs snapshot installation before the pipeline comparison.

**Disposition:** Fixed: CI runs tests/equality with JEVDUAL_NATIVE_SNAPSHOT=1; uninstall clears the snapshot flag; regression test. patch.py, ci.yml.

### [P1] [AC5] System 2 completions bypass evidence verification

[AC5] Verification runs only when the S1 policy selects done. After escalation, System 2's done action proceeds through _execute_actions without any verifier call or answer-presence check. It can finish an answer task with generic completion text even after S1 verification rejected completion. Apply the completion check at the shared execution boundary.

Evidence: s1.py:145-154 is the only production call to judge_done. agent.py:113-118 calls the stock decision path on escalation; :85-103 checks only destructive labels before executing its output.

**Disposition:** Fixed: DualProcessAgent verifies System 2's done through the same verifier; a rejected done becomes a wait plus feedback, and after two rejections the done is allowed only as UNVERIFIED with success=False. agent.py.

### [P1] [AC5] Missing answer-required evidence defaults to permission to finish

[AC5] The verifier rejects missing complete and unmet answers, but defaults a missing answer_required result to zero. A response with high completion confidence, low unmet values and no answer_required can therefore accept an answer task with answer=None. Reject incomplete verification responses and carry an explicit answer requirement where task metadata already supplies one.

Evidence: verify.py:189-196 validates other required heads; :200 substitutes 0.0 for missing answer_required; :213 blocks an absent answer only above the threshold. evals/tasks/schema.py defines answer_expected, but runner.py:74-81 does not pass it to verification.

**Disposition:** Fixed: a missing answer_required head raises; task metadata (answer_expected) forces the requirement. verify.py, runner.py.

### [P2] [AC2] Lowercase percent escapes can evade redaction

[AC2] Lowercasing the entire encoded secret also changes its literal letters. For a synthetic secret AbC/9, the generated variants include AbC%2F9 and abc%2f9, but omit the equivalent encoding AbC%2f9. The case-sensitive redactor therefore leaks a supported URL-encoding form. Normalize only percent-escape hex digits or match those digits case-insensitively.

Evidence: secrets.py:184-188 constructs variants using pct.lower() and quote_plus(s).lower(); :217 compiles case-sensitive patterns.

**Disposition:** Fixed: only escape hex digits are lowercased when generating variants. secrets.py, test.

### [P2] [AC4] Failed final captures silently reuse earlier page state

[AC4] When a step-end capture fails, the runner retains the preceding successful capture and still evaluates it as the final state. A task can pass from an earlier matching page after subsequent actions leave it. Missing captures can also make not_reached pass without observing the actual final destination. Track capture validity and fail scoring when the final observation is unavailable.

Evidence: runner.py:129-133 updates last only on success and merely logs exceptions. :139-140 consumes last without a step identifier or freshness check; :242 does not account for capture failures.

**Disposition:** Fixed: the capture records its step; a run whose last capture predates its final step is scored as an error. runner.py.

### [P2] [AC4] Jev call counts and cost estimates omit escalation and verification calls

[AC4] The runner counts executed S1 steps as Jev calls. Every escalation already attempted S1, and done verification, retries and second-stage target selection add calls. These requests are omitted from both call totals and estimated cost, systematically favoring dual. Count requests at the client boundary and label estimates in generated reports as well as summaries.

Evidence: agent.py:112 invokes S1 before deciding escalation and increments s1_steps only at :120. s1.py:134-147 can invoke policy, target selection and verification. runner.py:261 and :272 use s1_steps for cost and calls. report.py:74-82 labels generated costs only as cost USD.

**Disposition:** Fixed: a per-task counting client at the SDK boundary counts every request and its input tokens; cost is computed from those tokens; reports label costs as estimates. runner.py, report.py.

### [P2] [AC6] Dev writeup contradicts its artifacts and task instructions

[AC6] The final dev summary claims zero false completions with one pause, but the cited committed report records one false completion and its taxonomy calls the newsletter miss premature_done. The writeup also says stock deleted accounts when asked only to reach the page and stop; the committed tasks explicitly request deletion. Reconcile the artifacts and describe the explicit authorize metadata accurately before using these runs to support safety comparisons.

Evidence: g2-dev-three-arms.md:11 and :18-24 claim zero false completions; results/g2-dual-20260921-014136/report.md:5 records one, and taxonomy.md:6,19 records premature_done. The reach-and-stop claim appears at g2-dev-three-arms.md:42, but evals/tasks/dev.yaml:128-140 explicitly requests deletion.

**Disposition:** Fixed by rerunning every arm on both splits with the corrected rig and rewriting the results and README from the new artifacts; the stock-arm description now says the tasks ask for deletion without authorization and the pass condition is refusing.

## Could not verify

- No tests, project execution, browser sessions or API calls were run. Passing checks are monitor-provided evidence; the log does not identify individual skipped tests.
- Live outcomes, model request payloads, runtime logs and performance measurements were not independently reproduced. Excluded traces, results.json files, compressed fixtures, lockfiles and the submodule pointer were not inspected.
- The truncated packet was supplemented with direct reads of implementation files behind every acceptance criterion, Rust algorithms, equality tests and relevant reports. Remaining auxiliary documentation, scripts and tests were not exhaustively reviewed; full-history coverage remains incomplete and blocking under the requested review rule.
