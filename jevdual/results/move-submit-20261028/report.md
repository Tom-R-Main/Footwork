# Qualified Finder move and Chrome submission recovery

October 28, 2026. The installed nominal chain and the interrupted chain with truncated HTTP response loss passed. **The full portfolio gate remains open for disconnects before HTTP response headers:** that fault produced two ingress events from one agent click, so reconciliation correctly refused to declare success.

## Frozen runtime and checks

The final runtime is commit `2ae0a5f263841008f17986a750fbb1596dc9f91f`, installed from an offline, standard-library-built wheel with SHA-256 `3c3d16574abcf3a52b43834d524aff8aea01769c049bb888e9c797487f465bfa`. Wheel inventory/RECORD verification passed, and all eight changed runtime module origins were checked inside the installed site. [Manifest](candidate-2ae0a5f/manifest.json) and [runtime/module hashes](candidate-2ae0a5f/runtime.json) bind the evidence. Subsequent commit `d2afee1` adds the eight helper tests already included in the test run; it changes no runtime file.

[The full suite](tests-final.txt) passed **2142 tests, with 26 skipped**. Ruff and the notebook checker passed. This uses existing host dependencies on macOS 26.5.1 and pinned `cua-driver 0.38.0+footwork.d5373879`; it is not clean-machine onboarding. No provider calls, network dependency installation, merge or deployment occurred. The delegated worker used the inherited session model; no separate model provider was invoked.

## Installed qualification

All rows below use the same final installed runtime, fresh owned fixtures, native app UI for effects and read-only independent oracles. No filesystem rename/move, image transformation or direct HTTP submission supplied a required effect.

| Trial | Finder | Preview | Chrome and recovery | Outcome |
| --- | --- | --- | --- | --- |
| [Ordinary chain](trials/proven-nominal/summary.json) | Exact rename and two-window move; same inode/bytes, old path absent and siblings unchanged | Qualified new Undo transition, saved clockwise pixels/dimensions, checked again after closing | One ingress and one exact row; native result unknown, independent pre-admitted receipt resolves it; replay adds no ingress | All three handoffs completed |
| [Interrupted chain](trials/proven-interrupted/summary.json), `--interrupt --loss truncated` | Same checks; original move-token replay sends no new input | Same saved-pixel and persistence checks | One ingress/row after truncated HTTP body; actual controller killed after ingress before CLI result; read-only reconciliation resolves the attempt with no native count invented | All three handoffs completed after three SIGKILLs |
| [Pre-header disconnect](trials/proven-disconnect/disconnect-oracle.json), `--loss disconnect` | Passed | Passed | Two ingress events, one deduplicated row; zero qualified service receipts; submission remains unknown | Chrome handoff refused; portfolio gate open |

The interrupted run killed owned controllers with return code `-9` at Finder→Preview, Preview→Chrome and after browser ingress. The third kill injection was observed to land. The retained stage checkpoints and the service event recovered the chain; no uncertain input was redispatched. The combined run exercises interruption and truncated response loss together. A separate [truncated-response component run](trials/component-truncated/summary.json) on precursor `1406a53` also recorded one ingress without a controller kill; it is component evidence, not a connected-chain pass.

After the final disconnect failure, original-token replay and repeated reconciliation kept ingress at two, left the operation unknown and did not advance Chrome. [Replay evidence](trials/proven-disconnect/disconnect-replay.json) records that boundary. The same duplicate-ingress failure was retained from development. Pinned SDK source inspection found a single AXPress on this route; the producer of the second HTTP request remains unproven. A single row must not hide duplicate requests.

## Implementation

Finder move now requires a second destination window registered before admission by its exact protected marker, directory identity and PID/window. The producer copies the sole verified source, checks a new clipboard generation and exact owned file URL, reacquires the registered destination, rechecks source/clipboard/destination and invokes Move Item Here. It qualifies only the same-inode path transition with unchanged bytes. Counts are acknowledged-input lower bounds.

Rename completion now handles Finder replacing its transient editor after Return. The current matching editor may authorize reacquiring only the already bound window. No additional Return or editor write is sent. The normal exact filename AXURL/inode must become available before confirming; basename matching does not authorize file input. Wrong app/value/main/explicit window, missing targets and persistent editing refuse.

Preview captures its existing narrow result predicate while the exact document still holds foreground ownership, before restoring the previous app. It checks ownership before input and around readback. The accepted predicate is unchanged; saved pixels remain a separate task-correctness check.

Chrome startup may register `--ticket-manifest`. Admission binds an empty owned ledger, persistent fixture identity, exact numeric-loopback origin, artifact identity, fresh request fields and native operation identity. Only the exact observed four-field Register asset submission receives that preparation. One matching new ingress and one durable row can yield a separate `ticket_submission` receipt. Duplicate/old ingress, changed ledger/artifact/fields or reused claimed nonce cannot clear uncertainty. Receipt retention precedes finalization, so restart can use historical evidence without UI or SQL writes to the service. The original native record is retained when available; the killed-controller case has no returned native capsule and still invents no delivery count.

Focused/public tests challenge stale/replaced targets, occupied/wrong destinations, missing/duplicate/changed destination windows, clipboard and ownership changes, wrong Preview transitions, changed ledgers/artifacts/fields, nonce claims, duplicate ingress and a real SIGKILL between service-receipt retention and finalization. These simulated and HTTP component checks are distinct from the installed app trials.

## Limits, accounting and cleanup

Qualification is for these finite owned fixtures under a reserved desktop using the existing `exclusive_desktop` posture. It does not establish active-human coexistence, generic Finder folders, Go to Folder navigation, arbitrary websites, semantic browser tab incarnation or repeated Preview rotations. Preview trials use a fresh owned process with process-local state restoration suppressed and exact document-path readiness. Ordinary keyword/replacement checks and exact Finder grants remain enabled; explicit no-judge fixture mode was fixed before each trial.

[Trial accounting](trials.json) retains 22 trajectories, including early no-send/readiness failures, uncertain modal attempts, precursor Preview failures, component runs and successful final chains. Failed attempts were not converted into successful ones. The preregistered notebook records the mechanism changes; [harness source](harness/live_driver.py) and installed hashes make the final trials inspectable. Early app startup races were repaired with read-only readiness checks. GUI cleanup is sequential between final trials.

[Cleanup](cleanup.json) verified that all recorded owned listeners stopped accepting connections, shared Finder and Preview stayed alive, and all three final saved images still passed the pixel oracle. The retained hashes of eleven uncertain operation rows within this package were unchanged across cleanup. Assets, databases and earlier uncertainty histories remain available in the private run roots recorded by the trial inventory.

The next unresolved boundary is the duplicate HTTP ingress after pre-header disconnect. Keep that operation blocked; investigate transport/action duplication with a separately preregistered probe before expanding the support claim.
