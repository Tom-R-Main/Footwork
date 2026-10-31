# Light profile: Footwork without CUA or browser-use in the base install

Written 2026-10-30 at `origin/main` `52601b1`; reviewed against merged Linux reliability base
`5acf3b2` on 2026-10-30. The original baseline observations below remain historical. Sources: the Muse light-mode proposal and the Claude and
Codex assessments of it (2026-10-30), the source checks recorded below, the repo-learn library at
`output/repo-learning/linux-consolidation/library` (card `installed-cli-serves-version-matched-guide-v1`
and its nearest cards), and the Legible Loop v6 draft (26 September).

**Milestone:** an agent in a 2-CPU / 8 GB sandbox installs Footwork from binary wheels, with no Rust or
C compiler, and drives a Chrome that Footwork owns. Available routes retain authority checks, honest receipts
and completion rules. Durable browser mutations remain unavailable until L3c qualifies admission,
unknown outcomes and restart recovery; neither the current browser nor a new CDP transport has that
guarantee merely by owning Chrome. Footwork tells it which profile it has, what that
profile can do and how to get the rest. The full profile keeps its current behavior, receipts included.

Every package opens with a notebook file (`docs/notebook/<date>-<package>.md`) whose predictions are
committed before the tests that resolve them, and closes with a summary and
`uv run python -m evals.notebook docs/notebook --check`.

## What is already true

Checked on `52601b1` unless noted.

- **The command path already imports without the heavy dependencies.** With `browser_use`, `cdp_use`,
  `cua_driver`, pyobjc, `jeepney`, `anthropic` and `openai` blocked by an import hook, `jevdual.cli`,
  `agent_cli`, `session`, `native`, `browser_driver`, `linux_session`, `linux_x11` and
  `capability.backend` import. `tools`, `agent` and `evidence` do not: they import browser-use at module
  level. This proves import-time availability only. L1 must isolate every runtime constructor and SDK input,
  including the Linux target probe; L2 must separately prove installed dependency closure. (A
  module that imports may still need the dependency when called; L0 turns this into a test.)
- **browser-use serves the exported `DualProcessAgent` loop and DOM helpers.** The public
  `footwork run` command currently constructs `NativeAgent` over CUA, not `DualProcessAgent`;
  its actual import closure determines its install hint. `tools.py`, `agent.py`,
  `evidence.py`, `s1.py`, `chrome_profile.py`, `patch.py`, `testing.py`, `menu.py`'s DOM functions
  (`_is_sensitive_input`, `_page_text`) and the `_pure`/`_adapters` twins, which delegate whole
  functions (`build_snapshot_lookup`, `PaintOrderRemover`, `filter_dynamic_classes`). The session
  browser route builds its menu with `menu_from_semantic` from CUA's snapshot and never touches
  browser-use.
- **The CUA surface is small and enumerable.** Constructors: `CuaDriver.create(embedded=True)` in
  `session.py`, `cli.py`, `coexist.py` and `capability/backend.py`, and `configured_driver(pid)` in
  `browser_driver.py`. Driver methods: `list_apps`, `list_windows`, `get_window_state`, `click`,
  `invoke_menu`, `verify_state`, `shutdown`, `call_tool`. `call_tool` names: `press_key`, `type_text`,
  `set_value`, `scroll`, `hotkey`, `bring_to_front` (desktop) and `browser_prepare`,
  `get_browser_state`, `browser_click`, `browser_type`, `browser_navigate` (browser). Typed inputs:
  `ListAppsInput`, `ListWindowsInput`, `GetWindowStateInput`, `ActionTarget`, `ClickInput`,
  `ClickPosition`, `InputDeliveryMode`, `InvokeMenuInput`, `VerifyStateInput`.
  `tests/contract/test_cua_driver_seams.py` pins it (16 tests).
- **The browser bridge surface is smaller still.** `BrowserBridge` exposes `attach(expect_url)`,
  `observe() -> WebMenu`, `act(menu, operation, id, text, route)` and `navigate(url)`. `key`,
  `hotkey` and `menu` already refuse. Click defaults to the `dom_event` route (the trusted route did
  nothing on six background controls on 2026-09-25); `--route trusted` is opt-in. Typing replaces held
  text only through the foreground posture.
