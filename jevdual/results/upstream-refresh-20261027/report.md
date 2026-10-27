# CUA and Browser-use refresh — October 27, 2026

Footwork is updated to the local reference snapshots on branch `codex/upstream-cua-browser-use-20261027`. Implementation commit: `bde0c2898884c5ea22082baa2141b2ed70908919`. This is a locally built and checked change; hosted CI, publication and other operating systems remain unverified.

## Source and artifact identity

| Component | Adopted source |
| --- | --- |
| Browser-use | 0.13.14; submodule `2cc71890e65056b67fdb29d98bb407749c15bb08`; the installed package matches the critical Agent, DOM, tool and session source files |
| CUA Python and native engine | `d5373879e9e0baf5a63999ac4d26902340c0ce20`; distribution `0.38.0+footwork.d5373879` |
| CUA source archive | SHA256 `606d8c8696aa54afcff32f285f8f6730a8eef1b6c2b4730372f5ce2b0fe426b1`; immutable Git source, Rust 1.97.1 and locked Cargo dependencies |
| CUA native wheel | SHA256 `b2729cb0607bb47e858ba66d123ccf8f60232a1e6991d366b935d234dab18737`; macOS arm64, minimum deployment target 13.0 |
| Footwork consumer wheel | SHA256 `6e4abc6723594470684f3a8c30bc28873c3bda5e4f40afa3f379de27ff188e51`; checked pure-Python package |

The CUA PyPI package stopped at 0.37.0 during this work. An intermediate wheel used the 0.38.0 native release, but final comparison found that release behind the reference Rust implementation. The final build compiles the reference engine itself. Its actual CLI doctor reports the full `d5373879…` commit. Both clean installations contain a native library with the source-build hash. Published-release validation remains separate evidence.

## Verification ledger

| Criterion | Observed evidence | Result and boundary |
| --- | --- | --- |
| Current APIs preserve existing integration | Full suite: 1,738 passed, 21 skipped, 5 live tests deselected | Pass; includes 12 headless browser tests and source build, contract, session, authority and receipt checks |
| Inherited Browser-use behavior | All 138 selected upstream tests passed on final dependencies | Pass; removed the previous navigate-test exclusion |
| Native source identity | CLI doctor build commit; compiled CLI/SDK and wheel hashes; installed SDK hashes on Python 3.12/3.14 | Pass on this Mac; no released native binary substitutes for reference source |
| Consumer installation | Fresh caches, private state, binary-only dependencies, explicit built CUA wheel, isolated imports and doctor on Python 3.12.6/3.14.7 | Both pass; same existing macOS host and permission database |
| Native public workflow | Installed MCP bind/read, append to the owned TextEdit fixture, exact destination readback, actual detached installed worker, reconnect/replay without duplicate append | Pass on Python 3.12; initial owned Chrome foreground prerequisite applies |
| Source packet | Frozen source commit, 29 members, verified source-only CUA archive and helpers, existing archive bounds | Pass; packet SHA256 `ee2a0001855690f5edc6646de6c2d68292c17a0ecf864d148035eb11f04b3870` |
| Unchanged adjacent code | Rust formatting, Clippy and 19 Rust tests; 97 JavaScript tests | Pass |
| Hygiene and cleanup | Ruff, notebook validation and diff checks; fixture document/browser/listener cleanup receipts | Pass; only owned fixture resources closed |

The first inherited navigation probe timed out with both unpatched and patched code. Footwork's runner discarded upstream's session-scoped asyncio loop settings. Restoring those settings made both probes pass and restored the complete upstream selection. This establishes the current failure mechanism, not the cause of a historical timeout in another environment.

A real doctor invocation initially rejected valid whitespace in normalized Python metadata. The Python parser now uses standard specifiers; dependency diagnostics also recognize exact local source-version pins and reject a different build. Regression tests retain fail-closed behavior for absent, invalid and incompatible metadata.

## Native attachment prerequisite

CUA refuses a new background DevTools connection while another app is in front on the same Space. The first installed trial preserved that refusal and dispatched no capability append. Bringing only the owned fixture Chrome to the foreground before initial bind allowed the complete installed workflow to pass. Footwork retains background delivery and its existing authorization host, policy thresholds and Jev default. Normal native constructors explicitly select embedded execution, and observations request full structured snapshots.

The native trial verifies current destination content and replay behavior for one owned fixture. It does not qualify arbitrary profiles, apps, Spaces, permission prompts, screenshot modes, crash timing or general disk persistence. No model/provider calls or heldout evaluations ran. No performance or model-quality result was updated.

## Reproduce and inspect

From `jevdual/`, install Rust 1.97.1 and the platform prerequisites in [the source-build guide](../../docs/upstream/cua-driver-build.md), then run `uv sync`, `uv run pytest -q -m 'not live'`, `scripts/upstream_tests.sh`, and the contributor checks. Build the CUA wheel before consumer installation; the checked installation and onboarding guides supply it explicitly.

Local evidence is retained under the repository's ignored `output/` directory:

- `upstream-refresh-head-final-tests.log`, `upstream-refresh-head-upstream.txt`
- `cua-native-head/build-receipt.json`, `upstream-refresh-native-head-doctor.json`, `upstream-refresh-head-installed-origins.json`
- `upstream-refresh-head-package/receipt.json`, `upstream-refresh-head-clean312/receipt.json`, `upstream-refresh-head-clean314/receipt.json`
- `upstream-refresh-head-installed-trial/receipt.json`, `upstream-refresh-head-fixture/cleanup.json`, `upstream-refresh-head-packet/`
- Earlier disconfirming probes: `upstream-refresh-doctor-before.json`, `upstream-refresh-browser-bind-probe.txt`, `upstream-refresh-browser-pure-go-back.txt`, `upstream-refresh-local-pin-before.txt`

The source archive and build procedure are committed; compiled wheels and native caches remain local. Cross-platform source build routes and CI prerequisites are configured but have not been executed on hosted runners in this package.
