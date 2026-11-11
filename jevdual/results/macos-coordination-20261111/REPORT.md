# macOS qualification of merged PR21

**Verdict: broad filmed/multitasking qualification failed.** Basic native coexistence and control handoff passed on this Mac. A reservation-owner circular wait is reproduced both with real macOS kernel locks and the public CLI. The recorded filmed approach also stopped at the existing playback-stall guard, so successful smooth pointer travel is not qualified.

## Artifact and scope

- Reviewed merge: `ac892a75211900ca6e252a46bca4f0da2362af6b`, PR21, based on `f5d41c4`. Isolated branch: `codex/macos-coordination-qualification`; prediction commit: `74f44e8`.
- macOS 26.5.1, arm64. Exact imported source and all 17 changed runtime-file hashes: [runtime.json](runtime.json). The host's Darwin kernel version is 25.5.0; the macOS product version in runtime.json is authoritative.
- Used the existing project dependency environment with `PYTHONPATH` selecting this merged checkout, CUA `0.46.0+footwork.5486b624.cleanup2`. No focus1/helptag overlay or global release activation. The optional Jev Rust acceleration is absent in this source worktree; the CUA native engine is present and was used live. The supported pure-Python Jev profile is separate from the native macOS effector.
- User explicitly handed over the desktop for the rehearsal. Only a fresh localhost Chrome profile/window, a fresh separate TextEdit process/document, and task-owned session directories were driven. Existing Suno/signed-in windows were not targets.
- Live commands used the actual default per-user coordinator. Fixture setup created the owned apps; dispatch, reservation, observe/cancel/yield and the circular-wait scenario used the public `python -m jevdual.cli` entry point. Independent TextEdit AX readback, Quartz pointer/focus observations and fixture pointer events supplied postconditions.

## Blocking finding: a reserved owner waits behind its own blocked competitor

At `python/jevdual/coordination.py:204–209`, every earlier conflicting waiter is treated as a fairness barrier, including a waiter that the requesting owner's persistent reservation prevents from entering. This produces circular waiting during command gaps:

1. A filmed command exits, retaining its desktop/subject reservation.
2. Another operator queues a command touching the reserved subject or desktop.
3. The film's next command presents the valid reservation token, but waits behind that earlier command.
4. The earlier command cannot acquire until the reservation is released. The film stalls until the competitor times out or is cancelled. Public default timeout is 30 seconds; repeated competitors can repeatedly stall the take.

The real-kernel [counterexample](reservation_probe.py) uses the unchanged Coordinator with a private registry and actual SQLite/flock. The owner proceeds without a competitor, stalls with an earlier waiter, then proceeds immediately after that waiter is cancelled; independent background resources remain available. [Observed result](reservation-probe.json): owner admission failed after the explicit 0.3-second probe bound, with `resources busy`.

The live public-CLI check reached the same cycle with two ordinary `look` commands on actual native sessions: the subject observer was waiting, and the film owner was also waiting with its valid reservation token. Cancelling only the subject waiter's exact request token allowed the film's `look` to exit successfully. The recorded request snapshot is in [live.json](live.json), criterion `reserved_owner_continues_with_waiter`.

This is the same case raised by the PR's automated review at `discussion_r4534724737`; final merged source still contains the barrier. It is not inferred solely from that review.

Suggested repair, **not implemented**: allow a reservation holder to bypass earlier waiters blocked by that holder's own reservation, while preserving active/revoked/orphaned owner exclusion and fairness for other waiters. Add the specific command-gap counterexample and parent/child/partially overlapping resource controls before repair. Do not bypass all fairness whenever a token is present.

## Live criterion ledger

The harness recorded 15 assertions: 11 passed and four failed. Three failed assertions are downstream consequences of the single aborted pointer approach, not three independently diagnosed defects.

| Criterion | Result | Evidence / limit |
|---|---|---|
| Owned TextEdit native session | Pass | Public start, exact owned PID and filename |
| Owned Chrome subject native session | Pass | Public start, exact owned PID/title |
| Filmed native session | Pass | Public exclusive/filmed start with observed geometry |
| Reservation survives command exit | Pass | Registry retains desktop and subject app reservation |
| Saved observe-only access | Pass | Public output explicitly `live: false` |
| Pointer setup | Pass | Public `park --place`, actual Quartz position |
| Filmed approach | **Fail** | Public `point` exited 4: `pointer_contended`, `aborted:playback_stall` |
| Independent background mutation | Pass | Concurrent public native append; independent AX equality matches baseline plus exactly one marker |
| Pointer reaches target | **Fail** | Aborted take retained no successful endpoint; actual pointer remained near setup |
| Background preserves foreground | Pass | Same owned Chrome front PID before/after append |
| Page independently receives pointer hover | **Fail** | No target `pointerenter`, consistent with the aborted approach |
| Reserved owner continues past its blocked waiter | **Fail** | Actual two-waiter cycle described above |
| Owner resumes after competitor cancel | Pass | Public owner look completes after exact waiter cancellation |
| Revocation prevents further pointer input | Pass | Public point exits 7, reservation unavailable; Quartz position unchanged |
| Old token cannot revoke new handoff | Pass | Explicit reserve creates new token; stale yield leaves it active |

