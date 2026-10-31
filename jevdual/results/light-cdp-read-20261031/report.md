# L3a-1 direct-CDP observation: verification

Prediction LCD1 (`docs/notebook/2026-10-31-light-cdp-read.md`), committed in `41b3296` before the code.
Implementation `211f666`, stacked on L1b (`545fe23`, PR 15).

Environment: macOS arm64, Google Chrome 156.0.8078.79 headless (`--headless=new`), temporary profile per
test; the main checkout's `.venv` with worktree source on `PYTHONPATH`, `JEVDUAL_PURE_PY=1`.

| Check | Result |
|---|---|
| First real-Chrome run of `test_the_owned_browser_is_observed_as_the_fixture_declares` | **failed**: 5 extra candidates from user-agent shadow internals, including the password's inner text as a label (`•••••••`, one bullet per character) |
| After skipping AX nodes outside the main-frame DOM index | `tests/test_cdp_effector.py` 13 passed (3 real Chrome) |
| Full suite `-m "not browser and not live"` | 2535 passed, 95 skipped, 1 failed (`test_cua_driver_version_is_pinned`, the borrowed venv's pre-`cleanup2` wheel, as on base) |
| ruff `python tests` | clean |

Real-Chrome assertions: candidates equal the fixture's declared controls (label, role, operation, value,
checked, offscreen); neither the password nor its length appears in page text, labels, values or the
value map; the disabled button has no candidate; the offscreen link is offscreen; one same-origin iframe
makes the snapshot incomplete (`child_frames: 1`); click, type and navigate refuse with
`browser_mutation_unqualified`, `dispatched=False`, `delivery=not_sent`; after a reload the old ref
refuses `document_changed`; an endpoint whose browser pid differs refuses `browser_identity_mismatch`; no
`Input.*`, `Runtime.*`, `DOM.focus`, `DOM.set*`, `Page.navigate`, `Page.reload` or `Target.create/close`
method was sent by the effector (fixture navigation used a separate setup connection).

Not run: Linux, headed mode, the CUA comparison on the same pages (the CUA browser route needs an
on-screen window in the person's session), hosted CI for the browser-marked tests (CI deselects them).
