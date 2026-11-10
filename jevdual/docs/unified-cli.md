# Install once, use the Footwork CLI

Footwork ships one `footwork` executable for its browser, desktop and auxiliary tool families. Discovery does not start a driver or contact a model:

```sh
footwork tools
footwork schema
footwork doctor
footwork --json tools
```

The catalog states each family's actual commands and prerequisites. Missing hardware, OS permissions, optional runtimes or an injected browser adapter remain explicit gaps; discovery does not grant access.

## Choose an installation profile

The base `jevdual` wheel is the light profile: judgment, exact file checks, owned CDP and read-only
Lightpanda support without CUA or browser-use. Chrome and the pinned Lightpanda executable remain
separate prerequisites for their respective routes.

| Selection | Additional dependencies |
| --- | --- |
| `jevdual` or light bundle | No native or agent dependencies |
| `jevdual[desktop]` | Pinned CUA, PyObjC on macOS, Jeepney on Linux |
| `jevdual[agent]` | Pinned browser-use |
| Full bundle | Desktop and agent extras, plus simulator tools unless `--core-only` is selected |

`footwork tools` and `doctor` report the profile observed from installed distributions; Python does
not retain the extras originally requested. This reports dependency presence, not qualified runtime
access. An unsupported native request in a light environment refuses with `effector_unavailable`
before creating a driver. Install the matching full bundle to use those commands.

## Build one bundle

From `jevdual/`, build a light bundle using existing Python:

```sh
python scripts/sync_tool_resources.py --check
python scripts/build_agent_bundle.py --profile light --output /absolute/owned/footwork-light-bundle
```

For native desktop, the legacy browser route and the browser-use agent, build a full bundle with uv
and the [CUA native build prerequisites](upstream/cua-driver-build.md):

```sh
python scripts/build_agent_bundle.py --profile full --output /absolute/owned/footwork-full-bundle
```

Both bundles contain the same portable Footwork wheel, `install.py`, and a SHA256 manifest. The full
bundle additionally carries the exact host-platform CUA wheel. To reuse a checked native wheel,
pass `--cua-wheel /absolute/path/cua_driver.whl` to the full builder; its source pin must match.
The light builder never builds or carries CUA. No registry publication is required.

Install the chosen bundle into a new environment:

```sh
python /absolute/owned/footwork-light-bundle/install.py --profile light \
  --venv /absolute/owned/footwork-env --python 3.12
/absolute/owned/footwork-env/bin/footwork tools
```

For a full bundle, use its path and `--profile full`. A mismatched profile refuses before creating
an environment. Use the absolute executable from the agent host or add its `bin` directory to PATH.
On Windows the executable is under `Scripts`. Existing environments are refused rather than
overwritten. The installer uses an existing Python and either uv or venv with pip/ensurepip.
It never downloads Python or compiles dependencies: missing compatible binary wheels stop
installation. The full bundle's CUA wheel must match the interpreter's OS and architecture before
an environment is created; Linux wheels also require compatible system libraries.

`--offline` disables network access to package indexes. Supply compatible wheels for every selected
transitive dependency in the bundle directory; locally cached uv artifacts may also be available.
`--core-only` omits simulator dependencies from full installs. Node, ffmpeg, cameras, platform
libraries and applicable OS grants remain separate prerequisites. Swift/Vision OCR is macOS-specific.
These profiles do not establish a RAM or startup improvement; small-host measurement is separate.

## Browser and computer operations

The legacy `footwork browser start/look/do` verbs and `footwork desktop` route to the existing session commands. `start`, `look`, `do`, `read`, `done`, and `status` retain the existing admission checks, fresh target identities, receipts and completion verification. Browser start uses Footwork's dedicated Chrome; desktop start selects a running native app. Use separate explicit `--session` directories for independent tasks. Initial same-Space Chrome attachment may require bringing that owned Chrome window to the foreground.

For delayed native controls after navigation, use `footwork look --until "Song description" --timeout 10 --session /absolute/session`.
This repeats fresh read-only observations until an exact offered candidate label appears, with a
0.1–60 second deadline (default 10). It sends no input and prints the final available observation.
Timeout exits 6; partial coverage does not establish absence. A matching title, address value or page
text does not satisfy the check. Duplicate labels can satisfy appearance but retain all existing action
ambiguity checks. Appearance proves neither task completion nor that an action is authorized.
The deadline bounds cooperative observation and polling; driver shutdown still runs to completion.
This option currently supports native sessions only; ordinary `look` is unchanged.

