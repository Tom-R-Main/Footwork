# Release of main at 474958e: records

The scripts here are kept exactly as they ran. `qualify.sh` was run with SHA-256 `4c28d3de…805c23`,
and the records name these files. Their known defects are listed below instead of fixed in place. Fix
them in a copy before reusing them for another release. Notebook:
`docs/notebook/2026-11-14-release-474958e.md` (RDP1 to RDP6).

## What each record shows, and what it does not

- `release-verification.json`: the staged release's installed bytes match the wheels, and its CLI
  answers from a hostile directory. Written by `stage_release.py` and `verify_release.py`.
- `live/release/release-live.json`: the release probe's 20 criteria. It records its interpreter,
  `jevdual`, the driver's source and version. Its `protected_chrome_*` entries are **Chrome renderer
  processes** (`--type=renderer`), not the browsers listening on 9333, 9444 and 9555 (RDP4).
- `live/filmed/verdict.json` and `live/drag/run.json`: the filmed-page probe and the drag acceptance.
  **Neither records which interpreter or `jevdual` its product commands ran.** That they ran the staged
  release is inferred, not recorded (RDP6).
- `activation.json`: the selection of `current`.
- **Not in these records:** the separate closure checks made by the session that handed over the
  screen. Those are that session's own evidence: owned PIDs absent, 9466 not listening, the registry
  empty, no capture, alert or notice, the button up, `current` unchanged, and the listening browsers'
  PIDs by `lsof`.

## Known defects of the scripts as run

1. `release_probe.py`, `protected_chromes()`: matches any process whose command line carries
   `--remote-debugging-port=N` and keeps the last match, which is a renderer. Its docstrings call these
   the protected Chrome instances. Read the listening process instead (`lsof`, or a process without
   `--type=`). The defect is inherited unchanged from `results/converge-release-20261111/`.
2. `probe_filmed_page_pointer.py` and `probe_drag_points.py` (in `scripts/`, run from 325a105): their
   product subprocesses run `sys.executable -m jevdual.cli` without `-I`. They are not isolated from
   `PYTHONPATH` or the current directory.
3. `activate_release.py`: the "no Footwork process" check matches `jevdual.browser_holder`, but a
   filmed session's holder runs as `jevdual.browser_session_holder`, so an idle holder would not have
   been seen. The converge-release activation's cleanup gate (owned PIDs gone, listening browsers
   unchanged) was not carried over.
4. `stage_release.py`: the converge-release original had no closing launcher check either. This one
   asserts `current` unchanged at the end, but not the launcher's hash.
5. `qualify.sh`: after a probe that does not hold, it still runs its closing readings, and the script
   can exit 0. Its `held` lines are correct, but its exit status is not a verdict. Read the `held` lines
   and the records.
