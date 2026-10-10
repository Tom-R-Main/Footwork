# Fresh dependency installation qualification

The local fresh-install boundary passes on this macOS arm64 host with Python **3.12.6** and **3.14.7**. Each profile installs **115 packages** from an independent empty cache as binaries, passes dependency consistency and strict prerequisite checks, and executes its actual installed server/worker through the exact generated configuration. This is fresh dependency and redirected user-state evidence on the existing Mac, not a new machine or fresh OS/TCC database.

Final source: 2613cff. Wheel: jevdual-0.0.1-py3-none-any.whl, 75 members, SHA256 54a4085c992f7066c105f1ce3772d310725b457858543766ea8958cb2e4a275a. Repeated builds match. [Summary](summary.json).

| Profile | Binary install / consistency | Strict prerequisites | Actual native / restart / report |
| --- | --- | --- | --- |
| Python 3.12.6 | pass, 115 packages | pass | pass, one exact append and one journal record |
| Python 3.14.7 | pass, 115 packages | pass | pass, one exact append and one journal record |

[3.12 installation](py312-installation.json), [3.14 installation](py314-installation.json), [3.12 native](py312-native.json), [3.14 native](py314-native.json).

## Isolation and actual execution

Profiles have no system-site inheritance, dependency-borrowing .pth or repository imports. Installer configuration discovery and index overrides are disabled; Python paths, optimization overrides and provider credential variables are removed without printing values. Each profile has private HOME, XDG config/cache and temporary directories. Installed wheel tags, resolved versions, import paths and fresh cache byte counts are recorded. System Python/stdlib, OS frameworks and existing Chrome/TextEdit are explicit prerequisites.

The generated server, detached worker and report adapter now use Python isolation mode (-I). Four shadow packages planted in the host working directory cannot override the installed modules. Actual server and registered worker diagnostics confirm the fresh environment prefix, private HOME, loaded module and Cua SDK library paths, disabled user site, and disabled known browser-use telemetry/cloud sync. Each profile has five linked runtime contexts. Worker code origin is implied by its isolated invocation and installed parent package and separately checked by the interpreter probe; its __main__ file origin is not recorded directly. These are diagnostics, not operation authority or completion receipts.

Both native flows read the owned source value, append exactly once, restart the server, and collect the same operation on repeated token. The independent AX oracle reads Invoice report followed by 17.25 USD. Historical applied reports validate. The updated isolated report rejects the retained A1 completed/applied claim over its actual unknown operation even in the shadow working directory, leaving the original DB hash unchanged. [Negative report](unknown-report-negative.json).

## Setup improvements and review

Doctor now exposes met/blocked prerequisite status, stable blocker codes, interpreter/architecture and installed distribution locations. Default diagnostic success remains exit 0; strict mode returns exit 1 for blockers. A bare wheel without dependencies reproduces missing prerequisites: default 0, strict 1, blocked status. [Missing prerequisites](missing-prerequisites.json). Doctor performs no driver startup, permission requests, input or journal recovery. Met prerequisites do not certify a window, effect, saved file or completed job.

Reference mechanisms:
- Cua doctor.rs 28–103 provides structured status/error semantics. Its newer doctor also removes legacy files at 571–606; that command is not used or copied.
- Hermes install.sh 17–21 disables ambient uv configuration; platform artifact validation at 326–394 reinforces checking actual binaries and hashes.
- Open Computer Use install-config-helper.mjs 613–717 probes the exact configured stdio command with initialization and tool discovery.
- Arc permission guidance ties grants to the responsible terminal/editor and relaunch. Existing same-host guidance is retained.

Source versions differ: local browser-use 0.13.11 and Cua 0.34 are references, while Footwork retains browser-use 0.13.10 and cua-driver 0.28.2. The newer browser-use platform marker is not adopted; Footwork uses sys_platform == darwin. No upstream source copied or pins changed.

Claude reviewed the plan, isolation/provenance changes, launch remediation and actual final native receipts through the authorized mailbox, without paid calls. His cwd-shadowing blocker was independently reproduced and fixed for all three launch paths. Final evidence review has no blocker and approves this bounded local qualification; the nonblocking __main__ origin gap above remains explicit.

## Retained runs and checks

Initial v1 attempts stop before resolution on mutually exclusive uv flags. V2 installs are dependency-only evidence with inherited HOME and Python 3.14.5/3.12.6. V3 installs qualify the prior U1 artifact's private profile. The first 3.14 native run executes correctly but fails the actual HOME gate because a relative profile path was passed. All are retained, not regraded. [Failure context](retained-failures.json), [cwd-shadow baseline](cwd-shadow-baseline.json).

Final full suite: **1,485 passed, 27 skipped**. Ruff passes; final notebook closeout is checked separately. The owned fixture holder exits0; independent checks confirm its browser PID is absent and no matching owned TextEdit document window remains. [Cleanup](cleanup.json).

## Limits

Existing macOS, system frameworks, browser/editor installations and TCC grants remain shared. Fresh OS permission prompts and an independent machine remain unqualified. There is no exhaustive filesystem or outbound-network trace; configured state is redirected and known browser-use telemetry is disabled. Arbitrary apps, saved-file persistence, whole-job certification and unwrapped interactive prose remain outside the slice.

No global configuration/permission changes, push, merge, publication or paid model calls occurred. Local run environments, caches and evidence remain owned by the active worktree. [Consumer guide](../../docs/capability-packaging.md).
