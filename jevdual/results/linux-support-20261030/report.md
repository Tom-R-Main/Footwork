# Linux installation foundation, 2026-10-30

Observed outcome: installation and diagnostics checked; full Linux desktop support unverified. Prediction commit: `07cffe8`, based on merged `1301074`. `checked-files.json` binds the changed executable sources used by these checks. The final commit is recorded by Git rather than embedded in its own file.

## Changes

- The generated bundle installer accepts existing Python with uv, external pip >=22.3, or venv's bundled ensurepip. It rejects incompatible CUA OS/architecture before environment creation and requires binary dependencies. Existing environments are preserved.
- Dedicated Chrome discovery accepts installed Linux binaries or an explicit executable. Attachment checks exact executable, profile argument, debugging port, user and process incarnation. Missing executable fingerprints and ambiguous matching processes refuse attachment.
- The standalone host probe and installed doctor report selected prerequisites, visible cgroup limits and session indicators without exposing environment values, launching apps or claiming readiness.
- The existing pure-mode lazy-UUID test now checks the documented disabled behavior as well as retaining its normal repr/hash checks. Production patch behavior is unchanged.

## Evidence

| Boundary | Observed result | Limit |
| --- | --- | --- |
| Full pure-Python suite | 2213 passed, 70 skipped, 13 deselected | Local macOS dependency environment; no native extension or live browser lane |
| Final focused changes | 60 passed | Includes generated installer execution and ownership refusals; no live CUA |
| Lint / resource snapshot / notebook | Passed | Static/source consistency |
| Portable consumer wheel | Rebuilt, installed in an isolated local environment, checked outside checkout | Dependency-free packaging qualification |
| Linux portable build | Same SHA256 as the local build: `7d24e3c5ddcf849107da31d0f29fc91c2ec35f4a7253c1cec998df226dbf9adc` | Does not include compiled CUA |
| Linux installed CLI | Real product installed without dependencies; discovery works, strict doctor exits 1 with blockers | Deliberately incomplete dependency installation |
| Linux generated installer | Installs local synthetic product/CUA wheels and runs entrypoint with no uv/base pip | Tests installer mechanics, not real native dependency compatibility |

The Linux checks used cached ExecuFunction image `cccffcb67e43865ba6b48e38519f1bab9cbdaf7a8294fc6089448e2777775542`, Ubuntu 24.04 amd64 on Docker's Linux VM through emulation on the arm64 Mac. Containers used two CPUs, 2 GiB memory, 128 PIDs, dropped capabilities, no network, read-only source/artifact mounts and disposable filesystems. No package downloads or cloud allocations occurred.

`execufunction-host-probe.json`, `linux-wheel-build.txt`, `linux-installed-discovery.json` and `linux-installer-fixture.txt` retain the corresponding observations. `pytest-pure-final.txt` and `focused-final.txt` contain final test outcomes. Initial failures remain in `pytest.txt` and `pytest-pure.txt`: first an unbuilt-worktree native-backend expectation, then the corrected pure-mode test assumption. Both modes of the corrected patch test were checked separately.

Reproduce the source checks from `jevdual/` using an existing dependency environment, with the checkout's `python/` on PYTHONPATH:

```sh
JEVDUAL_PURE_PY=1 PYTHONPATH=python python -m pytest -q -m 'not browser'
ruff check python evals tests scripts
python scripts/sync_tool_resources.py --check
python -m evals.notebook docs/notebook --check
python scripts/capability_package_check.py --run-dir /absolute/fresh/package-check
```

The package check requires existing uv and Python. The standalone sandbox probe needs only Python: `python3 -I -S python/jevdual/host_probe.py`. Two implementation workers used the parent session's inherited model settings; the parent reviewed their changes, reran checks and performed the Linux container checks. This was not a review by different model families.

## Next boundary

The prepared `scripts/linux/Dockerfile` has not been built. Network installation approval is pending under the user's supplied AGENTS.md. After approval, build the pinned Linux CUA wheel and qualify its native observation/action routes before porting Footwork's macOS-specific helpers. No Linux native support claim, CI result, Meta sandbox result, PR, merge or publication is established here.
