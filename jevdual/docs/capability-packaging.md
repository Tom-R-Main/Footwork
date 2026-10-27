# Install the capability slice

The capability wheel runs the current macOS browser-to-TextEdit slice without Rust or a model provider account. It contains Python runtime modules, `arbiter.toml`, the MIT license, dependency metadata and the `footwork-capability` entry point. The existing maturin build still provides optional Rust acceleration.

The scope is narrow: read one loopback HTTP browser fixture and append to one identified TextEdit document. The caller supplies existing process IDs, window IDs, URL and document path. Footwork checks identity when binding and before input. This package does not discover arbitrary apps or authorize a broader job.

## Build and inspect the actual artifact

From `jevdual/`, use Python 3.11 or newer:

```sh
python scripts/build_capability_wheel.py --output /absolute/owned/artifacts
python scripts/build_capability_wheel.py --verify /absolute/owned/artifacts/jevdual-0.0.1-py3-none-any.whl
```

The builder uses the standard library and downloads nothing. It refuses to replace an existing wheel. The verifier compares the ZIP inventory and bytes with the permitted source inventory, checks required runtime resources, verifies every RECORD hash and size, and checks the declared license path. Fixed ZIP timestamps and ordering make builds from unchanged source repeatable in the same Python environment.

Only `.py` runtime files, the policy file and generated distribution metadata ship. Research runs, tests, caches and compiled extensions are excluded; source symlinks are rejected. Dependencies are declared rather than bundled. The wheel retains the full current dependency list, including exact MCP, browser-use, cua-driver and psutil pins. It is not a reduced-dependency distribution.

### Consumer artifact checks

The separate `capability-package` CI workflow builds the wheel twice, verifies its bytes and RECORD, and installs it offline without dependencies in a fresh environment. It checks the installed console entry point, isolated imports from a directory containing shadow packages, strict refusal of missing prerequisites, and conservative reporting when the journal is absent. Run the same check locally with an existing Python and uv:

```sh
python scripts/capability_package_check.py --run-dir /absolute/footwork/output/new-package-check
```

CI defines Linux/Python 3.12 and macOS arm64/Python 3.12 and 3.14 profiles. The macOS profiles build the hash-pinned CUA wheel and then run the fresh-cache, private-state, binary-only dependency installer with that wheelhouse. Receipts and the candidate wheel are retained as CI artifacts. These checks neither launch native input nor qualify macOS permission prompts. Each interpreter's two builds must match; byte identity across operating systems or compression-library versions is not required.

## Install into a fresh environment

CUA `0.38.0+footwork.d5373879` builds its Python bindings and native engine from the pinned reference source because published packages lag that commit. First build the dependency wheel for the destination platform; see [CUA wheel provenance and builds](upstream/cua-driver-build.md). From `jevdual/`, with an existing Python and uv:

~~~sh
rustup toolchain install 1.97.1 --profile minimal
uv build vendor/cua-driver --wheel --out-dir /absolute/owned/cua-wheels
uv --no-config venv --python /absolute/python3 /absolute/owned/venv
uv --no-config pip install --python /absolute/owned/venv/bin/python \
  --default-index https://pypi.org/simple --only-binary :all: \
  --find-links /absolute/owned/cua-wheels \
  /absolute/owned/artifacts/jevdual-0.0.1-py3-none-any.whl
/absolute/owned/venv/bin/python -I -m jevdual.capability.cli doctor --strict
~~~

This installation fetches dependencies. Binary-only mode refuses missing wheels instead of compiling them. The [fresh-install qualification](../results/clean-installation-20261010/report.md) covers macOS arm64 with Python 3.12.6 and 3.14.7; broader Python metadata does not qualify every version or architecture. Existing Chrome, TextEdit, macOS frameworks and permissions remain prerequisites.

Doctor reports prerequisite status and blocker codes, with interpreter, architecture and installed distribution locations. Ordinary diagnostics return 0 when the report finishes. With --strict, blocked prerequisites return 1; malformed configuration returns 2. Met prerequisites do not certify a window, effect, current content or completed job. Screen Recording status is advisory here; a capture route still needs its own successful check.

Generated server and report commands use Python isolation mode (-I), preserving the environment interpreter. The detached worker uses the same mode. This excludes the host's current directory, Python environment overrides and user site packages from imports. Generated host settings also disable browser-use telemetry and cloud synchronization; they do not block all possible network access.

Optional qualification diagnostics use FOOTWORK_RUNTIME_AUDIT_DIR pointing at an existing private owned directory. Actual server/worker contexts record loaded module and SDK library origins after binding. These files are diagnostic data, separate from receipts and authority, with no field text or credential values. Normal setup requires no audit directory.

## Install offline

Use an owned environment with the declared dependencies already available. For example, with `uv` already installed:

```sh
uv pip install --offline --no-deps --python /absolute/owned/venv/bin/python /absolute/owned/artifacts/jevdual-0.0.1-py3-none-any.whl
/absolute/owned/venv/bin/python -I -m jevdual.capability.cli doctor
```