- **Chrome identity is Footwork's, not CUA's.** `launch_chrome`, `chrome_pid` (unique root, executable,
  uid, profile and port arguments) and `_incarnation` (start time) run before CUA sees anything. CUA
  contributes the authorization callback and the DevTools client. Chrome listens on a fixed loopback
  port (`FOOTWORK_CHROME_PORT`, default 9333).
- **The capability wheel is already pure Python.** `scripts/build_capability_wheel.py` produces
  `py3-none-any`; the Rust core is optional (`JEVDUAL_PURE_PY=1` runs the twins). It still declares
  the full dependency list (`docs/capability-packaging.md`).
- **`host_probe.probe()` already reports what doctor needs**: memory, cgroup CPU and memory limits,
  executables, session indicators and prerequisite candidates, with `runtime_qualification:
  "unverified"`.
- **There is already an operation-level seam.** `capability/contracts.py` defines `Backend`
  (`validate`, `dispatch`, `readback`, `same_incarnation`). The effector seam in L1 sits below it, at
  the driver; it does not replace it.

## Corrections to the earlier assessment

- `linux_x11.py` is a read-only Xlib probe ("Isolated read-only Xlib helper"). The Linux helpers give
  exact text (AT-SPI) and identity, not a desktop effector. Enumeration, snapshots, input, focus and
  delivery evidence remain to be built.
- An owned effector qualifies against independent outcomes (fixture ledger, saved bytes, readback from
  a separate process), never against agreement with CUA.
- "No JS-click fallback" was wrong as stated: the DOM-event click is today's default route. The rule is
  that no route switches or resends automatically after an unknown outcome.
- `--remote-debugging-pipe` needs a process that outlives each command, because every `footwork browser
  …` command is its own process. Pipe custody is therefore a broker decision (L3b), not a flag.

## Decisions

| # | Decision | Outcome |
|---|---|---|
| D1 | The README says "browser-use is the foundation and stays a dependency." Moving it to an extra reverses that. | **Decided 2026-10-30:** browser-use moves to the optional `[agent]` install; the README credit changes with L2. |
| D2 | Extras only add packages, so the light set must be the base of some distribution. Either the base of `jevdual` becomes light and full is `jevdual[desktop,agent]`, or a new `footwork-core` distribution is light and `jevdual` depends on it plus CUA and browser-use. | **Decided 2026-10-30:** one distribution whose base is light. Nothing is on a public registry yet (`capability-packaging.md`), so local recipes, bundles, the lockfile and all CI consumer recipes must change together. `cua-driver`'s local version label cannot be hosted on PyPI anyway, so the patched desktop artifact needs a wheelhouse, bundle or suitable private index. An extra
  declares that artifact; it does not host it. Public-registry installation of the light base is a
  release goal, not an available command today. A second name would double release and qualification artifacts for no install that a single name cannot express. |
| D3 | Whether the light profile runs Chrome headless. | **Decided 2026-10-30:** the constrained browser profile defaults to headless on both platforms; `--headed` is explicit and
  requires a usable display. The existing CUA profile keeps its current launch behavior. No display
  variable is treated as proof of display readiness. Record the mode in session state and receipts. The posture rules stay unchanged in both modes; relaxing them for headless is a later, measured change. |

## Order

| # | Package | Behavior change | Size | Depends on |
|---|---|---|---|---|
| L0 | Baseline and guards | none | S | — |
| L1a | Lazy CUA compatibility boundary; retain SDK request/result semantics | none | M | L0; reliability PR12 merged |
| L1b | Owned typed requests and normalized result records | none | M | L1a |
| L3a | Direct-CDP browser effector, port transport; nondurable preview | new opt-in effector | L | L1b |
| L3c | Browser durable admission, retained unknowns and restart reconciliation | new qualified mutation route | L | L3a |
| L2 | Dependency split and profiles | install contents | M | L3a and L3c qualified |
| L4 | Agent discovery | new fields and `guide` | M | L2 |
| L3b | Pipe custody through a broker | browser transport | M | L3a |
| L5 | Upstream provenance manifest | docs and CI | S | L1a |
| L6 | Owned Linux X11 desktop effector | later opt-in effector | L, incremental | L1b, L5; separate implementation package |