[Live summary and command identities](live.json). [Reproducible live harness](live_probe.py). Full stdout/stderr, session snapshots and the video remain private under the task's ignored `output/macos-coordination-20261111/native-live/` directory.

The recording is a real 6.010-second H.264 video, 2024×1524, captured from only the owned Chrome window. [Capture metadata](capture-metadata.json). A decoded frame was inspected and shows the synthetic fixture and cursor, without unrelated windows. Its existence proves capture worked; the approach failure means it does not qualify successful filmed motion.

Private recording path: `/Users/thomasmain/projects/footwork/.local-reviews/macos-coordination/jevdual/output/macos-coordination-20261111/native-live/rehearsal.mov`.

The motion guard's existing gap limit is 50 ms. The result records only successful-post maximum gaps, so the saved `10.4 ms` figure is **not** the interval that caused the abort. No instrumentation measured the failed interval. Recording overhead, first-event/native timing, background work and per-sample coordinator checks were not causally isolated; do not label this a proven PR timing regression. No guard threshold was changed and the failed take was not retried.

## Existing suite checks

- Focused coordinator, browser identity, filmed-session, posture, holder and exact CUA contract checks: **159 passed in 10.24 seconds**, [focused.txt](focused.txt). Native UI in those tests is simulated except the explicit live rehearsal above; coordinator tests exercise actual processes and OS locks.
- Initial default offline sweep: **1 failed, 2927 passed, 93 skipped, 66 deselected in 147.43 seconds**, [offline-full.txt](offline-full.txt). The only failure is `tests/test_scaffold.py::test_backend_matches_env`: this worktree has no optional Jev `_core` extension and auto-selects pure Python, while that assertion requires the explicit pure-profile environment flag. No native CUA version check was deselected.
- Explicit supported pure-Python profile full sweep: **2926 passed, 95 skipped, 66 deselected in 144.53 seconds**, [offline-pure-python.txt](offline-pure-python.txt). Two additional native-core checks are skipped under the explicit pure profile. This profile keeps real CUA installed and does not simulate native input in the separate live harness.
- Ruff of the relevant merged runtime/tests passed, [ruff.txt](ruff.txt). Notebook check and result redaction are recorded before the evidence commit.

Commands from this worktree's `jevdual/`:

```sh
PYTHONPATH="$PWD/python" /Users/thomasmain/projects/footwork/jevdual/.venv/bin/python \
  -m pytest -q tests/test_coordination.py tests/test_browser_target.py \
  tests/test_filmed_session.py tests/test_posture.py tests/test_browser_holder.py \
  tests/contract/test_cua_driver_seams.py
JEVDUAL_PURE_PY=1 PYTHONPATH="$PWD/python" \
  /Users/thomasmain/projects/footwork/jevdual/.venv/bin/python \
  -m pytest -q -m 'not browser and not live'
```

Probe scripts refuse existing scratch directories; choose fresh task-only output paths for another run. They are qualification artifacts, not a new general-purpose verification framework.

## Cleanup and limits

[Cleanup evidence](cleanup.json): both owned app processes exited; no process retained the owned Chrome profile. Default coordinator had no active requests and both run-owned reservations were explicitly revoked. No button-down or keyboard injection was used by the filmed point path. The fixture server and capture process exited. The first preflight refusal for recent human input is retained in [live-preflight-refusal.json](live-preflight-refusal.json); no native fixture/input started on that refused attempt.

Qualified subset: this exact source/dependency combination on this Mac can create/persist reservations, perform an independent native background append while a take owns another app, preserve focus, read saved observations, cancel further pointer work and protect a new handoff from a stale token.

Not qualified: continued takes with queued competitors, successful smooth filmed pointer travel under the exercised concurrent/capture conditions, actual drag/button-held cleanup on this Mac, hard-kill recovery after actual held input, arbitrary apps, cross-user control, window-birth identity, independent Screen Sharing desktops, or the old user-local installed Footwork release. No product source was changed or installed. The confirmed circular-wait defect should be repaired and rerun before a broad macOS filmed multitasking claim.
