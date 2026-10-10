# Independent onboarding preparation

The self-checked U2 packet is prepared from frozen source aa971782964a42d12d1ea8a52d6617476e8e3c63 on local branch codex/independent-onboarding. PR #2 remains at reviewed commit 7669d3d with four passing CI checks. No new PR, push, merge or registry publication occurred.

The 13-member packet SHA256 is 1eed24b44e1749ccee387a1677d89e43d4ac4616554eac4f80f02cb75e5d6a31. Its wheel remains the reviewed 9bb0440d7bd981df7dc70bbd22f97861a7ed32a88bf6de7a18c2f46982fef3a7 artifact. Only the packet manifest, runbook and VM-plan text changed between v1/v2; every qualification helper and runtime wheel byte stayed identical.

Observed preparation checks:

- Two frozen v2 builds match and verify every permitted Git-snapshot payload member, manifest digest and wheel RECORD/source inventory.
- All seven helpers import from the unpacked packet outside the checkout with installed Python 3.12.6 and 3.14.7 environments; four documented help entry points pass on both. Provider packages were not imported during the v1 probe.
- The new fixture-to-config helper creates a fresh private task/configuration with isolated commands. Placeholder resource IDs are configuration inputs only; no bind, native input or journal creation occurred.
- Malformed/reused configuration attempts refuse and preserve existing bytes. Changed helper bytes, an extra archive member and a foreign expected source commit are rejected.
- Frozen v1 can still be verified from the later checkout by explicitly selecting f39b76a. The initial verifier failed after the committed evidence-only 16c13ac change; aa971782 reads fixed payloads from an immutable Git snapshot and accepts an explicit expected commit. The earlier staging-path baseline did not changeHEAD and is not repair evidence.
- Seventeen selected notebook/packaging tests and Ruff pass. These are preparation checks, not native first-use qualification.

Archive paths remain under output/u2-packet-v1, output/u2-packet-v2 and their separate repeat builds. Smoke environments, tampered negative artifacts and receipts remain under output/u2-packet-smoke-v1/v2. Reverify from the repository using the explicit frozen commit:

~~~sh
uv run --no-sync python scripts/build_onboarding_packet.py \
  --wheel ../output/delivery-package-py312-v4/build-one/jevdual-0.0.1-py3-none-any.whl \
  --verify ../output/u2-packet-v2/footwork-onboarding-u2.zip \
  --source-commit aa971782964a42d12d1ea8a52d6617476e8e3c63
~~~

The packet's guides require an independently provisioned SIP-enabled Mac/guest and an observed denied Accessibility baseline, then an explicit human permission transition from the actual responsible host, actual installed native oracle/restart/report and exact cleanup. Chrome, TextEdit and compatible Python/uv must be present. Screen Recording remains advisory for the DOM/AX slice and is not inferred from an AX success.

Reference mechanisms came from local Cua's separate SIP-on permission lane, responsible-host guidance and Arc's Accessibility-only route. The proposed [Lume VM setup](../../docs/onboarding-vm-plan.md) was checked against the [quickstart](https://cua.ai/docs/lume/quickstart) and [CLI reference](https://cua.ai/docs/lume/reference/cli/vms); it is not locally executed. This host had 7.9 GiB free disk and neither launcher on PATH. Lume's about 50 GB free-disk prerequisite makes storage selection necessary before VM creation.

Independent environment selection and actual U2 runtime qualification remain pending. Claude review was requested through the authorized mailbox but is still queued/unread at this recording boundary; there is no independent approval claim. The user-authorized two-hour caffeinate hold is running PID 40049, from about 19:15 to 21:15 EDT, with idle system/display and user-active assertions verified. The lock probe reported unlocked after launch. Persistent sleep/lock settings and OS permissions were not changed.
