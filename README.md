# Footwork

**A verified browser agent.** Footwork puts a cheap, calibrated guard from
[TypeSafe Jev](https://docs.typesafe.ai) in front of any LLM browser driver: every claimed completion is
checked against page evidence and the trajectory before it counts, and every irreversible action passes a
gate. On top of that guard, Jev can also take the fast, mechanical steps itself (System 1) while the LLM
(System 2) keeps the reading, comparing and deciding. Built on
[browser-use](https://github.com/browser-use/browser-use) 0.13.10 as a library, not a fork.

The Python package is `jevdual` (in [`jevdual/`](jevdual/)); Footwork is the project. Every number below is
from a run directory under [`jevdual/results/`](jevdual/results/), and every experiment was pre-registered in
[`jevdual/docs/experiments/`](jevdual/docs/experiments/) before it ran.

## What it does, measured

Three arms are compared on the same tasks: **stock** browser-use with the LLM alone, **guarded** (the LLM behind
Jev verification and the gate, no Jev actions), and **dual** (the guard plus Jev taking the mechanical steps).
System 2 in every run is Muse Spark 1.3 Contributor over the Meta Model API, chosen because it is cheap and
fast and therefore the hardest baseline for Jev to beat on cost.

**Fixture heldout**, 10 local tasks, frozen settings, rerun once when the verifier changed
([`results/heldout-adopt.md`](jevdual/results/heldout-adopt.md)):

| arm | pass | false completions | driver steps | Jev calls | est. cost USD | wall s |
|---|---|---|---|---|---|---|
| stock | 9/10 | 1 (deleted an account when told to reach the page) | 33 | 0 | 0.049 | 708 |
| dual | 10/10 | 0 (paused before the click) | 24 | 76 | 0.049 | 522 |

**Live sites**, 55 tasks on Wikipedia, MDN, docs.python.org, arXiv, GitHub, PyPI and three practice sites,
three same-code runs ([`results/q9-live-dev.md`](jevdual/results/q9-live-dev.md),
[`results/q9b-coherent.md`](jevdual/results/q9b-coherent.md)):

| arm | pass | false completions | driver steps | Jev calls | est. cost USD | cost per verified pass |
|---|---|---|---|---|---|---|
| guarded | 50 to 52 / 55 | 0 | 226 to 260 | 80 to 84 | 0.385 to 0.412 | 0.0086 to 0.0100 |
| dual | 51 to 52 / 55 | 0 | 161 to 193 | 360 to 391 | 0.449 to 0.492 | 0.0100 to 0.0117 |
| stock (one run) | 51 / 55 | 1 (its own LLM judge accepted it) | 265 | 0 | 0.382 | |

What that says, in order of how sure we are:

- **The guard is the product.** Zero false completions on every split and run, on these predicates, at
  about two Jev calls per task, and at the LLM's own cost. The LLM alone deletes the account when asked to
  reach a page, and its own judge marks that a success.
- **Jev acting saves driver work, not money yet.** Dual makes 23 to 29% fewer driver requests than the
  guarded arm across two same-night samples and runs its own steps at a median 1.4 s against 15.7 s for an
  LLM step, but pays for that in Jev volume; task wall time between the arms is not distinguishable on
  live sites, and dual matches stock's cost only on the fixture heldout so far.
- **System 2 delegating bounded subgoals to Jev did not pay** in three measurements
  ([`Q9`](jevdual/docs/experiments/Q9.md)): more cost, no more completions. The executor reached 5 of 30
  assignments; an audit then found software defects behind most of those failures, fixed in the tree and
  not yet re-measured. Delegation stays available as a tool, off by default.

## How it works

```
                 task ─────────────────────────────────────────────┐
                                                                   ▼
   ┌──────────── System 2: the LLM driver (browser-use loop) ────────────────┐
   │  reads, compares, decides, composes; may call delegate_subgoal /        │
   │  find_evidence; proposes actions and eventually `done`                  │
   └──────────────────────────────┬──────────────────────────────────────────┘
                                  │ every action, either system
                                  ▼
   ┌──────────── the guard (code + Jev nouls, ~1 call per check) ────────────┐
   │  destructive gate: pause before delete / pay / send unless the task     │
   │  authorises that action;  done verification: `complete` + one          │
   │  `unmet` noul per requirement, judged on the page AND the trajectory,   │
   │  claims graded against evidence atoms, a per-run ledger by kind         │
   └──────────────────────────────┬──────────────────────────────────────────┘
                                  │ optional: dual mode
                                  ▼
   ┌──────────── System 1: Jev (one speculative fan-out per step) ───────────┐
   │  Choice: operation  ·  Choice: target (conditional per operation)       │
   │  Nouls: goal_done · stuck · needs_reasoning · destructive · login ·     │
   │  bot_check;  a code-owned arbiter (arbiter.toml) acts, escalates,       │
   │  retries the next-best target, or asks for confirmation                 │
   └─────────────────────────────────────────────────────────────────────────┘
```

- **Verification** ([`verify.py`](jevdual/python/jevdual/verify.py), [`ledger.py`](jevdual/python/jevdual/ledger.py)):
  a done is accepted only when the `complete` noul and every requirement's `unmet` noul are inside the
  accept band; answers must quote evidence atoms found on the full page text; requirements that name an
  action are judged from the trajectory once the page has moved on; a requirement judged met stays met
  unless it is a current-state requirement and the page later contradicts it.
- **Gate** ([`agent.py`](jevdual/python/jevdual/agent.py)): keyword and noul rules on the target, the URL,
  the focused element for Enter, and `evaluate`; scoped by the task's `authorized_actions`.
- **Arbiter** ([`arbiter.py`](jevdual/python/jevdual/arbiter.py), [`arbiter.toml`](jevdual/python/jevdual/arbiter.toml)):
  confidence floors, noul thresholds, streak and no-effect rules. Every threshold is a starting point
  recorded in the file; none has been tuned on heldout data.
- **Rust** ([`crates/jevdual-core`](jevdual/crates/jevdual-core)): paint-order occlusion, snapshot lookup,
  element hashes and evidence matching as PyO3 ports with pure-Python twins and equality tests. Honest
  note: the DOM pipeline is not the bottleneck; Jev and the driver are.

## The eval rig

- `evals/`: arms `stock`, `s1_only`, `dual`, `guarded`, `delegate`, `delegate_evidence`; predicates on observed
  state (URL, page text, returned answer, URL checkpoints for multistep tasks), never on the agent's claim;
  browser-use's own LLM judge recorded per row as a comparison, never as the grade.
- Task sets: a local fixture site (`dev`, `heldout`), 55 live dev tasks and 24 live heldout tasks, and 42
  judge-graded tasks imported from browser-use's agent tasks and Mind2Web. Heldout splits are never debugged.
- Method: pre-registered questions with predictions and decision rules, paired bootstrap intervals over
  tasks (`evals/paired.py`), results written after every task run, resumable, secrets redacted.
- browser-use's own CI modules run against this package with the patches active
  (`scripts/upstream_tests.sh`); one of them caught a real bug in the paint-order port.

## Quick start

```sh
git clone --recurse-submodules https://github.com/Tom-R-Main/Footwork.git
cd Footwork/jevdual
uv sync                        # builds the PyO3 crate; Rust 1.95 via rust-toolchain.toml
uv run pytest                  # unit and equality tests, no keys needed
```

To run the agent or the evals you need a TypeSafe key (`TYPESAFE_API_KEY`) and a System 2 key
(`MODEL_API_KEY` for the Meta Model API, or wire another provider in `evals/runner.py`):

```sh
uv run python -m evals.runner --split dev --arm stock --arm guarded --arm dual --llm meta
uv run python -m evals.runner --split live-dev --arm guarded --llm meta --task lw-python-creator
uv run python -m evals.paired results/<before> results/<after> --arm dual
```

Use the guard alone with any browser-use agent by constructing `DualProcessAgent` with an `ArbiterHook`
verifier and no S1 policy; see `evals/runner.py` (`guarded` arm) for the exact wiring.

## Repository map

| path | what |
|---|---|
| [`jevdual/python/jevdual/`](jevdual/python/jevdual/) | the package: agent, policy, menu, arbiter, verify, ledger, secrets, tools, evidence, patch |
| [`jevdual/crates/jevdual-core/`](jevdual/crates/jevdual-core/) | Rust hot paths (PyO3) with pure twins under `python/jevdual/_pure/` |
| [`jevdual/evals/`](jevdual/evals/) | runner, predicates, report, metrics, paired comparison, task files, fixture site |
| [`jevdual/results/`](jevdual/results/) | every run directory and its write-up; the README's numbers come from here |
| [`jevdual/docs/experiments/`](jevdual/docs/experiments/) | pre-registered questions Q1 to Q9 with results and decisions |
| [`jevdual/docs/`](jevdual/docs/) | design notes, the Rust boundary rule, upstream reuse inventory |
| [`browser-use/`](browser-use/) | upstream pinned as a submodule at the studied commit; the package imports the PyPI release |

## Status

Research code with a working product core. The guard and the reactive dual loop are measured and
documented; delegation and evidence selection are experimental; calibration of the thresholds from human
labels is the next open question ([`Q1`](jevdual/docs/experiments/Q1.md)). Read
[`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a change.

## Credits

Ideas were taken from six MIT-licensed sibling projects (jev-ultrafast, fastbrowse, jev-browser,
jev-for-chrome, public-browser) and, ideas only, from browserclaw (AGPL); browser-use's test fixtures and
judge are reused under MIT ([`docs/upstream-reuse.md`](jevdual/docs/upstream-reuse.md)). MIT license.
