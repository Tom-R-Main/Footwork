# IR2: Mac-hosted Linux candidate guard, first run

**Result at tested boundaries:** the candidate stopped a second mutation after an ambiguous first EditableText acknowledgement in both actual pinned helpers and the public native retained-reference setter. All 14 selected cases returned normally and met their registered expectations. This is a candidate patch; Footwork's installed CUA pin and vendor archive are unchanged.

## Source, venue and order

- IR2 prediction/preregistration committed in `707a5c7` before any IR2 resolving test. The Linux cloud chat prepared a draft but was stopped by an automated possible-cybersecurity-risk review before building or testing IR2. The user then moved tests to this Mac; the venue amendment and byte-recovered patch were committed in `8d8ad55`.
- The tested package was frozen at Footwork commit `86fece5898f8f4256432db9718e2158b5fa1cf2d`. Candidate patch SHA256 `c1367501dc3f3eeca7f2f4d8d0afd3dda6c3c64af9542e4690ee3fb6d1f2d6a3`. Carried CUA archive SHA256 `5588fa808559de5982f9195c1031696f51a67b057164fd42b60485ac6c30b401`, upstream `d5373879` plus cleanup2; Cargo.lock SHA256 `3a75d89d3f2fc53cf9e910beb3a754b28f27d29f2a2d4feed632b3959eed557f`.
- Actual arm64 Linux execution ran inside Docker Desktop on the Mac, from locally cached image ID `sha256:f4b6128e6e031af4e1b13b5fc66c31573172a6fbbb1694b47eb1ac62a29eb264`. The container had `--network none`, no host desktop/auth sockets, a read-only root and only named project paths mounted. Rust 1.97.1 compiled the complete pinned Linux module with the candidate patch and appended test-only IR1 child module. Default Cargo feature fingerprint and 40 exact cached dependency artifacts were reused. Compile and link exited0 with no diagnostics; binary SHA256 `0ffc93c1eab592e6caabd7cf495fd707feb80c1c3d14611c725e8dd91de96f98`. [Build record](execution-build/build.json).
- A first build attempt exited before compilation because the Rustup shim tried to write to a read-only home. The harness was committed again to call the already installed compiler binary directly; no network fetch or runtime probe happened in the failed attempt. [First stderr](execution-build/first-attempt-stderr.txt).

## Independent target effects

Each case used a fresh owned D-Bus daemon and an independent Python AT-SPI target. The target fsynced `method_received`, `effect_applied` and `reply_behavior` entries. The runner graded the receipts, and the parent independently re-read all raw journals, checked event order and recounted effects. [Run summary](first/summary.json); [parent verification](parent-verification.json).

| Boundary | Fixture reply | Attempts / effects | Candidate outcome |
| --- | --- | ---: | --- |
| `set_value_on`, `write_through_editable_proxies`, public native `set_value_ref` | ACK | 1 / 1 each | success |
| Same three | false before effect | 2 / 1 each | success through existing alternate method |
| Same three | effect then D-Bus error | 1 / 1 each | `text_write_uncertain`, no alternate write |
| Both private helpers | effect then withheld reply, declared100ms client timeout | 1 / 1 each | `text_write_uncertain`, no alternate write |
| Public native `set_value_ref` | effect then withheld reply, ordinary3s budget plus500ms backstop | 1 / 1 | `text_write_uncertain` at3507ms, no alternate write |
| Direct D-Bus call control | effect then withheld reply,100ms | 1 / 1 | timed-out client error |
| Deliberate double-write control | two ACKed SetTextContents calls | 2 / 2 | final value TOKEN, proving readback alone hides an effect |

For the directly comparable post-error and shortened-timeout helper cases, the saved IR1 unchanged-source run had two target effects; this Mac candidate run had one. The IR1 baseline was x86_64 cloud Linux and this candidate was arm64 Linux on the Mac, so the comparison is source/fixture matched but not architecture paired. The independent control on this Mac detected a deliberate two-effect sequence. The public ordinary-budget withheld-reply case had one effect in both runs; the candidate changed its error classification, not that effect count. The `ordinary_zbus_timeout_ms:25000` field retained by the IR1 probe is an unverified label and is not treated as a measured default timeout.

All 14 clients returned without a watchdog. The 28 explicit target/bus waits completed with no escalation. The test container exited and no test container remained running. These are owned-fixture cleanup facts, not a whole-machine process census.

## Scope and unresolved paths

The candidate source also changes token re-resolution and TypeText/SetValue error projection, but this run did **not** invoke the registered `TypeTextTool` or `SetValueTool`, their full identity/authorization routes, a real desktop, or a Footwork CLI. A source review and successful compile do not qualify those routes. The optional `run_steps` foreground retry found in IR1 is a separate dispatch mechanism and remains unchanged. Explicit `false` replies still permit a second attempt by design; this fixture rejected before effect, but a real target that applies and then returns `false` is outside the established at-most-once claim. Default-helper withheld cases that reached watchdogs in IR1 were not rerun.

The pinned CUA distribution and Footwork product remain unchanged. This candidate is suitable for a targeted registered-tool regression package before any pin replacement or upstream proposal. There is no claim that the unexplained automated cloud flag was a false alarm.

## Task scratch and storage

The 1,608-file Mac build scratch was archived on External SSD and independently checked against the source file hashes before removal. The archive is 40,872,238 bytes, SHA256 `630b7d760ddee592e8577fe8ca56f249af96fa669ffd3ef38120d3fd54e0575f`. Docker Desktop was stopped normally after its test containers exited; no process held the scratch at removal. Removing only this task-owned regenerable directory increased measured Mac filesystem free bytes by 259,948,544. The cached Docker image remains for later outer-route tests. [Archive and reclamation receipt](scratch-archive-receipt.json). Historical Footwork output candidates from the separate space audit were not deleted.
