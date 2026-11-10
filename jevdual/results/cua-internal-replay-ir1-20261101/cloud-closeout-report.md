# IR1: first-run evidence, recovery-only closeout

Preregistration transport **d7f888101290e5100ad90f39d924beefbeb0935b** exactly matches supplied three blobs from **56df6cf6a56a10bfe8e16e4f0174ad57405a5676**. Frozen test package **48f93946b39e9f51f45b291b57152692e0d55033**. Actual cloud base2b5325e differs from unavailable parent2ea51b3; native archive is identical, SHA256 **5588fa808559de5982f9195c1031696f51a67b057164fd42b60485ac6c30b401**.

The parent reported an automated security check flagging the audit execution for possible cybersecurity risk. On recovery inspection the already-started run had finished. **No blocked command was retried, no new audit case executed, no bypass attempted.** No active audit runner/helper remained; no closeout signal was sent. Saved results below are from that original run only.

## Saved boundaries and effects

| Boundary / fault | Attempts / applied effects | Saved outcome |
| --- | --- | --- |
| Both actual private helpers, normal ACK | 1 / 1 each | Success |
| Both helpers, false before effect | 2 / 1 each | Successful alternate write |
| Both helpers, apply then explicit D-Bus error | 2 / 2 each | Success; acknowledged error, **not missing ACK** |
| Both helpers, apply then withhold; declared100ms client timeout | 2 / 2 each | Success after alternate method; missing-reply evidence scoped to altered timeout/private helper |
| Public native `set_value_ref`, post-effect error | 2 / 2 | Success; SetTextContents→InsertText, final TOKENTOKEN |
| Public native `set_value_ref`, withheld reply, ordinary3s+500ms backstop | 1 / 1 | Timeout error at3502ms; no alternate observed |
| Helper-default withheld arms | 1 / 1 each, partial | **Unavailable**: both hit40s watchdog, exit−15, no client result |
| Direct100ms D-Bus timeout control | 1 / 1 | `InputOutput(...TimedOut...timed out)` |
| Deliberate equal-final-value double SetTextContents | 2 / 2 | Final TOKEN; journal detects both effects |
| `linux_ax.set_value_ack`, ACK / withheld | 1 / 1 each | ACK succeeds; withheld returns AXError after2.009s, no alternate send |

SetValue helper's post-effect alternates produce TOKEN→TOKENTOKEN. Insert-first helper's alternate SetTextContents can leave TOKEN→TOKEN, hiding the extra effect in final value alone. Independent target journals record method receipt, applied transition and reply behavior, fsynced before withholding; the service never waits holding a journal/object lock and continues servicing later methods.

The `default25s` case names and `ordinary_zbus_timeout_ms:25000` output field were **unverified fixture assumptions**, not measured default-timeout evidence. The40s watchdog outcomes cannot establish normal helper completion, default timeout replay or a normal-return negative. Preserve them as unavailable; no retry is authorized in this closeout.

The public reachability result is the actual platform-native cached-ref function, **not the registered SetValueTool, full CUA SDK authorization route, or desktop binding**. No generic outer SetValueTool keyboard fallback is claimed. No public TypeText route was exercised.

## Separate actual core dispatch

Actual pinned cached core registry/run_steps invokes the counted registered Tool twice when foreground_fallback=true and delivery_mode is omitted, despite its first error carrying dispatched=true/may_have_landed=true/retryable=false plus foreground advice. The independent per-attempt journal preserves that first result; the final batch report alone says success/one step. This proves registry retry, **not D-Bus effects**. Normal ACK invokes once; true pre-send refusal invokes twice but declares one effect; false/default fallback, explicit/inherited background delivery and direct-tool controls invoke once. No product run_steps/run_actions/run_script call was established; script-authored retries are not tested here.

The Footwork AX control calls the actual single-write method over the private bus but stubs binding/writability/identity validation. Its linux_ax.py hash **ee6d25eb4a36970868094f5e5ac21b33e3adf3e8698abf28dcb6c3f1a34d4c1d** matches the parent's current file; cloud native.py hash differs. This is a supplemental single-send uncertainty control, **not current whole-product runtime qualification or a generalized Footwork bug**.

## Build, counts and cleanup

Both offline compiles succeeded with Rust1.97.1. The entire pinned Linux module was compiled, with a test-only child-module suffix; production function bodies/constant prefix and Cargo.lock were retained byte-for-byte. Default Cargo feature selection and40 cached dependency artifacts were selected by exact existing Cargo fingerprint. No dependency install/fetch or pin change. [Build provenance](execution-build/build.json), [frozen commands/package hashes](command.json). Audit binary SHA256 **fe767c90d60e62f368d8c96d802359e4b8fc066251d5ceb9fb1de86959cefbbd**. Cached core artifacts are separately hashed; no claim of a new clean dependency build.

There are **26 saved receipts:24 normally returned clients and2 watchdog-unavailable clients**. The overall driver exit1 retained red one-effect safety assertions; it was not converted to success. All36 explicit target/private-bus waits completed, no helper escalation. The outer supervisor recorded no remaining descendants, no intervention or monitor errors. All55 captured process identities were absent on recovery inspection. These are scoped test-owned cleanup facts, not a global census or product guarantee.

Raw [first-run journals and receipts](first/), [stdout](stdout.txt), [stderr](stderr.txt), [supervisor cleanup](cleanup.json), and [compact closeout](closeout.json) are preserved. No production fix, new test, shared desktop mutation, OBS change, install/fetch or push/PR occurred during recovery/closeout. Parent owns further review; this package stops here.
