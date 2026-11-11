# Complete bounded opaque-control ancestry

November 11, 2026. A minimal generic read-only repair to `ax.control_backing` extends its direct parent walk from 32 to 64 nodes, including the control and terminal native window. The actual Studio diagnostic is retained by the parent in private output; this package verifies the mechanism through simulated native objects and the public CLI, without live UI calls.

The preregistered public-CLI scenario `test_native_deep_control_ancestry_public_projection_still_requires_every_peer` first failed because complete 33- and 34-node paths to the exact owned window yielded no qualified literal identifiers. After the repair, both identifiers qualify. Making the second peer's parent unreadable then withholds both, preserving the complete observed-peer requirement. No input is dispatched by this scenario.

Every visited object must still belong to the exact PID, have a readable role and lead through a valid closest HTTP(S) WebArea to the actual bound AXWindow/AXSheet. Another window or application terminates the proof with refusal. Native-object equality now detects cycles, including different proxy objects representing the same native object; intermediate unreadable roles are explicitly refused. Reaching the exact native window as node 64 succeeds. A 65-node path does not become a truncated proof and remains refused.

The function has no expected-document argument: it reports the actual closest document. An invalid closest URL cannot borrow an outer valid WebArea's URL. Existing all-peer document/identity/collision checks remain unchanged. Named-control lookup, semantic-section and named-control-identity traversal limits are unchanged. No new candidate kind, input route, posture, action authority or app-specific condition is introduced.

## Validation

| Boundary | Result | Private evidence |
| --- | --- | --- |
| Public CLI 33/34-node reproduction before repair | Failed at missing qualified literal identifier | output/deep-control-ancestry-red.txt |
| Direct boundary/negative cases, AX semantics and public reproduction | 71 passed | output/deep-control-ancestry-focused.txt |
| Affected native/AX/session/visual inspection/SDK seams | 551 passed | output/deep-control-ancestry-affected.txt |
| Changed AX source and dedicated tests lint | Passed | local Ruff check |

Checks use `PYTHONPATH=output/foreground-web-text/overlay:python .venv/bin/python -m pytest` from `jevdual/`, retaining the pinned focus1 project SDK. Negative cases include excessive depth, foreign/error owners, unreadable role/parent, invalid closest URL without outer-document borrowing, missing WebArea, other window/application, native cycles and alias proxies. Actual Studio live qualification, overall ease and task persistence remain separate parent-run questions.

Notebook preregistration: docs/notebook/2026-11-11-deep-control-ancestry.md, committed before the failing scenario ran. No network, provider call, real UI action or global installation occurred.
