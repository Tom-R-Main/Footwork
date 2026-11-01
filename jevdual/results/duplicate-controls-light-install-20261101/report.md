# Duplicate controls and lightweight installation: integration

Checked source: `81d6985791298d151c9610bc10b1b00816137b07` on `codex/duplicate-controls-light-install`. Prediction commits `7b326f2` and `ecb01de` preceded the resolving tests. Implementation commits are `68c240c` (native ambiguity) and `81d6985` (profiles). The code is committed locally; no push, PR, hosted CI or merge is asserted.

## Checked behavior

The independent backing-control scenario first demonstrated wrong-target writes after identical controls reordered or were replaced. The repair refuses known native duplicate collisions, including peers hidden by pruning and collision evidence retained across session save/load. Unique supported controls still work. The modeled203-test affected suite and the final integrated suite include these regressions; see [native evidence](../duplicate-controls-20261101/report.md). This is simulated public-CLI evidence, not live desktop qualification.

The base wheel now installs the light dependency closure; desktop and agent requirements are explicit extras. Light bundles contain no CUA wheel and perform no native build. Full bundles preserve the exact pinned CUA role and explicit full extras. Consumers stay binary-only and refuse incompatible profile selections or missing binaries. See [installation evidence](../light-install-20261101/report.md).

## Final verification

- **Source suite:**2848 passed,51 skipped,66 deselected, exit0. Command from `jevdual/`:

```sh
PYTHONPATH=/Users/thomasmain/projects/footwork/output/duplicate-controls-light-install-20261101/pinned-cua:/Users/thomasmain/projects/footwork/jevdual/python .venv/bin/python -m pytest -q -m 'not browser and not live'
```

The first run with the shared project environment had2847 passes and one failure: its installed CUA lacked the existing `.cleanup2` source pin. A matching checked local binary wheel was installed into a task-owned overlay; the shared virtualenv was left unchanged. The successful rerun loaded the overlay's actual module/metadata. Both outputs are retained, and `verification.json` records the environment. No version assertion was relaxed.

- **Static/reproducibility gates:** Ruff, notebook format, the103-file tool-resource snapshot, and offline/no-build lock validation pass. All300 resolved package versions and artifact hashes remain unchanged.
- **Final wheel:** SHA256 `0c777e645947f308e93b01e939eaf964dae5a6e77c81c7d4ef269e7f51d41a4a`;217 wheel entries,212 product files. The source inventory/RECORD verifier passes. Light and full bundles contain byte-identical product wheels and valid SHA256 manifests.
- **Fresh resolver install:** the final wheel installed35 packages into a new private environment/cache using only binary packages from the approved PyPI source. Dependency consistency and installed origins pass. CUA, browser-use, PyObjC and Jeepney are absent. Installed catalog/schema/doctor report the light profile; native apps requests stop with `effector_unavailable`.
- **Installed real read:** the public installed CLI reads a loopback HTML/JavaScript fixture through the existing pinned Lightpanda binary. Heading/link/script text is present; private field values are withheld; action refs/input mutation remain absent; no POST occurs; completion is not asserted. All212 installed product files match the wheel. Cleanup is reported as bounded owned processes stopped with incomplete whole-tree inventory, not global orphan absence.
- **Actual bundle consumer:** the generated light installer succeeds offline in another new environment using the previously resolved project-owned cache. This second check is not a fresh-cache claim. A light/full mismatch refuses before environment creation. A full bundle with no cached transitive dependency wheels exits1 at binary resolution with no compilation/fallback. Full fresh dependency installation and native delivery were not rerun.

Exact final artifact/install/public-CLI receipts and the replayable local probe are retained under [light-install-20261101](../light-install-20261101/).

## Limits

Known duplicate controls deliberately remain unavailable for generic native actions until a qualified identity seam exists. An incomplete backend tree can still hide unknown peers, and fresh label selection keeps its current-query semantics. The repair is not universal native object identity.

These checks qualify the changed local source and macOS arm64/Python3.12.6 light artifact. New Linux/macOS CI jobs are configured but were not run on a provider in this chat. There is no new live desktop, paid provider, heldout, general browser completion, typing, small-host capacity, startup-time or RAM-saving claim.
