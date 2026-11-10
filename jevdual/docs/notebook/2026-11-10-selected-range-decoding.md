# Selected-range bridge representation

## SRD1 · prediction · 2026-11-10 18:05
Question: does the new foreground replacement route stop before text synthesis because the real macOS bridge returns a tuple range where the decoder assumes a CFRange object?
Hypothesis: accepting only validated two-integer tuple or CFRange attribute representations fixes this selection readback boundary while malformed ranges still stop typing, and preserves the historical uncertainty of the already attempted selection.
Test: public CLI simulated-Mac replacement scenarios use the real selected_range decoder with AXValueGetValue returning tuple, CFRange-like object and malformed/negative/noninteger representations. Reproduce tuple failure before repair, then run focused foreground/native/ABI checks on the unchanged project overlay.
Predicts: baseline tuple range prevents type_text after Select All; repaired tuple/object ranges allow one type request only when the complete expected selection agrees. Invalid ranges refuse selection qualification and emit no type request. No historical receipt is rewritten and no SDK rebuild is needed.
Against: malformed data is coerced into a valid range, typing occurs before complete selection proof, tuple support changes native bindings, or the failed live operation is relabeled as if its selection never happened.
Refs: output/suno-20261110/foreground-lyrics-signal.txt; python/jevdual/ax.py::selected_range; python/jevdual/native.py::_type_web_foreground
