# Linux next tranche: source-grounded implementation sequence

Grounded 2026-10-30 against the cloud evidence through `2e4afc9` and eight local reference repositories. Recommendation: make the existing X11 path reproducible under cold start, partial failure and cancellation before expanding application or Wayland support. The next implementation tranche is bounded by sections 1–3 below; sections 4–6 are later gates.

## Evidence and source versions

Observed in Codex Cloud: Debian 13/native x86-64 ran 2,434 regression tests and 13 browser tests, plus installed CLI/MCP append, replay/restart, exact saved-file checking, synthetic OCR and simulator checks. Rootless Openbox search paths and a recovered Mousepad session exposed separate setup failures. The `045fc5d` receipt correction failed against the real SDK envelope. See [acceptance](../results/linux-vm-acceptance-20261030/report.md) and [negative retest](../results/linux-vm-save-receipt-20261030/report.md). These are different artifact/run records, not one final green result.

The source study is read-only. No reference repository was fetched, built, installed or modified. Thirty cited files were compared byte-for-byte with their checkout HEADs; [the snapshot manifest](../results/linux-next-tranche-20261030/reference-snapshots.json) records revisions and SHA256. All paths in the source descriptions below are relative to `/Volumes/External SSD/referencerepos/`.

| Repository | Observed HEAD | Relevant contract |
| --- | --- | --- |
| CUA | `2d974f1843c7343a70affba9d21e7362979edec3` | Public reply decoration; X11 ownership; AT-SPI; compositor identity/input |
| Coder | `b15958555d9e7904055b0c2a76c511e53f044a3d` | Reaping, signal and subprocess wait ownership |
| systemd | `8cd79c27cf58ae24fa21378ddbe11962d0294db8` | Readiness, partial-start cleanup, process-tree shutdown and controller limits |
| Selkies | `58b6c350cd29ee4f4a2423ea1cbf9f927979064f` | Bounded X handshake and desktop search paths |
| Xpra | `5f4bcc672d4267ce59e6dbe75f94cb6783d3d518` | XRes versus client PID claims; property invalidation |
| LibreOffice | `6a31b3dc8666ac89c50582f11897764f83ab4227` | Toolkit text offsets, document model and save transitions |
| Hyprland | `27bdfef92d25c73b51a1cc0c3defded09e0a0344` | Compositor identity, activation, locks and callback lifecycle |
| River | `65a908430dddc6728a5f71c89974b786e48302fb` | Window identity versus creator PID; WM authority; logical coordinates |

The `linux/` kernel checkout named in the Linux skill's older inventory is absent. No kernel-source, physical-seat or hardware conclusion follows from this study. Containers share their VM's kernel; Debian userspace and a reference source revision do not identify that running kernel's behavior.

Footwork still builds CUA from pinned source `d5373879e9e0baf5a63999ac4d26902340c0ce20`. The reference CUA HEAD is newer. Its patterns are candidates for comparison; adopting them requires an explicit source/build change and seam qualification. No dependency bump is part of this plan.

## 1. Close the public SDK receipt contract

Observed: Linux's foreground transaction refuses before the input body if activation cannot be confirmed. The platform tool produces `code/detail/effect/suggestion`; the core subsequently adds `hint` and `next_call`. Inspecting the producer alone missed the actual public SDK boundary. The captured cloud ToolResult has all six fields, no ActionResult and `effect=none`.

Reference: `cua/libs/cua-driver/rust/crates/cua-driver-core/src/recovery_hint.rs:1028–1058` documents and implements decoration at the dispatch seam. The same mechanism is present in the pinned source and demonstrated by the [recorded SDK reply](../results/linux-vm-save-receipt-20261030/045fc5d-refused-profile-sdk.json).

The local correction permits those two optional metadata keys while preserving the error/code/effect/no-action predicates. Neither advisory field is interpreted or executed. Unknown semantic fields and contradictory delivery retain uncertainty. A public CLI scenario reconstructs the actual `cua_driver.ToolResult`; the actual capture fails before the correction. This closes the local replay gap, not the pending real installed-cloud repeat.

Acceptance: rebuild and byte-check the installed wheel; repeat the broken-WM save with unchanged disk bytes, `refused`, `dispatched=false`, zero delivered input and no save readback. Then run the fresh-profile working control through saved-byte verification. Keep both receipts and the SDK envelope. Minimal mocks alone no longer satisfy this seam.

## 2. Make the isolated X11 session a bounded lifecycle

Observed Footwork gaps: `scripts/linux/desktop-session.sh:25–47` can block inside `XOpenDisplay`, publishes `started` immediately after spawning Openbox/Mousepad, and inherits application config/state. Its cleanup signals direct children and uses unbounded `wait` (`:16–22`). The cloud runs demonstrate why an open X connection, a live editor process and an exact editable target are different states.

Sources:

