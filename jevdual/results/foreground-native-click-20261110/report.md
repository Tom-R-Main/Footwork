# Explicit foreground native click

Preregistration `3f2ad22`; baseline against `e6785a7` has five public CLI failures because explicit click delivery was unavailable (`baseline.txt`).

`do click TARGET --click-delivery foreground` now requires native macOS, foreground posture and normal action gates. Unsupported operations, browser/mixed routes, owned-file selectors and `--no-judge` refuse before binding. Shared foreground admission retains the three-second idle rule. The route checks the filmed-take gate if present, activates and verifies the exact window, freshly reobserves/rematches semantic/resource identity, then sends one SDK `InputDeliveryMode.FOREGROUND` click on the fresh element token. No pixel-coordinate target or automatic retry is introduced. The ordinary background path is unchanged.

The pinned CUA token path in `platform-macos/src/tools/click.rs` checks Chromium select refusal before cursor animation or AX input. Its `set_value.rs::chromium_select_open_refusal` reports `select_menu_would_raise_window` and recommends explicit foreground only when authorized. That source boundary does not repair the older Python exception's uncertain historical receipt. The new explicit route retains actual SDK delivery metadata, and both SDK refusals and ambiguous replies stop after one attempt.

16 public CLI scenarios pass (`scenarios.txt`): fresh-token foreground delivery, unchanged one-attempt background refusal, human activity, target/window drift, hidden duplicate peer after activation, unknown delivery, structured SDK refusal, and unsupported combinations before binding. The affected session/native/menu/posture/CLI/discovery/authorizer/evidence/operations and all CUA contract tests pass: 686 tests (`focused.txt`). Ruff and notebook checks pass. No SDK rebuild/install, native-byte change, worker UI action or live probe occurred.

Commands from `jevdual/`:

```sh
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py -k 'explicit_foreground_native_click or native_dropdown_background_refusal'
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py tests/test_session.py tests/test_session_targeting_audit.py tests/test_native.py tests/test_menu.py tests/test_control_state.py tests/test_posture.py tests/test_ax_semantics.py tests/test_native_foreground_intent.py tests/test_native_receipts.py tests/test_cli.py tests/test_agent_cli.py tests/test_authorize.py tests/test_authorization_parity.py tests/test_session_evidence.py tests/test_session_operations.py tests/contract
.venv/bin/ruff check python/jevdual/{native,session,cli}.py python/jevdual/effectors/cua.py tests/test_session_scenarios.py tests/test_agent_cli.py
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m evals.notebook docs/notebook --check
```

A click acknowledgement is not proof that a menu opened. Parent-owned live testing must reobserve actual menu choices and preserve the earlier unknown receipt separately. Range-focus preparation is a later independent package.