L1a is the first implementation PR. It must preserve the merged reliability fix and current SDK
payloads. L1b changes data representation only after that seam is checked. L3a remains opt-in in the
full install; L2 must not make a preview browser into a default durable mutation route. L3b and L6
remain later packages, not prerequisites for the initial light release. Each implementation PR names
its checked artifact, remaining packages and recovery to the preceding qualified release.

## L0. Baseline and guards (no behavior change)

- **Import-closure test.** `tests/test_import_closure.py` runs a subprocess with a `sys.meta_path` hook
  that blocks `browser_use`, `cdp_use`, `cua_driver`, `Quartz`, `AppKit`, `ApplicationServices`,
  `jeepney` and `mujoco`. It imports the CLI, session, capability server and Linux modules (expected
  to pass) and `tools`, `agent` and `evidence` (expected to fail until L2 moves them behind
  `[agent]`). It exercises `footwork --json catalog`, `schema` and `doctor` under the block: catalog/schema
  remain usable and doctor accurately reports missing dependencies rather than claiming readiness.
  Expected nonzero diagnostic status is not an import-closure failure.
- **Golden receipts.** Record receipts, operation journals and `look` outputs for the existing
  browser fixture jobs (form, append, ticket) and the desktop TextEdit/Mousepad jobs at the merged PR12 baseline `5acf3b2`.
  Existing independent fixture outcomes remain the oracle. Normalize only explicitly listed volatile
  timestamps/UUIDs/paths; compare all refusal codes, effect/delivery words, evidence and dispatch flags.
  Reuse retained baseline runs where artifact identity matches; do not erase earlier failures.
- **Resource baseline.** In the working Linux VM, record actual cgroup limits and headroom, artifact
  hashes, download size, wheel count, install time, cold/warm observation time, cgroup peak memory
  and PID counts for the binary full profile. No deliberate source rebuild is needed to establish the
  consumer baseline. Later compare light on the same host and include a 2-CPU / 3-GiB / zero-swap
  qualification plus an explicitly constrained-headroom case; a nominal 8-GB VM is not its headroom. Owned output directory: `results/light-profile-baseline-<date>/`.

Exit for L1a: import/discovery guards and retained fixture comparisons pass. Runtime resource
measurement is required before light-profile performance claims, not before a no-behavior adapter.

## L1a / L1b. Effector seam (no behavior change)

Collision: this rewrites driver construction in `session.py`, `native.py`, `browser_driver.py`,
`coexist.py`, `cli.py` and `capability/backend.py`. PR12 has merged as `5acf3b2`; base the work on it. Also include `linux_session._target_probe`,
  which constructs the SDK in a fresh worker process.

- **L1a compatibility boundary.** `effectors/cua.py` owns every SDK import, lazy request constructor,
  embedded-driver creation and configured browser authorization host. Factories expose a typed
  `EffectorUnavailable` with capability, missing distribution and a version-appropriate install hint.
  Keep SDK requests/results intact in this package: lossless compatibility is the promise, not a
  completed portable data model. Existing browser compatibility entrypoints delegate to the adapter;
  strict root/incarnation authorization and awaited shutdown remain unchanged. Never convert a broken
  transitive import or native loader failure into “optional package absent.”
- **L1b owned contract.** Narrow `DesktopEffector` and `BrowserEffector` protocols and frozen records
  describe exactly what callers read. Derive the fields from callers and fixture coverage as well as
  seam tests; those tests assert subsets and do not define complete snapshots. Normalize every enum,
  optional field, unknown extension and refusal payload without strengthening evidence or dropping
  delivery/coverage metadata. Preserve `hint` and `next_call`, whose removal previously broke refusals.
- Replace generic `call_tool` inside bridge callers with bounded typed adapter operations in L1b.
  No unrestricted new tool or raw CDP surface is exposed to the host agent.
