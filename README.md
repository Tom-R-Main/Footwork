# Footwork

[![ci](https://github.com/Tom-R-Main/Footwork/actions/workflows/ci.yml/badge.svg)](https://github.com/Tom-R-Main/Footwork/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.11%2B-blue) ![rust](https://img.shields.io/badge/rust-1.95-orange) ![license](https://img.shields.io/badge/license-MIT-green)

**A verified computer-use agent, for the browser and for native macOS apps.** Footwork puts a cheap,
calibrated guard from [TypeSafe Jev](https://docs.typesafe.ai) in front of whoever drives: every claimed
completion is checked against observed state and the trajectory before it counts, every irreversible action
passes a gate, and every action comes back with a receipt saying what visibly changed. On top of that guard,
Jev can also take the fast, mechanical steps itself (System 1) while the driver (System 2) keeps the
reading, comparing and deciding. The driver can be an LLM loop (browser-use 0.13.14 as a library, not a
fork) or the operator at the keyboard: a person, or an agent such as a Claude Code session, one command at a
time. Native apps are driven in the background through the [Cua Driver](https://github.com/trycua/cua)'s
accessibility tree, beside a person still using the same Mac.

The [Linux X11 port](jevdual/docs/linux-support.md) also supports the installed browser/desktop CLI,
scoped Mousepad MCP append and recovery, and Linux OCR. Its isolated runtime evidence is separate
from the macOS benchmarks below. Wayland, shared foreground control and physical cameras remain unqualified.

The Python package is `jevdual` (in [`jevdual/`](jevdual/)); Footwork is the project. Every number below is
from a run directory under [`jevdual/results/`](jevdual/results/), and every experiment was pre-registered in
[`jevdual/docs/experiments/`](jevdual/docs/experiments/) before it ran.

For an agent integration, start with [capability installation](jevdual/docs/capability-packaging.md)
and the [agent-host recipe](jevdual/docs/installed-agent-host.md).
CUA is built from the [pinned Python and Rust reference source](jevdual/docs/upstream/cua-driver-build.md); building its dependency wheel requires Rust 1.97.1 and native development tools. The wheel supplies five MCP tools
for one scoped browser-to-TextEdit job on macOS, with durable operation results and validated completion
reports. The Linux destination is Mousepad; see the platform guide for its narrower document contract.
It needs existing Python, Chrome and applicable host permissions. The bundle installer can use uv or pip.
The current candidate
does not discover arbitrary apps; its disposable fixture helpers derive the identifiers for that test job.

Optional [browser inspection utilities](tools/browser-inspection/README.md) collect redacted,
timestamped evidence through an existing tab/CDP adapter. They are dependency-free ESM helpers,
separate from the Python driver and verification gates. Their contract is tested offline; live
capture fidelity must be calibrated on the selected browser.

The optional [desk paper inbox](tools/desk-inbox-experiment/README.md) connects a saved
camera frame to local text recognition and a reviewed inbox note. Its private review keeps
the original image and OCR text. `footwork check-artifact` checks the saved note against
the approved source bytes without a model call; it does not judge recognition accuracy.

[Project-linked workbench records](tools/workbench-notes/README.md) attach reviewed evidence
to an explicit project, repository revision and proposed check. The optional
[MuJoCo workcell](tools/physical-workcell/README.md) explores a body interface with
physical-state feedback and a conditional computer work-order update. Simulation results
remain separate from real-camera and robot qualification.
Its [image-guided route](tools/physical-workcell/IMAGE_GUIDED.md) supplies calibrated RGB views
to an agent, accepts frame-bound proposals and requires fresh visual placement evidence before
the conditional local computer action.
The [repeatable episode interface](tools/physical-workcell/EPISODES.md) binds varied cases,
retains images when perception fails, and compares fresh-agent decisions with a deterministic
RGB controller. [SIM3 results](jevdual/results/repeatable-work-orders-20261010/report.md)
record all twelve attempted episodes and their limits.
The [independent controller](tools/physical-workcell/CONTROLLER.md) owns a simulated episode
in a separate process, with reconnectable operation status, cancellation evidence and
conservative receipt-based restart recovery.
[SIM4 results](jevdual/results/independent-controller-20261010/report.md) record disconnect,
cancellation and crash trials, retained failures and the boundary of supported recovery.

## One installed interface for agents

Use the [unified CLI installation guide](jevdual/docs/unified-cli.md) to build one host-specific bundle and install it into an isolated environment. `footwork tools` discovers commands, `footwork schema` describes their inputs, and `footwork --json …` returns a machine-readable result envelope. Browser and desktop groups share the existing session operations; camera, inbox, workbench, workcell and inspection utilities are carried in the wheel. Optional hardware, OS grants and browser-tab adapters remain explicit prerequisites.

## Drive it

```sh
footwork start "Compute 48 times 13" --app Calculator --require "The display shows 624"
footwork look                    # the menu of what can be done now, with ids, and the last receipt
footwork s1 --act                # System 1's proposal on this observation (one Jev call), dispatched
footwork do click 12             # through the gate; settle, reobserve, print the receipt
footwork done "624"              # the verifier judges the claim against the window and the trail
```

Also `do type | append | key | hotkey | menu | scroll | enter`, `status`, and `footwork run` for the whole
loop: by default the measured **guarded** arm (an LLM decides every step behind the guard), or `--arm dual`
for Jev as System 1 with the LLM on escalation. Nothing dispatches on an id from an older
observation; text comes from the task or from named secrets (`{NAME}` read from `$FOOTWORK_SECRET_NAME`,
never printed); `--authorize "<label>"` names the one change the operator approved. Sessions default to
`background_only`: the person's front app, pointer and keyboard are left alone (`--mode` grants more).
`start --browser` drives footwork's own Chrome profile through the Driver's DevTools route instead of the
accessibility tree. Needs macOS with Accessibility granted to the process that runs it, and a TypeSafe key.

For private visual inspection, use a numeric ID from the current native observation:

```sh
footwork inspect-target 12 --operation click --postcondition "The selected editor enters crop mode"
```

This records a fresh window PNG, target-bound manifest and static HTML preview under the session's
`inspection/` directory. The preview outlines the offered target over the unchanged original image
and displays the operation and required postcondition. It makes no model calls, executes no action
and does not verify the stated effect.
Sessions that have handled secrets withhold screenshots before capture. Missing or unqualified
capture geometry, truncated observations and changed target identities refuse inspection.
Native AX projections may be partial: the manifest records that limit, and label-based inspection
requires a complete observation. Browser inspection through this command is not yet qualified.

`footwork visual-check --request request.json --session SESSION` prepares one native advisory
document/reference or crop/subject check. It records the original capture and a structured receipt.
Explicit `--provider decisions --disclose` enables one bounded provider request using an existing
key; the default contacts no provider. Visual answers grant no action or completion authority.
See [visual check inputs, limits and escalation](jevdual/docs/visual-checks.md).

Measured this way on 2026-09-25 ([`docs/plans/legible-harness.md`](jevdual/docs/plans/legible-harness.md)):
Calculator 48 × 13 in 30 s (System 1 proposed every step at p ≥ 0.94, verifier accept 0.98); TextEdit
append-and-save in 9 s, the save confirmed by the window title losing its edited mark.

## What it does, measured

### The browser

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

- **The guard is the product.** Zero false completions on the guarded arm on every split and run, on these
  predicates, at about two Jev calls per task, and at the LLM's own cost. The guard is not infallible: in
  the Q8 run the dual arm clicked an authorized Delete twice and the verifier accepted it
  ([`results/q8-consent.md`](jevdual/results/q8-consent.md), the one false completion). The LLM alone deletes the account when asked to
  reach a page, and its own judge marks that a success.
- **Jev acting saves driver work, not money yet.** Dual makes 23 to 29% fewer driver requests than the
  guarded arm across two same-night samples and runs its own steps at a median 1.4 s against 15.7 s for an
  LLM step, but pays for that in Jev volume; task wall time between the arms is not distinguishable on
  live sites, and dual matches stock's cost only on the fixture heldout so far.
- **System 2 delegating bounded subgoals to Jev did not pay** in three measurements
  ([`Q9`](jevdual/docs/experiments/Q9.md)): more cost, no more completions. The executor reached 5 of 30
  assignments; an audit then found software defects behind most of those failures, and the repaired build
  was measured again ([`results/q9e-delegate-fixed.md`](jevdual/results/q9e-delegate-fixed.md)): 36
  verified against 41 for the same-day guarded arm, $0.644 against $0.424, 3 of 27 assignments reached.
  Delegation stays available as a tool, off by default.
- **Declaring the contract to the driver did not pay** ([`Q11`](jevdual/docs/experiments/Q11.md)): model
  requests rose 21% per task with completions unchanged. Neither did receipts for every action
  ([`Q12`](jevdual/docs/experiments/Q12.md), [`results/q12-live-dev.md`](jevdual/results/q12-live-dev.md)):
  repeated no-op clicks fell 18% but requests per unit of progress did not move (−0.02 [−0.14, +0.10], over
  the 53 tasks with some progress in both arms), and verified passes fell by 4 pooled. Receipts are kept as
  an honesty measure, not as a saving; the input defect they exposed is fixed first.

### Native apps and a shared machine

- **The arbiter's target confidence ranks wrong System 1 steps on accessibility-tree menus**
  ([`Q10`](jevdual/docs/experiments/Q10.md), [`results/q10-native-dev.md`](jevdual/results/q10-native-dev.md)):
  AUROC 0.90 [0.85, 0.94] on Calculator and TextEdit, against 0.80 on the web. That is a ranking result on
  two apps, whose agreed wrong steps come from two tasks; it is not a calibrated probability, and it does
  not yet say anything about unfamiliar apps. After verifier and task fixes, dual is within one task of guarded (13 against 15 of 18,
  [`results/q10b-native-dev.md`](jevdual/results/q10b-native-dev.md)); the gap is one repeated-sequence task.
  Native stays experimental.
- **A session runs beside a person without taking their work, input or focus**
  ([`Q15`](jevdual/docs/experiments/Q15.md)): 15 of 15 coexistence cases passed every check (another app,
  another document of the same process, a foreground step beside an idle or moving person, a conflicting
  edit). In none of three attempts did the person's move overlap a foreground step, so that race is covered
  by a unit test, not a live one. `background_only` is the default; `foreground_permitted` holds the front for 36 to 65 ms and only
  after 3 s of idle.

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
rustup toolchain install 1.97.1 --profile minimal  # pinned CUA source compiler
uv sync                        # builds Footwork and the exact CUA native reference
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
| [`jevdual/python/jevdual/`](jevdual/python/jevdual/) | the package: agent, policy, menu, arbiter, verify, ledger, receipts, secrets, tools; native arm (`native`, `desktop`, `posture`, `coexist`); operator surface (`cli`, `session`) |
| [`jevdual/crates/jevdual-core/`](jevdual/crates/jevdual-core/) | Rust hot paths (PyO3) with pure twins under `python/jevdual/_pure/` |
| [`jevdual/evals/`](jevdual/evals/) | runner, predicates, report, metrics, paired comparison, task files, fixture site |
| [`jevdual/results/`](jevdual/results/) | every run directory and its write-up; the README's numbers come from here |
| [`jevdual/docs/experiments/`](jevdual/docs/experiments/) | pre-registered questions Q1 to Q15 with results and decisions |
| [`jevdual/docs/`](jevdual/docs/) | design notes, plans (`plans/legible-harness.md` is the current one), the Cua survey, the Rust boundary rule, upstream reuse inventory |
| [`browser-use/`](browser-use/) | upstream pinned as a submodule at the studied commit; the package imports the PyPI release |

## Status

Research code with a working product core. The guard and the reactive dual loop are measured on the
browser; the native arm and the operator session are measured on a small native split and a coexistence
suite and stay experimental. Delegation and evidence selection are off by default. The
[status audit of 2026-09-26](jevdual/results/status-audit-20260926/README.md) reproduced five contract
breaks offline (operator sessions following the active browser tab, field receipts that overstate, a secret
in a receipt, the browser path continuing when its destructive judgment fails, short documents replaced
unpaused). Open, in order ([`plan`](jevdual/docs/plans/next-work.md)): those fixes, authorization parity
across routes, the input loss after navigation, then receipts again (Q12b), verifier evidence and recovery,
a narrower declaration (Q11b), and one contract across browser and native (Q13). Whether the browser should
go through the accessibility tree too (Q14) has a working route but no comparison yet. Calibration claims
wait on the human audit sheets. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a change.

## Credits

Ideas were taken from six MIT-licensed sibling projects (jev-ultrafast, fastbrowse, jev-browser,
jev-for-chrome, public-browser) and, ideas only, from browserclaw (AGPL); browser-use's test fixtures and
judge are reused under MIT ([`docs/upstream-reuse.md`](jevdual/docs/upstream-reuse.md)). MIT license.
