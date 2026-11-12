# Filmed pointer record handoff

Implementation checkout: `/Users/thomasmain/projects/footwork`, branch
`codex/suno-end-to-end-20261110`. Preregistration `3b2eed5`; primary implementation
`90cc8f1`; trace exception-classification fix `66192c9`; final playback-boundary metadata `168d5b1`. No push, install, native
pointer posting, or recorder take was performed. Existing `.venv` imports the
edited source directly.

## Record

`footwork park X Y --session S` appends `S/pointer-gestures.jsonl`, as do `point`,
automatic filmed approaches, drag, setup placement, and owned title-bar input.
No retention cap; legacy summary still keeps its latest 50. Successful session
replacement resets the artifact transactionally; refused replacement retains it.
The schema and completeness contract are documented in `docs/pointer-records.md`.
`final/example-line.jsonl` is one complete small fake-poster line with real raw-clock
stamps; `final/example-one-second.jsonl` is a 120-post one-second fixture, 24,695 bytes.
Neither is evidence of live pointer motion or OS event delivery.

**Known gap:** SDK hover and explicit foreground-click post internals are opaque.
They get additional records with `completeness: unavailable_sdk_samples`, null
sample series, raw call bounds and measured before/after geometry. They cannot be
used as complete D1 paths. A native SDK telemetry build remains necessary; the
change does not substitute or refuse these existing input routes. Full planned
pointer-motion section 3.6 provenance/hash fields are also outside this subset.

## Evidence

- Baseline focused tests: 29 passed (`baseline-tests.txt`).
- Final focused tests: 46 passed (`focused-tests.txt`), including raw clock
  brackets, >50 moves, origin/scale metadata, point/click/drag, opaque SDK flags,
  partial aborts, post exceptions, pre-post exceptions, dwell interruption,
  title-bar down/up/warp and session replacement.
- Historical fake-clock comparisons assert identical event sequence, deadlines,
  final points, outcomes and lateness for both players (`final/probe.json`).
- Final relevant broad subset: 559 passed (`final-broad-subset.txt`) on `168d5b1`.
- Full repository Ruff check passes (`ruff.txt`); notebook check passes
  (`notebook-check.txt`). Full suite loaded at `66192c9`: 3432 passed, 62 skipped,
  one baseline-reproduced SDK pin failure (`final-full-tests.txt`). The later
  timestamp-field semantic change is covered by the final 46 focused and 559
  relevant broad tests; no final-full claim is made for `168d5b1`.
- Intermediate suite loaded modules during review fixes: 3430 passed, 62 skipped,
  one existing SDK version-pin failure (`full-tests.txt`). A subsequently
  interrupted verification is retained separately. Neither is presented as the
  final frozen candidate's full-suite result.
- Baseline independently reproduces the pin failure (`baseline-pin.txt`): installed
  `0.46.0+footwork.5486b624.cleanup2`; expected `focus1` or `focus1.helptag1` suffix.

Python is Footwork's `.venv` 3.12.6; `time.monotonic` implementation is
`mach_absolute_time()`. 100/100 RAW brackets contain converted mach ticks, and
100/100 contain monotonic_ns (`final/probe.json`). Direct float `time.monotonic()` reads
also bracket 100/100 (`clock-float.json` and independent
`clock-monotonic-float.json`). The measured timebase is 125/3. The maximum final-probe mach
read bracket was 1,209 ns; the reader interval is the uncertainty, not an assumed
clock offset. The playback scheduler remains monotonic; its anchor is paired to
RAW with a recorded interval.

Six alternating baseline/instrumented one-second real-clock, fake-poster pairs:

| Lateness, ms | Baseline | Instrumented |
|---|---:|---:|
| p50 | 0.001375 | 0.001333 |
| p95 | 0.002875 | 0.002751 |
| maximum | 0.066708 | 0.206208 |
| maximum gap | 8.397542 | 8.538375 |

P95 delta is -0.000124 ms, within the preregistered +0.1 ms guardrail. The
maximum single-sample lateness increased by 0.139500 ms. These measurements do
not establish zero overhead or a speedup. All outcomes arrived, with gaps below
the existing 50 ms stall limit. The full suite ran concurrently; individual
samples and source hashes are retained in `final/probe.json`. The measured final
candidate is `168d5b1`; earlier `90cc8f1` results remain in the parent directory
for provenance and are not substituted for the final measurements.

Thirty standalone metadata/serialization measurements on the final record
(`final/record-overhead.json`): metadata preparation median 0.066625 ms, maximum
149.567083 ms (cold AppKit import); JSON encode plus append median 0.278834 ms,
maximum 0.423500 ms. These are outside scheduled playback; the existing dwell is
unchanged, and append happens after it. `recording_started_ns` distinguishes
metadata preparation from the actual `playback_started_ns`. Cold preparation can
add invocation latency before the scheduled path starts; end-to-end native CLI
latency was not measured.

## Owned implementation line counts against b6a291b

| File under jevdual/ | Added | Removed |
|---|---:|---:|
| .gitignore | 3 | 0 |
| docs/experiments/pointer-records-20261111.md | 9 | 0 |
| docs/notebook/2026-11-11-pointer-records.md (prereg only) | 9 | 0 |
| docs/pointer-records.md | 59 | 0 |
| python/jevdual/ax.py | 11 | 3 |
| python/jevdual/drag.py | 16 | 1 |
| python/jevdual/filmed.py | 58 | 3 |
| python/jevdual/native.py | 56 | 17 |
| python/jevdual/pointer_trace.py | 144 | 0 |
| python/jevdual/session.py | 6 | 2 |
| scripts/pointer_record_probe.py | 186 | 0 |
| tests/test_pointer_records.py | 320 | 0 |

Runtime code: six files, +291/-26. All preregistration/implementation files: twelve, +877/-26. The total above includes the prerequisites,
fixtures, reusable probe and schema documentation; result artifacts and notebook
outcome updates are separate evidence, not runtime changes.
