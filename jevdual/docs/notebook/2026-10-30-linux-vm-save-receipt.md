# Installed Debian VM save-refusal correction

## LINUXVMSR1 · prediction · 2026-10-30 16:06
Hypothesis: the 045fc5d bridge fix recognizes the real pinned CUA foreground_unavailable pre-input response on this Debian VM, so the earlier no-window-manager save refuses without claiming dispatched input.
Test: rebuild the portable product bundle from 045fc5d implementation bytes, install into a fresh consumer environment and verify package hashes. Repeat the original installed CLI/MCP fixture with rootless Openbox data paths intentionally absent; the unchanged qualification harness must stop at save. Inspect its real save receipt for refused/dispatched=false/delivered_count=0/readback=null and independently verify unchanged disk bytes. Then repeat with working desktop paths and fresh state/output, requiring the full journey and exact saved bytes. Run focused native/session/SDK/notebook tests with strict identity predicates unchanged.
Predicts: the broken-desktop case reaches the same qualified foreground refusal and records no delivered chord or persistence readback; the working-desktop case still saves exactly once and passes independent artifact verification.
Against: the actual SDK reply does not match the qualified shape, any refused save claims dispatch or readback, the disk changes during refusal, or the corrected installed build refuses the working qualified save.
Refs: commit 045fc5d; results/linux-vm-acceptance-20261030/failed-runtime/driver-save.json; results/linux-vm-save-receipt-20261030/; docs/notebook/2026-10-30-linux-save-receipt.md

## LINUXVMSRU1 · update · 2026-10-30 16:09
Resolves: LINUXVMSR1 = failed
Observed: the 045fc5d wheel installed and all 191 package files matched; only native.py changed from the previous wheel. Focused native/session/SDK/notebook tests passed 226, and receipt tests passed 7. The real no-window-manager run reproduced the old unverifiable/dispatched=true/readback-added save result and failed the independent saved-byte assertion. The working-desktop control stopped earlier when the current native observation had no element labelled text area; no save receipt exists for that control. These are separate failures, not successes.
Next: capture the real pinned SDK ToolResult without changing it, compare its structured envelope to the strict recognizer, and repeat the working-desktop control with read-only readiness checks. Do not change product or identity predicates during diagnosis.
Refs: results/linux-vm-save-receipt-20261030/045fc5d-refused.json; results/linux-vm-save-receipt-20261030/045fc5d-working.json; results/linux-vm-save-receipt-20261030/focused.txt; results/linux-vm-save-receipt-20261030/receipts.txt

## LINUXVMSR2 · exploratory · 2026-10-30 16:09
Question: which real ToolResult field prevents 045fc5d from recognizing the foreground gate, and can the owned working desktop expose a stable exact text target before dispatch?
Test: use a fresh owned Xvfb/D-Bus/Mousepad fixture and a transparent read-only recorder around the actual CUA call_tool response; retain the exact scoped hotkey arguments, structured response and unchanged return value. Record the bridge save effect and independent disk bytes. Observe ready native targets without mutating them before a separate unchanged successful-path qualification.
Refs: python/jevdual/native.py:_linux_foreground_no_send; scripts/linux/desktop-session.sh; results/linux-vm-save-receipt-20261030/
