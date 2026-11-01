# IR2: candidate guard for ambiguous CUA Linux text writes

## Question and hypothesis

Can a small candidate patch to the exact carried CUA Linux source preserve an ambiguous EditableText failure through native callers and prevent an alternate mutation within one invocation? IR1 found two independently journaled effects after a post-effect D-Bus error in both actual helpers and public native `set_value_ref`; a withheld reply replayed in helpers under a declared100ms timeout. This package evaluates a candidate only. Footwork's installed `cua-driver` distribution and vendor archive stay unchanged.

## Design

Start from the same carried `d5373879+cleanup2` archive, SHA256 `5588fa808559de5982f9195c1031696f51a67b057164fd42b60485ac6c30b401`. Preserve an explicit false reply as a separate acknowledged-rejection branch for compatibility; propagate a mutation method's transport error as an ambiguous effect and stop all later text/Value/keyboard routes in the same invocation. At caller boundaries, preserve the error rather than reducing it to `false`, `None`, a stale-target guess, or a generic retry suggestion. A timed-out in-flight call is ambiguous. The exact patch and test harness must be committed as a frozen package before execution.

First execute selected cases in Linux cloud chat `01a18d7f-d0d0-733c-93c9-8f554f4190df`, host `durable`, using the already owned private D-Bus fixture and offline cached build. Keep each case fresh and use its target-owned fsynced journal as the effect oracle. Compare unchanged IR1 source against the candidate where useful; no network install/fetch, shared desktop input, production pin change, or public push. The test-only source inclusion must still compile complete production Linux code with no copied mutation function. Record patch identity, build features, command, timeouts, attempts/effects, return classification and process cleanup.

Required controls: normal ACK succeeds with one attempt/effect; explicit false-before-effect remains a compatible two-attempt/one-effect path where the candidate promises it; post-effect error and withheld reply with a declared100ms timeout each stop with one effect and an error/uncertainty; deliberate double-write journal control still detects two effects. Exercise both actual helpers and public retained-reference `set_value_ref` where reachable. Inspect all outer `TypeTextTool` routes and `SetValueTool` error projection; a source-only review does not qualify public TypeText runtime. The IR1 ordinary-budget public withheld case and two default-helper watchdog cases are not rerun merely to turn unknowns into green counts. Keep actual batch `run_steps` retry as a separate later package.

## Primary metric and decision

Target-owned applied mutation entries per one invocation after the first applied effect, separately for each tested fault and boundary. A candidate holds at a named boundary only if the first effect was independently recorded before reply loss/error, no later mutation is recorded, and the caller returns uncertainty or an error that does not invite blind replay. A passing helper alone does not qualify the registered tool or Footwork product. Any second effect, swallowed ambiguous error, untested outer route or stale build identity limits or fails the corresponding claim. A false-before-effect control that stops rather than falls back is an explicit compatibility change to report, not a silent pass.

## Evidence discipline

The notebook prediction is committed before execution. The candidate patch and harness get their own frozen commit before the first resolving test. Preserve original IR1 receipts; write new results to `results/cua-ambiguous-write-ir2-20261101/`. Run `scripts/redact_results.py` before committing result artifacts. Append a dated result section without editing the preregistration above.