On macOS, `footwork do type "Observed web field" "Text" --web-text-delivery foreground`
explicitly uses the focus-guarded native web text route. It requires the exact
`cua-driver==0.46.0+footwork.5486b624.cleanup2.focus1` runtime and a session started with
`--mode foreground_permitted` or `exclusive_desktop`. Shared foreground mode still requires three
seconds without human input. Existing action and replacement authorization gates apply;
`--no-judge`, browser mode, append and other operations refuse this option. A non-web target also
refuses before field mutation.

This is an explicit operation, never a fallback after uncertain background input. For a replacement,
the route activates the exact window, reobserves the field, sends a token-bound foreground Select All,
then revalidates identity/value and independently reads the complete selection before typing.
The driver proves addressed field focus inside its foreground activation guard before text synthesis.
If selection or delivery becomes uncertain, the command stops without retrying. A retained SDK
zero-text refusal stays separate from earlier preparation input. Read the receipt and inspect the
rendered field: AX value agreement does not establish that the renderer or server accepted the edit.
The exact target must have a readable current value; missing readback is never assumed empty.
The strict route requests positive character pacing, disabling the SDK's batched partial-tail retry
even if web ancestry cannot be established during delivery.

To edit only an existing selection, add `--web-text-range START:LENGTH`, measured in UTF-16
code units. For example, `footwork do type "Lyrics editor" "signal" --web-text-delivery foreground
--web-text-range 0:0` inserts at an already observed caret at offset zero. The option does not move
the caret, change the selection or send Select All. Independent fresh AX range and selected-text
reads must exactly match the requested slice of the unchanged raw field value. Surrogate splits,
out-of-value ranges, and values/results above 65536 UTF-16 units refuse before text synthesis.
The receipt compares the complete resulting value, including preserved prefix, suffix and trailing
whitespace. Unavailable or contradictory readback stays unverified. This is separate from whole-field
replacement; it does not normalize an AX terminal newline or establish rendered/server acceptance.

For a read-only DOM observation, use `footwork browser lightpanda read URL --executable /absolute/lightpanda`.
This separate profile owns one fresh external prebuilt engine and connection, withholds input/editable
values, and supplies no input authority or geometry. Run `footwork browser lightpanda artifact` and
`guide` for the installed pin and contract; see the [read-only Lightpanda guide](lightpanda-readonly.md).

For owned headless browsing, use the explicit `footwork browser cdp` route. It keeps guarded admission and unresolved operations across CLI and holder restart without CUA or a desktop session at runtime. Only the bounded native-button route is enabled; typing stays disabled and acknowledgement is not completion. Run `footwork browser cdp guide` for the installed contract, or read the [owned CDP guide](owned-cdp.md). The base light package supports this route without native or agent extras.

The original top-level verbs remain compatible. `footwork capability` exposes the existing scoped MCP configuration/server/report commands through the same executable. Its browser-to-TextEdit scope remains intentionally bounded; it does not grant generic input access to an MCP host.

### Native form targets

Native observations show an available ancestor label in brackets after a control. To distinguish
repeated actions, qualify the label with that exact section:

```sh
footwork desktop do click 'section:example.test::link:MANAGE' --session /absolute/path/session
```

The section must come from the observation. Footwork rechecks the role, label and section before
dispatch; a numeric ID whose meaning changed requires a fresh selection. A row without readable
context, or multiple controls with the same qualified identity, remains ambiguous even if pruning
shows only one representative. Native accessibility context is not a persistent DOM element ID.

On macOS, a bounded accessibility read retains web-field placeholders separately from actual values
and uses them to label otherwise unnamed fields. A verified empty field stays empty in value
readback. A changed observed set of text fields invalidates a pending placeholder-based selection;
reobserve after adding or removing rows. Missing attributes and replacements with identical observed
semantics remain limits of this semantic identity model.

Popup descendants take priority over ordinary page controls in the native candidate budget. To use
a larger budget, set it when starting a fresh session:

```sh
footwork desktop start 'Inspect the form' --app 'Google Chrome' \
  --native-menu-cap 240 --session /absolute/path/new-session
```

