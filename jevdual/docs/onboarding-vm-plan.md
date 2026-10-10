# Disposable macOS environment plan

The current Mac is arm64, macOS26.5.1/build25F80, with24GiB installed memory. On2026-10-10, its project volume had only7.9GiB available. Neither lume nor tart was on PATH. No hypervisor, restore image or guest was installed by this preparation.

A spare independently provisioned Mac is the shortest qualification route. For a local guest, select an approved storage directory with adequate physical capacity before installation or image download. Lume's [quickstart](https://cua.ai/docs/lume/quickstart) calls for about50GB free disk and8GB free memory; installed memory is not evidence of free memory. Our initial proposed guest allocation is4CPU/8GBRAM/64GB virtual disk, subject to current host availability. Do not place it in the reference repository corpus.

Use a fresh Apple restore image with its selected version, URL and SHA256 recorded. Create an ungranted SIP-enabled guest; verify SIP inside it. The local Cua reference separates granted golden-image regressions from its SIP-on permission-flow lane. Its pregranted seed, permission seeding helpers and SIP-off base do not establish our first-use baseline.

After approval of the exact installer, image and storage path, install a pinned Lume release through its documented installer. Inspect the installer and version before executing; its installation/configuration paths must be included in that approval. The CLI [reference](https://cua.ai/docs/lume/reference/cli/vms) supports a local IPSW and explicit storage:

~~~sh
lume create footwork-u2-20261010 --ipsw /absolute/approved/restore.ipsw \
  --cpu 4 --memory 8GB --disk-size 64GB --storage /absolute/approved/vm-storage
lume run footwork-u2-20261010 --storage /absolute/approved/vm-storage
~~~

These are proposed commands, not executed or validated locally. Recheck the installed CLI's help before running. Complete Setup Assistant in the visible guest, then transfer only this qualification packet. Do not share the host home, repository, account credentials or signed-in browser profile. Keep normal SIP settings and observe initial permission status before granting anything.

Use the guest's interactive Terminal for U2. SSH-only execution does not establish the same responsible GUI host. Guest user/permission setup and the exact storage choice remain pending. Export the qualification records before stopping or retiring the guest; deletion requires scoped approval and a fresh target check.

References: local Cua libs/cua-driver/tests/runners/macos-lume/README.md, SIP-on permission-flow lane; local Arc README Accessibility-only setup; local Cua responsibility-chain guidance. Those reference versions supply mechanisms, not upgrades to Footwork's pinned driver.
