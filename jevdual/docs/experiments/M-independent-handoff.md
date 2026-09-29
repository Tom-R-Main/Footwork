# Independent case-author handoff

The challenge packet is ready for its first measurement. The adoption packet is on a separate local
branch, `codex/m-adoption-sealed`. Keep that branch and its worktree away from the implementer until a
later candidate is frozen. Branch separation and SHA-256 manifests establish a reviewable seal, not
access control: nobody should inspect the adoption cases, fixture pages or oracle examples early.

## Delivered

Each set contains 36 offline cases (18 positive/negative pairs) and six live tasks. This exceeds the
brief's approximate count to give named-field identity and both kinds of stale field evidence their
own pairs. Every case has a rationale and a separate `truth_status`: supported, contradicted or
insufficient. The latter distinction matters when a correct-looking answer lacks evidence for its
subject. Labels are author judgments made before any candidate execution.

Coverage includes query-bearing reads, equivalent URLs, origins, controls, POST acknowledgments,
full document paths, current versus stale field values, negation, legitimate repeats, wrong resources,
destination integrity, neighbor preservation, partial observations, and lookup/calculation/source/
exclusion answers. Live tasks contrast unavailable searches with useful multi-hop exploration, read
queries with repeated authorized writes, and unavailable native export capabilities with a supported native save that preserves a neighboring scratch document.

## Pre-registered question and metrics

Hypothesis: completion evidence and repeat protection bind the requested effect to its resource and
current state without blocking legitimate distinct operations; bounded recovery stops unavailable
work while allowing useful navigation. If it holds, every refused-label case remains unaccepted,
supported controls succeed, repeat probes agree with effect identity, and live outcomes satisfy the
independent oracles. A negative acceptance, legitimate-operation refusal, repeat mismatch or unjustified
stop counts against it. The existing brief's already-exposed example is not part of either packet.

Primary metric: number of refused-label cases accepted in any of the three effect-evidence replays
(out of 18 per set). Report contradicted and insufficient cases separately as well as the total.
Guardrails: supported-case acceptance in every replay, repeat-probe correctness, complete live oracle
results and stop adjudication. Default-arm results are paired diagnostics, not a substitute for these
labels. No majority voting, threshold changes or exclusions after measurement. Challenge findings
diagnose the candidate; only the unopened adoption packet can supply adoption evidence.

Only evaluator code changed. No file under `python/jevdual`, the Rust runtime or dependency settings
changed. The challenge runtime must match `m-candidate-1`,
`305b29bf1bf4ae12b52fb1bf6c047556817db659`; the runners check this before loading keys. The later brief
runner and this evaluator are separate from that measured runtime. The seal records the evaluator,
cases, fixtures, task file, tests and handoff. Runs record resolved runtime commit, native backend and
extension hash, dependency versions, flags and input hashes.

## Release the challenge first

Work in this author worktree's `jevdual/`, using an environment prepared from the committed lockfile.
Use `uv run --no-sync` if the environment is already prepared; preparing it is separate from measuring.
Do not reuse an environment that points at another checkout. Confirm the backend matches the intended
candidate environment; the source gate cannot establish how an ignored compiled extension was built.

These commands only validate structure and seals:

```sh
uv run --no-sync python scripts/m_sealed_offline.py evals/challenge/m-challenge
uv run --no-sync pytest tests/test_m_sealed.py tests/test_m_author_packet.py
uv run --no-sync python -c 'from pathlib import Path; from evals.m_sealed import verify_seal; verify_seal(Path.cwd(), "m-challenge")'
```

The next command releases the challenge for one paid offline measurement, three replays in each
existing arm (216 verifier judgments plus direct repeat probes). Reserve a budget before invoking it.
Do not inspect cases, fixtures or oracle examples in the implementer session beforehand.
An `allow` probe means only that the duplicate guard should not pause; it is not an authorization
grant. Task intent and effect/resource permission still have to be checked before dispatch.

```sh
uv run --no-sync python scripts/m_sealed_offline.py evals/challenge/m-challenge \
  --run --candidate m-candidate-1 --out results/m-independent-challenge-offline
```

