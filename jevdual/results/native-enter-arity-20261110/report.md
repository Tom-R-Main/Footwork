# Reject ignored native enter text

Prediction: ba8ff28, with a clock metadata correction c000b5b committed before resolving tests.

`footwork do enter TARGET TEXT` previously accepted and printed text that the native Return-only operation ignored. It could also resolve secret-looking text unnecessarily. The CLI now rejects any native enter tail, including an explicit empty argument, before secret resolution or driver binding. It returns2 with explicit guidance: type the field, reobserve and verify its content, then enter the target. No implicit fill-and-submit operation is introduced.

## Validation

- `red.txt`: corrected baseline public CLI scenarios have3 failures and2 passes. Nonempty and empty tails reached the existing Return dispatch; unresolved secret syntax took the existing secret-resolution path.
- `pytest.txt`:270 affected session-scenario, session, CLI, agent/discovery, authorizer and native tests pass after repair.
- `notebook.txt`: notebook validation passes. Changed-file Ruff and `git diff --check` pass.

The initial scenario needed explicit Return authorization because Calculator's fixture also exposes a Delete button. The correction preserves the production authorizer and lets the test reach the intended argument boundary.

Commands from `jevdual/`:

```sh
uv run --no-sync pytest tests/test_session_scenarios.py tests/test_session.py tests/test_cli.py tests/test_agent_cli.py tests/test_authorize.py tests/test_native.py -q
uv run --no-sync ruff check python/jevdual/session.py tests/test_session_scenarios.py
uv run --no-sync python -m evals.notebook docs/notebook --check
git diff --check
```

## Limits

These are offline simulated-Mac checks, not live Suno or installed-wheel qualification. Target-only enter still passes through the existing gates before sending Return. BrowserBridge does not implement enter; the new argument guard applies only to native sessions, and the browser scope test proves it does not intercept that existing route. Other ignored-tail operation rules and direct Python NativeBridge calls are unchanged.
