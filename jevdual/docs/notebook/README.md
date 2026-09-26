# Engineering notebook

The experiments in `docs/experiments/` are pre-registered because a prediction written after the
result cannot be wrong. The notebook applies the same rule to the engineering between experiments:
debugging, harness changes, audits and fixes. Its purpose is to let whoever works next, and whoever
reviews the work afterwards, see which diagnoses held, which failed, and why, without relying on
anyone's recall of a session.

It sits between two records that already exist:

| Layer | Written by | When |
|---|---|---|
| Execution trace (`traces/`, `run.log`, receipts, test output) | the harness | continuously; never copied into the notebook |
| **Notebook** (this directory) | whoever does the work, person or agent | before a substantive test, and when evidence changes the diagnosis |
| Results and experiment files (`results/`, `docs/experiments/`) | the experiment | at a decision |

## When to write

- **Before** a substantive test or harness change: a `prediction`, or `exploratory` when there is no
  hypothesis yet.
- **When evidence changes** the diagnosis, the confidence or the next action: an `update`. A failed
  prediction, a surprise, a regression, or finding that the test cannot tell the explanations apart
  all qualify.
- **At a boundary** (a work package closes, is abandoned or handed off): a `summary`.

Not for routine steps. An expected test passing, a file read, or a rerun that changes nothing gets no
entry. Proportion is part of the practice: an entry nobody needs to decide the next action is
narration.

## Format

One file per work package, `YYYY-MM-DD-<slug>.md`. Each entry is a level-two heading and
`Field: text` lines; `uv run python -m evals.notebook docs/notebook --check` validates it and
`tests/test_notebook.py` runs that check on this directory.

```
## A1 · prediction · 2026-09-26 15:10
Question: why does a second `do` click a different tab?
Hypothesis: SessionState keeps pid and window, not the tab; bind() attaches to the active tab.
Alternatives: the driver itself retargets on focus change.
Test: scenario test, switch the active tab between two `do` commands.
Predicts: with the tab persisted, the second command refuses with a typed code and dispatches nothing.
Against: it still dispatches to the new tab, or an unchanged tab is refused.
Refs: results/status-audit-20260926/probes.json

## U1 · update · 2026-09-26 15:40
Resolves: A1 = held
Observed: test_tab_switch_refused fails before the change, passes after; no other scenario changed (commit abc1234).
Inferred: the driver does not retarget on its own.
Next: A2.
```

| Kind | Required | Optional |
|---|---|---|
| `prediction` | Hypothesis, Test, Predicts, Against | Question, Alternatives, Refs, Revises |
| `exploratory` | Question, Test | Refs |
| `update` | Observed, Next | Resolves, Inferred, Changes, Refs |
| `summary` | Established, Uncertain, Decision | Refs |

## Rules

- **Predict before testing.** `Predicts` and `Against` are written before the test runs. `Against`
  names an outcome that would count against the hypothesis; a prediction with nothing that could
  contradict it is `exploratory`.
- **Append only.** An outcome is a later `update` with `Resolves: <ID> = held | failed |
  inconclusive`. A changed prediction is a new entry with `Revises: <ID>`. Earlier text is not edited.
- **Observed apart from inferred.** `Observed` is what a trace, receipt, test or screenshot shows;
  `Inferred` is what it is taken to mean. Passing a task, or a test, does not prove the mechanism.
- **Refer, do not copy.** Cite run directories, commits, test names and trace paths. Traces and
  `run.log` stay out of the repo, and no secret or page content from a trace enters the notebook.
- **Freeze what is measured.** Patch freely while exploring. A measured comparison runs on a named
  commit; a change mid-run starts a new version, as `CONTRIBUTING.md` already requires.

## Reading it afterwards

`uv run python -m evals.notebook docs/notebook` prints the predictions held, failed, inconclusive and
open, and each failed hypothesis with the observation that resolved it. The failed ones are the
point: they show where the diagnosis went wrong and what the next harness change should address. A
package that closes with no failed prediction either went well or predicted too safely; the summary
says which.