`--no-deps` installs the artifact alone. It does not prove that a fresh machine can resolve every dependency offline. A consumer needs a compatible Python environment, the declared dependencies, native macOS frameworks, an existing browser fixture and TextEdit document, and applicable Accessibility and Screen Recording permissions. `doctor` reports versions and existing permission status for its process; it never requests permissions, opens settings, starts apps or creates a journal. Run doctor from the same host or terminal that will launch the server: macOS may attribute permissions differently across hosts. Treat a bind accessibility error as authoritative even if another process's doctor reported granted. Missing prerequisites remain the caller's responsibility.

Run consumer checks outside the checkout. The console entry point shares the CLI implementation but does not enable Python isolation; `PYTHONPATH` and user site packages can still affect it. Automation and host adapters should use the generated `python -I -m jevdual.capability.cli` commands. The console entry point is for interactive use. Detached execution also uses isolation mode with that interpreter to launch the installed `jevdual.capability.execution_worker` module.

## Create one configuration per job

Choose a new absolute run directory with an existing nonsymlink parent. Supply the owned fixture's actual identifiers:

```sh
/absolute/owned/venv/bin/python -I -m jevdual.capability.cli config \
  --run-dir /absolute/owned/job-run \
  --source-pid 123 --source-window 456 \
  --source-url http://127.0.0.1:8000/ \
  --destination-pid 789 --destination-window 1011 \
  --document /absolute/owned/invoice.txt
```

The identifiers above are placeholders, not a reusable registration. Configuration creates a private directory and private JSON files: `scope.json`, `host.json`, `report-schema.json` and `run.json`. Its opaque task ID is recorded in the scope. `host.json` contains a per-job MCP stdio server command using the configuring interpreter's absolute path, preserving its virtual environment. Adapt this ephemeral configuration to the host's own configuration format; nothing is registered globally.

Reuse the directory, task and journal only to reconnect or restart the same job. A new job needs a new directory. Configuration fails if its directory exists and does not create a journal or start a server. Retain the run directory as the operation history and recovery context; do not substitute an empty journal to bypass an unresolved operation.

Check a run without taking journal ownership:

```sh
/absolute/owned/venv/bin/python -I -m jevdual.capability.cli doctor \
  --scope /absolute/owned/job-run/scope.json \
  --journal /absolute/owned/job-run/operations.sqlite
```

Diagnostics report whether the configured document and processes exist; window identity is checked at bind. If the task already has operations, diagnostics warn that the full history belongs in its completion report. A read-only ledger check never performs startup recovery or dispatches input. Doctor uses the declared `packaging` dependency to parse the installed distribution's requirements. Missing metadata or parser makes compatibility unverified and blocks strict prerequisites.

## Enforce the completion adapter

The host must produce structured claims matching `report-schema.json`. The run manifest supplies `report_adapter`, including the durable task ID. After stopping the host, pass its final report through that command, for example:

```sh
/absolute/owned/venv/bin/python -I -m jevdual.capability.cli report \
  --journal /absolute/owned/job-run/operations.sqlite \
  --task task_REPLACE_WITH_GENERATED_ID \
  --input /absolute/owned/job-run/host-report.json
```

Publish only the returned `trusted_summary`, including when validation rejects the host's claims. Never publish raw host prose as a fallback. `--summary` emits only that string. Exit 0 means the claims are accepted, exit 1 means they are rejected, and exit 2 means the input or journal cannot be validated. An accepted `unknown` report still means historical effects are unknown.

The summary describes the configured task's admitted operation history as of its ledger snapshot. It does not certify current GUI content, disk persistence or the host's wider goal. Merely offering the MCP `report` tool does not enforce the host's final answer; the publication adapter is required.

## References

The local chrome-devtools-mcp package verifier checks the artifact produced for publication rather than trusting a source file list. This builder applies that mechanism to its actual wheel; it copies no upstream source. The license metadata follows [PEP 639](https://peps.python.org/pep-0639/): `License-File: LICENSE` resolves under the wheel's `.dist-info/licenses/` directory.

The setup improvements use the structured prerequisite/error mechanism in local Cua, ambient-configuration isolation in Hermes, and exact emitted-command MCP discovery in Open Computer Use. Implementations are independent. Newer reference versions are not dependency upgrades; Footwork retains its pinned seams. The newer Cua doctor also performs legacy-file cleanup, so it is not used as a read-only verifier here.

## Qualified local candidate

The repaired guest permission-reset journey and one installed Claude Code task both passed with independent review. See [the guest report](../results/u3-packet-v4-permission-20261012-v3/report.md) and [the real-host report](../results/installed-agent-release-20261012-v2/report.md). The local release bundle preserves wheel9bb0440d and helper source445a348; its manifest identifies release documentation separately. It includes an [agent-host recipe](installed-agent-host.md) and exact qualification limits. Public registry publication, other hosts, pixel capture and disk persistence are separate gates.

## CUA 0.38 initial browser attachment

Before the first source bind, bring the owned fixture Chrome window to the foreground once. CUA 0.38 refuses a new background DevTools attachment while another app is in front on the same Space. Footwork preserves that refusal. Subsequent reads and native append operations retain background delivery; the installed conformance trial passed with this initial foreground prerequisite on macOS arm64. This check covers the owned fixture and current host permissions, not other profiles, Spaces or apps.
