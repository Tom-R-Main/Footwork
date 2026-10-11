# U2 disposable Mac provisioning handoff

Recorded 2026-10-11 19:20 UTC. The fresh disposable guest `footwork-u2-20261011` was installed from an authenticated Apple restore image and is running at the human Setup Assistant boundary. This closes provisioning only. The independent permission journey remains unexecuted.

Root bound the native Tart app to exact PID `25080` and window `footwork-u2-20261011`, observed the fresh welcome page, then the Language page with English selected and Apple's license-use notice. Evidence is the native CUA tool images in this chat; no screenshot file path is invented. Root has requested human license approval. The worker performed no guest GUI input, account setup, SSH enablement, TCC grant or SIP change. Root owns further GUI actions.

Tart's runtime configuration reports 4 CPUs, 8192 MB memory, a 64 GB logical disk and 1280x800px display. Actual launch arguments disable clipboard, audio and USB passthrough, capture system keys, and attach only the validated asset ISO read-only. There are no host directory shares; a scoped check found no TCP listener on the Tart PID. Guest SIP and initial Accessibility status have not been measured.

## Provenance and launcher choice

Local Cua reference commit: `5458c77b04a6e5e7a099929e0c4d4366e83dd403`. Lume 0.6.1 release source: `3350f504014c85416009a90fcb339fe556ce02fc`. The notarized Lume asset passed official digest/signature checks, but release source confirms automatic host clipboard reads in native mode and its CLI supplies no VNC bind-address control. No Lume guest was created. These source findings were also checked against the exact release, not just the local checkout.

Tart 2.40.1 source: `05edeac562bae804ea4f88592cfbc98cc6791b5d`. The [official asset](https://github.com/openai/tart/releases/tag/2.40.1) matches SHA256 `363e2701154a8155cbc1bb6d845430c9b42697d2a186bc49574471ca2877db46`. Strict/deep code-signature verification passed for Cirrus Labs, Inc., Team `9M2P8L4D89`. **Gatekeeper diagnostics rejected both bundle and inner CLI as Unnotarized Developer ID; no ticket is stapled.** Normal CLI, create and run nevertheless succeeded under unchanged OS policy. No quarantine/security override was performed. The launcher is distributed under FSL-1.1-ALv2. It is local qualification infrastructure and is not bundled in the MIT Footwork packet.

Launcher, cache, temporary state, images and guest storage reside under `/Volumes/External SSD/footwork-u2-20261011`. No global installer or LaunchAgent was used. `TART_HOME` isolates runtime storage, and inherited trace export is disabled for this invocation.

## Image and delivery integrity

Apple Virtualization supplied macOS 26.6.2/build 25G83's restore URL. The downloaded image contains exactly 19,772,231,540 bytes and matches Apple's advertised SHA256 `885503b7f4b06609e9a512f2befd40f59730640a3f1233e3892d60affdd51c95`. Original parallel transfer failed with curl exit 18; its context remains. Five exact HTTP206 continuations recovered only missing bytes after Content-Range validation. Streamed assembly combined writes with hashing and fsync; the resulting file is 0444 with recorded device/inode/size/mtime and a private non-symlink parent before create.

The qualification ISO SHA256 is `89f082fcdc943449f1994d70cd4bd30b08b88ecf6abceec7d42c33c206049f6d`. A standard-library Joliet parser independently verified its exact six-member inventory and every payload byte against the staged files. It contains only packet v3, Python 3.14.7 installer, uv 0.12.5 archive, Google Chrome DMG and two provenance/checksum files. It was built without mounting a host volume. **Guest volume/read-only/hash readback remains pending.**

Packet v3 SHA256: `769c08c89061731368db33d78b180e7c8c96d531190f43bee44263642a76fd0f`. Python and uv match official hashes; Python's installer is signed/notarized by the Python Software Foundation. Chrome DMG checksum passes, but host read-only attach was denied; its inner app signature/version must still be checked in the guest. No prerequisite was installed on the host.

## Evidence and remaining gates

Structured values and source/runtime references are in `summary.json`. Ignored raw evidence remains in the sibling output directory: launcher/release provenance, original and resumed transfer headers/logs, image proof, ISO proof, installer log, final configuration/list, process state and runtime log. Do not commit raw logs or downloaded binaries.

VM1 is inconclusive because Lume creation was never run. VM2 is held for provisioning to actual visible Setup Assistant only. VM4 is held for authenticated range recovery. VM5 is inconclusive: installation finished normally before the planned controller pause, so that extension was not executed. VM3 remains open; UO2 remains unexecuted.

Next: the human completes the license/account boundary without sharing credentials. From interactive guest Terminal, root verifies OS/SIP and the attached volume/hashes, installs the reviewed prerequisites and wheel, then records the denied Accessibility baseline before any grant. The explicit grant/restart/readback transition and installed append/restart/report/cleanup oracle follow. The denial probe requires installed dependencies; installation does not grant Accessibility. Existing host grants, successful installation and a visible setup page do not qualify that journey.
