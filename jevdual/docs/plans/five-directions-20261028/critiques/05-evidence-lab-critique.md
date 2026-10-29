# Critique: Plan 5, reproducible evidence lab

Reviewed October 28, 2026 against `5d494c6`. Paths are relative to `jevdual/` unless they start with `../`. The only thing I ran was a read-only recount script, kept in a scratchpad. No app, model or provider was touched.

**Verdict.** The thesis is sound and the stop rules are honest. But the plan proposes as new a lab whose parts mostly exist already. It ignores the one independent reproduction the repo has attempted, and its two headline acceptance tests (recount, conformance) would pass for a broken system.

## 1. Factual claims

Claims that hold: the arms (`evals/runner.py:40-69`, ablations `:81`); missing fields and cost read as 0 (`evals/paired.py:20-21,47,56`); Q19 contamination and rerun (`results/q19-heldout.md:72-80`); VQ1 frozen schedule and grouped scoring (`results/vq1-local-20261008/report.md:5-7`); recovery scope (`results/reusable-body-recovery-20261012/report.md:35`); CI is deterministic and simulation only (`../.github/workflows/ci.yml:44-70`).

Claims that are imprecise or overstated:
- The judge-graded distinction is at `evals/tasks/README.md:46-52`, not `:13`.
- Calling the browser runner an adapter whose "scripted control" needs no paid model hides a detail: the scripted arm runs only programmatically (`evals/runner.py:806-807`), and its trace header records it as `s1_only` (`:356`). That is the very labelling ambiguity the lab says it will remove.
- **The biggest problem is omission.** The proposed `evals/lab/` modules duplicate existing code:
  - `scripts/verify_onboarding_packet.py:12-40`: manifest with source commit and member hashes; rejects changed or escaping members.
  - `evals/visual_qualification/runner.py:180,339`: `freeze` and `score_run`; VQ1 already publishes `recount/summary.json`.
  - `evals/adjudication.py:1-29`: eligibility (contaminated, superseded) apart from outcomes (`unsupported_claim`, `truthful_stop`), which is milestone 4's labelling scheme.
  - Attempt ledgers (`results/bench-operator-20261011/attempt-ledger.json`), SIM9's 12-case fault matrix (`docs/experiments/SIM9-network-body-adapter.md:11`), seal-tampering checks (`docs/experiments/M-independent-handoff.md:124-128`).
- Milestone 1 should consolidate this code, not start a parallel tree.

## 2. Research value

**Deterministic recount buys almost nothing as specified.** I recomputed `aggregate()` over every committed `results.json` and compared it with its `summary.json`. 70 of 73 TaskResult-shaped directories matched exactly on tasks, pass, verified_pass, false_done, llm_requests and cost. The other 3 (d2/d3/d4) use a different schema. The match is expected: the summary comes from the same function over the same rows (`evals/report.py:209-214`). So recount checks arithmetic, not grading.

The grading itself cannot be redone from what is retained. Predicates read `page_text` and `visited_urls` (`evals/predicates.py:11-17`), but `TaskResult` does not store them (`evals/report.py:12-72`), and traces are git-ignored (`.gitignore:16,18`; `../CONTRIBUTING.md:45`). The valuable property is **regrade**, which means re-applying the oracle to the retained observations. That requires changing what gets retained, and that change runs straight into redaction (§3).

**Live reproduction is resampling, not reproduction.** Hosted models (Jev, Muse) cannot be pinned to weights, GUI start state is the known failure mode (Q19 H09), and Q19 has ten tasks run once each (`results/q19-heldout.md:1`). The plan never says what discrepancy counts as "failed to reproduce", so milestone 5 cannot fail. The reproducible tier is VQ1's frozen-observation replay, which isolates model judgment from GUI nondeterminism. Make it central, not a label (plan line 47).

**Conformance is not discriminatory.** Milestone 3's acceptance is "same task contract, same result schema" (plan line 41). An adapter that reports success without producing the effect would pass that. The packet README's promise to "discover a broken adapter" (`docs/plans/five-directions-20261028/README.md:25`) is not met.

## 3. Feasibility and sequencing

- **Redaction is a hidden blocker for `pack`.** `scripts/redact_results.py:57-62` only rewrites exact secret values in `.json`, `.jsonl`, `.md` and `run.log`. In the 2,787 committed result files (270 MB), it never touches 211 `.txt`, 97 `.html`, 262 `.png`, 56 `.pdf` or 12 `.csv` files. Image and PDF evidence needs human review or exclusion before any share policy can be honest.
- **Milestone 2 picks the easy family.** The browser fixture server starts fresh every time (`evals/fixtures/server.py:108-117`), so "explicit start-state reset" there is free. The hard reset problem is native, and evidence from the browser family does not carry over.
- **Milestone 3 needs an external party.** It requires "one independently implemented adapter" but names no author. If Footwork's own agents write it, it is not independent: the VQ1 report notes "same inherited model … not model diversity" (`results/vq1-local-20261008/report.md:15`).
- **The plan ignores U2.** A fresh SIP-enabled guest already failed first use (grant actor uncaptured, Chrome verification failed, cleanup unconfirmed; `docs/experiments/U2-independent-onboarding.md:31`), so the "first external reproduction" (line 45) has happened. A same-host "second checkout" is explicitly not first-use evidence (`U2:5`).
- **Milestone 4 overlaps Plan 1.** "Stable attempt identity" is Plan 1's operation journal. Picking Plan 5 alone leaves that dependency unowned.

## 4. Acceptance criteria

These are testable: rejecting changed members, complete slot accounting, keeping labels distinct.

These are unfalsifiable or trivially met:
- "exact deterministic recount" (already true, per §2)
- "without source coaching" (not defined or logged)
- "a declared live or simulated development trial" (no pass margin)
- "independence is described accurately"

## 5. Risks and blind spots

- Publishing task corpora to a provider that trains on prompts (the Muse contributor tier) contaminates future held-out sets. Sealing needs a rule for which providers may see a sealed case.
- Demand is called a hypothesis (line 5), but nothing tests it before milestone 3. Find two outside adapter builders first.
- Opportunity cost: the recorded product decision is the capability-system direction (`README.md:5`). This plan changes the audience before showing that anyone outside the project would use the lab.

## 6. Strongest ideas to keep

1. **Slot-state accounting:** every scheduled slot ends as exactly one of completed, refused, failed, contaminated, interrupted or not_run. An unknown cost or observation stays `null`, never 0. Fix `paired.py:56` first.
2. **A mutant-adapter conformance suite.** It replaces schema conformance. The reference adapter must pass, and each of these broken adapters must fail:
   - claims success with no effect
   - retries an uncertain GUI operation automatically
   - acts on a stale observation
   - skips owned teardown
   - silently drops a slot
   - writes `0` for an unknown cost

   Use the SIM9 matrix as the template.
3. **An evidence packet manifest** built by extending `verify_onboarding_packet.py`. It records the source commit, member SHA-256 hashes, a member `unavailable` list with the reason for each, and an evidence tier per row (live, native, simulation, mock, replay). The verifier rejects tampered or extra members.
4. **A regrade tier:** retain each oracle's input (redacted observation plus digest) so the label can be recomputed, not just the summary.
5. **The stop rules** (plan line 53), and the fallback of an offline audit/regrade utility.

## 7. Weakest ideas to drop

- A separate `footwork-lab` CLI and a parallel `evals/lab/` tree.
- Recount of summaries as an acceptance criterion.
- Milestone 5's "independent reproduction release" until there is a named reproducer and a discrepancy margin.
- A browser-only portable pack presented as portability evidence.
