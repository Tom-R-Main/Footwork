# PyObjC selected-range decoding

The live foreground replacement attempted Select All, then stopped in selection readback because
AXValueGetValue returned a tuple and the new decoder assumed `.location`/`.length` attributes.
The decoder now accepts a validated two-integer tuple or a CFRange-like object with those integer
attributes. It rejects negative, malformed, boolean, float and string values without coercion.

Prediction commit:bc89878. `red.txt` reproduces the tuple failure through the public CLI with the
real decoder and synthetic macOS API replies. The baseline has10 failures and2 preserved-behavior
passes. `pytest.txt` records338 passing affected scenario, native, foreground, posture and pinned
ABI checks. Changed-file Ruff, notebook validation and `git diff --check` pass.

The valid tuple and CFRange scenarios emit one guarded Select All and one type request only after
full-selection proof. Invalid representations emit no type request and retain uncertainty about the
earlier attempted selection. This does not rewrite the original live receipt or claim that its
preparation never happened.

Command from `jevdual/`:

```sh
PYTHONPATH=/Users/thomasmain/projects/footwork/jevdual/output/foreground-web-text/overlay:/Users/thomasmain/projects/footwork/jevdual/python .venv/bin/python -m pytest tests/test_session_scenarios.py tests/test_native.py tests/test_native_foreground_intent.py tests/test_posture.py tests/contract/test_cua_driver_seams.py -q
```

Only the Footwork Python decoder and scenarios changed. The qualified focus1 SDK wheel and native
bytes remain unchanged; no rebuild, install or global activation occurred. Live Suno delivery on
the repaired source remains for root's SUN14 test.
