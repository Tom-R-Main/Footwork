# Softtrigr reference audio and first test brief

November 10, 2026. These are delegated Qwen audio observations with independent file/level measurements, not human acceptance or a calibrated music-quality evaluation.

## Source and perception evidence

The user selected their Softtrigr YouTube channel as musical grounding. Three full uploads were retrieved with the user-approved project-local yt-dlp installation, decoded/transcoded to MP3, and inspected with ffprobe. The source is lossy public-upload audio, not a Studio master. Original/reference songs were not edited.

Reviewer: `qwen/qwen3.8-omni-flash` through OpenRouter, returned provider Alibaba. Each full MP3 was supplied in `input_audio` with the same prompt and without title, lyrics or description as hints. Private manifests retain media SHA256, bytes, model/provider, response IDs and usage under `output/suno-20261110/`.

| Reference | Duration | Qwen's sonic observations | Proposed element to carry forward |
| --- | --- | --- | --- |
| [Te Trago](https://www.youtube.com/watch?v=WdPvcBVtUw0) | 350.656s | Spanish intimate breathy/spoken-sung vocal; sparse reverberant guitar, low pulsing bass, languid atmosphere | Vocal proximity and hypnotic low end |
| [Cleanup Complete](https://www.youtube.com/watch?v=zxXXIYkO2Ek) | 311.339s | English breathy voice, sparse slow piano, reverberant empty space and an AI-erasure narrative | Melancholy piano and quiet space; original new theme |
| [Encore, Silence](https://www.youtube.com/watch?v=pdyM3pFvCCU) | 217.429s | French/English intimate male vocal, electronic house pulse, warm pads and vinyl/static texture | Bilingual phrasing, restrained dance pulse and tactile noise |

The model also suggested technical issues, including sibilance and bass overlap in Encore, Silence. Those remain hypotheses; they have not been independently confirmed by expert listening. Describing a track as compressed or quiet is not itself a measured defect.

## Independent signal measurements

FFmpeg `ebur128=peak=true` measured the supplied MP3 files, without producing normalized replacements:

| Reference | Integrated loudness | Loudness range | True peak |
| --- | --- | --- | --- |
| Te Trago | -19.0 LUFS | 6.0 LU | -0.4 dBFS |
| Cleanup Complete | -20.5 LUFS | 9.5 LU | -0.1 dBFS |
| Encore, Silence | -17.2 LUFS | 7.4 LU | -0.5 dBFS |

These figures describe the retrieved/transcoded files. They do not prove whether a sound is intentional, establish absence of clipping in an earlier master, or grade musical quality.

## Known reviewer limitation

A preregistered ten-second synthetic audio test distinguished silence from two low tones followed by a longer high tone. The model's reported intervals were off by roughly one to two seconds and overstated tone durations. Use its song timestamps as approximate localization hints; use editor time and source-audio measurements for exact boundaries. OpenRouter reported audio_tokens0 despite supplied audio and successful discrimination, so usage accounting is not an inspection-coverage certificate.

The two successful probes cost $0.00042524 combined; the three reference reviews cost $0.00410187 combined, as reported by OpenRouter. Five successful paid requests have run. No fallback model was used.

## Original test brief

Title: **Sous le signal (Footwork Test 2026-11-10)**.

Combine close French/English vocals, a sparse melancholy felt-piano motif, warm pulsing sub-bass and restrained minimal-house rhythm. Keep negative space, a compact structure and an ending with room to decay. Use original lyrics about retaining a human pulse in a quiet machine world. Do not cover an existing melody or reuse the reference lyrics.

Run-owned full and short input drafts are in `output/suno-20261110/draft-brief/`. The shorter intended version fits the current bounded readback limit. An attempted shorter Styles revision did not read back as applied, so the original long Styles prefix remains the observed state. Title entry was confirmed; lyrics entry exposed an unresolved rich-text failure. No generation was submitted at this report boundary.

The first intended editor operation is a bounded ending fade saved as a derivative, followed by reopened-state and playback comparison. Neither is complete yet.
