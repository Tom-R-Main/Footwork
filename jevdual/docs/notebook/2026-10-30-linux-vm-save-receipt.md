# Installed Debian VM save-refusal correction

## LINUXVMSR1 · prediction · 2026-10-30 16:06
Hypothesis: the 045fc5d bridge fix recognizes the real pinned CUA foreground_unavailable pre-input response on this Debian VM, so the earlier no-window-manager save refuses without claiming dispatched input.
Test: rebuild the portable product bundle from 045fc5d implementation bytes, install into a fresh consumer environment and verify package hashes. Repeat the original installed CLI/MCP fixture with rootless Openbox data paths intentionally absent; the unchanged qualification harness must stop at save. Inspect its real save receipt for refused/dispatched=false/delivered_count=0/readback=null and independently verify unchanged disk bytes. Then repeat with working desktop paths and fresh state/output, requiring the full journey and exact saved bytes. Run focused native/session/SDK/notebook tests with strict identity predicates unchanged.
Predicts: the broken-desktop case reaches the same qualified foreground refusal and records no delivered chord or persistence readback; the working-desktop case still saves exactly once and passes independent artifact verification.
Against: the actual SDK reply does not match the qualified shape, any refused save claims dispatch or readback, the disk changes during refusal, or the corrected installed build refuses the working qualified save.
Refs: commit 045fc5d; results/linux-vm-acceptance-20261030/failed-runtime/driver-save.json; results/linux-vm-save-receipt-20261030/; docs/notebook/2026-10-30-linux-save-receipt.md
