# Private Studio EQ analysis method

The private analyzer will live at `output/suno-studio-20261111/analyze-eq.py`; exports belong to `output/suno-studio-20261111/exports/`. The forthcoming inputs are `studio-flat-baseline.mp3` and `studio-hi-pass.mp3`. Neither has been analyzed by this worker. Supply cutoff from actual UI evidence; no preset frequency is assumed.

Method and synthetic checks are preregistered in `docs/notebook/2026-11-11-studio-eq-analysis.md`. The implementation and fixture media stay ignored; this report will retain source hash, synthetic results and invocation recipe. No tracked production helper or framework change is needed.
