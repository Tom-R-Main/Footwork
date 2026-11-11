# Private Studio EQ analysis method

The private analyzer lives at `output/suno-studio-20261111/analyze-eq.py`; exports belong to `output/suno-studio-20261111/exports/`. The forthcoming inputs are `studio-flat-baseline.mp3` and `studio-hi-pass.mp3`. This worker processed synthetic fixtures only. No actual Studio pair, UI cutoff, saved EQ setting or acoustic outcome is claimed.

Preregistration: `b35d9ca`, notebook `docs/notebook/2026-11-11-studio-eq-analysis.md`. The ignored analyzer's frozen SHA256 is `5ef6babafea2c5367d298bcf25da5f68acf3a94950b2f5a34ad4c8820876f3fd`; its ignored self-check source is `output/suno-studio-20261111/selfcheck-eq.py`, SHA256 `052e831a15e454f67d5678df088ddf7ab12772770112c83b95f1edd8d8d2eeb5`. No tracked production helper or framework changed.

## Execute only after the real exports and cutoff exist

From `jevdual/`, replace `OBSERVED_UI_CUTOFF_HZ` with the independently read numeric Hz value and choose a fresh output filename:

```sh
.venv/bin/python output/suno-studio-20261111/analyze-eq.py output/suno-studio-20261111/exports/studio-flat-baseline.mp3 output/suno-studio-20261111/exports/studio-hi-pass.mp3 --cutoff OBSERVED_UI_CUTOFF_HZ --out output/suno-studio-20261111/exports/studio-eq-comparison.json
```

Exit0 means an aligned diagnostic was written, not that EQ quality or persistence passed. Exit2 writes alignment uncertainty without aligned spectrum/RMS claims. Exit1 refuses invalid inputs, decode/output errors or existing output. There is no automatic retry or model/provider operation. The output path must have an existing parent inside `jevdual/`.

Inputs must be local regular MP3/WAV files, nonempty and at most256MiB each. ffprobe retains selected codec/rate/channel/duration/size fields, plus streaming file SHA256. Metadata and decoded durations must be at most600seconds. The analyzer accepts at least12seconds for three4second anchors. Accepted files decode completely with FFmpeg `-xerror`; an extra-second output cap bounds deceptive over-duration files and then rejects them. Probe/decode subprocess deadlines are30/120seconds each; this is not a single aggregate CLI deadline. Only file/pipe protocols are allowed. No loudness normalization is applied.

## Fixed diagnostic settings

- Decode48kHz stereo float PCM. Retain original format/rate/channels and decoded counts; equal formats do not prove equal encoder padding.
- Correlate independent channel reference-band signals at common-duration fractions1/6,1/2,5/6, with4second windows and plus/minus250ms search. Require all reference correlations at least0.5, no search-boundary peak and lag spread at most48samples. Use median lag; trim1second from each end of the common aligned overlap.
- Report overall/per-channel RMS, RMS changes, peaks, correlation and least-squares gain. Stereo powers/correlations are combined after per-channel computation, preventing opposite-phase cancellation.
- Welch PSD uses32768sample Hann windows and50percent overlap, normalized to power per Hz and integrated over bins. The UI-derived cutoff fc defines low fc/4..fc/2, transition fc/2..2fc and reference max1000,4fc..max4000,8fc Hz. Invalid, unresolved or Nyquist-bound bands refuse.
- Retain baseline/edited powers per channel and combined, raw band changes and changes relative to the reference band. Repeat metrics over three equal interior segments. Weak baseline powers remain visible; no automatic high-pass acceptance threshold is supplied.

## Synthetic mechanics evidence

`selfcheck.json` records eight checks, all passed:

| Check | Synthetic result |
| --- | --- |
| Planted12dB selective low-band reduction | −12.00dB relative to the reference, including all three segments |
| Uniform6dB gain reduction | Raw low-band change−6.00dB; normalized change approximately0dB; recovered global least-squares gain |
| Opposite-phase stereo | Nonzero retained low-band power, approximately0dB normalized gain-only change |
| Broadband signal with733sample leading padding | All three anchors recover733samples, zero lag spread |
| Different offsets across the piece | Alignment unresolved; no aligned spectrum emitted |
| Invalid frequency bands | Zero/nonfinite cutoff and above-Nyquist reference rejected |
| Local synthetic stereo WAV CLI | Full decode, hashes and sample counts retained; existing JSON preserved on second invocation |
| Duration bounds |601second metadata refused; a smaller patched cap confirms excessive actual decoded duration is refused |

The fixture uses deterministic noise seed73182, a75Hz tone and cutoff200Hz, all synthetic settings. They do not supply the actual Studio cutoff. `ruff.txt` records final private-source lint. Notebook validation and diff checks pass; the run-directory redactor changed zero files. The first lint pass requested `pairwise` and explicit subprocess check flags; those style repairs did not alter settings or measured claims.

Interpret a future result using actual UI state and exported source identity. Preferential low-band attenuation relative to a materially powered reference supports a technical spectral change; a uniform level shift alone does not. Reference-band processing, re-encoding, limiting, frequency-dependent phase and weak bands limit attribution. Exact sample preservation, filter order/transfer function, project persistence and aesthetic improvement require separate evidence. No credentials, provider calls, UI actions, network access or installations occurred in this work package.
