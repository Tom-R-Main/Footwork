# Filmed pointer host-clock records

## PGR1 · prediction · 2026-11-11 12:35
Question: can filmed pointer playback expose planned and posted samples without changing its path, admission, scheduling or outcomes?
Hypothesis: an optional in-memory observer around the existing poster calls, with CLOCK_UPTIME_RAW timestamps and serialization after playback, preserves fake-clock playback exactly and adds less than 0.1 ms to real-clock p95 lateness against the current player with a fake poster.
Test: scenario and player fixtures cover parks, automatic approaches, drags, more than 50 moves, contention and poster exceptions; paired one-second real-clock fake-poster runs compare existing lateness figures; real Python 3.12 clock reads bracket mach_absolute_time and posted samples.
Predicts: paths, scheduled deadlines and outcomes remain equal; every owned posted sample lies within raw-uptime reads; Python clock mapping is measured rather than assumed; p95 lateness delta is under 0.1 ms.
Against: a fixture changes delivery/admission, a timestamp lies outside its bracket, or paired p95 lateness increases at least 0.1 ms.
Refs: design/FILM-DIRECTION.md D1 and design/pointer-motion/PLAN.md section 3.6 in demogeek; results/pointer-records-20261111 (to be written)

## PGRU1 · update · 2026-11-11 12:46
Observed: prediction was preregistered under heading PR1 in commit 3b2eed5, before any resolving test. The global notebook validator found that PR1 was already used by 2026-10-10-pr-review-remediation.md. Candidate 90cc8f1 changes only this heading's ID to PGR1; its prediction body is identical. This is an administrative collision correction, not a claim that the PGR1 heading itself was committed before the tests.
Next: retain both commits as the preregistration evidence; resolve PGR1 from the named candidate's timing and clock probe.

## PGRU2 · update · 2026-11-11 12:46
Resolves: PGR1 = held
Observed: candidate 90cc8f1 and baseline b6a291b exact fake-clock post sequence, deadlines, final points, outcomes and lateness match for move and drag. Focused suite passes 43 tests including more than 50 session moves, automatic approach, SDK incompleteness, abort, poster exception and dwell interruption persistence. Six alternating one-second real-clock fake-poster pairs meet the preregistered p95 delta guardrail; report retains all individual lateness values and byte count. Python 3.12.6 CLOCK_UPTIME_RAW brackets mach_absolute_time converted by the reported timebase; both monotonic_ns and the actual monotonic float clock are within raw-uptime read brackets. results/pointer-records-20261111/probe.json, clock-float.json, focused-tests.txt.
Inferred: the owned post recorder meets the bounded offline prediction. Lower observed lateness is scheduler noise, not evidence that instrumentation speeds playback. The full suite was running concurrently, so the comparison is a shared-machine measurement. No native events were posted and actual WindowServer delivery remains untested.
Next: full-suite result and handoff; SDK follow-on pointer posts remain explicitly unavailable pending a separate native telemetry build.

## PGRU3 · update · 2026-11-11 12:52
Observed: 66192c9 corrects setup/title-bar trace labels when exceptions occur before the posting boundary; 168d5b1 separates recording_started_ns (including metadata preparation) from nullable playback_started_ns and motion anchor t0_ns. The final 168d5b1 focused suite passes 46 tests and the relevant native/session/posture subset passes 559. A full suite loaded at 66192c9 passes 3432, skips 62 and reproduces only the installed SDK version-pin failure; it is not represented as full coverage of the later timestamp-field change. Ruff and notebook checks pass. A fresh six-pair comparison on named 168d5b1 meets the p95 guardrail; individual samples, the increased single-sample maximum, record size and cold metadata/serialization costs are retained in results/pointer-records-20261111/final. Baseline reproduces the pin failure in baseline-pin.txt. report.md gives exact source/evidence boundaries.
Next: hand off the owned-path D1 subset with explicit SDK incompleteness and no native delivery claim.

## PGRS1 · summary · 2026-11-11 12:52
Established: filmed owned moves append versioned planned/post-boundary series to the session's pointer-gestures.jsonl without the legacy 50-summary cap; raw uptime clocks, requested target, measured final location, coordinate units, relevant display scales and conversion origins are recorded. Existing paths, scheduler deadlines and outcomes match the fixture baseline; exceptions retain partial evidence. Source is on codex/suno-end-to-end-20261110, commits 90cc8f1, 66192c9 and 168d5b1 after preregistration 3b2eed5; no push or native pointer input was performed.
Uncertain: CUA-owned hover/foreground-click internal posted samples remain unavailable and explicitly incomplete; native WindowServer delivery, complete D1 take acceptance and end-to-end CLI latency are untested. Cold metadata preparation and after-dwell append add invocation latency outside the unchanged scheduled path. Full-suite driver version pin is an independently reproduced environment mismatch.
Decision: hand off the implemented owned-path telemetry, exact schema/examples and bounded offline evidence; a separate native SDK telemetry build is required to close the every-route requirement.
Refs: results/pointer-records-20261111/report.md; final/probe.json; final/example-line.jsonl; final-full-tests.txt; final-broad-subset.txt; focused-tests.txt
