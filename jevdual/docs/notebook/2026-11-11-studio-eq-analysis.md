# Private Studio EQ analysis

## SEA1 · prediction · 2026-11-11 03:47
Hypothesis: full-band per-channel power analysis with reference-band normalization distinguishes planted low-frequency attenuation from uniform gain while stereo-preserving correlation recovers a shared padding offset without cancellation of opposite-phase channels.
Test: ignored private analyzer, deterministic broadband stereo noise with a low-frequency tone, controlled low-band attenuation12dB versus uniform6dB reduction, opposite-phase stereo and a known leading padding offset. Separate local synthetic WAVs check the exact ffprobe/complete-decode/CLI/output boundary, invalid band/duration bounds and output overwrite refusal. No actual Studio files, provider call, UI, credentials or installs.
Predicts: planted selective reduction has low-minus-reference change approximately12dB lower, uniform gain has approximately zero normalized band change, opposite-phase channels retain nonzero measured power, padding is recovered and ambiguous/inconsistent alignment remains explicitly unresolved. Valid local files produce a new JSON with hashes, metadata and declared settings; existing output is preserved.
Against: uniform gain is labeled frequency-selective, downmix cancellation removes stereo evidence, wrong alignment is accepted, unsupported bands or over600second media are analyzed, existing output is overwritten, or claimed actual-song measurements precede the real exports.
Refs: output/suno-studio-20261111/analyze-eq.py; results/studio-eq-analysis-20261111/report.md

## SEA2 · prediction · 2026-11-11 03:47
Hypothesis: fixed diagnostic settings can expose alignment and spectral uncertainty without tuning toward forthcoming Studio output.
Test: use48kHz stereo float decode, three4second anchor centers at one-sixth/one-half/five-sixths of the common duration, reference-band correlation within plus/minus250ms, lag spread at most48samples and all peak correlations at least0.5 away from the search boundary. Align by median lag only when these settings pass; trim one second from each end of the common overlap. Welch uses32768sample Hann windows,50percent overlap and independent channel powers. Bands follow actual supplied UI cutoff fc: low fc/4..fc/2, transition fc/2..2fc, reference max1000,4fc..max4000,8fc; reject bands touching/exceeding24kHz or containing no FFT bin. Report raw powers, raw and reference-normalized changes, overall/per-channel RMS/peaks/correlation/gain and three equal interior segments.
Predicts: no synthetic or actual result silently changes settings; insufficient or inconsistent evidence yields a diagnostic unresolved result rather than an asserted high-pass qualification.
Against: settings are modified after observing Studio spectra, low-energy evidence is hidden, or unresolved alignment is used as qualified edit evidence.
Refs: output/suno-20261110/compare-fade-audio.py; output/suno-20261110/compare-repeat-four.py; docs/notebook/2026-11-11-suno-studio.md

## SEAU1 · update · 2026-11-11 03:53
Resolves: SEA1 = held; SEA2 = held
Observed: eight synthetic mechanics checks pass. The planted selective low-band change measures minus12dB relative to reference, while uniform minus6dB gain produces approximately zero normalized change. Opposite-phase stereo retains power. All three broadband padding anchors recover733samples; inconsistent offsets remain unresolved without spectrum. Local synthetic WAV CLI checks complete decode, metadata/hashes and overwrite refusal, and duration/band refusals pass. Final private-source Ruff passes; no actual Studio audio or cutoff was read.
Changes: implemented only ignored analyze-eq.py and selfcheck-eq.py, with fixed settings and bounded local ffprobe/FFmpeg. Twelve seconds minimum supports the three declared four-second anchors; input size is bounded256MiB and per-process probe/decode deadlines30/120seconds. No tracked production helper or framework changed. Initial lint-only corrections use pairwise and explicit subprocess check flags.
Next: hand off the frozen private source and exact future invocation. Root alone may measure actual exports after UI cutoff/source identity exist; no waiting or further calibration is needed here.
Refs: predictionb35d9ca; results/studio-eq-analysis-20261111/report.md; results/studio-eq-analysis-20261111/selfcheck.json; results/studio-eq-analysis-20261111/ruff.txt

## SEAS1 · summary · 2026-11-11 03:53
Established: a private local analyzer distinguishes the planted frequency-selective change from uniform gain, preserves stereo power and reports padding alignment and uncertainty with fixed settings. Source hashes and future CLI recipe are retained in the public method report.
Uncertain: real Studio baseline/Hi-Pass media, actual UI cutoff, exported spectral behavior, persistence and aesthetic improvement remain unmeasured by this worker. Diagnostic alignment thresholds and reference selection are method settings, not proof of every signal's correct alignment or attribution.
Decision: close mechanics-only work and leave actual locked-desktop/export continuation to root. No provider/network/UI call, credential read or installation occurred.
Refs: results/studio-eq-analysis-20261111/report.md; output/suno-studio-20261111/analyze-eq.py

## SEAU2 · update · 2026-11-11 03:54
Resolves: SEA2 = held
Observed: the notebook parser resolves one prediction per update; SEAU1's combined field closed only SEA1. The same synthetic evidence and frozen analyzer retain all declared alignment/Welch/band settings without actual Studio media inspection or post-measurement threshold tuning.
Next: close SEA2 explicitly and hand off the existing source/hash/recipe; no additional synthetic or actual media run is required.
Refs: results/studio-eq-analysis-20261111/selfcheck.json; results/studio-eq-analysis-20261111/report.md
