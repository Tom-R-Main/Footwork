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
