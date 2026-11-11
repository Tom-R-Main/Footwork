# Scoped native DOM control identity

Exploration preregistration `4b221d9`; implementation preregistration `fe12558` (NCI3). The bounded authorized read-only probe independently resolved both owned More options controls as AXPopUpButton with distinct complete AXDOMIdentifier values. Direct AXParent chains reached their closest AXWebArea at depths9 and5 with the same actual complete song URL (`output/suno-20261110/control-document-scope.json`). No SDK-ancestry containment fallback, focus write or input occurred. The original SUN25 probe had not captured the document URL.

Baseline on the preregistered source: both public CLI distinct-control cases failed because same-label controls collapsed to one candidate (`baseline.txt`).

The source qualifies AXButton and AXPopUpButton controls by exact bound PID/window/role/frame resolution, matching independent AXTitle/Description, an untruncated nonempty DOM ID, and the closest direct AXWebArea's actual complete HTTP(S) URL. Every observed semantic peer must qualify with a unique DOM ID, identical document URL and CFEqual WebArea ancestor before pruning. DOM IDs over512 characters or containing whitespace/control characters, unsupported/malformed document scopes, unknown ancestor equality, duplicate IDs and unreadable peers fail closed. Reads are bounded to64 controls and32 ancestors; repeated groups are considered before singleton groups. Editable AXComboBox behavior remains unchanged.

Complete scoped metadata refines pruning, ambiguity and fresh rematching; it persists across CLI calls and appears in observations and inspect-target manifests/escaped previews. Saved numeric choices and final rematching reject changed IDs/documents, lost qualification and reordered backing IDs. Grants bind the document/DOM ID pair; an old ordinal grant cannot clear a newly scoped peer. New metadata containing known secrets is scrubbed and loses qualification. Controls without DOM IDs keep existing ambiguity, including Main Play. No row song URI, sibling URL or geometric identity is inferred.

`scenarios.txt`:19 scoped-control public CLI scenarios pass. `inspection-ax.txt`:31 inspection/AX cases pass. `focused.txt`:805 affected session/native/menu/posture/AX/CLI/authorization/grants/evidence/visual and CUA contract tests pass. Ruff, notebook validation and diff checks pass. The focused command was corrected from a nonexistent singular test_visual_check.py path before the successful run; no tests ran under that misspelled command.

Commands from `jevdual/`:

```sh
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py -k native_scoped_dom
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest -q tests/test_session_scenarios.py tests/test_session.py tests/test_session_targeting_audit.py tests/test_visual_inspection_session.py tests/test_visual_native.py tests/test_visual_checks.py tests/test_native.py tests/test_menu.py tests/test_control_state.py tests/test_posture.py tests/test_ax_semantics.py tests/test_native_foreground_intent.py tests/test_native_receipts.py tests/test_cli.py tests/test_agent_cli.py tests/test_authorize.py tests/test_authorization_parity.py tests/test_session_evidence.py tests/test_session_operations.py tests/test_grants.py tests/contract
.venv/bin/ruff check python/jevdual/{native,menu,ax,session}.py tests/test_session_scenarios.py tests/test_ax_semantics.py tests/test_visual_inspection_session.py tests/test_session_evidence.py
PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m evals.notebook docs/notebook --check
```

Qualification covers observed peers, not unseen controls in an incomplete AX snapshot. DOM IDs may change on a rerender, requiring a fresh choice. The read-only live probe establishes availability of the proposed scope; synthetic tests do not establish actual menu opening. No worker live input, SDK rebuild/native-byte change or installation occurred. Parent owns subsequent live qualification on frozen source.
