# Independent first-use qualification

This packet prepares U2; it is not a passed first-use result. It contains the reviewed standalone wheel, MIT license and qualification helpers, with hashes in MANIFEST.json. No code runs automatically. Product processes load the installed wheel; helper code supplies the fixture and independent oracle. The full Footwork runtime source, development environment, provider credentials and evaluation results are absent.

Use an independently provisioned Mac or a new SIP-enabled macOS guest with a visible logged-in session. A pregranted CI runner or cloned granted seed cannot establish the initial permission transition. Record the actual environment and launch host; do not reset this MacBook's permissions to simulate a fresh machine.

## Verify and install

Compare the archive SHA256 with its accompanying preparation report before extracting. The manifest identifies the source commit and hashes every payload member. Work inside the extracted footwork directory. Provision compatible Python and uv through their normal installers on the independent environment; the packet does not install them or macOS.

Open an interactive guest Terminal and define the packet directory:

~~~sh
cd /absolute/extracted/footwork
PACKET_ROOT="$(pwd -P)"
cd jevdual
python3 scripts/capability_clean_install.py \
  --python /absolute/python3.12 \
  --wheel "$PACKET_ROOT/artifacts/jevdual-0.0.1-py3-none-any.whl" \
  --run-dir "$PACKET_ROOT/output/install-v1"
~~~

The installer uses a fresh environment, empty cache, private state and public binary packages. Preserve failures as their own version; a new attempt needs a new run directory. Existing dependencies, source code, Rust and model accounts must not satisfy missing prerequisites.

## Record denied first use

Record macOS version/build with sw_vers, SIP status with csrutil status, and the interactive responsible host's identity/version. Before changing permissions:

~~~sh
"$PACKET_ROOT/output/install-v1/venv/bin/python" -I -m jevdual.capability.cli doctor --strict \
  > "$PACKET_ROOT/output/doctor-before.json"
"$PACKET_ROOT/output/install-v1/venv/bin/python" -E -s scripts/capability_fixture.py \
  --run-dir "$PACKET_ROOT/output/denied-fixture-v1"
~~~

Record each command's exit code. With missing Accessibility, strict doctor must exit1 and report its blocker. The fixture must refuse before creating its directory, browser or document. If Accessibility is already granted, preserve the installation result and mark this lane ineligible for first-use permission qualification. A locked display, missing dependency or failed probe is not an observed permission denial.

The human grants the required permission to the actual responsible host in the guest's System Settings. Record the prompt or settings transition and any required host restart. Do not grant arbitrary helper paths or change SIP/TCC databases. Run subsequent commands from the same host. Screen Recording status is advisory for this DOM/AX slice; capture needs its own evidence. Record any additional permission required by an actual route or fixture cleanup.

Repeat isolated strict doctor into doctor-after.json. Met prerequisites alone do not prove resource access or execution.

## Drive the installed public path

In one Terminal, start and retain the owned fixture:

~~~sh
"$PACKET_ROOT/output/install-v1/venv/bin/python" -E -s scripts/capability_fixture.py \
  --run-dir "$PACKET_ROOT/output/fixture-v1"
~~~

Only after its ready response identifies the owned scope, use another Terminal from the same responsible host:

~~~sh
"$PACKET_ROOT/output/install-v1/venv/bin/python" -E -s scripts/capability_fixture_config.py \
  --scope "$PACKET_ROOT/output/fixture-v1/scope.json" \
  --run-dir "$PACKET_ROOT/output/job-v1"
"$PACKET_ROOT/output/install-v1/venv/bin/python" -E -s scripts/capability_installed_trial.py \
  --python "$PACKET_ROOT/output/install-v1/venv/bin/python" \
  --scope "$PACKET_ROOT/output/job-v1/scope.json" \
  --host-config "$PACKET_ROOT/output/job-v1/host.json" \
  --journal "$PACKET_ROOT/output/job-v1/operations.sqlite" \
  --isolation-root "$PACKET_ROOT/output/install-v1" \
  --run-dir "$PACKET_ROOT/output/native-v1"
~~~

The fixture configuration helper copies observed identifiers into the public config command, which generates a fresh job task. It confers no permission or execution authority. The installed trial exercises the exact generated isolated MCP command, real detached worker, exact append, same-token restart and journal-validated report. Its independent AX oracle checks the owned document and one journal operation. No model is invoked.

Use only the entry points listed here; the other bundled modules supply imported qualification functions. They are not consumer tools or additional tasks to execute.

## Close and retain

Stop the fixture with Ctrl-C. Confirm its browser process is absent, its exact document window is closed and no owned worker remains. A reported cleanup failure needs an independent check or manual close of that exact owned document; do not substitute killing all Chrome/TextEdit processes.

Retain installation receipts, before/after diagnostics and exit codes, host/OS/SIP identity, consent observations, native receipt/journal/runtime contexts and cleanup evidence. Sanitize observations before sharing. Mark U2 passed only when an observed denied baseline, explicit permission transition and every native/postcondition/cleanup gate pass. This proves the scoped historical append/recovery/report behavior; it does not prove saved-file persistence, arbitrary apps or the host's entire goal.
