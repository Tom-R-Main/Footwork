# L1b owned browser contract: verification

Prediction: `docs/notebook/2026-10-31-light-browser-contract.md` LBC1, committed in `dbd14d4` with the
characterization tests before the refactor (`390fda1`).

Environment: macOS arm64, the main checkout's `.venv` (Python with `cua-driver 0.38.0+footwork.d5373879`,
the pre-`cleanup2` wheel), worktree source on `PYTHONPATH`, `JEVDUAL_PURE_PY=1`.

| Check | Base `701fd32` | Branch `390fda1` |
|---|---|---|
| `tests/test_browser_contract.py` characterization (9) | 9 passed | 9 passed |
| `tests/test_browser_contract.py` L1b additions (9) | 9 failed (attributes and adapter absent) | 9 passed |
| Full suite, `-m "not browser and not live"` | 2503 passed, 95 skipped, 1 failed | 2512 passed, 95 skipped, 1 failed |
| ruff `python tests` | — | clean |

The full-suite branch count includes the nine characterization tests, collected before the L1b additions were
appended. The single failure on both is `tests/contract/test_cua_driver_seams.py::test_cua_driver_version_is_pinned`:
the pin expects `.cleanup2`; the borrowed venv has the earlier wheel. It says nothing about this change.
Summaries: `suite-base-701fd32.txt`, `suite-light-l1b.txt`.

Not run: the 18 browser/live tests (real Chrome and CUA), hosted CI, an installed-wheel check, Linux. The CUA
browser replies are modelled on the vendored source at `d5373879`, not recorded from a live driver.
