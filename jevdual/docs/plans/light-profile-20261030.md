# Light profile: Footwork without CUA or browser-use in the base install

Written 2026-10-30 at `origin/main` `52601b1`. Sources: the Muse light-mode proposal and the Claude and
Codex assessments of it (2026-10-30), the source checks recorded below, the repo-learn library at
`output/repo-learning/linux-consolidation/library` (card `installed-cli-serves-version-matched-guide-v1`
and its nearest cards), and the Legible Loop v6 draft (26 September).

**Milestone:** an agent in a 2-CPU / 8 GB sandbox installs Footwork from binary wheels, with no Rust or
C compiler, and drives a Chrome that Footwork owns with the same authority checks, operation history,
receipts and completion rules as the full install. Footwork tells it which profile it has, what that
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
  level. The remaining work is metadata, runtime selection and refusals, not an import refactor. (A
  module that imports may still need the dependency when called; L0 turns this into a test.)
- **browser-use serves only the `footwork run` agent loop and its DOM path.** `tools.py`, `agent.py`,
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
| D2 | Extras only add packages, so the light set must be the base of some distribution. Either the base of `jevdual` becomes light and full is `jevdual[desktop,agent]`, or a new `footwork-core` distribution is light and `jevdual` depends on it plus CUA and browser-use. | **Decided 2026-10-30:** one distribution whose base is light. Nothing is on a public registry yet (`capability-packaging.md`), so only local recipes and bundles change. `cua-driver`'s local version label cannot be hosted on PyPI anyway, so a full install always needs the bundle's wheelhouse; only the light base can install from a registry alone. A second name would double release and qualification artifacts for no install that a single name cannot express. |
| D3 | Whether the light profile runs Chrome headless. | **Decided 2026-10-30:** decide by environment, not profile: headless when no display is present, headful when one is, overridable with `--headless`/`--headed`. Record the mode in session state and receipts. The posture rules stay unchanged in both modes; relaxing them for headless is a later, measured change. |

## Order

| # | Package | Behavior change | Size | Depends on |
|---|---|---|---|---|
| L0 | Baseline and guards | none | S | — |
| L1 | Effector seam, CUA behind one adapter | none | M | L0; in-flight reliability work merged |
| L3a | Direct-CDP browser effector, port transport | new opt-in effector | L | L1 |
| L2 | Dependency split and profiles | install contents | M | L3a qualified |
| L4 | Agent discovery | new fields and `guide` | M | L2 |
| L3b | Pipe custody through a broker | browser transport | M | L3a |
| L5 | Upstream provenance manifest | docs and CI | S | L1 |
| L6 | Owned Linux X11 desktop effector | new opt-in effector | L, incremental | L1, L5 |

L3a precedes L2 so that the light profile has a browser on the day it exists, and so both browser
effectors can be compared on the full install first.

## L0. Baseline and guards (no behavior change)

- **Import-closure test.** `tests/test_import_closure.py` runs a subprocess with a `sys.meta_path` hook
  that blocks `browser_use`, `cdp_use`, `cua_driver`, `Quartz`, `AppKit`, `ApplicationServices`,
  `jeepney` and `mujoco`. It imports the CLI, session, capability server and Linux modules (expected
  to pass) and `tools`, `agent` and `evidence` (expected to fail until L2 moves them behind
  `[agent]`). It also asserts that `footwork --json catalog`, `schema` and `doctor` exit 0 under the
  block.
- **Golden receipts.** Record receipts, operation journals and `look` outputs for the existing
  browser fixture jobs (form, append, ticket) and the desktop TextEdit/Mousepad jobs at `52601b1`.
  These are L1's equality oracle.
- **Resource baseline.** In a 2-CPU / 8 GB Linux VM, measure today's install: download size, wheel
  count, wall time and peak RSS, with and without a prebuilt CUA wheel, and the RSS of one `browser
  look`. Owned output directory: `results/light-profile-baseline-<date>/`.

Exit: the test is in CI; golden receipts and the baseline report are committed.

## L1. Effector seam (no behavior change)

