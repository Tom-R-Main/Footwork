# Selected-range bridge representation

## SRD1 · prediction · 2026-11-10 18:05
Question: does the new foreground replacement route stop before text synthesis because the real macOS bridge returns a tuple range where the decoder assumes a CFRange object?
Hypothesis: accepting only validated two-integer tuple or CFRange attribute representations fixes this selection readback boundary while malformed ranges still stop typing, and preserves the historical uncertainty of the already attempted selection.
Test: public CLI simulated-Mac replacement scenarios use the real selected_range decoder with AXValueGetValue returning tuple, CFRange-like object and malformed/negative/noninteger representations. Reproduce tuple failure before repair, then run focused foreground/native/ABI checks on the unchanged project overlay.
Predicts: baseline tuple range prevents type_text after Select All; repaired tuple/object ranges allow one type request only when the complete expected selection agrees. Invalid ranges refuse selection qualification and emit no type request. No historical receipt is rewritten and no SDK rebuild is needed.
Against: malformed data is coerced into a valid range, typing occurs before complete selection proof, tuple support changes native bindings, or the failed live operation is relabeled as if its selection never happened.
Refs: output/suno-20261110/foreground-lyrics-signal.txt; python/jevdual/ax.py::selected_range; python/jevdual/native.py::_type_web_foreground

## SRDU1 · update · 2026-11-10 18:07
Resolves: SRD1 = held
Observed: the real-decoder public CLI scenarios reproduced the tuple AttributeError before type_text, while the CFRange-like object case already passed. Baseline results were10 failures and2 passes. The repaired decoder accepts a two-integer tuple or an object with integer location/length attributes, rejects malformed, negative, boolean, float and string components without coercion, and passes338 affected foreground, native, posture, scenario and ABI checks. Ruff and notebook validation pass.
Changes: normalize only the two observed range representations in ax.selected_range. The native synthesis/selection route, SDK bytes, exact pin and historical operation records remain unchanged.
Next: root uses the same project wrapper on the new frozen source commit for SUN14, with fresh observation and the existing authorization.
Refs: prediction bc89878; results/selected-range-decoding-20261110/red.txt; results/selected-range-decoding-20261110/pytest.txt; results/selected-range-decoding-20261110/report.md

## SRDS1 · summary · 2026-11-10 18:07
Established: the foreground replacement path can decode a PyObjC tuple range as well as a CFRange-like object, and still requires the complete expected UTF-16 selection before text. Invalid ranges stop after the attempted selection with no subsequent type request in the public CLI scenarios.
Uncertain: live Suno rendering and content delivery after this decoder fix remain for root. The earlier live operation retains its unknown selection/preparation outcome; neither the patch nor the tests retroactively labels it no-input.
Decision: deliver the Python-only repair without an SDK rebuild or global activation. Keep prior broad-suite evidence separate from these focused checks.
Refs: results/selected-range-decoding-20261110/report.md
