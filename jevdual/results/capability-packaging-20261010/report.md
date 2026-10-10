# Local capability package qualification

The pure-Python MIT wheel is built and checked locally. The final artifact has 74 members and SHA256 `f734ad127da548ce1b12d3e95b114f76d9893cefe58e6a188d49059cdd3414f7`. Repeated builds produce identical bytes. Source freeze: `b28af7c`; artifact and MCP version: `0.0.1`. [Artifact manifest](artifact.json), [summary](summary.json).

The wheel includes the runtime modules, policy data, MIT license, dependency metadata, CLI entries and verified RECORD hashes. It excludes Rust binaries, research/evaluation data, tests, caches and secrets. The original maturin acceleration build and pinned driver/model roles remain unchanged. Package checking follows the local chrome-devtools-mcp artifact verifier's mechanism; no upstream source is copied. License metadata follows PEP639.

## Consumer boundary

The final wheel was installed offline with `--no-deps` into an owned virtual environment. Dependencies were explicitly reused from the existing environment through a project-owned `.pth` file. This proves package installation and installed runtime behavior; it does not prove a fresh machine can resolve dependencies offline. The pure fallback runs without a Rust toolchain or provider account for the supported slice.

Outside source, with PYTHONPATH removed, the installed console entry point successfully generates a private per-job UUID task/configuration, refuses overwrite with exit2, reads all nine declared dependency requirements from installed metadata, reports current permission/scope prerequisites, rejects the retained unknown completion claim with exit1 without changing its DB, and returns unavailable exit2 for recursive malformed JSON. [CLI receipt](installed-cli.json).

The actual installed MCP server then binds the owned browser/TextEdit resources, launches its real detached fixed-action worker, appends the exact source value, and returns the same operation after server restart and repeated token. The independent AX oracle confirms one exact append; the durable journal contains one record. The installed report validator accepts the applied claim. Doctor subsequently warns about existing ledger history. [Worker receipt](installed-worker.json), [history diagnostic](doctor-existing-ledger.json).

Package and worker module paths and Python prefix resolve inside the installed environment, with no repository source on the import path. Worker registration, observed kernel executable/cmdline and packet match. Module origin is qualified through the installed interpreter probe, inherited module resolution and actual receipt-backed execution, rather than direct child-memory inspection. macOS exposes the framework Python executable in kernel argv0 while Python preserves the venv interpreter; the verifier checks both identities.

## Review and checks

The final full local suite passes **1,473 tests with 27 skips**. Ruff and notebook checks pass. The skipped native/browser/live paths are not silently credited; the dedicated installed-native run supplies the relevant real-surface evidence.

Claude reviewed the completion contract, implementation, packaging and all remediations through the authorized mailbox without additional paid calls. No packaging blocker remained. Fixed follow-ups derive doctor requirements and server version from installed metadata and clarify responsible-process permission attribution. Doctor's optional requirement parser degrades to unverified if absent.

Two initial installed-harness failures remain retained: v1 stopped before input on lexical path comparison; v2 executed correctly but rejected the macOS argv0 representation. V3 qualified the first unchanged wheel with the corrected evidence chain. V4 qualifies the final rebuilt artifact and generated task. [Retained harness context](retained-harness.json). No original run was regraded.

The owned fixture holder exited cleanly. Independent identity checks confirm its browser PID is absent and no TextEdit window names the owned document. [Cleanup receipt](cleanup.json). Operation/run evidence, wheels and the owned verification environment remain under the active worktree's output directory.

## Limits and next boundary

This remains the macOS loopback browser-to-TextEdit slice with explicit resource IDs. It does not discover arbitrary apps, verify saved-file persistence, certify the host's whole job or control unwrapped interactive prose. The enforcing publication adapter is required; [A2](../operation-completion-20261010/report.md) qualifies its four native cases. Original A1 remains7/8 answer acceptance.

No remote CI, push, merge, public registry publication, global host configuration or network dependency installation occurred. The next release check is a clean-machine dependency install and first-use journey through the same per-run setup and enforced adapter. [Consumer guide](../../docs/capability-packaging.md).
