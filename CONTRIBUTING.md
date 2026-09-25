# Contributing

Footwork is research code with an evaluation discipline. The discipline is the part worth protecting.

## Ground rules

- **Numbers come from run directories.** A claim in a README or results doc cites a directory under
  `jevdual/results/`. If a change moves a number, rerun and cite the new directory; do not edit the number.
- **Heldout splits are never debugged.** `heldout.yaml` and `live-heldout.yaml` are run once per adoption.
  A heldout miss becomes a new dev task, never a fix aimed at the heldout task.
- **Pre-register before you run.** A new question gets a file in `jevdual/docs/experiments/` with the
  hypothesis, the predictions if true and if false, the design, one primary metric, guardrails and a
  decision rule, committed before the run. Results are appended under `## Result`; the text above it is not
  edited afterwards (amendments are dated and appended).
- **Thresholds are settings, not tuning targets.** Every number in `arbiter.toml` and `VerifyPolicy` is a
  recorded starting point. Changing one is a settings change: say so in the commit, note it in
  `results/e1-frozen.md`, and rerun the fixture heldout once.
- **Secrets never appear in the repo.** Task secrets are fixture demo logins scoped to their origin;
  `scripts/redact_results.py` runs on every run directory before it is committed; traces and `run.log`
  are git-ignored.
- **A bug found by driving becomes a scenario first.** `jevdual/tests/test_session_scenarios.py` runs the
  real `footwork` commands against a simulated Mac (`tests/fixtures/native_world.py`); reproduce the bug
  there, see it fail, then fix the harness, not the scenario.
- **Upstream seams are pinned.** browser-use and cua-driver are exact versions with contract tests under
  `jevdual/tests/contract/`; a bump lands only with those tests green or updated in the same commit.
- **Rust ports keep a pure-Python twin** and an equality test over the recorded fixtures
  (`jevdual/docs/rust-boundary.md`).

## Working on it

```sh
cd jevdual
uv sync
uv run ruff check python evals tests scripts
uv run pytest                              # no keys needed
JEVDUAL_BROWSER_TESTS=1 uv run pytest -m browser   # launches headless Chromium
scripts/upstream_tests.sh                  # browser-use's own CI modules against this package
```

Evals need `TYPESAFE_API_KEY` and a System 2 key; see the README. Commit run artifacts
(`report.md`, `results.json`, `summary.json`, `taxonomy.md`, paired tables) but never `traces/` or
`run.log`.

## Commits

One change per commit, message says what changed and why with the evidence, and tests for behaviour
changes. Runs that cost money are launched only when the change they measure is committed.