- Keep upstream seam tests where CUA is installed; add implementation-independent tests for identity,
  stale references, pre-dispatch refusal and unknown outcomes. L1a also tests the absent-package path
  and the public discovery commands in a subprocess with heavy imports blocked.

Notebook prediction (draft):

```
## LP1 · prediction · <clock time before running>
Hypothesis: putting CUA behind effectors/cua.py changes no receipt, journal entry or refusal code.
Test: replay L0's golden fixture jobs and the full suite (native and JEVDUAL_PURE_PY=1) before and after.
Predicts: byte-identical receipts and journals apart from timestamps and ids; seam tests pass unchanged in content.
Against: any receipt, effect word or refusal code differs, or a module outside effectors/cua.py imports cua_driver.
```

Exit: AST checks find SDK import statements only in `effectors/cua.py`; existing scenarios,
real-SDK seam tests and installed discovery pass. Record runtime tests not repeated on this package
separately from retained PR12 reliability evidence. L1b closes only after normalized-contract checks.

## L3a. Direct-CDP browser effector, port transport

`python/jevdual/effectors/cdp/`, Footwork-owned, standard library, `orjson` and a maintained pure-Python WebSocket client, no `cdp-use`.
Do not implement WebSocket framing as part of an effector port.

- **Transport.** A bounded asyncio WebSocket client for the browser endpoint, with request IDs,
  response correlation, event routing, cancellation and explicit disconnected/unknown states. Chrome starts with
  `--remote-debugging-port=0`; Footwork reads `DevToolsActivePort` from its own profile directory and
  connects to the browser-level path it names, after `chrome_pid()` and `_incarnation` match the
  recorded root. Parity with today's fixed loopback port, without a predictable port. (WebSocket
  framing is provided by the transport dependency, not handwritten.)
- **Identity.** Each ref binds browser incarnation, context, target, CDP session, frame, nonempty
  `loaderId` and backend node. Reobserve that exact tuple and the node's connected/editable/enabled
  state, operation eligibility and relevant semantics before dispatch. Unknown generation invalidates
  refs. Never recover a missing node by matching a replacement label. Initial qualification may omit
  child-frame controls with explicit partial coverage; otherwise iframe navigation/OOPIF session changes
  require their own tuple. A main-frame loader check alone is insufficient. `targetId` survives reconnection while the browser lives, which
  makes the "page is the identity between commands" workaround in `session.py` a fallback, not the
  primary key.
- **Snapshot.** `Accessibility.getFullAXTree` joined to `DOM.describeNode` by `backendDOMNodeId`,
  emitted in the shape `menu_from_semantic` already consumes (`page`, `snapshot`, `refs` with
  `ref`/`role`/`name`/`states`/`actions`/`value`), so `WebMenu`, candidate ids and receipts stay
  unchanged. Refs bind the complete identity tuple above; omissions, unsupported frames and truncation are
  explicit coverage fields. Sensitive-input redaction ports the rule now
  read from browser-use's `_SENSITIVE_INPUT_TYPES` and `_SENSITIVE_AUTOCOMPLETE_PREFIXES` into a
  Footwork constant, with provenance (L5).
- **Actions.** Click `dom_event`: `DOM.resolveNode` then `Runtime.callFunctionOn` in an isolated world
  (`Page.createIsolatedWorld`). Click `trusted`: `DOM.scrollIntoViewIfNeeded`, `DOM.getBoxModel`,
  `Input.dispatchMouseEvent` press and release at the content-box centre. Type: support only explicitly qualified editable field types, read the complete pre-value,
  check exact focus, set an explicit caret-to-end for append or select-all for an authorized replace,
  then `Input.insertText` and exact post-value readback. Refuse unsupported contenteditable, readonly
  and sensitive fields. Preserve the existing empty-or-append rule and posture gate on replace. Navigate:
  `Page.navigate`, then a bounded wait on `Page.lifecycleEvent`. The route used goes in the receipt.
- **Readback.** Value, checked state and URL are read in the isolated world to avoid page-patched
  reader functions. This is DOM-state evidence, not independent proof of submission or persistence.
  Fixture ingress counts, stored rows and saved bytes establish those separate postconditions.
