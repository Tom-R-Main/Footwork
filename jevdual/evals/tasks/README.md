# Eval task sets

Two files, one rule.

- `dev.yaml` — debug freely. Read traces, change thresholds, add tasks that
  reproduce a failure.
- `heldout.yaml` — **never debugged.** It is run once per arm at the end (task
  E1). Do not open a trace from a heldout run to fix a bug. If a heldout task
  fails, write a *new* dev task that captures the same failure class and fix it
  there. Every heldout miss is attributed to a failure class in the results
  write-up, not repaired.

Tasks are graded by their predicate against observed state (final URL, captured
page text, returned answer), never by the agent's claim of success. `{site}` in
`start_url` is replaced by the fixture server base URL from
`evals/fixtures/server.py`. Tasks tagged `live` hit the public web and are
expected to be flakier; report them separately.

## Live task sets (experiment program, `docs/experiments/`)

- `live-dev.yaml` — public pages with stable facts (Wikipedia, MDN, docs.python.org, arXiv,
  RFC Editor, Project Gutenberg, GitHub, PyPI, DuckDuckGo) and practice sites built for browser
  automation (saucedemo.com, the-internet.herokuapp.com, httpbin.org). Debug freely.
- `live-heldout.yaml` — **never debugged**, same rule as `heldout.yaml`. Run once per arm per
  adoption.

Every task in a live split is tagged `live` and starts at an `https://` URL; the runner includes
them without `--live` when the split name starts with `live`. Secrets are scoped to the start
page's origin and never appear in task text. Practice-site credentials are the sites' published
demo logins, kept in `secrets` anyway so the redaction path is exercised.

Extra fields for the program:

- `checkpoints:` key intermediate states, each a `url_contains` predicate; a `multistep` task
  passes only if every checkpoint URL was visited (WebCanvas-style).
- tag `multistep`: three or more dependent subgoals (Q4). Always carries `checkpoints`.
- tag `consent`: the task reaches a send/submit/order/remove step (Q8). Authorised tasks set
  `authorize: true` and must complete; unauthorised ones use a `not_reached` predicate and must
  stop before the irreversible URL. Every consent endpoint on the practice sites discards input;
  nothing real is sent or bought.
- tag `tabs`: the task opens a second tab and must switch to it.

Live pages drift. Predicates use canonical URLs, years and names, not counts or prices that
change. A task no arm passes in any repeat is reported as `unreachable`, not counted as a miss.
