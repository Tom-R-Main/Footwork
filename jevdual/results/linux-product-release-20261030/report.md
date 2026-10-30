# Linux preview: product release checks

Source `40ae59f` consolidates the VM-tested Linux branch with main `f849e16`. The product docs now lead with a workflow chooser and a checked first result, while Linux desktop support is explicitly a preview. These checks qualify that merged artifact; the earlier combined-build report remains separate evidence.

## Fresh checks

- macOS source, Python 3.12, `JEVDUAL_PURE_PY=1 PYTHONPATH=python`: **2,464 passed, 94 skipped, 13 browser tests deselected**. This is the host's platform/dependency scope; it does not replace the Linux CI suite.
- JavaScript inspection/experiment/transport suites: **97 passed**.
- Ruff, all **103** packaged-resource snapshots and notebook format checks passed.
- Built the portable product wheel using the repository bundle builder and the already qualified pinned native arm64 CUA wheel. Product SHA256: `c7392c1cc0eaf25bad74f6ba73258007c4f0b988b2363bab707e87151163d6f7`.
- Installed the generated bundle into a fresh native Linux arm64 consumer environment, Python 3.14.4, with binary dependencies and simulator extra. All **193 package files** match the wheel.
- Public installed `tools`, `doctor` and `schema browser start` exit 0. The documented artifact example returns `ok=true`/exit 0 for matching bytes and `ok=false`/exit 6 after the saved bytes change. [Receipt](quickstart-receipt.json), [check script](quickstart_check.py).
- Installed public browser read, CLI append, MCP append, duplicate-token prevention, restart recovery and saved-file exact-byte checks passed, with process exit 0. Save was through the direct NativeBridge in the dedicated fixture; no public model guard was bypassed. [Receipt](installed-journey.json).

The Linux container used the cached native-tools image, init, two CPUs, 3 GiB memory, zero swap, 512 PIDs and 512 MiB shared memory. It had no host desktop sockets or credentials; the harness explicitly chose Chrome's no-sandbox mode inside this isolated fixture. Normal product launches retain their sandbox default.

## Retained limitations and failures

The first harness invocation guessed an unavailable Chrome ELF path and stopped after native append with `FileNotFoundError`; [output](linux-journey.txt). This was an invocation error. A fresh owned desktop and the observed `/opt/google/chrome/chrome` executable completed the journey above.

The final supervisor cleanup snapshot lists one editor zombie, with no live survivors, no forced PIDs, complete observed inventory and no signal failures. A subsequent `/proc/528` check found that PID absent. Both session records are retained; the snapshot is not rewritten to claim zero zombies.

The [earlier consolidated VM report](../linux-consolidation-vm-20261030/report.md) retains a post-success native teardown abort and intermittent repeated-session target timeouts. This successful journey does not resolve those failures or establish repeated-session reliability. Wayland, shared foreground control, provider-backed planning and physical devices remain unqualified. Hosted CI and merge status are recorded by the PR, separately from these local checks.

## Documentation grounding and review

The uv, Playwright and Coder READMEs informed the consumer path: state the useful capability, connect the real installer to a small observable result, then offer deeper routes. Footwork's pinned native dependency prevents copying their registry-install shortcuts. Historical measurement tables were preserved.

The canonical local repo-learn library is `/Users/thomasmain/projects/footwork/output/repo-learning/linux-consolidation/library`; its export contains `consumer-quickstart-connects-install-to-observable-result-v1` with source hashes, bounded evidence, novelty comparison and transfer limits. A separate GPT-6.1 Sol context reviewed the product docs against actual CLI schemas and found no actionable defect. This is independent context, not model diversity. The source review's native reliability findings are retained as the preview limits above.
