# Bounded foreground-intent refusal diagnostics

Preregistration: `f539653`. The public CLI baseline lost structured SDK refusal
metadata while correctly withholding application input.

The repair attaches a finite diagnostic to the existing foreground refusal error
and carries it through NativeEffect.native_readback into the existing public CLI
session JSONL action/receipt metadata. No session/parser/SDK changes are needed.
The compact refusal summary includes safe status; the complete bounded record is
at `native_readback.foreground_intent` on the `do` record (also retained under the
receipt's action). Inspect this existing output after the one authorized command.

Recorded fields are pinned bring_to_front code/status enums, strict request
acceptance and exact-window booleans, action effect/error-code classification,
requested PID/window and match booleans for observed PID/window checks. No foreign
identity numbers, arbitrary code strings, raw tool/error text, URL/title or other
payload fields are copied. Unknown strings become `unrecognized`; missing or
invalidly typed booleans/identities remain null/unknown. The known code vocabulary
comes from the pinned local bring_to_front Rust producer, not prose matching.

This record diagnoses an attempted activation gate; it supplies no new authority,
input-success claim or guarantee that activation itself made no system change.
Every original refusal and exact-window/native-focus check remains unchanged.
There is no extra SDK/read/activation call or automatic retry in the patch.

Validation with the existing focus1 overlay:

- `baseline.txt`: two public CLI cases fail before instrumentation.
- `scenarios.txt`: both public refusal cases pass, with one bring_to_front request,
  zero application input and no retained fixture-private strings.
- `focused.txt`:756 native/session/posture/authority/CLI/pinned-contract tests pass,
  including malformed/wrong-identity/type/unknown diagnostics and exact-success
  activation behavior. Ruff, notebook and diff checks pass.

Focused command from `jevdual/`:
`PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_native_foreground_intent.py tests/test_native.py tests/test_native_receipts.py tests/test_posture.py tests/test_session_scenarios.py tests/test_session.py tests/test_session_evidence.py tests/test_session_operations.py tests/test_authorize.py tests/test_authorization_parity.py tests/test_agent_cli.py tests/contract`

Worker evidence is simulated/source-only. No live native/UI or SDK call, network,
installation, runtime activation or native rebuild was performed. No cause of the
actual scheduled-run activation refusal is inferred; parent owns live diagnosis.
