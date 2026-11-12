# Read-only numeric control observation

November 11, 2026. Repaired numeric metadata loss for existing native slider/spinbutton candidates. This is generic Footwork observation support, with no app-specific workflow or new action route.

The real CLI simulated-Mac scenario `test_numeric_controls_keep_read_only_snapshot_values` first failed because supplied fader and tempo values were absent from start output. After repair, start/look retain their original numeric spelling; saved candidates and target inspection retain a `numeric` object with `source: cua.window_state`, finite floating-point value, independently supplied `min`/`max`, range consistency when both are supplied, and a bounded value description with explicit clipping provenance.

Missing and invalid fields remain absent. No unit is inferred from a label or description. Boolean, nonfinite, locale-formatted, unit-bearing and excessive values are not parsed as numeric values. Contradictory finite bounds are reported with `range_valid: false`, never silently swapped. The pinned SDK contract uses the literal `min` and `max` fields; contract checks now cover both.

`NativeMenu.values` and `exact_ax_values` remain restricted to editable text. Sliders and spinbuttons still offer only their previous click operation. Numeric metadata supplies neither identity nor mutation authority and does not make a missing or ambiguous control actionable. Matching accessibility state does not prove a web renderer changed or a project saved. Floating-point metadata is approximate; the supplied numeric spelling remains in the display value.

## Validation

| Boundary | Result | Private run evidence |
| --- | --- | --- |
| Public CLI reproduction before repair | Failed at absent Track volume readout | output/numeric-observation-red.txt |
| Native projection, menu, public session scenarios and SDK seams | 483 passed | output/numeric-observation-affected.txt |
| Numeric guards and read-only visual target inspection | 49 passed, no model or dispatch | output/numeric-observation-inspection.txt |
| Changed native/menu/numeric/inspection source lint | Passed | local Ruff check |

Tests run from `jevdual/` using `PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest`, preserving the exact project `0.46.0+footwork.5486b624.cleanup2.focus1` SDK. An initial base-environment contract invocation failed because that environment exposes cleanup2 without focus1; the corrected project route passed. No install, provider call, real UI action or actual Studio qualification occurred in this package.

Preregistered notebook: docs/notebook/2026-11-11-numeric-observation.md. The parent performs integrated validation after concurrent lifecycle/media fixes settle.
