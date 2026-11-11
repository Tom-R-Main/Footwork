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
