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
