# Installed Footwork macOS qualification — November 11, 2026

PR [22](https://github.com/Tom-R-Main/Footwork/pull/22) is merged at
`f821f032a81ba567a4c20298789fae55f79edc78`. The stable user-local
`/Users/thomasmain/.local/bin/footwork` now selects that full-profile release.
Installed package/discovery checks pass. The native fixture passes all 15 criteria
with 1.5 seconds of recording setup before motion. The first immediate-recording
attempt remains a 12/15 failure with a safe pointer-contention refusal.

## Merge and source evidence

The merged source tree is `c0fdea1798105147ae4f4fb0617ebb1ac2292a30`, identical
to qualified PR head `a3f3ff5b14ca8cd2e0e83e77d5e5b434d8f1127b`.
The fairness change and motion diagnostics are included; no motion threshold or
contention guard changed during installation or the installed rehearsals.

The source qualification in `../macos-coordination-20261111-fix/REPORT.md`
records 2941 passed, 95 skipped and 66 deselected in the full source test run,
red/green fairness regression checks, and the previous source native rehearsal.
That full suite was not rerun against the installed wheel.

Main had no required checks or branch rules; none were bypassed or altered.
Five PR checks passed, including both macOS full consumers (Python 3.12/3.14),
both light consumers and the installed Linux browser job. Two Linux jobs failed
before product installation/tests while apt could not resolve Ubuntu mirrors.
See `merge-policy.json`, `ci-final.json` and `linux-ci-failure.json`.

## Installed artifact

Active release:
`/Users/thomasmain/.local/share/footwork/releases/f821f032a81ba567a4c20298789fae55f79edc78`.
The `current` symlink was switched atomically after inactive-release validation.
The previous `f5d41c482e158eac18b15f5820bd6be150f00097` release remains available.
The stable launcher's bytes were unchanged (SHA256
`8b786ec4bebfd7b8fe62e478f6e017ed2048fe31489395fc180b15978f49e793`).

The full bundle uses exact CUA `0.46.0+footwork.5486b624.cleanup2`.
All 218 Footwork runtime/resource files and eight CUA package files match their
wheels byte for byte in candidate, inactive, active and final verification.
The bundle hashes and dependency provenance are retained in `preparation.json`
and the installed `footwork-release.json`.

The initial offline candidate install refused uncached pinned dependencies.
An authorized binary-only network install warmed the cache; the final versioned
release installed offline. The temporary candidate was removed after confirming
it had no running processes (`candidate-cleanup.json`).

Actual stable-launcher tools, doctor, desktop-control schema and control status
passed from an owned directory outside the checkout, with a deliberately hostile
`PYTHONPATH`/cwd module. The launcher uses isolated Python (`-I`); imports resolve
inside the new release. Six unified discovery/simulator checks also passed.
See `final-verification.json`, `active-verification.json`, and `unified-cli.json`.

## Native installed execution

After the user's explicit idle-desktop handoff, every product command used the
stable installed launcher from the owned non-checkout directory. Helpers used
the new release's isolated Python. The fixture created a separate Chrome profile,
a loopback page and a separate TextEdit process/document, with exact PID/window
binding. It used a pointer approach, without a native click/button-down.

| Attempt | Result | Motion evidence |
| --- | --- | --- |
| Immediate recording startup (`live-cold-capture.json`) | 12/15 | Safely refused `pointer_contended:pointer_moved` after 19 posts; maximum successful gap 34.0 ms, maximum post 32.7 ms, no `stall_gap` |
| 1.5-second recording setup (`live.json`) | 15/15 | Arrived at independently read-back (550, 477), page `pointerenter`; 86 posts, maximum successful gap 11.7 ms, maximum post 11.1 ms, no `stall_gap` |

Both attempts passed reservation persistence, saved observe-only state,
independent AX text append without stealing the foreground, the reserved owner
completing while an earlier competitor remained waiting, explicit cancellation,
revocation refusing pointer dispatch, and stale-token yield preserving the newer
owner. In the first attempt, the three failed criteria were the approach and its
dependent endpoint/hover checks.

The successful take supports this ready-capture fixture setup only. One contrast
does not establish capture startup as the cause, qualify immediate-start capture
reliability, or explain the original source playback stall. Those causes remain
unresolved; diagnostics and fail-closed guards are retained.

Both recordings are valid H.264 captures; the ready-capture recording is 8.003 s.
Visual inspection of its 3-second frame shows the pointer over the task-owned
target. This corroborates the native endpoint/page readback without establishing
general application behavior or human acceptance. See `cleanup-capture.json`;
recordings/frame remain in private `output/installed-coordination-20261111/`.

Both runs report no remaining requests and revoked owned reservations.
Independent post-run checks found neither run's Chrome/TextEdit PIDs nor the
warm runner still present. No further pointer retry was performed.

## Decision

Keep the merged full-profile release active. Installed identity, discovery and
the tested macOS coordination behavior are verified, with a qualified 15/15
ready-capture fixture pass and the failed cold-start take preserved. Keep the
previous release for rollback. Do not label the unresolved motion causes fixed,
the cold-start path qualified, or overall hosted CI green.