The default is 160 candidates; the supported range is 1–1000. The setting persists through later
observations and action revalidation. Increasing it cannot recover elements omitted by the driver;
`elements_incomplete` remains a separate limitation. A selector missing from a capped observation
is reported as unobserved within that budget, rather than absent from the page.

Early targeting refusals append `attempted_action` entries to `session.jsonl`, with `dispatched=false`,
a reason code, selector and observation coverage. These records do not count as dispatched `do`
actions or create success receipts. Typed payloads are omitted. Click receipts and field readback
do not prove server persistence; a saved form needs a separate save-and-reload check.

`--json` wraps command output and the underlying exit code for agents. JSON stdout appears once in `data`, with an empty `output`; ordinary text stays in `output` and stderr stays in `diagnostics`. Read the underlying action receipt to determine effects: an exit code or successful transport alone does not prove that an action applied or a task completed. For a long-lived capability server, retain its MCP stdio protocol rather than wrapping the stream.

`doctor` reports optional Jev Rust acceleration separately from the native CUA driver. The portable wheel uses the pure Python backend; that does not prevent desktop control. Native observations require Accessibility permission for the process hosting Footwork and report a permission blocker directly. Permission status describes prerequisites; it does not qualify a live capture or action. If startup fails, the session is not initialized; correct the reported cause and complete `start` before using `look` or `do`.

`doctor` also includes `host_prerequisites`: OS, architecture, Python, available memory, visible Linux cgroup limits, executable presence and session indicators. The same probe runs before installation with `python3 python/jevdual/host_probe.py` from `jevdual/`, or after installation with `python -m jevdual.host_probe`. It does not launch programs, contact providers, or expose environment-variable values. A present executable or display variable does not qualify a working browser or desktop. Linux native workflows remain unqualified; see [Linux qualification](linux-support.md).

The dedicated browser launcher recognizes installed Linux Chrome/Chromium binaries. Set `FOOTWORK_CHROME_EXECUTABLE` to the actual browser executable for a nonstandard installation such as Chrome for Testing. The process must match that executable, the exact owned profile and debugging port, and the current user. A shell wrapper with a different process executable does not qualify. These legacy launch checks do not supply missing desktop permissions or durable browser admission; the explicit CDP route above uses its own holder and authority protocol.

## Auxiliary families

Run `footwork tools` and family help to discover the installed commands. Camera capture, saved-frame inbox review, workbench notes, physical-workcell operations, and browser inspection analysis use bundled resources instead of checkout-relative paths. Their writable state belongs in an explicit output root selected by `FOOTWORK_TOOL_OUTPUT_ROOT`; installed package files are read-only resources.

Git-frozen research qualification and scoring commands retain their source-checkout requirement, reported per command in the catalog. They are not promoted to portable production operations.

Browser capture libraries that need a selected host tab and CDP adapter are exposed with their installed library paths and adapter requirements. A shell command cannot manufacture that host session. Offline inspection comparison, coverage and summarization remain executable without a browser.

## Maintain the packaged resources

`tools/` remains authoritative. After changing a runtime tool, run `python scripts/sync_tool_resources.py` and commit its generated snapshot and manifest. The drift check and installed-wheel tests reject stale resources. Test files, environments, caches, result directories and private output are excluded. Both the accelerated maturin wheel and the portable consumer wheel carry the same snapshot.

## Structured invocation and prerequisites

Agents can avoid shell quoting with a bounded JSON request:

```sh
printf '%s' '{"command":"schema","args":["browser","start"]}' | footwork invoke --input -
```

`invoke` accepts up to 64 KiB and 256 string arguments, uses the same command router, and always returns the JSON envelope. Recursive invocation and wrapping a live MCP/service stream are refused before dispatch. Run long-lived servers without `--json` so readiness and protocol output remain visible.

Discovery and observation do not contact a model provider. Commands that request Jev judgment or model-driven execution retain their existing credential and admission requirements. Doctor reports runtime prerequisites; it does not validate model credentials or certify a completed GUI effect.

The macOS CI artifacts include `ci-agent-bundle/install.py`, its manifest and both wheels. Download the artifact for the desired Python profile, then run its installer against a new environment as above. This path needs compatible Python and either uv or venv with pip/ensurepip; the consumer does not need a checkout or Rust compiler. Native control remains scoped to its [macOS permissions](quickstart.md) and [Linux X11 preview](linux-support.md); the explicit owned CDP route has the separate headless qualification described above.
