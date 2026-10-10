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

## Install offline

Use an owned environment with the declared dependencies already available. For example, with `uv` already installed:

```sh
uv pip install --offline --no-deps --python /absolute/owned/venv/bin/python /absolute/owned/artifacts/jevdual-0.0.1-py3-none-any.whl
/absolute/owned/venv/bin/python -m jevdual.capability.cli doctor
```

`--no-deps` installs the artifact alone. It does not prove that a fresh machine can resolve every dependency offline. A consumer needs a compatible Python environment, the declared dependencies, native macOS frameworks, an existing browser fixture and TextEdit document, and applicable Accessibility and Screen Recording permissions. `doctor` reports versions and existing permission status for its process; it never requests permissions, opens settings, starts apps or creates a journal. Run doctor from the same host or terminal that will launch the server: macOS may attribute permissions differently across hosts. Treat a bind accessibility error as authoritative even if another process's doctor reported granted. Missing prerequisites remain the caller's responsibility.

Run consumer checks outside the checkout with `PYTHONPATH` unset so repository files cannot satisfy missing installed modules. The entry point and `python -m jevdual.capability.cli` use the same implementation. Detached execution uses that interpreter to launch the installed `jevdual.capability.execution_worker` module.

## Create one configuration per job

Choose a new absolute run directory with an existing nonsymlink parent. Supply the owned fixture's actual identifiers:

```sh
/absolute/owned/venv/bin/python -m jevdual.capability.cli config \
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
/absolute/owned/venv/bin/python -m jevdual.capability.cli doctor \
  --scope /absolute/owned/job-run/scope.json \
  --journal /absolute/owned/job-run/operations.sqlite
```

Diagnostics report whether the configured document and processes exist; window identity is checked at bind. If the task already has operations, diagnostics warn that the full history belongs in its completion report. A read-only ledger check never performs startup recovery or dispatches input. Doctor parses the installed distribution's requirements when the optional `packaging` parser is available; otherwise it reports dependency compatibility as unverified.

## Enforce the completion adapter

The host must produce structured claims matching `report-schema.json`. The run manifest supplies `report_adapter`, including the durable task ID. After stopping the host, pass its final report through that command, for example:

```sh
/absolute/owned/venv/bin/python -m jevdual.capability.cli report \
  --journal /absolute/owned/job-run/operations.sqlite \
  --task task_REPLACE_WITH_GENERATED_ID \
  --input /absolute/owned/job-run/host-report.json
```

Publish only the returned `trusted_summary`, including when validation rejects the host's claims. Never publish raw host prose as a fallback. `--summary` emits only that string. Exit 0 means the claims are accepted, exit 1 means they are rejected, and exit 2 means the input or journal cannot be validated. An accepted `unknown` report still means historical effects are unknown.

The summary describes the configured task's admitted operation history as of its ledger snapshot. It does not certify current GUI content, disk persistence or the host's wider goal. Merely offering the MCP `report` tool does not enforce the host's final answer; the publication adapter is required.

## References

The local chrome-devtools-mcp package verifier checks the artifact produced for publication rather than trusting a source file list. This builder applies that mechanism to its actual wheel; it copies no upstream source. The license metadata follows [PEP 639](https://peps.python.org/pep-0639/): `License-File: LICENSE` resolves under the wheel's `.dist-info/licenses/` directory.
