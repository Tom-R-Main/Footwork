# Native Return argument refusal

## EAR1 · prediction · 2026-11-10 16:49
Question: can the native CLI reject text that its Return-only enter operation currently accepts and misleadingly prints without changing enter's authority or input behavior?
Hypothesis: validating native enter arity after parsing and before secret resolution or driver binding prevents ignored text from appearing to have been typed, while retaining target-only Return and browser behavior.
Test: public CLI simulated-Mac scenarios for a nonempty tail, explicit empty argument, unresolved secret-looking tail, and target-only Return; reproduce the accepted ignored text before repair, then run affected session, CLI and authorizer checks.
Predicts: native enter with any trailing argument returns2 before binding, resolving secrets or dispatching; its error explicitly instructs type, observe/readback, then enter. Existing target-only enter still sends one Return; other routes and browser behavior remain unchanged.
Against: rejected text reaches a driver or history as delivered input, an empty tail is accepted, a secret-looking rejected argument is resolved, target-only enter no longer works, or the fix performs an implicit fill-and-submit.
Refs: docs/notebook/2026-11-10-suno-end-to-end.md; python/jevdual/session.py::parse_do; python/jevdual/native.py::NativeBridge.act