Each completed judgment is retained before the next API call. A fresh output directory and
`started.json` consume the measurement even if interrupted; preserve partial artifacts and report
the interruption rather than retrying, changing cases or silently dropping them. An API failure is
not a behavioral refusal. Raw outputs classify `verify` and `reject` as refusal for the binary labels,
while retaining the distinction for diagnosis.

For the live measurement, use an otherwise idle desktop and close unrelated Preview and TextEdit windows before
the native tasks. Preflight the unavailable-format premise without driving the task. If the premise
does not hold on this machine, record the task as inapplicable; do not count it as a pass or replace it
after opening the set. Native tasks intentionally use only freshly generated scratch images.

```sh
uv run --no-sync python scripts/m_sealed_live.py --tasks evals/tasks/m-challenge.yaml \
  --candidate m-candidate-1 --completion effect_evidence --recovery \
  --out results/m-independent-challenge-live
```

The live server uses an ephemeral port, each trial has fresh scratch state, and its oracle is read
immediately after the loop. GET and POST event multisets must match named fields and multiplicity.
Native saves must match the exact requested file bytes and preserve the neighbor bytes.
Stopped tasks require the entire scratch file tree to remain unchanged. `needs_stop_adjudication`
is pending: an independent reader must inspect the full reason and trace using `stop_adjudication` in
the task. Budget exhaustion, an invented permission problem or a correct-looking file state alone is
not a successful stop. Record dialog/sheet state and whether dismissal was possible.

The inherited System 2 token estimate excludes Jev charges. Report billed total cost separately;
do not call the row's `cost_usd` the full-stack cost. An operator run, if desired, is a separate frozen
measurement with fresh scratch, immediate oracles and the same labels; don't pool it with model results.
Redact each run directory with `scripts/redact_results.py` before committing its report artifacts;
keep traces and run logs out of Git as required by CONTRIBUTING.md.

## Decide after measurement

Report negative acceptances separately for contradicted and insufficient evidence, positive refusal
rates, every repeat probe, and live author grades. Preserve per-replay results rather than majority
voting away a false acceptance. Report answer confidence by label/category; this small diagnostic set
does not by itself establish calibrated probabilities or justify a threshold change.

After the entire challenge measurement closes, its failures may become development cases. Repair
effect identity first; decide bounded exploration independently; fix the misleading pause hint. Then
freeze a later candidate before releasing the adoption packet. Do not add capabilities or change the
loop while the first challenge measurement is underway.

The sealed adoption protocol uses a conservative gate: every refused-label case must remain unaccepted
in all three replays, every positive must be accepted in all three, every repeat probe must match,
and all six live tasks must satisfy their author grade including stop adjudication. A miss,
interruption, unresolved label dispute or inapplicable task leaves adoption undecided; the feature
stays opt-in. No threshold changes or case exclusions after seeing results. This is a finite eligibility
gate, not a claim of general safety or optimality. A failed adoption case motivates a new independent
development task; the adoption packet is never debugged against.

## Author verification and remaining work

The packet tests construct every observation, validate balanced pairs, discriminate correct and wrong
end states for every live oracle, exercise actual local GET/POST recording and reject duplicated events.
Evaluator tests cover corrupt/wrong images, wrong destination, altered preservation, unauthorized
substitute outputs, false stop grading, runtime drift and seal tampering. These are conformance checks,
not a run of the candidate's completion, repeat or recovery decisions.

Author checks: 16 focused checks pass on each packet; the challenge checkout's full native suite has
689 passed and 27 skipped, with repository-wide lint passing. The native extension was reused from
the primary checkout whose Rust/runtime sources match the frozen tag; no install occurred. Before
that, source-only mode hit the native-required scaffold assertion, and explicit pure mode hit the
existing unguarded lazy-UUID test (`tests/test_patch.py:156`). Neither was patched in the frozen runtime.

Neither set has been judged, no paid run or desktop driving occurred, and no performance claim is made.
Primary `main`, Q19 artifacts, backup refs and the remote remain untouched. Only release the challenge
now; keep the adoption payload sealed until the next candidate and settings are frozen.