- **Prohibited.** No raw CDP or JavaScript passthrough to the agent, no automatic route switch, no
  resend after an unknown outcome.
- **Selection.** `FOOTWORK_BROWSER_EFFECTOR=cdp|cua` and `browser start --effector`, recorded in
  session state so a session never changes effector mid-task. The default stays `cua` until
  qualification passes.
- **Qualification.** Run the browser fixture jobs and the ticket fixture through both effectors on the
  full install. The oracle is the fixture's independent ledger (ingress count, stored row) and the
  journal, not CUA. Include the pre-header cells: the navigation POST restart is Chromium's
  (`PHU1`), so the CDP effector should reproduce it; fetch submission should keep one ingress
  (`PHU2`). The open unknown is whether `Input.insertText` and `dispatchMouseEvent` reach a background
  tab in a headful window without selecting it; test this with a page-visibility probe like the one
  used on 2026-09-25.

Notebook predictions to write first: (1) CDP and CUA produce the same menu candidates for each fixture
page; (2) each fixture job ends in the same ledger state and receipts under both effectors; (3) a
`loaderId` change between observe and act is refused with nothing dispatched.

Exit: the bounded supported surface passes on macOS and Linux, including same-URL reload, same-
document node replacement/repurposing, child-frame navigation or omission, focused-selection changes,
disabled controls and removed pinned tab with a live sentinel tab. No automatic target rebind,
route switch or uncertain retry is permitted. Headless/headed results are recorded separately.

## L3c. Browser operation authority and recovery

The current `browser_authority_unqualified` refusal remains until this package closes. Owning a CDP
transport or observing a changed DOM does not supply durable admission.

- Persist browser/context/target identity and operation arguments before dispatch; reuse the existing
  authority store and `Backend` admission/readback contract without weakening native identity checks.
- Separate not-sent, admitted/possibly-sent, observed effect, verified postcondition and completed.
  Any loss after admission retains unknown and blocks redispatch, including after CLI/broker restart.
- Reconcile unknown operations through read-only evidence bound to the intended resource and arguments.
  A changed URL or a confirmation-looking node cannot settle a server effect alone.
- Require the configured guard/authorization route, mutation receipt and postcondition evidence.
  A missing guard refuses; missing readback leaves completion unverified.
- Qualify a fixture that commits a mutation and then drops the acknowledgement. Restart the CLI,
  retry the same operation and prove independent ingress stays at one; include interrupted admission,
  unavailable readback and a missing-policy negative control. Document browser-internal POST retries
  separately; Footwork cannot promise global exactly-once execution from a local operation ledger.

Exit: lost-ack/restart/duplicate controls pass on the exact installed light candidate. Until then,
L3a is an opt-in nondurable preview, and durable browser mutations refuse before launch/input.

## L2. Dependency split and profiles

| Install | Contents |
|---|---|
| `jevdual` | `typesafe-sdk`, `orjson`, `psutil`, `mcp`, `packaging`, the WebSocket transport and the CDP effector |
| `jevdual[desktop]` | `cua-driver` (pinned), pyobjc on darwin, `jeepney` on linux |
| `jevdual[agent]` | `browser-use==0.13.14` |
| `jevdual[tools]` | `mujoco` |
| full | `jevdual[desktop,agent]` from the bundle wheelhouse: today's install |

- `build_capability_wheel.py` writes the extras into the metadata; the wheel stays `py3-none-any` and
  the Rust core stays an optional acceleration wheel. Agent-host recipes and the onboarding packet
  name `jevdual[desktop,agent]` explicitly.
- Installs are binary-only (`--only-binary :all:`). When a wheel is missing for the platform, the
  installer stops with one line naming the package and the profile that avoids it. It never falls
  back to compiling.
- Runtime refusals come from the L1 factories, before any backend import: code
  `effector_unavailable`, the missing distribution, and the exact artifact-aware next command. Commands check their actual capabilities: `footwork run` currently needs desktop, whereas
  `DualProcessAgent` and its DOM helpers need `[agent]`. An SDK-present import failure is a broken
  install, not an absent extra. Patched CUA hints name the matching bundle/wheelhouse; do not suggest
  a public-index command that cannot resolve its pinned local version.
