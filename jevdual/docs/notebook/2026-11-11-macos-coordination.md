# macOS qualification of merged desktop coordination PR21

## MACC1 · prediction · 2026-11-11 10:28
Hypothesis: merged ac892a75211900ca6e252a46bca4f0da2362af6b still applies its earlier-waiter fairness barrier to a valid reservation owner, creating circular waiting when a competing command queues during a filmed command gap.
Test: first run a small real-kernel coordinator scenario on macOS with a persistent desktop/app reservation, an earlier conflicting waiter and the reservation owner's next request. Preserve the failure before any product change. Check that cancelling the competitor lets the original owner proceed and that independent background resources are admitted.
Predicts: the reservation owner times out or stalls despite its valid token while the competing request cannot enter; after the waiter is cancelled the owner proceeds. This would block unrestricted filmed-reservation qualification even if all existing tests pass.
Against: the owner enters promptly with the earlier blocked waiter still present, or the suspected barrier is not reachable from the public CLI.
Refs: PR21 discussion_r4534724737; python/jevdual/coordination.py; tests/test_coordination.py

## MACC2 · prediction · 2026-11-11 10:28
Hypothesis: on this unlocked arm64 Mac with the exact cleanup2 SDK, the merged public CLI can bind a fresh owned native fixture, persist a filmed reservation across CLI exit, permit independent background native work and fence a canceled session without new pointer input.
Test: run focused and default offline checks using the merged checkout and existing dependency environment. On synthetic task-only windows and files, exercise public CLI start/look/control/point, independent app background append and independent readback, saved observe-only output, queued conflict behavior and explicit yield/cancel. Preserve the native window, process, SDK and source identities and cleanup outcomes. Check macOS HID idle before pointer moves; never evade a human_active or screen_locked refusal. If prerequisites or the circular-wait defect prevent a required check, mark that criterion failed/unverified rather than passing from fixtures. No provider calls, installation, global release activation or existing user-document mutation.
Predicts: live supported paths retain exact targets, an active take reserves both subject and desktop, unrelated background native input stays independent, and revocation stops further point commands. A small real pointer rehearsal is possible only with unlocked/idle desktop and owned observed targets.
Against: wrong resource mutation, pointer/focus interference, missing reservation, revoked input, unreadable real target, or inconclusive capture/input cleanup. Existing direct-library coexistence tests alone do not prove the CLI coordinator.
Refs: docs/desktop-coordination.md; docs/experiments/macos-desktop-coordination-20261111.md; results/macos-coordination-20261111/