- Selkies `addons/base/services/xvfb/run:85–115` separates socket existence from a timed handshake, checks server liveness and fails startup. `addons/desktop/services/lxqt/run:67–82` describes missing desktop wrapper search paths; `addons/base/container-entrypoint.sh:35–43` establishes a private runtime directory. Use these contracts; do not copy home-directory configuration deletion from the desktop recipe.
- systemd `man/systemd.service.xml:229–236` separates execution from readiness, and `:557–594` covers partial-start cleanup. `man/systemd.kill.xml:63–101` gives an owned process-tree termination/escalation contract. This does not require systemd inside a container.
- Coder `agent/reaper/reaper_unix.go:54–77,103–123` separates orphan reaping from ordinary child wait ownership. Its test `agent/reaper/reaper_test.go:183–207` explicitly distinguishes a child's signal from grandchild propagation. Do not introduce a competing global reaper into the Footwork process.

Implementation unit: replace the fixture shell's implicit lifecycle with one owned session runner. Reserve an unused display; create fresh private XDG config/cache/data/state/runtime directories; record explicit optional rootless data/config prefixes. Give startup one monotonic deadline. Stages are X handshake, usable WM, accessibility bus, and one exact fixture text target. Each potentially blocking probe runs with a bound. A recovery dialog is a distinct readiness refusal, never a target to auto-dismiss.

Monitor critical components after readiness. Cancellation or component death transitions to cleanup. Terminate only owned processes/groups, wait a bounded grace period, escalate if needed, then record forced cleanup separately. Use container init at the container boundary. Do not signal an unrelated user desktop or delete ambient application state.

Acceptance: stalled handshake; occupied display; no WM; missing rootless theme/config; absent bus; root-only AT-SPI tree; recovery modal; cancellation before and after ready; Xvfb/bus/editor death; TERM-ignoring child; orphaned grandchild; repeat under a 512-PID ceiling. Assert no ready record on failed startup, bounded completion, no duplicate input and no surviving owned descendants where observable. A nested display does not establish physical lock or seat safety.

Extend `host_probe.py:80–131` with bounded visible cgroup PID/event and swap counters. The actual earlier failure exhausted processes with zero OOM events. systemd `man/systemd.resource-control.xml:425–439,570–584` treats swap and task limits independently. Report inaccessible/delegated/ancestor limits as unknown; a snapshot is diagnostic evidence, not a reservation. Record selected PID1/reaping facts without process argument or environment dumps.

## 3. Recover the owned Linux browser without a visible window

Observed: `python/jevdual/browser_driver.py:555–569` always calls macOS `open -na Google Chrome` when a qualified Chrome process has no visible windows. Linux startup coverage with an existing window does not cover this branch. The launcher also uses wall time and discards its `Popen` handle (`:144–150`).

Implementation unit: use the qualified Linux executable and exact owned profile for new-window creation, with monotonic readiness and retained launch identity. Distinguish a reused persistent browser from a newly owned helper; cancellation must not kill a persistent browser merely because attachment failed. Preserve executable, UID, profile, port and process-incarnation checks.

Acceptance: close every window while retaining the browser process, invoke the public startup route, and bind the new window in the same profile. Challenge wrapper versus ELF executable, early process exit, failed spawn, conflicting browser roots, wrong profile, cancellation and unrelated windows. Keep this change independently reviewable from the session runner.

## 4. Qualify text semantics and save generations before app breadth

Observed: LibreOffice GTK exposes UNO character counts and text ranges directly (`vcl/unx/gtk3/a11y/atktext.cxx:252–276,671–679`); insertion constructs a UTF-8 string from a byte length and forwards a position (`atkeditabletext.cxx:94–106`). Whole-value setting goes through a void callback with exception handling (`:75–90`). An acknowledgement is insufficient to establish exact resulting text. Toolkit counts/offsets must be tested, particularly astral characters, before equating them with Python codepoints.

Footwork's independent complete readback and single-write/no-retry rule should remain. Do not transplant newer CUA's `atspi/native.rs:5270–5286` fallback from failed `SetTextContents` to `InsertText`: an uncertain mutation must not trigger a second mutation.

Acceptance matrix: actual GTK and Qt fixtures; empty/whitespace values, astral Unicode, combining marks, CRLF, 4096/65536 boundaries, same-length concurrent changes, lost acknowledgements, owner replacement and truncated trees. Refuse inconsistent offset/count semantics until a qualified adapter exists. Also propagate a single observation deadline across resolve/capability/value calls: currently `NativeBridge.observe` checks its budget before starting a worker, while each `_Bus` operation starts a separate deadline. Source inspection identifies a composed-budget risk; a delayed-bus test must measure it before making a runtime latency claim. Cancelling `asyncio.to_thread` does not stop its thread.

