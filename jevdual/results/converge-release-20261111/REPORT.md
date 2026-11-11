# Converged release 6d571a1: build, live qualification and activation — November 11, 2026

Status: the release built from PR #24 at `6d571a1ed7c7bf77576279a01053f77fc20ce469` passes all 20
live criteria on macOS and is the active user-local release. The previous release `eded45c` is kept
for rollback. The largest posting gap was 47.8 ms against the unchanged 50 ms limit, much closer
than the previous qualification's 21.6 ms. Notebook: CVM2 to CVM4 in
`docs/notebook/2026-11-11-converge-main.md`.

## Driver

The branch pins `cua-driver==0.46.0+footwork.5486b624.cleanup2.focus1`. A first attempt with the
`…focus1.helptag1` wheel was refused by the bundle builder and cannot resolve against the pinned
`desktop` extra (`driver-blocker.json`, CVM2). The release uses the pinned focus1 wheel, SHA-256
`22083ce34aa45a2404bda2b27ad120156c7380da8a659879e00df139a69393ec`, whose hash and eight files match
`results/foreground-web-text-20261110/` and whose source archive is the vendored one in
`vendor/cua-driver/PROVENANCE.md`. That the native library was built from that source rests on the
recorded build, not a rebuild.

Compared with `eded45c` (cleanup2) this adds the foreground text-focus patch. It lacks the HelpTag
repair the Suno menu route was qualified with; `eded45c` lacks it too. Shipping helptag1 needs a
packaging change.

## Build, install and verification

- Built from a `git archive` export of the exact commit with `scripts/build_agent_bundle.py --profile
  full`; the product wheel is reproducible across two builds (`install-summary.json`).
- Offline suite for the commit, browser-launching tests excluded: 3415 passed, 98 skipped, 2 failed,
  both environment-only in the development virtualenv (driver pin, native-backend scaffold check).
- Installed offline into a new prefix; all 219 product files and 8 driver files match their wheels;
  commands pass from a hostile working directory and `PYTHONPATH`, importing only from the release
  (`release-verification.json`).

## Live qualification

Run through the new release's own interpreter, before activation, by `release_probe.py`. The CVM3
prediction was committed and pushed (`1cbc0a7`) before the run. The idle gate waited about 16
minutes while the owner was active and started at 15.9 s idle with the screen unlocked. Owned
TextEdit and Chrome processes and a local fixture page only.

All 20 criteria pass (`release-live.json`): native, subject and filmed starts; persistent desktop
and subject reservation; saved observe-only state; pointer setup and filmed approach; exact
independent background append; pointer readback at (550, 477); the person's front application
untouched; independent page hover; the reserved owner finishing while a competitor waits; revocation
fencing the pointer (exit 7, pointer unmoved); a stale yield preserving the newer owner; a complete
`pointer_gesture/1` record with real post timings; recorded posts equal to moving samples; the gap
under the unchanged limit; the record's endpoint matching readback; a revoked point recording no
posts.

| Metric | This run | Previous qualification (PSTR3, `eded45c`) |
| --- | --- | --- |
| Posted / moving samples | 86 / 86 | 86 / 86 |
| Largest posting gap | 47.8 ms (posts 6 to 7) | 21.6 ms |
| Largest post call | 12.0 ms (first post) | 11.7 ms |
| Largest acknowledgement | 46.5 ms | 9.8 ms |
| Recorder call, median / p95 | 0.013 / 0.018 ms | not present |

CVM3 failed on its duration clause: acknowledgement took almost five times as long as in PSTR3. The
recorder itself costs microseconds, so the time is in main's unchanged wait for pointer readback
(inferred). One run cannot say how often a filmed move would now reach the 50 ms limit; when it
does, the move refuses rather than reporting arrival (`timing-summary.json`).

## Cleanup

Owned applications exited, coordinator requests are empty, both run reservations are revoked
(`release-cleanup.json`). The six-second recording decodes and shows the pointer on the target.
The browsers on ports 9333 and 9555 kept their process IDs and start times. The probe's own
protected-browser snapshot wrongly included Chrome helper processes; those helpers started before
the first owned command.

## Activation and rollback

With no Footwork process running and the coordinator empty, `current` was moved atomically from
`releases/eded45c48d550b6867e1ce1314de64c41cbcfae8` to `releases/6d571a1…`; the launcher is
unchanged (`activation.json`, `active-verification.json`). To roll back, point
`~/.local/share/footwork/current` at the `eded45c` release.

## Not verified

Traced drags and clicks with a yield or cancel mid-gesture; the AXFocused ownership fence against a
revoked owner; the HelpTag route; held-button cleanup; how often acknowledgement latency approaches
50 ms under load. Recordings and raw samples stay private in `output/converge-release-20261111/`.
