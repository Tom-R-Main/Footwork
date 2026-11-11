# Immediate-start pointer repair — November 11, 2026

Status: the fixed installed CLI passes all 15 native qualification criteria with
immediate recording startup, no capture startup sleep and no timing wrapper.

## Defects and repair

`bfbd44e` repairs the direct Quartz player; `2930faf` includes the corrected notebook
IDs and preregistered installed qualification. The active full-profile installation
selects exact commit `2930faf4bfa5818fb33bd3369e92f843810ded13` from local branch
`codex/macos-pointer-startup-fix`. This change has not been merged or pushed.

The timed loop previously constructed its first mouse event through lazy PyObjC
bridges, immediately treated a submitted position as delivered, and could return
success after a slow final post because no next sample checked its elapsed time.
It also checked foreign-input fences before a scheduled sleep rather than after it.

The repair prepares a nonposted mouse event and resolves posting before playback
starts. Each actual post must obtain matching pointer readback before another post
or success. Posting, checks and acknowledgement share the original pre-post 50 ms
budget. The original `1.5 * max_step + 2` spatial contention threshold still refuses
immediately; matching readback requires float32-equivalent coordinates, with no new
spatial grace. Cancellation, ownership and foreign key/button checks stay active
while waiting and are checked freshly after scheduled sleeps. The telemetry adds
`max_ack_ms` separately from `max_post_ms` and the failed interval.

Pointer acknowledgement establishes location, not event provenance or application
handling. The existing first-cut position/counter detector still cannot identify
every transient foreign motion between observations; no passive tap or new OS
permission was introduced. The stricter precision assumption is supported by
retained coordinates on this Mac, not a universal Quartz guarantee.

## Evidence before the fix

Five no-input fresh-process probes measure first mouse-event construction at
16.8–23.7 ms; later construction is below 0.007 ms (`cold-quartz.json`). New-source
no-input probes move that work into preparation; the first subsequent unposted
event takes 0.007–0.009 ms (`prepared-quartz.json`). Total constructor preparation
also includes importing Quartz and must not be compared directly to only an event
construction measurement.

The retained immediate-start failed take submitted sample 19 while its rounded
refusal coordinate is within 0.024 pt of earlier sample 14. Its final readback is
exactly sample 19 after float32 rounding (`retained-trajectory.json`). That is
consistent with queue lag but does not independently identify the moving actor.

After a fresh explicit desktop handoff, the unchanged installed `f821f03` fixture
with timing-only wrappers and immediate recording startup passes all 15 criteria.
Its trace measures first event construction at 6.06 ms, first native post at
13.68 ms, and location snapshots up to 8.90 pt behind the most recently submitted
sample (`diagnostic.json`, `diagnostic-stages.json`). Neither intermittent native
failure recurred. Both owned apps exited; requests cleared and owned reservations
were revoked (`diagnostic-cleanup.json`). Raw timing rows and recordings stay in
private `output/pointer-startup-20261111/`.

Apple documents [event posting as stream insertion](https://developer.apple.com/documentation/coregraphics/cgevent/post(tap:).md),
without an acknowledgement of pointer delivery. The source and native trace show
why submitted position cannot be assumed to be current readback.

The original playback stall occurred after its first posted sample, but its failed
interval/stage was not retained. Cold construction is a demonstrated avoidable
source of timed-loop work, not a proven complete historical attribution. Genuine
scheduler/native-post stalls still intentionally refuse at 50 ms.

## Offline checks

Before implementation, black-box regressions produce 12 failures and two passing
outside-tolerance controls (`delivery-red.txt`). They cover real QuartzPoster with
fake cold Quartz, delayed delivery, missing delivery, a slow final post, interruption
during delivery, and the public simulated-Mac point boundary. A further two-case
red run demonstrates foreign input during scheduled sleep can precede an unintended
move (`delivery-fence-red.txt`).

The repaired focused suite passes all 197 tests (`focused-final.txt`). Controls
cover one outstanding post, final actual endpoint, outside-tolerance immediate
refusal, cancellation/foreign keys, exactly one drag release, float32 readback
equivalence, and a 30 ms post plus 30 ms delivery refusing at the original shared
50 ms deadline rather than resetting its budget.

The full offline run has 3,015 passed, 106 skipped and one failure: a duplicate
notebook entry ID (`offline-full.txt`). Only that package's entry identifiers were
corrected afterward; the notebook test and full validator then pass
(`notebook-green.txt`; validator output in private output). No runtime changed after
the full run. Full Ruff passes (`ruff.txt`). Independent static review finds no
actionable issue; that reviewer ran no tests or UI (`review.json`).

## Installed artifact

A bundle built from the exact committed archive installed offline into a fresh
versioned full-profile release. Exact CUA remains
`0.46.0+footwork.5486b624.cleanup2`. All 218 Footwork runtime/resource files and
eight CUA files match the wheels before activation and through the stable launcher
after activation (`qualified-preparation.json`, `release-verification.json`,
`active-verification.json`). Product commands pass from an owned directory outside
the checkout with deliberately hostile cwd/PYTHONPATH modules; isolated Python
imports only the installed product.

The stable launcher is unchanged. `current` was advanced atomically, and the
previous `f821f03` release remains available. See `activation.json` and the new
release's `footwork-release.json`.

## Ordinary installed immediate-start qualification

After a fresh explicit desktop-ready reply, `installed_probe.py` launches every
product command through `/Users/thomasmain/.local/bin/footwork` from the owned
host directory outside the checkout. The isolated helper Python and the product
both import from the new release. It starts the owned-window recording and then
immediately starts the point command alongside the independent background append.
There is no sleep between capture startup and product motion launch. Initial
handoff idle checking, app setup and post-action readback remain as before.

All 15 criteria pass (`installed-live.json`): native starts, persistent subject and
desktop reservation, saved observe-only state, pointer setup/approach, exact AX
background append, preserved foreground PID, independent Quartz endpoint and
page hover, reserved owner completing while its competitor still waits,
cancellation fencing, and stale-token yield preserving the newer owner.

| Native motion metric | Observed |
| --- | --- |
| Posted samples | 86 of 86 moving samples |
| Largest successful posting gap | 21.6 ms |
| Largest posting duration | 11.7 ms |
| Largest acknowledgement duration | 9.8 ms |
| Failed stall interval | None |
| Independent expected / observed endpoint | (550, 477) / (550, 477) |
| Existing gap limit | 50 ms, unchanged |

The 6.087-second H.264 recording decodes successfully. Its inspected two-second
frame shows the pointer on the owned target. The page independently records
`pointerenter`; no native click/button-down was performed. Both task-owned app
PIDs are absent, requests are empty and all run-owned reservations are revoked
(`installed-cleanup.json`). Recordings/decoded frame remain private.

## Decision and limits

Keep the fixed installed release active and retain the prior release for rollback.
Cold bridge work is outside playback, asynchronous pointer delivery is bounded
without queuing several positions, and final-post stalls cannot report arrival.
The installed immediate-start fixture is qualified; no startup-delay result is
substituted for it. The fix remains committed locally and is not merged/pushed.

One successful native run does not prove general reliability or identify the exact
phase of the original untraced stall. Its historical cause remains partly
unresolved; the demonstrated player defects and retained negative controls support
the repair. Arbitrary OS scheduling stalls still fail closed at the same limit.
This fixture does not qualify arbitrary apps, other users/desktops, held-button
native cleanup, event identity, provider behavior or human acceptance.
