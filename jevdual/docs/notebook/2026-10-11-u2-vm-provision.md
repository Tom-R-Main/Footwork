# U2 disposable macOS provisioning

## VM1 · prediction · 2026-10-11 13:42
Hypothesis: a pinned upstream Lume launcher running with all configuration, cache, restore-image and VM storage under the approved External SSD folder can install a fresh Apple restore image without a global install, shared host credentials or pregranted guest permissions.
Test: inspect upstream installer/release and launcher help, verify downloaded release provenance, then create a 4 CPU/8 GB/64 GB SIP-default guest from the recorded Apple IPSW and launch its visible Setup Assistant; preserve paths, hashes, logs and status in output/u2-vm-provision-20261011.
Predicts: the release and image are identifiable, provisioning writes stay in the approved folders, the guest reaches initial Setup Assistant, and no unattended seed, host permission change or guest permission grant is needed for provisioning.
Against: the launcher requires a global service or writes elsewhere, hardware/storage blocks install, the image cannot be verified/provisioned, or the guest arrives pregranted instead of pristine.
Refs: docs/experiments/U2-independent-onboarding.md; docs/onboarding-vm-plan.md; output/u2-vm-provision-20261011

## VMU1 · update · 2026-10-11 13:57
Observed: Lume0.6.1 asset digest/signature/notarization and SSD-only configuration checks passed. Source inspection found its native viewer unconditionally reads the host clipboard before guest SSH is available, and its VNC CLI exposes no bind-address control; the queued controller was stopped before any VM create. The fresh Apple26.6.2/25G83 IPSW download remains active and its advertised SHA256 is recorded.
Inferred: a supported privacy-bounded native viewer requires a different launcher; launch proof and VM1 remain open.
Next: qualify pinned Tart with its supported --no-clipboard flag, then reuse the Apple image only after full SHA256 verification.
Refs: output/u2-vm-provision-20261011/launcher-provenance.json; output/u2-vm-provision-20261011/provision-state.json

## VM2 · prediction · 2026-10-11 13:57
Hypothesis: pinned upstream Tart2.40.1 with TART_HOME and temporary state on the approved SSD and --no-clipboard can provision a pristine macOS guest and show Setup Assistant without host clipboard access, VNC listener, folder sharing, guest SSH or pregranted permissions.
Test: verify official release digest/signature/license and actual CLI help/source flags, create from the fully verified Apple IPSW, configure4CPU/8GB/64GB, and run its native viewer with clipboard/audio/USB passthrough disabled and no directory/SSH/guest-agent setup; root observes the GUI and owns any human-dependent setup.
Predicts: CLI/source and runtime state confirm the supported disabled clipboard route and isolated storage, guest installation succeeds, and a real visible Setup Assistant is available before permission grants.
Against: the flags are unsupported or still read host clipboard, Tart requires unapproved global paths or paid terms, installation fails, or Setup Assistant/host isolation cannot be established.
Refs: output/u2-vm-provision-20261011/tart-release.json; output/u2-vm-provision-20261011/tart-run-pinned.swift; docs/experiments/U2-independent-onboarding.md

## VM3 · prediction · 2026-10-11 14:07
Hypothesis: hdiutil makehybrid can produce an ISO containing only the approved packet and downloaded prerequisite assets without attaching a host volume, and Tart's supported --disk path:ro route can expose that immutable image inside the pristine guest without host clipboard or directory sharing.
Test: stage exactly packetv3, Python3.14.7, uv0.12.5, ChromeDMG and their manifest/checksums, build an ISO under the approved SSD folder, verify its inventory/hash, and attach read-only on the first isolated Tart run; root later observes guest volume and verifies payload hashes.
Predicts: ISO creation does not require hostmount or global changes, contains the five declared source files plus checksum/provenance metadata, and Tart's CLI/source passes readOnly=true for the attachment.
Against: ISO creation fails like host DMG attach, unexpectedly includes other hostfiles, or the supported attachment cannot be made/readback as read-only inside the guest.
Refs: output/u2-vm-provision-20261011/tart-run-help.txt; output/u2-vm-provision-20261011/tart-run-pinned.swift; output/u2-vm-provision-20261011/prerequisite-provenance.json

## VMU2 · update · 2026-10-11 14:07
Observed: VM3's test enumerates four assets, while its Predicts line inadvertently says five source files; the intended inventory is the packet, Python installer, uv archive and Chrome DMG plus provenance/checksum metadata.
Next: measure that explicit four-asset inventory; do not add an extra asset to satisfy the mistaken count.
Refs: output/u2-vm-provision-20261011/prerequisite-provenance.json

