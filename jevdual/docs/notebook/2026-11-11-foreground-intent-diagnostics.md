# Foreground intent refusal diagnostics

## FID1 · prediction · 2026-11-11 03:04
Hypothesis: current native foreground activation refusals discard the SDK's bounded structured reason, preventing diagnosis even though application input correctly remains withheld.
Test: public CLI simulated-Mac foreground click receives exact-window activation refusal with structured code/status/request acceptance and observed identity mismatch. Assert retained sanitized metadata identifies the failing checks without any application input, retry or raw private strings. Cover wrong/malformed identity, unknown strings and existing successful activation contracts.
Predicts: baseline has no foreground-intent diagnostic; a whitelist-only record carried through existing native_readback preserves useful reason/match booleans while every original gate and no-input refusal remains unchanged.
Against: diagnostic changes activation behavior, dispatches input after refusal, leaks raw text/error/URL/title/foreign identities, or guesses missing/malformed observations as matching.
Refs: results/foreground-intent-diagnostics-20261111/
