# Selected Qwen/OpenRouter video route: controlled probe

Status: partial visual understanding; combined audio/video and fine-defect judgment failed this probe. This is one development check, not a general model ranking.

Preregistration: `docs/experiments/openrouter-media-live-20261110.md`, amendment committed in `e04fbd7`. Adapter at request time: TLS repair `e3eaecb`. Model/provider returned: `qwen/qwen3.8-omni-flash`, Alibaba. The full response and media hashes remain private under `output/suno-20261110/video-probe-review/` and `audio-probes/`.

## Known source versus response

The supplied MP4 is ten seconds, 320x180, 30FPS, with 300 video frames and an AAC mono audio track. It contains a white square moving rightward, blue background until5s then green, one black frame at4.4s, a static square during6–7s, and the previously qualified two-low/one-high tones.

| Check | Source construction | Qwen response | Outcome |
| --- | --- | --- | --- |
| Macro visual order | Blue then green; white square moving right | Identified these correctly | Held at coarse level |
| Single-frame flash | Black at4.400–4.433s | Reported no flash observed | Missed |
| Freeze | Approximately6–7s | Described smooth continuous motion and no pause | Missed; overgeneralized continuity |
| Audible events | Three isolated tones, verified in encoded MP4 | Could not confirm audible events, referenced supplied frames | Failed combined audio/video criterion |
| Spatial precision | Frame width320px | Estimated final x around360–400px | Inconsistent with source geometry |

This establishes some visual-content perception. It does not establish frame-complete exposure, reliable jank detection or that embedded audio reached attention. The provider did not return inspected-frame/interval coverage. Do not infer the exact preprocessing cause from the response alone.

## Independent checks on the same encoded file

FFmpeg blackdetect with a0.01s duration threshold reported4.400–4.433333s. Freezedetect with a0.4s duration threshold reported5.966667–7.000s. These agree with the constructed defects. AAC decoding and silencedetect show non-silent windows at approximately2–3,4–5 and6–8s, confirming the file itself contains the tones.

Commands and raw outputs: `output/suno-20261110/audio-probes/video-defect-detection.txt`, `video-audio-detection.txt`, and `video-ffprobe.json`. The chosen filter settings distinguish this known fixture; they are not universal acceptance thresholds for artistic media or static UI screens.

## Operational frictions

The old helper's120s socket timeout did not bound total elapsed time; the request returned only after several minutes. It completed before parent termination, so no process was killed and no inference was repeated. A separate source repair adds a total exchange deadline with retained uncertainty about remote completion after cancellation.

Although the request specified max_tokens1500, the response reports32300 completion tokens, including31982 reasoning tokens, for cost$0.01531165. The parameter did not bound all reported reasoning on this route. Explicit reasoning control and response accounting require qualification before another video request.

Six successful requests so far have a combined reported cost of$0.01983876, including audio probes and references. No automatic retries or fallback models were used.

## Consequence for the workflow

Use actual audio parts for listening and test explicit audio plus video if synchronized review is needed. Keep deterministic frame/audio measurements and source timestamps alongside the critic. Require timestamped findings to survive a targeted reinspection; a broad smoothness judgment is insufficient. The requested Suno UI journey remains independent of this perception probe and is still blocked on rich-text delivery at this report boundary.

## Follow-up: explicit audio sidecar and reasoning control

A new, preregistered joint-input request on helper72bd20b supplied the same MP4 and its original ten-second WAV as separate content parts, with reasoning.enabled=false. Qwen then reported two short beeps and a sustained tone alongside the correct macro visual sequence. Relative pitch was omitted; exact timing and geometry remained inaccurate, and the flash/freeze were still missed. The complete SUN13 prediction is inconclusive, while the audio-sidecar and reasoning-control mechanisms have positive evidence.

The response reported zero reasoning tokens,137 completion tokens and cost$0.00020179 within the60s total exchange deadline. This is one changed-payload/settings request, not a controlled performance comparison. Seven successful requests now report a combined$0.02004055. Source/response manifests: output/suno-20261110/joint-probe-review/. No claim of full-frame exposure or synchronized vendor attention is made.