- The binary-only installers (`scripts/capability_clean_install.py`, `scripts/build_agent_bundle.py`)
  take `--profile light|full`. Separate builder and consumer: the builder may compile explicitly requested artifacts; consumer
  install forbids compilation. Do not guess profile suitability from arbitrary 4-core/12-GB
  thresholds or from the absence of Rust on a correctly prepared binary consumer. Doctor reports
  observed cgroup limits/headroom separately from configured budgets and recommends a qualified
  profile only within its measured envelope. The agent explicitly selects; never switch an existing
  session's profile because host load changed. Regenerate/check `uv.lock`, wheel metadata, bundle
  role inventories and full-profile CI install commands together.
- CI: a `light` job installs `jevdual` from the built wheel with no extras into a fresh
  environment on Linux and macOS, runs the import-closure test in its passing form, and runs the browser
  fixtures headless through the CDP effector. Full jobs must install the explicit full extras and retain their existing behavior gates.

Notebook question: how much install/runtime cost does the light candidate remove on L0's measured
host? Report cold/warm time, bytes, peak cgroup memory and PIDs without inventing performance gates.
Correctness gates remain exact; resource limits are fixed before testing, never tuned after failures.

Exit: both profiles are qualified in the VM; README, `capability-packaging.md` and the quickstart
describe both.

## L4. Agent discovery

The rule from Legible Loop v6: declare the boundary where the agent acts, the moves it may make and
how the result will be judged. Q11 showed that more declaration produced 21% more driver requests, so
every field below is short and its effect is measured.

- **`doctor`** adds:
  ```json
  "profile": "light",
  "effectors": {
    "browser": {"selected": "cdp", "available": ["cdp"], "missing": {"cua": "jevdual[desktop]"}},
    "desktop": {"selected": null, "available": [], "missing": {"cua": "jevdual[desktop]"}}
  },
  "resources": "<host_probe resources>",
  "runtime_qualification": "unverified"
  ```
  Having the prerequisites does not mean a run will succeed, and doctor says so.