Collision: this rewrites driver construction in `session.py`, `native.py`, `browser_driver.py`,
`coexist.py`, `cli.py` and `capability/backend.py`. Start after the VM thread's reliability tranche
(native teardown abort, target-readiness timeouts) merges, or rebase onto it before review.

- New package `python/jevdual/effectors/`:
  - `base.py`: `DesktopEffector` and `BrowserEffector` protocols plus Footwork-owned frozen dataclasses
    for what crosses the seam (`AppInfo`, `WindowInfo`, `WindowState`, `ElementRef`, `ActionResult`,
    `BrowserSnapshot`). Field sets are exactly what the seam tests pin today: `test_window_state_fields`,
    `test_window_element_fields`, `test_action_result_fields`, `test_tool_result_fields`.
  - `cua.py`: the only module that imports `cua_driver`. It builds the driver, maps CUA types to
    `base` types, and owns the authorization host (`_host_class`) and `configured_driver`.
  - `__init__.py`: `browser_effector(pid, policy)` and `desktop_effector()` factories that return the
    CUA implementations and raise `EffectorUnavailable(kind, missing_distribution, install_hint)` when
    the import fails.
- `BrowserBridge` and `NativeBridge` take an effector instead of a driver. `call_tool(name, json)`
  becomes typed methods: `press_key`, `type_text`, `set_value`, `scroll`, `hotkey`, `bring_to_front`;
  `browser_prepare`, `browser_state`, `browser_click`, `browser_type`, `browser_navigate`.
- The seam tests move to `tests/contract/test_effector_cua.py` and run where CUA is installed. A new
  `tests/test_effector_contract.py` holds the implementation-independent contract that any effector
  must pass: identity refusal, stale ref refusal, no dispatch after a refused validation, unknown
  outcome kept unknown.

Notebook prediction (draft):

```
## LP1 · prediction
Hypothesis: putting CUA behind effectors/cua.py changes no receipt, journal entry or refusal code.
Test: replay L0's golden fixture jobs and the full suite (native and JEVDUAL_PURE_PY=1) before and after.
Predicts: byte-identical receipts and journals apart from timestamps and ids; seam tests pass unchanged in content.
Against: any receipt, effect word or refusal code differs, or a module outside effectors/ imports cua_driver.
```

Exit: `rg "cua_driver" python/` matches only `effectors/cua.py`; LP1 held.

## L3a. Direct-CDP browser effector, port transport

`python/jevdual/effectors/cdp/`, Footwork-owned, standard library plus `orjson`, no `cdp-use`.

- **Transport.** An asyncio WebSocket client for the browser endpoint. Chrome starts with
  `--remote-debugging-port=0`; Footwork reads `DevToolsActivePort` from its own profile directory and
  connects to the browser-level path it names, after `chrome_pid()` and `_incarnation` match the
  recorded root. Parity with today's fixed loopback port, without a predictable port. (WebSocket
  framing is the one piece of new protocol code; if it is not worth owning, `websockets` is a
  pure-Python dependency.)
- **Identity.** Every observation records `targetId`, the main frame id and its `loaderId` (document
  generation). Every action re-reads them first and refuses with `target_changed` or
  `document_changed` before dispatch. `targetId` survives reconnection while the browser lives, which
  makes the "page is the identity between commands" workaround in `session.py` a fallback, not the
  primary key.
- **Snapshot.** `Accessibility.getFullAXTree` joined to `DOM.describeNode` by `backendDOMNodeId`,
  emitted in the shape `menu_from_semantic` already consumes (`page`, `snapshot`, `refs` with
  `ref`/`role`/`name`/`states`/`actions`/`value`), so `WebMenu`, candidate ids and receipts stay
  unchanged. Refs bind `backendDOMNodeId` and `loaderId`. Sensitive-input redaction ports the rule now
  read from browser-use's `_SENSITIVE_INPUT_TYPES` and `_SENSITIVE_AUTOCOMPLETE_PREFIXES` into a
  Footwork constant, with provenance (L5).
