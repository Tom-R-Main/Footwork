# Independent first-use qualification

This packet prepares U2; it is not a passed first-use result. It contains the reviewed standalone wheel, MIT license and qualification helpers, with hashes in MANIFEST.json. No code runs automatically. Product processes load Python runtime files from the installed wheel; helper code supplies the fixture and independent oracle. A runtime source checkout, development environment, provider credentials and evaluation results are absent.

Use an independently provisioned Mac or a new SIP-enabled macOS guest with a visible logged-in session. A pregranted CI runner or cloned granted seed cannot establish the initial permission transition. Record the actual environment and launch host; do not reset this MacBook's permissions to simulate a fresh machine. A rerun on a previously provisioned disposable guest must be labeled a fresh permission-state run, not a new cold-OS installation. Only after explicit approval, the supported guest command `tccutil reset Accessibility com.apple.Terminal` can restore that host's denied state; never reset other hosts or edit the TCC database. Retain all earlier run directories.

## Verify and install

Compare the archive SHA256 with its accompanying preparation report before extracting. The manifest identifies the source commit and hashes every payload member. Work inside the extracted footwork directory. Provision compatible Python and uv through their normal installers on the independent environment; the packet does not install them or macOS.

The guest also needs TextEdit and Google Chrome at /Applications/Google Chrome.app, the executable used by the frozen fixture helper. Record the browser version and provision it through its normal installer before fixture execution. Launch Chrome once through Finder, let normal macOS verification finish, then quit it. Record this prerequisite separately; do not bypass Gatekeeper or count launch readiness as resource identity. Keep the fixture test profile unsigned-in. Missing Chrome is a browser prerequisite failure, not a permission denial.

Open an interactive guest Terminal and define the packet directory:

~~~sh
cd /absolute/extracted/footwork
PACKET_ROOT="$(pwd -P)"
QUALIFICATION_PYTHON=/absolute/python3.12
command -v python3 uv
"$QUALIFICATION_PYTHON" --version
uv --version
"$QUALIFICATION_PYTHON" -I "$PACKET_ROOT/jevdual/scripts/verify_onboarding_packet.py" \
  --packet-root "$PACKET_ROOT"
cd jevdual
"$QUALIFICATION_PYTHON" -E -s scripts/capability_clean_install.py \
  --python "$QUALIFICATION_PYTHON" \
  --wheel "$PACKET_ROOT/artifacts/jevdual-0.0.1-py3-none-any.whl" \
  --run-dir "$PACKET_ROOT/output/install-v1"
~~~

Set QUALIFICATION_PYTHON to the absolute executable installed for this run, not /usr/bin/python3. The system Python and Git commands can trigger a developer-tools installation dialog on a fresh Mac. The standalone helpers read their source commit from MANIFEST.json and do not need Git. Record the command paths and version output above. Verify members before installation creates output directories; stop on a nonzero verification exit. The archive hash from the accompanying report authenticates the manifest; member hashes detect changes after extraction.

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

The human approves the required permission for the actual responsible host in the guest's System Settings. The human or explicitly authorized operator changes that exact host's switch. Capture its off state, approval, actor and time, then its on state; separated denied/granted diagnostics without the actual transition do not pass this gate. Record any required host restart. Do not grant arbitrary helper paths or change SIP/TCC databases. Run subsequent commands from the same host. Screen Recording status is advisory for this DOM/AX slice; capture needs its own evidence. Record any additional permission required by an actual route or fixture cleanup.

Repeat isolated strict doctor into doctor-after.json. Met prerequisites alone do not prove resource access or execution.

## Drive the installed public path

In one Terminal, start and retain the owned fixture:

~~~sh
"$PACKET_ROOT/output/install-v1/venv/bin/python" -E -s scripts/capability_fixture.py \
  --run-dir "$PACKET_ROOT/output/fixture-v1"
~~~

The helper waits up to180seconds for its owned browser to expose a working private-profile CDP endpoint, then starts a separate30second unique-window identity phase. Startup health confers no scope authority. A typed failure is retained in fixture-status.json; stop on a nonzero exit and use a fresh directory for a later attempt.

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

Stop the fixture with Ctrl-C. The helper uses Accessibility to close only the window with the exact fixture document path. It may press a unique discard button only in that window's observed attached save sheet. Only identified English save sheets are supported; other dialogs refuse. It requests no TextEdit Automation grant. Retain cleanup.json and the fixture exit code. Confirm the owned browser process and loopback listener are gone, the exact document window is closed and no owned worker remains. A refusal, unknown result or manual close is a failed automatic-cleanup gate; preserve it and independently inspect only the exact owned resource. Do not substitute killing all Chrome/TextEdit processes. Cleanup does not certify whether TextEdit saved the edit before closing.

Retain installation receipts, before/after diagnostics and exit codes, host/OS/SIP identity, consent observations, native receipt/journal/runtime contexts and cleanup evidence. Sanitize observations before sharing. Mark U2 passed only when an observed denied baseline, explicit permission transition and every native/postcondition/cleanup gate pass. This proves the scoped historical append/recovery/report behavior; it does not prove saved-file persistence, arbitrary apps or the host's entire goal.
