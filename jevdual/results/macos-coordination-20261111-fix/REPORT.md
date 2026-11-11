# Reservation fairness repair and macOS requalification

**Outcome: fairness fixed; all 15 final native macOS fixture checks pass.** The earlier playback stall did not recur in either an instrumented diagnostic rehearsal or the final ordinary CLI rehearsal. Its original cause remains unresolved. The 50 ms motion guard is unchanged, and new diagnostics preserve the actual refused interval if a stall recurs.

## Changes and source identity

- Fairness fix: `cd630bb`. A validated reservation owner may bypass only earlier **waiting** requests blocked by that owner's own reservation. Active/revoked/orphaned claims remain barriers. Ordinary FIFO, unrelated earlier waiters, and earlier requests using the same reservation retain their position.
- Motion diagnostics: `768967a87bd513756c42820e5888e441770d573d`. `DragResult` records `stall_gap_s` separately from gaps preceding successful posts, and `max_post_s` measures the complete poster call. Filmed gesture records expose those values in milliseconds. No admission threshold, scheduling rule, cancellation check, late-input refusal or release cleanup was weakened.
- Prediction commits `0b5bd34` and `b068949` precede the tests they resolve. Final runtime hashes, exact imported module and seven installed CUA source/native file hashes: [runtime.json](runtime.json).
- Host: macOS 26.5.1 arm64. CUA: `0.46.0+footwork.5486b624.cleanup2`. Existing dependency environment with the project checkout selected explicitly; no SDK install/overlay, global release activation, push or merge.

## Fairness evidence

The earlier real-kernel counterexample failed on the merged code. A new public simulated-Mac scenario also returned exit 7 (`resources busy`) when the reserved session tried its next observation while a competing subject observer waited: [public red](fairness-public-red.txt).

Four new coordinator continuation cases failed before repair, while six controls passed: [coordinator red](fairness-red.txt). The repair passes all **35 coordinator tests**, including resource hierarchy, extra-resource requests, ordinary FIFO, unrelated/same-reservation waiters and active/revoked/orphaned exclusion: [coordinator green](fairness-green.txt). The original public scenario now passes: [public green](fairness-public-green.txt).

The exact real-kernel reservation probe was rerun with the final runtime and passed all four controls. Owner admission with its blocked competitor still present took approximately 1 ms, rather than timing out: [probe](reservation-probe.json), [reproducer](reservation_probe.py). It uses a task-private registry and real macOS locks/SQLite without a driver.

The final live public-CLI check is stronger: the film owner's ordinary `look` completed successfully **before** cancelling its competitor, while the other native observer's request remained waiting. No waiter cancellation was needed to make the film owner advance. [Live evidence](live.json), criterion `reserved_owner_continues_with_waiter`.

## Playback investigation

The original failed take is retained in `../macos-coordination-20261111/`. Its record contained only successful-post gaps, so the saved 10.4 ms number could not identify the failed interval. We did not infer a root cause from that number.

The initial non-input checks found:

- The exact planned path had 87 samples and maximum scheduled interval 10.424 ms, below the existing 50 ms limit.
- Across 300 real ownership checks, median cost was 0.086 ms and maximum 1.077 ms. This rules out a persistently over-budget check in that isolated sample; it does not exclude transient contention.

During the timing-only diagnostic rehearsal, original public CLI/input methods ran with wrappers recording durations. All 15 checks passed. Maximum `Claim.check` time was 1.872 ms; the first native mouse call was the slowest post at 20.682 ms; maximum moving gap was 22.045 ms. [Timing summary](timing-summary.json), [diagnostic live results](live-diagnosis.json), [diagnostic source provenance](diagnosis-provenance.json). The raw trace remains private at the path in the summary. The long `sleep_until` after movement was the intended dwell, not an inter-post stall.

No measured stage in that successful attempt crossed the guard. A transient native/event/scheduling delay remains possible; neither coordinator overhead nor native initialization is established as the cause of the original failure. We therefore made no speculative performance repair and changed no guard threshold.

Four diagnostic regression assertions failed before the telemetry change: [red](stall-diagnostics-red.txt). Afterward, 27 motion/filmed/public-scenario checks pass: [green](stall-diagnostics-green.txt). Deterministic slow-check, oversleep and slow-post cases still abort safely; no late next event is delivered. The public simulated-Mac scenario verifies that the actual failed interval is retained while zero late events are posted.

## Final ordinary CLI macOS rehearsal

Source: `768967a`. No timing wrappers. The full offline suite finished before native fixture/input setup, so that test load did not contaminate this timing observation. The user explicitly handed over the desktop. Native actions touched only a new localhost Chrome profile/window and a separate task-only TextEdit process/document.

| Criterion | Result |
|---|---|
| Owned TextEdit native session | Pass |
| Owned Chrome native subject | Pass |
| Filmed native start | Pass |
| Desktop and subject reservation survives CLI exit | Pass |
| Saved observe-only access says `live: false` | Pass |
| Public pointer setup | Pass |
| Ordinary public filmed point | Pass |
| Concurrent independent native append with exact AX readback | Pass |
| Quartz pointer endpoint equals observed target | Pass |
| Background edit preserves foreground app | Pass |
| Fixture independently records target pointer hover | Pass |
| Film owner's next command completes while competitor remains waiting | Pass |
| Owner completes before competitor handoff | Pass |
| Revocation prevents further pointer input | Pass |
| Stale yield does not revoke a new explicit handoff | Pass |

[Live results and command identities](live.json); [reproducer](live_probe.py). The motion posted 86 planned samples and reached exactly `(550,477)` screen points. Maximum successful gap was **20.7 ms**, maximum post call **20.3 ms**, and `stall_gap_ms` is null. The independent page ledger recorded hover, and the TextEdit value equalled the initial text plus exactly one marker.

The six-second window-only H.264 recording was decoded and a frame inspected: the cursor is over the synthetic target and no unrelated windows are captured. [Capture metadata](capture-metadata.json). This is actual recording evidence for the fixture rehearsal, not a quantitative film-quality benchmark.

Private recording: `/Users/thomasmain/projects/footwork/.local-reviews/macos-coordination/jevdual/output/macos-coordination-20261111-fix/native-final/rehearsal.mov`.

## Checks and delivery

- Full default offline suite in the supported `JEVDUAL_PURE_PY=1` Jev profile: **2941 passed, 95 skipped, 66 deselected in 143.18 seconds**, [output](offline-full.txt). The exact patched CUA version assertion was included. Optional Jev Rust acceleration remains separate from the real CUA native engine used live.
- Full repository Ruff: pass, [output](ruff-full.txt).
- Independent fresh-agent static review of the six changed runtime/test files: no actionable findings, [scope and limits](review.json). It executed no tests or native actions; owner-run evidence is separate.
- Notebook validation and redaction are run before the evidence commit. The summary refers to actual retained run files rather than copying UI traces into the notebook.

[Cleanup](cleanup.json): both owned native app processes exited, no process retained the owned Chrome profile, the fixture server/capture helper exited, no active run-owned requests remained, and all run-owned reservations were explicitly revoked. Existing signed-in apps and Suno documents were not mutated. The old user-local installed Footwork release was not replaced.

Qualification applies to this source/SDK/host and the exercised app/desktop/point/background/control workflow. It does not establish arbitrary-app behavior, a universally stall-free desktop, actual button-held drag cancellation or hard-kill cleanup, cross-user ownership, native window-birth identity, or independent macOS Screen Sharing desktops. Earlier failures remain preserved; two successful later rehearsals do not explain away the original transient stall.