- **`catalog` and `schema`** carry `requires_effector` per command using the real command graph (`browser *` → browser; native `start`, `apps`, `menu` and
  today's `run` → desktop; the exported planner → agent). Mixed commands report each required capability. An agent learns what it cannot do before it tries.
- **Refusals** are the L2 `effector_unavailable` shape, the same in the CLI JSON envelope and the MCP
  server.
- **`footwork guide [topic]`** prints version-matched guidance from
  `python/jevdual/_tool_resources/guide/*.md`, shipped in both wheels (the agent-browser `skills get
  core` mechanism, card `installed-cli-serves-version-matched-guide-v1`). Topics: `core` (the loop,
  authority, receipts, completion), `profiles`, `browser`, `desktop`. `--help` and `catalog` point to
  it in one line.
- **Measurement.** A small Muse trial in a light sandbox: tasks that need the desktop effector, with
  and without `guide`, counting turns until the agent installs the right extra or reports the limit
  correctly, and counting wrong-command attempts. Size it before running; it needs separately scoped spend/provider authorization. Deterministic discovery/refusal checks
  are the initial acceptance gate; absence of a paid trial does not justify an invented result.

Exit: installed doctor/schema/guide agree with actual profile capabilities; wrong-profile commands
refuse without dispatch and provide a resolvable artifact hint. A paid trial remains unrun unless scoped.

## L3b. Pipe custody through a broker

`--remote-debugging-pipe` gives the connection only to the launching process, which removes the
loopback port as an attack surface for other local users. Because each CLI command is a separate
process, a long-lived holder is needed:

- `footwork browser start` spawns a broker that launches Chrome with the pipe, holds fds 3 and 4, and
  serves a Unix socket in the session's private directory (mode 0700). The broker checks peer uid
  (`SO_PEERCRED` on Linux, `getpeereid` on macOS), authenticates the session/operation scope and relays only the effector's method set, not raw
  CDP. `browser stop` ends it.
- The MCP server is already long-lived, so it can hold the pipe without a broker.
- Same uid is not exclusive agent authority. Broker crash/timeout is not proof Chrome stopped;
  retain pending operations, cleanup ownership, survivor/uncertainty diagnostics and bounded shutdown.
- Owning the pipe proves only communication custody of the launched Chrome. Target, frame and `loaderId` checks
  from L3a still apply to every action.

Prediction: across 20 sequential commands the broker adds under 20 ms median per command, and a
second-uid process cannot reach the browser. Against: either fails, or a broker crash leaves an
operation recorded as anything but unknown.

## L5. Upstream provenance manifest

`docs/upstream/manifest.toml`, one entry per adopted mechanism:

```toml
[[mechanism]]
name = "sensitive-input-redaction"
upstream = "browser-use"
commit = "<sha>"
files = ["browser_use/dom/enhanced_snapshot.py:Lx-Ly"]
source_sha256 = "<hash of the cited lines>"
local = "python/jevdual/effectors/cdp/redaction.py"
tests = ["tests/test_redaction.py"]
```

Entries cover CUA's browser snapshot shape and authorization rules, browser-use's DOM rules, and any
mechanism L6 takes from CUA's Linux crates. `scripts/upstream_check.py` re-hashes each cited range in
a reference checkout and lists changes. A changed hash means review the mechanism, not that it broke;
an unchanged hash does not prove compatibility. Use repo-learn `verify` on the same evidence ids. The
CUA pin and `PROVENANCE.md` stay as they are while `[desktop]` exists.

## L6. Owned Linux X11 desktop effector (incremental)

Build only after L3a has qualified and L5 exists. Each step is its own notebook package, qualified on
independent outcomes, and ships behind `FOOTWORK_DESKTOP_EFFECTOR=owned` with CUA as the default:

1. Enumeration: apps and windows from EWMH (`_NET_CLIENT_LIST`, `_NET_WM_PID`) through the existing
   isolated Xlib helper pattern, with the PID start-time identity from `platform_identity.py`.
2. Snapshot: AT-SPI tree to `WindowState`, extending `linux_ax.py`.
3. Focus and input: XTEST key and button events, with the coexistence posture rules from
   `coexist.py`. This is the step most likely to fail qualification.
4. Delivery evidence: AT-SPI text readback from a separate process plus saved-file bytes, as
   `linux_documents.py` does today.

Wayland is a new identity backend (`linux-next-tranche.md` §6) and macOS comes last: background input
delivery there has not been traced. Neither is in scope here.

## Risks and open questions

- Background-tab input over CDP in headful Chrome is unverified (L3a).
- Headless and headful Chrome may differ on the fixtures (focus, visibility, lifecycle events). Run the
  light CI job headless and the comparison on both.
- WebSocket framing is new owned code. The alternative is the pure-Python `websockets` package.
- The full install now needs explicit extras and the bundle wheelhouse; any recipe that still says plain `jevdual` silently gets the light profile. Doctor's `profile` field and the refusals are the guard.
- The VM resource numbers in L0 do not exist yet. The light profile's benefit is predicted, not
  measured.
- Discovery fields can raise request counts (Q11). L4's trial is the check.

## Existing work-item identifiers

One task per package, with its exit criterion as acceptance criteria:

| Package | Existing ID |
|---|---|
| L0 | af8088e8 |
| L1 | 20f9e0dd |
| L3a | 519ce2ed |
| L2 | ce4f81e7 |
| L4 | 9ff3b7d5 |
| L3b | 4ec9260c |
| L5 | f9f68af7 |
| L6 | 5ee944c4 |


## Review disposition (2026-10-30)

Reviewed against PR13 `b3496f7` and merged reliability base `5acf3b2`; a second read-only context used
this session's model, not another model family. Findings corrected above: durable authority was
promised without an implementation; iframe/session identity and live node semantics were incomplete;
typing selection was unspecified; isolated-world readback was overclaimed; native `run` was assigned
the wrong extra; resource heuristics and consumer/source-build roles were unsupported. L1 is split so
compatibility isolation can be verified before a data-model migration. The resource and paid-discovery
studies remain unrun. No light-profile runtime guarantee follows from this plan review.
