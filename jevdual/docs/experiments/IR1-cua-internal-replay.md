# IR1: lost acknowledgements inside pinned CUA

## Question and hypothesis

Determine whether a single invocation of the carried CUA Linux native write implementation can apply another mutation after its first mutation applied but its acknowledgement was lost. Expected mechanism: an error/false reply is reduced to `false`, enabling another EditableText operation, focus retry or outer delivery route without proof that nothing was sent. Keep the batch dispatch mechanism separate from native transport evidence.

Source: Footwork baseline `2ea51b30c71c3135a895103615005d14fd26f0ca`; CUA `d5373879e9e0baf5a63999ac4d26902340c0ce20` plus cleanup2; archive SHA256 `5588fa808559de5982f9195c1031696f51a67b057164fd42b60485ac6c30b401`. This preregistration and notebook prediction must be committed before their resolving tests. The first execution belongs to Linux cloud chat `01a18d7f-d0d0-733c-93c9-8f554f4190df` on host `durable`.

## Design

Use an owned private D-Bus daemon and instrumented fixture object exposing the AT-SPI interfaces required by the actual pinned Rust helpers. The target service owns the mutation journal; CUA result fields cannot manufacture those journal entries. Each case gets fresh object/value state and a unique operation identity. A journal entry distinguishes method receipt, effect applied and reply behavior. Use ASCII tokens initially so Unicode length is not a confound.

Exercise actual `set_value_on` and `write_through_editable_proxies` or their public retained-reference callers. Test-only module inclusion may access private functions, but production function bodies, fallbacks, constants, dependency graph and build features must remain byte-identical to the pin. A copied/reimplemented function is a model and cannot resolve the native hypothesis. Record exactly which boundary was exercised.

Required cases:

1. Normal successful acknowledgement: one applied mutation and no alternate mutation.
2. Explicit rejection before applying: record the rejected attempt and one allowed successful fallback separately; counts of attempts and effects differ.
3. Apply then return a D-Bus error: distinguish an acknowledged error from a genuinely withheld reply. This tests ambiguous post-effect errors, not missing-ACK timing by itself.
4. Apply then withhold the response: prove the service committed before the client deadline; identify the client's actual timeout result and whether an alternate mutation arrives. Any shortened connection timeout is a declared fixture condition. Repeat with ordinary public-operation budgets where reachable; never promote a shortened/private-helper result to an ordinary public-tool result.
5. Control that the independent journal detects a deliberate second mutation even when final text equals the intended text.

For batch execution, register an independently counted test tool in the real pinned registry and invoke actual `run_steps`/batch ownership. Inspect initial error, stale re-find and foreground eligibility, including explicit `delivery_mode`, default `foreground_fallback:false`, and contradictory may-have-landed metadata. This proves dispatch-layer retry behavior only; it does not substitute for native D-Bus effects. `run_script` is separately traced for automatic versus script-authored retry.

Trace Footwork's product callers. Its current Linux text replacement/append uses `linux_ax` single-write calls, while macOS/non-Linux and browser routes differ. Preserve that scope in results. If practical with existing fixtures, verify the exact Footwork Linux owner returns uncertainty after one send; a mocked product test supplements but does not replace the native test.

## Primary metric

Number of target-owned **applied mutation entries** after the first applied mutation and before the original invocation settles, keyed by one invocation ID. Supporting observations: ordered methods/arguments, attempted sends, independently held ACK barrier, final value, exception/result classification, client/operation deadlines and elapsed time. Repeated value alone is insufficient; replacement can conceal earlier effects.

## Decision rule

Support replay at a named tested boundary only if (a) the first effect is independently recorded before reply loss, (b) the same unchanged CUA invocation issues another mutation, (c) the target independently records that second effect, and (d) acknowledged and pre-effect controls behave as specified. A dispatch-only batch result supports only its separate dispatch claim. Failure to build, reach the target, apply the first effect, lose the reply, or keep the journal independent is inconclusive.

If all qualified missing/error-ACK cases stop with one effect and uncertainty, resolve the tested hypothesis as failed at those boundaries. Missing coverage stays unknown. Record normal-default and altered-timeout results separately. No patch, dependency bump, overall safety claim or replay fix is part of this package.

## Guardrails and evidence

No paid providers, secrets, personal profiles, shared desktop input, production runtime changes or public push/PR. Use existing cached tools/dependencies first; a missing dependency/tool is a reported gap, not install/fetch authorization. Bound each case and whole run; retain and reap only owned fixture processes. Do not alter Cargo.lock or select newer source. Preserve OBS and all other cloud work.

Retain source/build/test hashes, exact commands, first-run output, explicit skips, independent journals and cleanup outcome under a package-owned run directory. Commit the test package separately from the prediction before measuring it. Append notebook updates and a result section after evidence; preserve this preregistration text. Apply the project's result-redaction procedure before committing run artifacts.

## Result · November 1, 2026

Partial first-run evidence is retained in `results/cua-internal-replay-ir1-20261101/report.md`. Actual pinned native-helper calls produced two target-owned effects after a post-effect error; a withheld-reply case also replayed under a declared100ms client timeout. Controls distinguish one acknowledged effect from two attempts with only one effect after pre-effect rejection. Full ordinary-budget/public-tool, batch and current-product outcomes were not imported after the cloud agent turn was flagged and the app tools lost transport. The overall preregistered audit resolves inconclusive beyond those named observed boundaries. No production fix or dependency change was made.
