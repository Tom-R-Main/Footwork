# Working in Footwork (for agents and people)

Read `CONTRIBUTING.md` first; its rules apply to every change. Two habits matter most for an agent
working here across sessions:

- **Keep the engineering notebook.** Before a substantive test or harness change, write a
  `prediction` in `jevdual/docs/notebook/<date>-<package>.md`: hypothesis, test, what it predicts,
  and an outcome that would count against it. Append an `update` when evidence changes the diagnosis
  (resolving a prediction as held, failed or inconclusive), and a `summary` when a package closes or is
  handed off. Refer to traces, receipts, tests and commits; never copy them. Skip routine steps.
  Format and rules: `jevdual/docs/notebook/README.md`; check with
  `uv run python -m evals.notebook docs/notebook --check` from `jevdual/`.
- **Commit the prediction before the test that resolves it.** A prediction committed with its own
  result cannot be told apart from one written afterwards.

The notebook is also where a session picks up after its context is lost: read the open predictions
and the last update of the current package before doing anything else.
