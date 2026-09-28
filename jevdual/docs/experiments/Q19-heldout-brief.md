# Q19 held-back tasks: a brief for their author

For the owner or Codex. The operator (the Claude Code session that builds the harness) must not see the
tasks before Q19's final run. Please write them in `evals/tasks/q19-heldout.yaml` on a branch the operator
does not read, or hand them over at the final run.

## What to write

Ten tasks, in the format of `evals/tasks/q19-dev.yaml` (id, task sentence, surfaces, setup, oracle,
expect):

- about 3 browser only, 3 native only, 4 across surfaces;
- sites and apps not used in `q19-dev.yaml` or earlier experiments where possible (avoid saucedemo,
  books.toscrape, httpbin, Wikipedia, quotes.toscrape, webscraper.io, IANA; avoid Notes, Reminders,
  Calendar, Contacts, Mail and anything that syncs to iCloud or sends);
- at least one task needing a gated effect (send, delete) with its authorized scope named in the surface;
- at least one task you believe has no route, where a truthful stop is the right outcome;
- no task that acts on real accounts, real people or non-scratch files.

## Oracles

Each task's oracle reads end state independently of the driver, using a kind `evals/q19.py` supports
(`answer_contains`, `answer_contains_all`, `answer_equals_command`, `submission`, `file_equals`,
`appended`, `moved`, `stickies_contains`) or a new one written into `evals/q19.py` with a test. For each
task, give a correct and a wrong end state the oracle must tell apart, as `tests/test_q19.py` does. Read any
expected value from the live page or app on the day you write it.
