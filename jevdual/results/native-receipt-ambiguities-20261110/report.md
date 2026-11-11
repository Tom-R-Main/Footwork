# Native receipt ambiguity classifications

Preregistration `4f820d7` (NRA1). Baseline: two public CLI cases failed, while the non-LF mismatch case already passed (`baseline.txt`). Parent-owned SUN30 evidence shows controlled Copy matched the original461-character/24-LF payload exactly while AXValue serialized456 characters/19 LF; those historical receipts remain unchanged.

Two classification-only changes in session.py:

- Ordinary native multiline whole-field replacement now reports `unverifiable` when its complete untruncated raw readback differs in internal LF pattern but every non-LF character matches exactly. The evidence requests independent readback and says not to retype automatically. No values are modified or normalized, and this condition never confirms delivery. Browser/secret behavior, truncation warnings, trailing-whitespace legacy behavior, non-LF mismatch and strict selected-range receipts remain unchanged.
- Native menu invocation with no visible change now reports `unverifiable`, because clipboard, disk or another-window effects are not observed by that UI diff. No-send refusals, saves and qualified native external-effect readback keep their existing handling.

Four public CLI cases pass (`scenarios.txt`), including a strict range LF mismatch that stays partial and a simulated Copy that advances only a clipboard-generation oracle. `focused.txt`:465 affected session, evidence, native receipts, foreground intent, operations, Finder moves, authorizer and CLI tests pass. Boundary tests preserve exact non-LF distinctions, browser/single-line/secret classification, unchanged raw values, truncation, menu refusal and qualified external proof. Ruff, notebook and diff checks pass.

Commands from `jevdual/`:

```sh
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py -k 'native_multiline_lf_serialization or native_menu_no_visible_change or lf_representation_receipt'
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py tests/test_session_evidence.py tests/test_session.py tests/test_native_receipts.py tests/test_native_foreground_intent.py tests/test_session_operations.py tests/test_session_finder_move.py tests/test_authorize.py tests/test_cli.py
.venv/bin/ruff check python/jevdual/session.py tests/test_session_scenarios.py tests/test_session_evidence.py
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m evals.notebook docs/notebook --check
```

No live UI, clipboard access, SDK build, native-byte change or installation occurred. The code supplies no new independent readback mechanism and does not establish DOM/server acceptance or edit completion.