- **Actions.** Click `dom_event`: `DOM.resolveNode` then `Runtime.callFunctionOn` in an isolated world
  (`Page.createIsolatedWorld`). Click `trusted`: `DOM.scrollIntoViewIfNeeded`, `DOM.getBoxModel`,
  `Input.dispatchMouseEvent` press and release at the content-box centre. Type: `DOM.focus` then
  `Input.insertText`, with the existing empty-or-append rule and the posture gate on replace. Navigate:
  `Page.navigate`, then a bounded wait on `Page.lifecycleEvent`. The route used goes in the receipt.
- **Readback.** Value, checked state and URL are read in the isolated world, so page scripts cannot
  shadow the readers.
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

Exit: all three held on macOS and Linux; the CDP effector passes `test_effector_contract.py`.

## L2. Dependency split and profiles

| Install | Contents |
|---|---|
| `jevdual` | `typesafe-sdk`, `orjson`, `psutil`, `mcp`, `packaging`, and the CDP effector |
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
  `effector_unavailable`, the missing distribution, and the exact next command, for example
  `uv pip install 'jevdual[desktop]'`. `footwork run` without `[agent]` refuses the same way.
- The binary-only installers (`scripts/capability_clean_install.py`, `scripts/build_agent_bundle.py`)
  take `--profile light|full`. They read `host_probe` and
  suggest `light` when the cgroup CPU quota is below 4 cores, available memory is below 12 GB, or no
  Rust toolchain or prebuilt CUA wheel exists. They suggest; the agent chooses.
- CI: a `light` job installs `jevdual` from the built wheel with no extras into a fresh
  environment on Linux and macOS, runs the import-closure test in its passing form, and runs the browser
  fixtures headless through the CDP effector. The current full jobs are unchanged.

Notebook prediction: in L0's VM the light install takes less than a quarter of the full install's
wall time and download size, and `browser look` peak RSS is within 10% of the full profile. Against:
either ratio is not met, or a light fixture job fails where full passes.

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
- **`catalog` and `schema`** carry `requires_effector` per command (`browser *` → browser; `desktop *`,
  `apps`, `menu` → desktop; `run` → agent). An agent learns what it cannot do before it tries.
- **Refusals** are the L2 `effector_unavailable` shape, the same in the CLI JSON envelope and the MCP
  server.
- **`footwork guide [topic]`** prints version-matched guidance from
  `python/jevdual/_tool_resources/guide/*.md`, shipped in both wheels (the agent-browser `skills get
  core` mechanism, card `installed-cli-serves-version-matched-guide-v1`). Topics: `core` (the loop,
  authority, receipts, completion), `profiles`, `browser`, `desktop`. `--help` and `catalog` point to
  it in one line.
- **Measurement.** A small Muse trial in a light sandbox: tasks that need the desktop effector, with
  and without `guide`, counting turns until the agent installs the right extra or reports the limit
  correctly, and counting wrong-command attempts. Size it before running; it is the only paid step in
  this plan.

Exit: doctor, schema and guide are in both profiles; the trial result is recorded either way.

## L3b. Pipe custody through a broker

`--remote-debugging-pipe` gives the connection only to the launching process, which removes the
loopback port as an attack surface for other local users. Because each CLI command is a separate
process, a long-lived holder is needed:

- `footwork browser start` spawns a broker that launches Chrome with the pipe, holds fds 3 and 4, and
  serves a Unix socket in the session's private directory (mode 0700). The broker checks peer uid
  (`SO_PEERCRED` on Linux, `getpeereid` on macOS) and relays only the effector's method set, not raw
  CDP. `browser stop` ends it.
- The MCP server is already long-lived, so it can hold the pipe without a broker.
- Owning the pipe proves only that Footwork launched this Chrome. Target, frame and `loaderId` checks
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

## exf

One task per package, with its exit criterion as acceptance criteria:

| Package | exf |
|---|---|
| L0 | af8088e8 |
| L1 | 20f9e0dd |
| L3a | 519ce2ed |
| L2 | ce4f81e7 |
| L4 | 9ff3b7d5 |
| L3b | 4ec9260c |
| L5 | f9f68af7 |
| L6 | 5ee944c4 |
