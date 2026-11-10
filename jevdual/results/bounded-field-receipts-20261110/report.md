# Native bounded field receipt repair

Prediction commit:1b24585. This report accompanies a local source repair, not a new installed artifact.

Native text candidates cap single-line display values at120 characters and multiline values at480. The old field receipt compared this preview to full intended text. It could report a correct long input as partial, or report confirmed when the intended text merely equaled the clipped preview while the actual unseen suffix differed.

The repair adds explicit native projection clipping metadata to Candidate and persisted session observations. Field receipt comparisons now return unverifiable when they require a clipped current value or clipped append baseline. Native look marks clipped values. Existing nondispatch, ambiguous identity, placeholder roster and password checks retain priority. A nontruncated field ending in a literal ellipsis retains normal comparisons; a legacy native cap-shaped ellipsis without provenance is conservatively uncertain.

## Validation

- `red.txt`:5 baseline failures include the two incorrect receipt conclusions, missing provenance for a valid literal ellipsis and two persisted append baseline variants.
- `pytest.txt`:328 affected tests pass, covering public CLI scenarios, session and evidence reconstruction, targeting audit, native projection, menu state, authorizer and CLI discovery.
- `adjacent.txt`:296 adjacent completion, capability, native receipt, Linux native, form acceptance and pinned CUA seam checks pass.
- Changed-file Ruff, notebook validation and `git diff --check` pass.

The actual type scenarios drive the public CLI through the simulated native setter and use backing fixture values as the independent equality oracle. The append scenarios reconstruct an already-pending action with a persisted long baseline, then resolve it through public look after a short current value appears. They test receipt reconstruction and do not establish that a real append was delivered.

Commands from `jevdual/`:

```sh
uv run --no-sync pytest tests/test_session_scenarios.py tests/test_session.py tests/test_session_evidence.py tests/test_session_targeting_audit.py tests/test_native.py tests/test_menu.py tests/test_authorize.py tests/test_cli.py tests/test_agent_cli.py -q
uv run --no-sync pytest tests/test_native_receipts.py tests/test_completion.py tests/test_capability_completion.py tests/test_capability_contracts.py tests/test_linux_native.py tests/test_native_form_acceptance.py tests/contract/test_cua_driver_seams.py -q
uv run --no-sync ruff check python/jevdual/menu.py python/jevdual/native.py python/jevdual/session.py tests/test_session_scenarios.py tests/test_native.py tests/test_session_evidence.py
uv run --no-sync python -m evals.notebook docs/notebook --check
git diff --check
```

## Limits and existing read routes

No live Suno, installed-wheel, server persistence or React replacement qualification is established. The new flag describes Footwork projection clipping only; false does not promise that the driver supplied exact complete content. A driver-truncated value without independently supplied provenance remains a limitation.

Public `read` calls carry.take on the displayed candidate and therefore carries the same bounded preview. NativeBridge's private values map retains supplied raw values, but mixes direct AX and SDK fallback sources. The existing target-scoped AX value helper can support a developer diagnostic after fresh unique field, role, frame and window qualification, but it is not a public full-read CLI contract. This repair adds no full-read or extra input feature.
