# What jevdual reuses from browser-use's test and eval infrastructure

browser-use is pinned as a submodule (commit d8110c5, MIT). Its tests, fixtures and judge are a
foundation we adapt rather than rebuild. This file is the inventory; each item names the upstream
source and what changed.

| upstream | where it lives here | what changed |
|---|---|---|
| `tests/ci/conftest.py::create_mock_llm` | `tests/fixtures/mock_llm.py` | Takes the agent's own tool registry; a scripted item can be a judge verdict. Drives `tests/test_agent_loop.py`: destructive gate, done verification, UNVERIFIED terminal, judge recording, all without a model. |
| `pytest-httpserver` pages per test | `tests/test_agent_loop.py` | Adopted as-is (dev dependency). Each test serves exactly the page it needs. |
| `browser_use/agent/judge.py` (judge prompt) and `Agent(use_judge, judge_llm, ground_truth)` | `evals/runner.py`, `evals/report.py` | The judge already ran on every dual and stock run with the System 2 model; the verdict, failure reason, `impossible_task` and `reached_captcha` are now recorded per row and summarised (agreement, false accept, false reject against predicates). It is the Q3 judge baseline. S1-only runs skip it. |
| `tests/agent_tasks/*.yaml` (`judge_context`) and `tests/mind2web_data/processed.json` | `scripts/import_upstream_tasks.py` → `evals/tasks/live-upstream.yaml` | Imported as `judge`-kind tasks: criteria become the judge's ground truth; rows are graded-by-judge and never mixed into predicate rates. Mind2Web is sampled round-robin across sites with real https start pages. |
| `tests/ci/test_multi_act_guards.py`, `test_action_loop_detection.py`, `test_redact_cascade.py`, `test_variable_substitution.py`, `test_dom_paint_order_serialization.py`, `test_dom_visibility.py`, `test_llm_output_truncation.py`, `test_llm_retries.py`, `test_tools.py`, `security/test_sensitive_data.py` | `scripts/upstream_tests.sh` via the `jevdual.upstream_pytest` plugin | Run unchanged from the submodule against our installed package with the jevdual patches active. This is the contract with the pinned commit for the seams we override. |
| `tests/ci/browser/*_template.html` | not yet | Candidate DOM fixtures for the Rust paint-order and snapshot ports. |

One upstream test is deselected in the script: `test_multi_act_guards.py::TestStaticGuard::test_navigate_aborts_remaining_actions`
hits the 180 s per-action navigate timeout on this machine both with and without the patches
(observed 2026-09-21), so it is an environment issue, not a seam regression.

Not reused: upstream's `evaluate_tasks.py` runner (subprocess-per-task, judge-only grading) and the
cloud eval workflow. Our runner grades by predicates first and records the judge alongside.

## Judge policy

The judge is the System 2 model (Muse Spark 1.3 Contributor in the evals) running upstream's judge
prompt over the task, the trajectory text and the last screenshots. It is cheap enough to run on
every trace. It is used three ways, and the reports keep them apart:

1. **Blind baseline on predicate tasks** (no ground truth): measures judge false accepts and false
   rejects against observed state. This is Q3's comparison arm and costs nothing extra.
2. **Grader on `judge`-kind tasks** (criteria as ground truth): for imported tasks and live tasks
   with no machine-checkable end state. Reported as graded-by-judge.
3. **Triage**: `impossible_task` and `reached_captcha` mark live tasks as unreachable rather than
   as misses.

The judge never overrides a predicate, and a judge pass on a `judge`-kind task is not evidence for
the predicate-graded pass rates quoted in the README.
