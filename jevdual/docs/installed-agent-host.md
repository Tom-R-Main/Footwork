# Use the candidate from an agent host

Install the wheel as described in [installation](capability-packaging.md). Keep the environment and job directory private. Run doctor from the same responsible host that will launch the MCP server; a grant observed from another terminal does not establish this host's access.

For a disposable qualification task, the bundled helpers create an owned browser page and TextEdit document. Use absolute paths for every command. Verify an extracted qualification packet before creating output; a release bundle has its own manifest and is a different artifact.

1. Run `jevdual/scripts/capability_clean_install.py` with an existing Python, the bundled wheel and a new output directory. Its empty cache and private state test fresh dependencies on the existing OS.
2. From that installed environment, run `jevdual/scripts/capability_fixture.py --run-dir /absolute/owned/output/fixture`. Wait for its ready response; keep this Terminal open. The helper records exact source/destination identity and waits for cleanup.
3. In another Terminal from the same responsible host, run `jevdual/scripts/capability_fixture_config.py --scope /absolute/owned/output/fixture/scope.json --run-dir /absolute/owned/output/job`. This invokes public configuration and creates `host.json`, `run.json` and `report-schema.json` for one job.

The generated `host.json` is the complete ephemeral MCP registration for a compatible host. It uses the installed environment's absolute Python path, `-I`, the exact scope and the durable journal. Import that registration per job rather than changing global agent settings. The configuration does not grant OS permission or execution authority.

For Claude Code, the bounded tested recipe uses `--strict-mcp-config`, `--mcp-config /absolute/owned/output/job/host.json`, `--tools ""`, and `--allowedTools` containing `mcp__footwork__bind,mcp__footwork__observe,mcp__footwork__act,mcp__footwork__status,mcp__footwork__report`. Disable hooks and settings inheritance with `--setting-sources "" --settings '{"disableAllHooks":true}'`, and disable slash commands and session persistence. Choose a model and budget supported by your host; this candidate's measured model and CLI version are in the evidence summary. Do not copy credentials into the job.

Ask the agent to read the invoice total from the specified source and append exactly that value to the identified document, preserving existing characters. Require a structured final report matching the generated schema, with every admitted operation and `persistence: "not_checked"` unless separate persistence evidence exists. Claude's `--json-schema` accepts the schema object and may expose a `StructuredOutput` finalizer alongside the MCP tools. That finalizer formats the report and grants no resource access.

After the host stops, write only its structured claims to a private JSON file. Invoke the exact `report_adapter` recorded in `run.json`, adding `--input /absolute/owned/output/job/host-report.json`. Publish only the adapter's `trusted_summary`, including rejected claims; never substitute raw host prose. Exit0 accepts claims, exit1 rejects them and exit2 means validation is unavailable. The report certifies recorded historical operations as of its snapshot, not current GUI content or saved-file persistence.

Finish the fixture with one Ctrl-C and inspect its `cleanup.json` and exit status. Confirm the exact document window, owned browser/listener and detached worker are gone. A missing confirmation does not qualify automatic cleanup. Preserve unknown or refused results and reconcile before any further action.

This recipe needs existing compatible Python/uv/Chrome, applicable macOS permissions and working agent-host authentication. The dependency installation and the model call use their respective networks. Only the product runtime is provider-independent. Fresh dependencies, guest permission-state qualification and actual agent execution are separate evidence lanes; the release manifest records what passed.

The measured host trial additionally applied product-only private HOME/config/cache/temp overrides, blanked ambient variable names ending in _KEY/_TOKEN/_SECRET, and enabled runtime audit in a private output directory. The host kept its existing opaque authentication. These diagnostic isolation settings do not come automatically from the generated registration; the latter supplies isolated imports and telemetry settings. The evidence records this distinction.
