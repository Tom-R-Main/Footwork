# Linux VM acceptance of the available checkout

## LINUXVM1 · prediction · 2026-10-30 15:50
Hypothesis: the prepared Debian 13 x86-64 environment can run the available checkout's offline regression suite and headless browser contracts, but cannot qualify the unpublished Linux implementation described in the supplied handoff.
Test: record checkout identity and VM prerequisites; run the no-provider Python suite, browser-marked tests and installed CLI diagnostics. Inspect the public browser launcher and native desktop prerequisites without replacing platform code or weakening identity checks.
Predicts: installed Python, Rust core and pinned CUA imports succeed, offline tests pass, and the headless browser route works; the public dedicated-browser/native desktop workflow remains blocked by macOS assumptions or missing graphical services in this checkout.
Against: imports or the available offline/browser tests fail, or the unchanged public CLI completes a Linux browser-to-editor journey with independently verified saved bytes.
Refs: results/linux-vm-acceptance-20261030/; supplied handoff identifies unpublished commits 818d586 and 653ee74, neither present in this checkout or advertised remote branches.

## LINUXVMU1 · update · 2026-10-30 15:52
Observed: the initial notebook identifier V1 duplicated an older package identifier. Notebook validation failed; the in-flight regression suite also reached that notebook failure. The heading is renamed to LINUXVM1 with its prediction text unchanged; its original committed form remains in 90c9fc4. Both imports, CUA app enumeration and all thirteen browser-marked tests passed. The public browser start exited 7 on the hardcoded macOS executable, and doctor reported platform_unsupported.
Next: retain the first regression result, repeat notebook checks after identifier repair, and probe an owned isolated X11 desktop directly through pinned CUA while the unpublished Linux branch remains unavailable.
Refs: results/linux-vm-acceptance-20261030/browser.txt; results/linux-vm-acceptance-20261030/browser-start.json; results/linux-vm-acceptance-20261030/doctor.json

## LINUXVM2 · prediction · 2026-10-30 15:52
Hypothesis: the VM's installed dummy Xorg driver, Mousepad and accessibility services can support isolated native Linux observation through pinned CUA even though the available Footwork application layer is macOS-specific.
Test: start an owned dummy Xorg server and session D-Bus, launch Mousepad on a disposable text file, and request the exact process window and accessibility snapshot through pinned CUA. Shut down owned processes afterwards.
Predicts: the server and editor start without privileged setup, CUA identifies the owned window, and its accessibility tree contains the fixture text.
Against: Xorg cannot start as this user, the window is absent, or the bounded accessibility snapshot cannot observe the known fixture text.
Refs: results/linux-vm-acceptance-20261030/native/; this is a driver/environment probe, not acceptance of the missing Footwork Linux implementation.

## LINUXVMU2 · update · 2026-10-30 15:54
Resolves: LINUXVM1 = failed
Observed: baseline f849e16 completed with 2253 passes, 28 skips and one failure caused by this package's duplicate notebook ID, subsequently corrected. All thirteen browser tests passed. The user then pushed and explicitly requested codex/linux-support at 0b1e82c; that exact commit was fetched and checked out, with only this package's notebook commits added locally.
Next: evaluate the requested Linux implementation from its installed wheel, with exact identity checks retained.
Refs: results/linux-vm-acceptance-20261030/pytest.txt; results/linux-vm-acceptance-20261030/browser.txt; commit 0b1e82c

## LINUXVMU3 · update · 2026-10-30 15:54
Resolves: LINUXVM2 = inconclusive
Observed: rootless dummy Xorg, session D-Bus, accessibility bus and owned Mousepad all started. CUA returned one owned window and a snapshot. The probe incorrectly examined opaque SDK repr strings rather than snapshot fields, so its fixture-text assertion failed without establishing a driver failure. All directly owned editor, window manager and Xorg processes were stopped.
Next: use the requested branch's existing qualification harness instead of extending the exploratory probe. Xvfb and Openbox are missing from the base image; obtain Debian binary packages in the existing user-owned sysroot.
Refs: results/linux-vm-acceptance-20261030/native/driver.json; results/linux-vm-acceptance-20261030/native-probe.txt

## LINUXVM3 · prediction · 2026-10-30 15:54
Hypothesis: the exact 0b1e82c product wheel and existing pinned native x86-64 CUA wheel can complete the documented installed CLI/MCP, replay/restart and saved-file qualification on Debian 13 after adding the missing isolated-desktop prerequisites.
Test: build the portable bundle with the cached CUA binary wheel, install into a fresh consumer venv with binary dependencies, verify installed package bytes, and run scripts/linux/qualify.py on the documented Xvfb/D-Bus/Openbox/Mousepad fixture. Run optional OCR/camera-refusal qualification and the branch's offline/browser tests; retain failures and prerequisite diagnostics.
Predicts: installed public CLI/MCP exact appends, duplicate prevention, restart agreement and independent saved bytes pass; synthetic OCR/review/replay and missing-camera refusal pass without physical-device claims.
Against: binary install or library loading fails on Debian, any strict process/window/document identity check refuses the fixture, or any required text/replay/save assertion fails.
Refs: docs/linux-support.md; scripts/linux/desktop-session.sh; scripts/linux/qualify.py; scripts/linux/qualify_optional.py; results/linux-vm-acceptance-20261030/
