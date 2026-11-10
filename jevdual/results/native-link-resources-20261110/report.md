# Native link resource identity

Preregistration `b38fb5f` (LRI1). Baseline on `114a1b9`: both public CLI distinct-resource cases failed because same-title native links were pruned to one candidate (`baseline.txt`).

Native macOS observation now reads AXURL from each exact PID/window/AXLink/frame before pruning, independently checks its AXTitle/Description against the observed label, and retains a complete HTTP(S) URL. Every observed semantic peer must qualify before resource identity distinguishes that group. Missing reads, the 64-link read limit and duplicate URLs preserve ambiguity, including when pruning hides peers. Relative, credential-bearing, whitespace-bearing, unsupported or over-2048-character URLs do not qualify. URL strings are never normalized or clipped into identities.

Qualified URLs refine native pruning, ambiguity, peer groups and live rematching. Persistence keeps the qualification bit with the URL; prior numeric choices refuse when the same ID changes URL or loses qualification. Native CLI observations show the full qualified href. Labels shared by two qualified links still require a fresh numeric choice. Browser hrefs and song-row buttons gain no additional identity authority.

`scenarios.txt`: 14 public CLI cases pass, covering both generated candidates, incomplete/hidden peers, duplicate URLs, read limits, saved-ID URL changes/reorder, final revalidation changes, and ambiguous label selection. AX decoder/projection tests cover NSURL and string representations, complete long URLs, independent name mismatch, rejection cases, pre-pruning ambiguity and no button inheritance. `focused.txt`: 615 affected tests and CUA contracts pass. Ruff, notebook validation and diff checks pass. An intermediate regression added null resource keys to ordinary button action metadata; the final change adds resource action metadata only for qualified native links.

Commands from `jevdual/`:

```sh
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py -k 'native_same_title_links or native_link_resource'
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py tests/test_session.py tests/test_session_targeting_audit.py tests/test_native.py tests/test_menu.py tests/test_control_state.py tests/test_ax_semantics.py tests/test_native_foreground_intent.py tests/test_native_receipts.py tests/test_cli.py tests/test_agent_cli.py tests/test_authorize.py tests/test_authorization_parity.py tests/test_session_evidence.py tests/test_session_operations.py tests/contract
.venv/bin/ruff check python/jevdual/{native,session,menu,ax}.py tests/test_session_scenarios.py tests/test_ax_semantics.py tests/test_native.py
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m evals.notebook docs/notebook --check
```

No worker UI actions/probes, SDK rebuild, native-byte changes or installation occurred. Synthetic scenarios establish resource targeting invariants, not live Suno navigation or task completion. Observation may remain incomplete; only the observed semantic peer groups are qualified. Buttons beside a song require their own distinct qualification.
