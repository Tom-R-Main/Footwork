# Final exact durable CDP safety-classification Linux qualification

**201/201 passed**, zero failures/errors/skips/warnings, in **63.52 seconds**. Numeric pytest and outer-runner exits are **0**; collector error/gap is false. [JUnit](junit.xml), [complete output](pytest.stdout.txt), [inspected cases/cells](inspected-summary.json).

Tested source: **`e4df2c6b04644c332c8a636c556ae2fee0822d28`**, detached `/workspace/footwork-durable-cdp-e4df2c6`, unchanged. Exact wheel `jevdual-0.0.1-py3-none-any.whl`: **211 entries**, SHA256 **`ae780174a9f0dcfc0583dd9ed9c814f9f940fbfa54b6f64fdf50aad38233b059`**. All **206 installed product package files** byte-match. [Build](build.json), [source/test/helper hashes and installed origins](environment.json), [collector provenance](collector-provenance.json).

Fresh consumer `/workspace/scratch/footwork-durable-cdp-e4df2c6/consumer` has binary pytest8.4.2, psutil7.2.2, websockets15.0.1, packaging26.3 and pytest dependencies; product installed with `--no-deps`. Neither CUA nor browser-use is installed/importable. The exact12 candidate test files were copied unchanged outside every checkout, with no checkout conftest or PYTHONPATH. FOOTWORK_EXECUTABLE is the installed footwork script, all subprocesses use its matching consumer Python, and Chromium's real ELF/default sandbox arguments are retained. [Exact command](command.json). This qualifies the explicit installed effector/CLI boundary; full dependency metadata remains unchanged and a public light metadata split is not claimed.

Prediction36aba24 and runnerbb6851a (unchanged collector3 fromeaba616) were committed before this single complete batch. The corrected, explicitly test-only collector preserves Popen arguments/results, original helper cleanup, actual command outputs, per-cell boundary snapshots and independent fixture records; helper hashes are recorded before measurement. No candidate product/test source was changed and no failed test was replaced. The earlier failed190-case artifact remains separately preserved, not relabelled ([first report](../cad7508-first/report.md)).

| Module | Passed |
|---|---:|
| CDP effector / transport / launch custody | 17 / 21 / 10 |
| CDP click / contract | 30 / 33 |
| Browser durable authority / holder / guard | 49 / 20 / 6 |
| Public CDP CLI / restart CLI | 3 / 3 |
| Startup CLI / startup lifecycle | 3 / 6 |

## Injected post-admission sensitivity controls

Both newly supplied cases `test_post_admission_retention_failure_never_certifies_no_send[False/True]` passed. They inject JournalError into result retention and mark_unknown after one mocked protocol activation. The return path must report `browser_retention_unverified`, `dispatched=null`, `retryable=false`; cancellation must propagate. Both assert the durable row remains dispatching/started, a second token is refused as unresolved, and activation count stays exactly1. [Exact passing case names/times](inspected-summary.json), with immutable candidate test hashes in environment.json.

These are **injected sensitivity controls, not a reproduced disk-full/storage incident**. The only runtime change from3484b03 is the narrow11-line post-admission classification fallback; no additional VM fault injection or exploratory probe was added. The prior [3484b03 199/199 run](../3484b03/report.md) and [cad7508 187/3 collector-failure run](../cad7508-first/report.md) remain independent retained history.

## Public interruption, recovery and stable-token receipts

| Cell | Independent ingress | Recovered state / disposition / phase |
|---|---:|---|
| [Prepared-commit holder exit](cells/prepared/receipt.json) | 0 | final / not_sent / not_sent |
| [Started-commit holder exit](cells/started/receipt.json) | 0 | unknown / unknown / ambiguous |
| [Retained-execution holder exit](cells/retained/receipt.json) | 1 intended | unknown / unknown / sent |

