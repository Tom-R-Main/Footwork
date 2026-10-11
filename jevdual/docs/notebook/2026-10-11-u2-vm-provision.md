# U2 disposable macOS provisioning

## VM1 · prediction · 2026-10-11 13:42
Hypothesis: a pinned upstream Lume launcher running with all configuration, cache, restore-image and VM storage under the approved External SSD folder can install a fresh Apple restore image without a global install, shared host credentials or pregranted guest permissions.
Test: inspect upstream installer/release and launcher help, verify downloaded release provenance, then create a 4 CPU/8 GB/64 GB SIP-default guest from the recorded Apple IPSW and launch its visible Setup Assistant; preserve paths, hashes, logs and status in output/u2-vm-provision-20261011.
Predicts: the release and image are identifiable, provisioning writes stay in the approved folders, the guest reaches initial Setup Assistant, and no unattended seed, host permission change or guest permission grant is needed for provisioning.
Against: the launcher requires a global service or writes elsewhere, hardware/storage blocks install, the image cannot be verified/provisioned, or the guest arrives pregranted instead of pristine.
Refs: docs/experiments/U2-independent-onboarding.md; docs/onboarding-vm-plan.md; output/u2-vm-provision-20261011
