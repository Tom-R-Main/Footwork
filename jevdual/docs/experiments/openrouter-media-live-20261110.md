# OpenRouter media input qualification for Suno review

## Preregistration

User authorization: use qwen/qwen3.8-omni-flash through OpenRouter; local key entry confirmed. Ground new Suno test songs in the user's Softtrigr YouTube uploads and preserve originals.

Hypothesis: the selected OpenRouter route supplies actual audio bytes to Qwen, allowing it to distinguish a known synthetic tone sequence from silence and then ground musical observations in supplied song audio.

Prediction if true: using the same neutral prompt, the tone fixture produces a description of two equal low tones followed by one longer, higher tone, while the silent fixture is reported silent or without audible events. Coarse timing should correspond to the known sequence.

Prediction if false: unsupported media or authentication errors, empty output, identical generic music descriptions for silence and tones, invented speech/lyrics or reversed/missing tone structure. A text-only response is not media qualification.

Design: freeze the adapter commit before calls; generate two ten-second mono PCM16 WAV files at 24kHz. Probe A has silence except 440Hz tones at2–3 and4–5 seconds and an880Hz tone at6–8 seconds, with short edge ramps. Probe B is silence. Supply the same prompt, without the intended signal pattern, to both. Record media hashes, input bytes, actual returned model, usage/cost and output. No keys, base64 data or Authorization values in evidence. No automatic retries or model fallback.

Primary metric: both fixtures classified correctly and tone ordering/duration distinguished, judged against the generated signal. This is a bounded mechanism check, not a musical taste or accuracy-rate benchmark.

Guardrails: initially at most six paid requests, each at most2000 output tokens. The two probes use at most500 output tokens each. Abort and diagnose unsupported input, unknown billing outcome or credential failure before retries. Private media and full responses remain under ignored output/suno-20261110. Existing songs remain unmodified. Download/install prerequisites and live foreground access retain their existing approvals and guards.

Decision rule: if both probe conditions hold, inspect actual reference audio and derive timestamp-grounded creative briefs. If either fails, fix the transport/probe or report the boundary; do not infer sonic qualities from titles/descriptions. Song creation and editing still require independent UI and persistence evidence.

## Amendment · 2026-11-10 17:23

The first five successful paid requests completed audio discrimination and three full-song reference reviews for a reported total0.00452711 dollars. Exact timing remains inaccurate. Extend this development package's limit to eight successful paid requests, each requesting at most2000 output tokens, to qualify video input and retain room for edited-song playback review. This is a bounded continuation under the user's selected-provider authorization, not a provider fallback or automatic retry. Failed TLS handshakes did not establish model inference and their original evidence remains retained.

Video probe: ten-second MP4 at30FPS,320x180, with blue background before5s and green thereafter, a white square moving left-to-right, a frozen square during6–7s, one black frame at4.4s, plus the known two-low/one-high tone audio. Supply a neutral prompt without this construction. Primary requirement is correct macro color/motion order and distinction of audible events; short-defect localization is secondary and must not be assumed from a claim to have watched the clip. Record frame exposure as unknown when the provider does not return it. The one-frame flash is not a condition for proceeding with song review, but missing it limits jank-detection claims.

## Amendment · November 10, 2026 17:50 EST

Seven successful calls now report0.02004055 dollars. A video request demonstrated that requested max_tokens is not a hard total-token or spend limit: reasoning was accounted separately. The repaired helper records this limitation, disables reasoning explicitly by default, and enforces a total exchange deadline. Its joint sidecar probe reported zero reasoning tokens but did not qualify precise timestamps or fine video defects. These results are retained, not treated as full video perception acceptance.

Extend the package to eleven successful calls to cover actual generated-song audition and edited output. The remaining four calls are reserved for at most two candidate-song reviews, one edit-boundary review and one final whole-song review. No further synthetic perception probe is planned. Each call uses the selected exact model, explicit reasoning off, at most2000 requested output tokens and a180s total exchange deadline; these settings do not promise a hard vendor spend cap. Stop on unknown delivery or billing and reconcile rather than retrying.

Candidate reviews receive the same brief and rubric, with filenames/titles withheld where practical. Require audible observations, confidence and a proposed bounded change; do not accept invented lyrics or precise timing from this route. Choose against the user's reference characteristics while labeling model judgment separately from human taste. For the editor check, retain original/export hashes and measured durations, review actual audio around the affected boundary and independently verify saved state through Suno. A model preference cannot satisfy edit persistence or prove non-target audio preservation.
