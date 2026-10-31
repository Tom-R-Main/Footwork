# Install once, use the Footwork CLI

Footwork ships one `footwork` executable for its browser, desktop and auxiliary tool families. Discovery does not start a driver or contact a model:

```sh
footwork tools
footwork schema
footwork doctor
footwork --json tools
```

The catalog states each family's actual commands and prerequisites. Missing hardware, OS permissions, optional runtimes or an injected browser adapter remain explicit gaps; discovery does not grant access.

## Build one bundle

From `jevdual/`, with uv, Python and the [CUA native build prerequisites](upstream/cua-driver-build.md):

```sh
python scripts/sync_tool_resources.py --check
python scripts/build_agent_bundle.py --output /absolute/owned/footwork-bundle
```

The bundle contains the Footwork wheel, the exact host-platform CUA wheel, `install.py`, and a SHA256 manifest. To reuse a checked CUA wheel, pass `--cua-wheel /absolute/path/cua_driver-….whl`. The source pin must match. No registry publication is required.

Install the bundle once into a new environment:

```sh
python /absolute/owned/footwork-bundle/install.py --venv /absolute/owned/footwork-env --python 3.12
/absolute/owned/footwork-env/bin/footwork tools
```

Use that absolute executable from the agent host or add its `bin` directory to the host's PATH. On Windows the executable is under `Scripts`. Existing environments are refused rather than overwritten. The installer uses an existing Python and either uv or its venv module. Without uv, it uses the interpreter's pip >=22.3 or seeds pip into the new environment from Python's bundled ensurepip. It never downloads Python or compiles dependencies: missing compatible binary wheels stop installation. The CUA wheel must match the selected interpreter's OS and architecture before an environment is created; Linux wheels also require compatible system libraries.

Installation includes the pinned MuJoCo tool extra by default; `--core-only` omits simulator dependencies. With uv, `--offline` uses locally available wheels and cache; with pip it disables package-index lookup and uses the bundle's local wheelhouse. The bundle initially contains the product and CUA wheels, so its transitive dependencies must also be supplied for an offline installation. Node, ffmpeg, cameras, platform libraries and applicable OS grants remain separate prerequisites. Swift/Vision OCR remains macOS-specific.

## Browser and computer operations

The legacy `footwork browser start/look/do` verbs and `footwork desktop` route to the existing session commands. `start`, `look`, `do`, `read`, `done`, and `status` retain the existing admission checks, fresh target identities, receipts and completion verification. Browser start uses Footwork's dedicated Chrome; desktop start selects a running native app. Use separate explicit `--session` directories for independent tasks. Initial same-Space Chrome attachment may require bringing that owned Chrome window to the foreground.

For owned headless browsing, use the explicit `footwork browser cdp` route. It keeps guarded admission and unresolved operations across CLI and holder restart without CUA or a desktop session at runtime. Only the bounded native-button route is enabled; typing stays disabled and acknowledgement is not completion. Run `footwork browser cdp guide` for the installed contract, or read the [owned CDP guide](owned-cdp.md). Package metadata still installs the full dependencies; the light installer remains pending.

The original top-level verbs remain compatible. `footwork capability` exposes the existing scoped MCP configuration/server/report commands through the same executable. Its browser-to-TextEdit scope remains intentionally bounded; it does not grant generic input access to an MCP host.

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
