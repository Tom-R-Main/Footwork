# Pointer recording overhead and clock calibration

Hypothesis: timestamping owned filmed pointer posts in memory preserves scheduling and increases p95 lateness less than 0.1 ms.
If true: fixture paths, deadlines, admission and outcomes match; raw uptime brackets all posts; paired p95 delta is under 0.1 ms.
If false: a fixture diverges, timestamps escape brackets, or p95 delta is at least 0.1 ms.
Design: real Footwork Python 3.12 clock reads compare monotonic_ns and CLOCK_UPTIME_RAW against ctypes mach_absolute_time/timebase. Run six alternating baseline/instrumented one-second paths with real scheduler and fake poster, no native input; baseline is loaded from the preregistration parent commit. Persist individual lateness samples and source identities. No heldout tasks or network.
Primary metric: instrumented minus baseline p95 lateness in milliseconds, over all posts.
Guardrails: no native event posting; exact fake-clock equality; preserve unrelated work.
Decision rule: accept if fixture equality and clock brackets hold and p95 delta is less than 0.1 ms; otherwise report and diagnose without changing pointer settings.
