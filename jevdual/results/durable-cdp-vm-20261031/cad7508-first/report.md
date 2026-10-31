# First durable CDP VM candidate: retained harness failure

**This is not a clean qualification.** Exact source `cad7508f8f4375735c0651c5e0aa5929f3b57700` ran one unchanged ten-module installed batch: **187 passed, 3 failed, zero skips**, in **29.31 seconds**. Pytest and outer runner exited **1**. All three failures are the test-only collector's `Path(Popen)` error while wrapping restart-fixture `_test_cleanup`; it prevented that helper's original cleanup. They are not attributed to the product and are not removed from the denominator. [JUnit](junit.xml), [full output](pytest.stdout.txt), [inspected summary](inspected-summary.json).

## Exact installed boundary

Candidate checkout: `/workspace/footwork-durable-cdp-cad7508`, detached and unchanged. Wheel `jevdual-0.0.1-py3-none-any.whl`, **211 entries**, SHA256 **`e466146e5ba77e68470eea7cca86d7beb84d42c3dfe3a7ac7e15ca06a6530660`**. All **206 installed product package files** byte-match. [Build](build.json), [source/test/wheel hashes and installed origins](environment.json).

Fresh consumer `/workspace/scratch/footwork-durable-cdp-cad7508/consumer`: binary pytest8.4.2, psutil7.2.2, websockets15.0.1, packaging26.3 and pytest dependencies; product installed `--no-deps`. CUA/browser-use are absent. Matching consumer Python and `FOOTWORK_EXECUTABLE` point at the installed script. Ten tests were copied unchanged outside checkout; no checkout conftest or PYTHONPATH. The test-only receipt plugin is explicit and its original source was committed before measurement at605d257; copied plugin/bootstrap hashes match [collector provenance](collector-provenance.json). Provider key was omitted from the test process environment; judgment uses the supplied fixture adapters, with no paid calls. [Command](command.json).

| Module | Passed | Failed |
|---|---:|---:|
| CDP effector / transport / custody | 17 / 21 / 10 | 0 |
| CDP click / contract | 30 / 33 | 0 |
| Browser durable authority | 49 | 0 |
| Browser holder | 18 | 0 |
| Browser guard | 6 | 0 |
| Public CDP CLI | 3 | 0 |
| Public holder restart | 0 | 3 collector cleanup errors |

## Per-cell retained evidence

The stock tests use an explicitly test-only holder shim calling `os._exit(86)` only after the original real journal transaction commits. Public look/click/status/recover/offline replay remain actual installed subprocess commands. The collector never patched product code, commands or replies. It recorded numeric process waits, public output and boundary files before temporary directories disappeared; holder nonces are hashed/redacted, not dumped. Full [observer events](observer.jsonl) accompany cell-specific receipts.

| Cell | Independent ingress | Recovered state / disposition / phase | Retained boundary |
|---|---:|---|---|
| [prepared](cells/prepared/receipt.json) | 0 | final / not_sent / not_sent | exit86 after admit commit; no execution receipt |
| [started](cells/started/receipt.json) | 0 | unknown / unknown / ambiguous | exit86 after start commit; no execution receipt |
| [retained](cells/retained/receipt.json) | 1 intended | unknown / unknown / sent | independent `/count` was1 **before exit86**; basis activation_ack |

All three markers have `heavy_imports=[]`, retained operation IDs match public recovery/status, and the original same-token replays return retained identity/disposition without another ingress. Completion remains unverified and retryable false. The prepared cell reached its final assertions before finally-cleanup failed. The started/retained cells reached recovery/status/replays/new-token refusal and correct ingress, but collector failure during the earlier cleanup call prevented the subsequent fresh-start/domain-block assertions from running. These partial cells are not promoted to passed tests.

The separate [real client-kill cell](cells/client-lost-ack/receipt.json) **passed**: the client was SIGKILLed after independent onclick ingress, one intended effect remained through repeat token/new-token block/stop/recover/offline replay. The [missing-guard cell](cells/missing-guard/receipt.json) **passed** with no admission or ingress. Durable/native separation, changed token/binding, missing/failed guard, absent readback, tampered evidence and disabled typing/other-route negatives passed their unchanged unit cases.

Actual installed output is retained for [tools](discovery/tools.json), [doctor](discovery/doctor.json), [schema](discovery/schema.json), [guide](discovery/guide.json). Doctor distinguishes prerequisite presence from `runtime_qualification=not_checked`, CDP needs no desktop/CUA, typing is disabled, acknowledgement is not business completion, unknown blocks new mutation, and full package metadata/light-split limits are explicit. No generic completion reader or metadata split is claimed.

## Process accounting and limits

Debian13.6, Linux6.18.57 native x86-64, Python3.12.14, Chromium154.0.8037.57, unchanged default sandbox flags. Visible policy remains **4-CPU quota / 16GiB**, cpuset0-4, cgroup PID/swap caps max; actual SwapTotal0. No 2CPU/8GB claim, system install, new VM/cloud infrastructure or runtime implementation change.

After pytest exited, the dedicated **test-only subreaper** captured **182 zombies and 36 live descendants**. Because the collector prevented fixture cleanup, the wrapper had to intervene: **36 SIGTERM attempts**, **35 sent by pidfd**, **one already exited**, then **202 adopted-child numeric waits**; final owned descendants are empty. Some original parents can reap children while termination proceeds, so pre-snapshot counts must not be equated with wrapper wait counts. [Pre-wrapper snapshot](post-pytest-before-wrapper-reaping.json), [cleanup receipt](cleanup.json), [observed identities](owned-process-history.json). This is wrapper cleanup of a failed harness run, not graceful product cleanup or a no-zombie guarantee. Non-atomic inventory/daemon-escape/global-cleanliness limits remain.

The raw `observer_gap=false` flag only checks explicitly handled observer-error records; these uncaught helper exceptions instead appear as failed pytest calls. That flag does **not** establish passive collection. The original frozen collector and copies remain intact. A separately versioned v2 collector restricts path snapshots to path-taking helpers and keeps snapshot errors outside original cleanup; it is prepared, **not yet measured**.

## Pending replacement

Parent review separately found holder TERM/INT setup too late during Chrome readiness, and CLI startup exceptions bypassing direct-child cleanup. This batch did not independently exercise those pre-readiness boundaries. Parent is fixing them and will supply another exact source/wheel/recipe. No old cell is rerun, no VM product patch is made, and no green gate is inferred from187 passes. All first failures and partial receipts remain preserved for comparison.