## VMU3 · update · 2026-10-11 14:13
Observed: the Apple byte-range downloader stopped with curl exit18 (partial transfer) at roughly90.7percent aggregate image bytes; completed segments and all partial files remain. The full-image SHA256 has not been checked and no guest exists. ISO creation/inventory verification succeeded without a hostmount; guest readback is pending.
Inferred: a bounded byte-range continuation can retain useful downloaded bytes, but partial transport success cannot certify the image.
Next: commit VM4 before resuming only incomplete ranges, preserving the failed original transfer logs.
Refs: output/u2-vm-provision-20261011/apple-range-00.log; output/u2-vm-provision-20261011/iso-verification.json

## VM4 · prediction · 2026-10-11 14:13
Hypothesis: Apple CDN supports precise Range continuation after a partial transfer, so a new downloader can finish only the missing bytes of retained ranges and produce the advertised complete-image SHA256 without downloading successful segments again.
Test: resume incomplete segments with Range beginning at their recorded absolute offset, require HTTP206 with matching Content-Range before appending, bound retries and preserve per-attempt headers/logs, then stream-assemble and compare the final whole-image SHA256 to Apple CDN metadata.
Predicts: retained segments remain unchanged, each range reaches its exact expected length, the complete image matches Apple SHA256885503b7f4b06609e9a512f2befd40f59730640a3f1233e3892d60affdd51c95, and only then the committed Tart provisioning test starts.
Against: the CDN ignores/rejects offsets, repeated partial transport prevents completion, existing bytes are altered, or final image hash differs.
Refs: output/u2-vm-provision-20261011/apple-ipsw-headers.txt; output/u2-vm-provision-20261011/download_apple_ranges.py

## VMU4 · update · 2026-10-11 14:41
Resolves: VM4 = held
Observed: five bounded continuation requests returned HTTP206 with exact absolute Content-Range; all missing bytes were retained in separate attempt files before append. Original completed ranges were not downloaded again. Single streamed assembly/fsync produced 19,772,231,540 bytes and Apple SHA256885503b7f4b06609e9a512f2befd40f59730640a3f1233e3892d60affdd51c95. The image is read-only with recorded file identity and private non-symlink parent; Tart creation started only after those guards passed. A redundant preliminary prefix-hash scan was stopped before network requests, preserving its script/context; no image was certified from that attempt.
Next: supervise Tart installation and hand its actual native viewer to root; VM2 and VM3 guest observations remain open.
Refs: output/u2-vm-provision-20261011/apple-ipsw-provenance.json; output/u2-vm-provision-20261011/provision-state.json; output/u2-vm-provision-20261011/tart-create.log

## VMU5 · update · 2026-10-11 14:41
Resolves: VM1 = inconclusive
Observed: pinned Lume integrity/signature/configuration checks passed, but native clipboard source behavior and absence of a supported VNC bind option caused its controller to stop before any guest creation. Actual provisioning now uses independently verified Tart2.40.1 with its supported disabled-clipboard route; the Lume guest hypothesis was not executed to completion.
Next: retain Lume findings as the launcher selection rationale; do not call them a Lume installation or first-use failure.
Refs: output/u2-vm-provision-20261011/launcher-provenance.json; output/u2-vm-provision-20261011/tart-launcher-provenance.json

## VM5 · prediction · 2026-10-11 15:11
Hypothesis: pausing only the Python controller before its create timeout while Tart continues verified disk work, then resuming after the create child exits, preserves the actual child exit status and allows existing configuration/viewer steps without restarting installation.
Test: inspect the active controller's Python/POSIX subprocess wait semantics and exact process relationships, pause only that controller if creation remains active near15:18, supervise the same child PID and scoped disk activity for at most15additionalminutes, then resume the controller after the child exits or becomes a zombie; preserve any timeout/failure without resetting the partial guest.
Predicts: Tart1958 continues writing while its supervisor alone is stopped, the completed child is reaped before timeout rejection in the resumed wait, and the same fresh guest reaches the queued native viewer with the selected isolation flags.
Against: pausing affects the child/process group, the resumed controller loses true exit status or times out despite completion, installation fails/stalls, or the15minute extension expires without a justified handoff.
Refs: output/u2-vm-provision-20261011/provision_tart_after_download.py; output/u2-vm-provision-20261011/python-popen-wait-source.txt; output/u2-vm-provision-20261011/installer-liveness-current.json

