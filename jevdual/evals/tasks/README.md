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