The stock test-only holder shim exits **86** only after each real journal transaction commits. Markers have `heavy_imports=[]` and retained operation IDs matching public recovery/status. The retained cell's independent HTTP `/count` is **1 before holder exit**, and execution evidence basis is `activation_ack`. None becomes business-completed: completion remains **unverified**, retryable false. Each same-token replay returns the original operation/disposition twice without more ingress. Changed/new token refusal and fresh startup under an unknown authority domain are asserted by the unchanged tests; no replacement browser profile or readiness descriptor appears in those blocked startup cases.

The separate [real public client SIGKILL cell](cells/client-lost-ack/receipt.json) passed with exactly **one intended ingress** through same-token replay, new-token refusal, stop/recover and offline replay. It kills the actual client after independent ingress while the real onclick is still executing, not a forged response. The [missing-guard cell](cells/missing-guard/receipt.json) passed with no admission or ingress. Unit negatives retain stale/foreign/changed binding, changed token/request, failed/absent guard, tampered evidence, missing readback and native/browser validator separation. Typing and unsupported input remain refused.

All raw public stdout/stderr hashes, parsed output, numeric exits and boundary snapshots are in [observer events](observer.jsonl) and the per-cell event files. Holder nonces are hash-redacted. Actual installed discovery outputs are retained: [tools](discovery/tools.json), [doctor](discovery/doctor.json), [schema](discovery/schema.json), [guide](discovery/guide.json). Schema names the executable `browser cdp click` path. Doctor keeps `runtime_qualification=not_checked` separate from prerequisite presence, names guard/absolute authority requirements and no desktop/CUA requirement. Guide explicitly states disabled typing, unknown/unverified acknowledgement semantics and pending light metadata split. No generic completion reader is tested or claimed.

## Real pre-readiness startup signals

All four dedicated startup supervisor processes and their holders exited **0**, with empty stderr, **no readiness publication**, and **zero captured LIVE processes before the supervisor's own test cleanup**. This liveness assertion precedes test termination/reaping.

| Cell | Captured identities | Zombies before test reap | Test-only reaped |
|---|---:|---:|---:|
| [TERM during launch](cells/startup-launch-15/receipt.json) | 10 | 5 | 5 |
| [INT during launch](cells/startup-launch-2/receipt.json) | 11 | 6 | 6 |
| [TERM during connect](cells/startup-connect-15/receipt.json) | 13 | 5 | 5 |
| [TERM during navigation](cells/startup-navigate-15/receipt.json) | 14 | 6 | 6 |

Each cell preserves the supervisor's actual stdout JSON, stderr/exit, and startup-boundary identity metadata before TemporaryDirectory deletion. The supervisor uses real Chrome and candidate product startup with bounded test-only delays at acquisition/connection/navigation boundaries; its Linux subreaping is **test infrastructure**, not product behavior. The remaining startup lifecycle unit cases cover cancellation while the worker thread owns the handle and explicit cleanup uncertainty. Startup CLI unit cases verify actual direct-child cleanup on exceptional readiness and preservation of successful startup.

## Environment and process accounting

Debian **13.6**, Linux **6.18.57**, native x86-64, CPython **3.12.14**, Chromium **154.0.8037.57**. Visible quota **4 CPUs** (`400000 100000`), cpuset0-4, **16GiB** memory, PID/swap cgroup caps max, actual SwapTotal0. No 2CPU/8GB claim, system installs, new VM/cloud resources, paid model calls or OBS/desktop capture occurred.

The outer wrapper's post-pytest snapshot contained **205 adopted zombies, zero live descendants**. It issued **zero extra signals**, reaped all205, and finished with **zero owned descendants**. [Pre-wrapper snapshot](post-pytest-before-wrapper-reaping.json), [numeric waits/cleanup](cleanup.json). The four nested startup supervisors separately report their5/6/5/6 zombies/reaps above. PID1 is `tail`; neither inner nor outer test-only subreaping is presented as graceful product zombie cleanup. Bounded/non-atomic inventory, daemon escape and global-process-cleanliness limits remain explicit.

This new exact-artifact batch resolves the earlier collector compatibility gap on these201 cases. It does not erase the first run's187/3 failures or its wrapper intervention, and does not assert universal reliability. Parent owns independent review, PR18 and merge; the VM made no runtime or test implementation changes.