Document breadth requires an explicit application contract. LibreOffice GTK does not implement `AtkDocument` (`atkwrapper.cxx:868–874`), while its model separately exposes location and modified state (`sfxbasemodel.cxx:1446–1450,1603–1627`). A read-only UNO prototype would first have to join an explicit model/document URL to the exact PID/window. Do not open a broad network listener or select the first document.

Save is a resource transition: LibreOffice transfers a temporary medium (`docfile.cxx:896–918`) using replacement or in-place fallbacks (`:2294–2330`); modified/title state changes separately (`objstor.cxx:2457–2468`). Footwork correctly invalidates an old Mousepad inode binding after atomic replacement. A future checked save should retire that generation and explicitly rebind, preserving historical execution versus current agreement. Test atomic and in-place saves, unrelated replacement, symlink swap, save-as, delayed failure and restart. Byte equality supports the saved-file claim; crash durability requires a separate filesystem contract.

## 5. Widen X11 ownership only with attributable evidence

Xpra distinguishes XRes server PID from client `_NET_WM_PID` (`xpra/x11/models/core.py:171–188,509–520,729–732`); XRes support requires version 1.2 (`xpra/x11/bindings/res.pyx:62–103`). Newer CUA's `platform-linux/src/x11_client_pid.rs:1–18,47–91` adds server self-PID proof and local-host checks before trusting resource attribution.

Proposed optional tier: server-backed ownership for clients missing the property, carrying provenance and retaining process incarnation. Test unsupported XRes, duplicate/server-owned resource replies, remote display, PID namespace mismatch, stale XID and conflicting ownership. None of these grants document identity. Property events should invalidate and wake a bounded re-read; they must not silently replace a retained target or prove a save. Xpra's guarded property callbacks (`core.py:292–307,695–745`) illustrate that separation.

## 6. Treat Wayland as a new identity backend

Footwork's exact-text binding currently requires a local X11 display and XID. Geometry alone cannot convert it into a Wayland binding. A later seam should carry a tagged backend, compositor instance, exact toplevel identity, process incarnation, coordinate space and a separately qualified AT-SPI join.

Source constraints:

- River `protocol/river-window-management-v1.xml:1030–1043` explicitly warns that creator PID is unreliable for security; `:1085–1106` supplies a nonreused window identifier. Its WM interface is for one window-manager client (`:37–58`), with focus requests in the manage sequence (`:1620–1628`). Do not seize WM authority as an automation shortcut.
- Newer CUA's `wayland/hyprland.rs:232–251,295–324,420–453` attests same-user socket peers, joins IPC and Wayland peers, and uses full unique window addresses. `hyprland_input.rs:1200–1255,1343–1378` qualifies exact targets and input lifecycle, revalidating and discarding stale pooled connections. Compare these capabilities with the pinned source/build before selecting Hyprland for an isolated pilot.
- Logical/window-local/preview coordinates differ. River describes logical dimensions and pointer positions (`protocol:423–447,1841–1873`) and double-buffered render state (`ARCHITECTURE.md:22–41`). Newer CUA documents logical capture coordinates (`hyprland_input.rs:301–304`); its foreground E2E's one-output, scale-1 constraints do not establish multi-output correctness.
- Lock-client destruction is not unlock: Hyprland `src/protocols/SessionLock.cpp:126–148` and River `river/LockManager.zig:177–215` make the distinction. Hyprland idle notifications have inhibitor/timer semantics (`IdleNotify.cpp:13–50`). Unknown must remain distinct from unlocked or idle.
- Callback cleanup is part of target safety: Hyprland removes the event source and transfers waiter ownership before invoking client code (`EventLoopManager.cpp:95–111`). Late callbacks must not act on destroyed targets.

Later acceptance: observe/exact-read first, then append/replay/restart, then explicitly exclusive input on one disposable native-Wayland compositor. Distinguish XWayland. Challenge nested-session socket contamination, compositor restart, sibling windows, address reuse, lost plugin/observer, late replies, mixed scaling/rotation and output removal. Shared foreground remains separate until actual user interruption, lock loss and conservative restoration are qualified on the intended seat.

## Handoff boundary

Implement units 1–3 independently, with notebook predictions committed before their resolving tests. Record the wheel/source identity, public SDK envelope, chosen session/backend, resource limits, readiness transitions and cleanup outcome for each acceptance run. Keep ambiguous mutations terminal until reconciled; no generic retries. Existing provider guards remain in force.

Units 4–6 are source-grounded designs awaiting experiments and authority-specific qualification. Reference checkout behavior, a passing mock and a nested compositor each support different claims. No new compositor, system service, kernel, physical device, cloud environment or shared desktop was activated in this study.

## Implementation follow-up

Units 1–3 were implemented and tested in the [Debian VM runtime tranche](../results/linux-runtime-tranche-20261030/report.md). It retains the final installed-wheel checks, staged readiness and cleanup faults, real SDK refusal, native zero-window browser recovery and the earlier failed runs. The scope and later gates above remain distinct.
