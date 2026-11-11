# Shared-desktop coordination validation

Primary implementation: `d34cdd8`, based on `f5d41c4`; subsequent X11 server-identity correction is recorded under MC3 in the notebook.

The public CLI now serializes session read/modify/write transactions and coordinates
app/window work across processes and authority databases. Foreground-capable work
and headed browser startup claim the actual desktop. Filmed starts retain desktop
and subject-app reservations across command gaps. Explicit control commands expose
owners/waiters, saved observe-only access, cancellation, handoff and orphan recovery.
New ordinary-browser sessions pin the original Chrome page ID and incarnation;
missing native windows and explicit tab handles refuse rather than selecting peers.

| Check | Evidence | Result |
| --- | --- | --- |
| Offline source suite | `pytest-final.txt` | 2988 passed, 23 skipped, 67 deselected |
| Repository lint | `ruff.txt` | passed |
| Installed tool resource snapshot | `resources.txt` | 103 files checked |
| Browser-inspection Node checks | `node.txt` | 97 passed |
| Real owned headless Chrome page catalogue | `catalogue-probe.json`, `catalogue-probe.py` | original pin established; same-URL replacement refused |
| Original native window disappears | `window-red.txt`; final scenario suite | dispatch reproduced before repair, refused after repair |

The final pytest command was `uv run --no-sync pytest -q -m 'not browser and not live'
--deselect=tests/contract/test_cua_driver_seams.py::test_cua_driver_version_is_pinned`,
with umask022 and the conventional `/tmp/.X11-unix` fixture directory present.
The explicit installed-version deselection accounts for one of the67 deselections.
This cloud image has upstream CUA0.46.0 rather than the required
`0.46.0+footwork.5486b624.cleanup2`; the failed installed-version assertion is retained
in `pytest-initial.txt` and `pytest-before-final-review.txt`. Rust and native build
headers are unavailable locally. No version assertion was weakened or relabeled.

The initial full run also exposed two wrapper compatibility regressions and
fixture failures caused by umask0077 and a missing X11 directory. The code
regressions were repaired; fixture setup was corrected for the final run.

Live macOS pointer/focus coexistence, CUA take capture and independent Screen Sharing
desktops remain unqualified. Native window creation identity is unavailable.
Only participating processes using this per-user registry are coordinated, and an
already admitted opaque SDK RPC finishes under ownership before a new owner enters.
See `docs/desktop-coordination.md` for exact scopes, migration and recovery commands.

Follow-up review reproduced a second desktop owner on X11 screen one while screen
zero of the same server was owned. The correction normalizes numeric screen
suffixes and common local Unix/loopback aliases; all25 coordinator tests pass
(`coordination-final.txt`), including independent X server coverage. The original
failure is retained in `x11-screens-red.txt`. CI is rerun on the corrected head.
