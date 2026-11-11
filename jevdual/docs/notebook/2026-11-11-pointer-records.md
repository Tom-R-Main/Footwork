# Filmed pointer host-clock records

## PR1 · prediction · 2026-11-11 12:35
Question: can filmed pointer playback expose planned and posted samples without changing its path, admission, scheduling or outcomes?
Hypothesis: an optional in-memory observer around the existing poster calls, with CLOCK_UPTIME_RAW timestamps and serialization after playback, preserves fake-clock playback exactly and adds less than 0.1 ms to real-clock p95 lateness against the current player with a fake poster.
Test: scenario and player fixtures cover parks, automatic approaches, drags, more than 50 moves, contention and poster exceptions; paired one-second real-clock fake-poster runs compare existing lateness figures; real Python 3.12 clock reads bracket mach_absolute_time and posted samples.
Predicts: paths, scheduled deadlines and outcomes remain equal; every owned posted sample lies within raw-uptime reads; Python clock mapping is measured rather than assumed; p95 lateness delta is under 0.1 ms.
Against: a fixture changes delivery/admission, a timestamp lies outside its bracket, or paired p95 lateness increases at least 0.1 ms.
Refs: design/FILM-DIRECTION.md D1 and design/pointer-motion/PLAN.md section 3.6 in demogeek; results/pointer-records-20261111 (to be written)
