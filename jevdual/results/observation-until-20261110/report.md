# Bounded native control appearance observation

Prediction commit: e9d3a8f. Development checkout follows25d4107 on codex/suno-end-to-end-20261110; this report accompanies the source patch rather than identifying an installed artifact.

The public native CLI now accepts `look --until "Exact label" --timeout 10`. It repeats fresh observations, checks exact offered candidate labels, and returns0 on appearance or6 on deadline. It retains partial-coverage warnings and the final completed observation. Appearance does not establish uniqueness, task completion, persistence, or permission to act. Browser sessions refuse this option before binding. The default timeout is10 seconds, accepted range0.1–60; labels are nonempty, at most80 characters, and contain no control characters or surrounding whitespace.

## Evidence

- `red.txt`: baseline parser rejects the proposed flags in13 public CLI scenario cases before implementation.
- `pytest.txt`:293 affected tests pass after implementation, including the session scenarios, CLI, discovery/schema, session evidence, targeting, visual inspection and notebook suites.
- `notebook.txt`: notebook validation passes. Changed-file Ruff and `git diff --check` also pass.
- `python -m jevdual.cli schema desktop look` reports both new arguments automatically.

The tests exercise delayed appearance, exact matching versus title/page-text decoys, final partial menu on timeout, duplicate labels retaining click refusal, invalid options without driver binding, cooperative observation cancellation with shutdown, upstream TimeoutError preservation, browser refusal, and distinct capture paths between wait polls.

Commands, from `jevdual/`:

```sh
uv run --no-sync pytest tests/test_session_scenarios.py tests/test_cli.py tests/test_agent_cli.py tests/test_session.py tests/test_session_evidence.py tests/test_session_targeting_audit.py tests/test_visual_inspection_session.py tests/test_notebook.py -q
uv run --no-sync ruff check python/jevdual/cli.py python/jevdual/session.py tests/test_session_scenarios.py
uv run --no-sync python -m evals.notebook docs/notebook --check
uv run --no-sync python -m jevdual.cli schema desktop look
git diff --check
```

## Limits

These are simulated-Mac and offline CLI checks, not live Suno, installed-wheel or native RPC cancellation qualification. The observation deadline applies to cooperative async observation and polling; driver binding and shutdown retain their existing behavior and may add elapsed time. No action or model call is sent by the new wait itself. An exact observed label can still reflect a delayed or inaccurate external AX tree; screenshot cross-checks and action gates remain necessary.
