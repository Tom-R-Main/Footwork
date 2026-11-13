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
`cua-driver==0.46.0+footwork.5486b624.cleanup2.focus1.helptag1.connected4.locate7` runtime (or an earlier qualified focus1 build) and a session started with
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
--web-text-range 0:0` inserts at an already observed caret at offset zero. The option does not set
a caret/selection offset or send Select All. It first makes one explicit AXFocused preparation write,
requires independent application-focused-element equality and the exact bound key window, then
reobserves/rematches the unchanged field and proves focus again. Focus acknowledgement alone is
insufficient. Independent fresh AX range and selected-text
reads must exactly match the requested slice of the unchanged raw field value. Surrogate splits,
out-of-value ranges, and values/results above 65536 UTF-16 units refuse before text synthesis.
The receipt compares the complete resulting value, including preserved prefix, suffix and trailing
whitespace. Unavailable or contradictory readback stays unverified. This is separate from whole-field
replacement; it does not normalize an AX terminal newline or establish rendered/server acceptance.
Focus preparation and text dispatch have separate evidence: if a preparation attempt precedes a
failure, the overall input remains uncertain while a code-boundary receipt can establish that
`type_text` was never called and zero text characters were dispatched. Focus is not retried; only
its independent readback is polled until a 0.2-second cooperative deadline before refusing text.

For an ordinary native multiline whole-field replacement, a complete untruncated readback that
differs only in its internal LF pattern is `unverifiable`. Every non-LF character must match exactly;
this classification neither normalizes the field nor confirms the edit. Obtain independent readback
before retyping, since AX serialization can differ from copied content. Non-LF mismatches, browser
and secret handling, trailing-whitespace legacy behavior and strict selected-range comparison keep
their existing rules. A native menu invocation with no visible change is also `unverifiable`:
clipboard, disk or another-window effects need their own readback before retrying.

Native macOS links may show a complete `href` read independently from their exact bound AXLink.
Same-title links with distinct qualified HTTP(S) resources remain offered as separate numeric IDs.
Choose the ID from a fresh observation; the shared title still does not resolve uniquely. URL changes
or lost qualification require another observation and choice. Every observed same-title semantic peer
must have a readable matching AX title/description and complete URL before resource identity can
distinguish the group. Missing peer evidence, duplicate URLs and the 64-link read limit retain
ambiguity even when menu pruning hides peers. URLs over 2048 characters, credentials, whitespace,
relative and unsupported URLs are not qualified. Buttons in song rows do not inherit link identity.

Named native AXButton and AXPopUpButton controls can also carry an exact `native_dom_id` scoped to
their closest direct AXWebArea's complete HTTP(S) `native_document_url`. A semantic peer group is
qualified only when every observed peer has a readable matching name/frame, a unique untruncated
DOM ID, the same document URL and independently equal WebArea ancestor. Missing or duplicate IDs,
mixed/unreadable document scopes and the 64-control read limit preserve ambiguity before pruning.
DOM IDs over 512 characters or containing whitespace/control characters do not qualify. A changed
ID, document or lost qualification requires a fresh choice; position and SDK index are not identity.
The complete scoped identity appears in observations and inspect-target manifests/previews, binds
grants, and is persisted across CLI calls. It does not infer a song-row resource or identify a Play
button that exposes no DOM ID. Other native controls retain their existing identity rules.

For a native macOS menu that needs its window in front, use
`footwork do click "More actions" --click-delivery foreground`. This explicit option requires
foreground posture, shared-desktop idle admission, and normal action gates; browser mode,
`--no-judge`, other operations and mixed delivery options refuse before driver binding.
The route activates the exact bound window, freshly reobserves and rematches the qualified target,
then sends one SDK foreground click addressed by its fresh element token. Errors and refusals stop
without retry or automatic fallback. The default remains background delivery. A click acknowledgement
does not establish that the menu opened; reobserve its actual controls before continuing.

To bind an observed untitled native panel, use `footwork start "Panel task" --app "Google Chrome"
--pid PID --window-id CGWINDOWID`. Both IDs must be positive; the window ID must fit unsigned32 bits.
The exact ID must appear once in that process's on-screen SDK window list, including untitled entries.
An absent or duplicate ID refuses without falling back to a titled or larger window. `--window-id`
requires `--pid` and cannot be combined with `--window`, `--browser` or `--url`. Invalid combinations
refuse before driver creation or session reset. Later observed PID/window checks, posture and target
guards remain in force. A panel opening a nested modal requires a new explicit observed binding;
the caller's parent window never implicitly routes input to its child.

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

Shared-desktop operators should use separate session directories and the
[coordination and take handoff commands](desktop-coordination.md). Filmed starts
reserve both the desktop and subject app across command gaps; `control status`
shows owners and waiters, and exact tokens govern yield/cancellation.