## VMU6 · update · 2026-10-11 15:12
Observed: VM5 was written at15:12EDT (clock19:12:02UTC), while its heading used15:11; the heading minute is approximate and git commit order remains the preregistration boundary. POSIX _wait polls waitpid before testing the elapsed deadline on each iteration, but a stop between that poll and deadline calculation would still permit a timeout on resume; the prediction does not assume away that narrow race.
Next: commit VM5 before any pause, prefer observing the controller sleeping in its wait loop, and report any resumed timeout honestly rather than inferring successful child status from a percentage.
Refs: output/u2-vm-provision-20261011/python-popen-wait-source.txt


## VMU7 · update · 2026-10-11 15:20
Resolves: VM2 = held
Observed: Tart creation returned success at15:14EDT before its timeout; get/list report the same owned guest running with4CPUs,8192MB RAM and64GB logical disk. Actual argv disables clipboard/audio/USB passthrough, captures system keys and attaches the verified ISO read-only. Root bound exactPID25080/window footwork-u2-20261011 and observed fresh welcome then actual Setup Assistant Language page/English/license-use notice in native CUA tool images. Root owns all GUI input; human license approval is pending.
Inferred: provisioning reached a visible pristine setup boundary; this does not establish guest SIP, initial TCC denial, ISO guest readback or the U2 permission journey.
Next: retain the running guest for human setup and root's independent onboarding qualification; VM3 remains open.
Refs: output/u2-vm-provision-20261011/delivery-record/summary.json; output/u2-vm-provision-20261011/provision-state.json; root native CUA tool images in this chat

## VMU8 · update · 2026-10-11 15:20
Resolves: VM5 = inconclusive
Observed: installer completed normally before the planned15:18pause boundary, so no controller pause, resume, swap or extended timeout was executed.
Next: preserve the proposed recovery and narrow wait-race caveat as untested; do not call VM5 held.
Refs: output/u2-vm-provision-20261011/tart-create.log; output/u2-vm-provision-20261011/provision-state.json

## VMS1 · summary · 2026-10-11 15:20
Established: pinned launchers/artifact provenance, safe supported Tart flags/storage, bounded authenticated Apple image recovery, exact ISO inventory/payload verification, successful fresh guest creation/configuration and root-observed visible Setup Assistant. No global launcher, host permission change, guest account/SSH/TCC grant or SIP change was performed.
Uncertain: guest SIP runtime status, denied Accessibility baseline, actual ISO guest read-only/hash readback and the complete installed U2 effect/restart/report/cleanup journey. Tart Gatekeeper diagnostics reported Unnotarized Developer ID even though normal CLI/create/run succeeded without policy overrides.
Decision: hand the running guest and all GUI ownership to root at the explicit human setup/license boundary; keep VM3 and UO2 open.
Refs: output/u2-vm-provision-20261011/delivery-record/report.md; output/u2-vm-provision-20261011/delivery-record/summary.json

## VMU9 · update · 2026-10-11 16:18
Observed: the user reports accepting the macOS license and creating the disposable guest account. Root observed the unlocked desktop and launched the guest interactive Terminal, com.apple.Terminal version2.15. Guest sw_vers reports macOS26.6.2 build25G83; csrutil reports SIP enabled. diskutil reports both media and volume read-only at /Volumes/FOOTWORK_U2 with the exact six staged filenames. Guest payload checksum verification is running; VM3 remains open until those results are observed. Native CUA modifier-key input is not reliably forwarded by the VM; unmodified menu navigation and printf octal-decoded commands execute in the same Terminal without clipboard sharing. No Accessibility grant or product installation has occurred.
Next: finish guest media verification, install verified prerequisites, then capture the denied installed diagnostic and fixture before any permission grant.
Refs: root native CUA tool images in this chat; guest /Users/tom/footwork-u2/baseline.txt; guest /Users/tom/footwork-u2/media-hashes.txt

## VMU10 · update · 2026-10-11 16:18
Resolves: VM3 = held
Observed: the guest read-only qualification volume contains the exact six staged files. The guest shasum check reports OK for all four executable/archive payloads, including packetv3. Root observed the completed output in the native viewer; guest media-hashes.txt preserves it. The prior host ISO parser verified the metadata files and payload bytes; the guest readback now establishes transport to the same independent environment.
Next: install verified prerequisites and execute UO2; preparation and media verification do not establish first-use permission or native effect success.
Refs: guest /Users/tom/footwork-u2/media-hashes.txt; output/u2-vm-provision-20261011/iso-verification.json; root native CUA tool images in this chat
