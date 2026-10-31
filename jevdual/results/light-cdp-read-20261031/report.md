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

## Takeover review and corrections — October 31

The preceding results describe the original candidate. Runtime source `817d1fb` supersedes it with
the following review corrections, each with a committed prediction and a failing control before repair:

- Sending and reply waiting share one command deadline. Backpressure cannot postpone that deadline.
  Cancellation releases pending records; an interrupted send retires the connection without retry.
- Endpoint validation parses scheme, host, credentials, port and path. A loopback-looking userinfo
  URL cannot open a remote connection, and endpoint diagnostics do not echo credentials.
- Existing directories, files and symlinks refuse before launch or mutation of a profile.
- Cleanup captures descendant pid/start identities while the root is owned, then revalidates them
  before individual signals. A TERM-resistant child is stopped after root exit; an unrelated live
  sentinel stays untouched. Lost inventory returns typed cleanup uncertainty. No group signal occurs
  after root reaping. This is a bounded known-descendant guarantee, not an atomic inventory, daemon-
  escape guarantee or proof of complete zombie reaping.
- Compound autocomplete fields (for example section/address tokens before a card field) redact
  sensitive values. The four new privacy/coverage assertions failed before correction and pass after.
- Unported custom controls keep completeness false. Field display previews remain bounded and are
  not qualified exact values for mutation.
- `websockets==15.0.1` is a direct dependency, using its existing locked artifact; offline lock
  consistency passes. This does not perform the L2 metadata split.

Parent verification on macOS arm64, Python 3.12.6, Chrome 156:

| Boundary | Observed result |
|---|---|
| Full regression suite, pure-Python twin, excluding browser/live | 2,571 passed, 95 skipped, 21 deselected |
| Fresh installed pure wheel outside the checkout, with only pytest, psutil and websockets | 48 passed; three real headless-Chrome tests; neither CUA nor browser-use installed |
| Installed wheel inventory, bytes and RECORD | 206 files verified; SHA256 `edb26c26f2c45bcc344dd106e57e9fc47f793adbd02416b788dff016a7412219` |
| Ruff, notebook structure, source whitespace and offline lock consistency | passed |
| Independent source recheck at 817d1fb | no remaining blocking finding within the observation-only scope |

The full-suite interpreter uses the previously prepared matching `.cleanup2` SDK test environment,
not a fresh full dependency installation. Its source path is absolute so subprocess discovery from
unrelated working directories sees this checkout. An exploratory run during remediation retained
seven failures: five from a relative PYTHONPATH, one from the duplicate notebook identifier, and one
from an intermediate transport test expecting asynchronous close to have completed at the command
deadline. The final frozen-runtime run above resolves those; the intermediate logs remain in ignored
`output/cdp-takeover/` rather than being reported as product failures or final acceptance.

The new `cdp-observation` workflow repeats the installed-wheel checks on Ubuntu against a real Chrome
binary, outside the checkout and without CUA/browser-use. It also verifies those packages are absent.
Its Linux result and final-head integration checks were pending when this report was published; PR 16
retains their status. This is an effector qualification check with a deliberately limited dependency
installation, not the future public light-install recipe. No 2-CPU/8-GB resource baseline is claimed.

The next input qualification uncovered a design constraint. A disposable installed-wheel probe checked
the intended field's focus, independently observed a page timer redirecting focus to a sentinel, then
sent exactly one `Input.insertText`. Only the sentinel changed. The plan now requires a target-local
delivery proof before enabling text input; post-readback cannot undo wrong-field input. DOM-event
clicking can qualify separately. Product click, type and navigation remain disabled in this PR;
cross-command continuity, exact text, durable authority, lost-ack recovery and L2 remain open.

Notebook: `2026-10-31-cdp-read-review.md`, `2026-10-31-cdp-transport-deadline.md`,
`2026-10-31-cdp-launch-custody.md`, `2026-10-31-cdp-input-targeting.md`.
