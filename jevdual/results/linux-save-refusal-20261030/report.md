# Linux save refusal receipt correction

The Codex Cloud Debian 13 acceptance task reported a refused Control-S with `foreground_unavailable` but `dispatched=true`. The retained failure was an activation gate: `_NET_ACTIVE_WINDOW` was unset, CUA reported no input sent, and the file checker caught the absent save. The cloud task retained its unchanged-product acceptance evidence locally in commit `bd0acb1`; that commit has not been imported into this branch.

The pinned native source's `platform-linux/src/input/foreground.rs::with_x11_foreground_opts` returns `foreground_unavailable` before calling the input body. `tools/impl_.rs::input_error_result` serializes the structured code/detail/effect/suggestion record with effect `none`. Footwork discarded that record when the SDK returned no ActionResult.

The Linux foreground route now recognizes only that exact structured error shape, matching the top-level code with no ActionResult. It emits `effect=refused`, `dispatched=false`, `delivered_count=0`, and `delivery_basis=qualified_gate`. Save readback is skipped because no chord was delivered. No dispatch, focus, identity, retry or persistence behavior changes.

The public CLI scenario and Linux adapter regression both fail against the baseline ([before](before.txt): two failures, eight passes) and pass after the fix ([after](after.txt): ten passes). Contradictory action records, positive delivery counts, malformed or mismatched structures and opaque errors retain uncertainty. [Focused regressions](focused.txt) passed 249 tests across native receipts, Linux input, foreground intent, public sessions, the pinned SDK seam and notebook validation. Ruff and source diff checks passed.

This is local regression evidence over simulated Linux replies plus pinned source inspection. The corrected wheel has not yet been rerun in the cloud VM. Prior bundles and acceptance artifact hashes continue to identify the original `0b1e82c` implementation; rebuild from the new branch head to test this correction.
