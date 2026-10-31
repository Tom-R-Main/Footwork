# Linux CDP observation baseline: candidate qualification preparation

Baseline main: `b03c4484e46fc57768ac5fbb692dee697aeea146` (PR16). Isolated worktree: `/workspace/footwork-cdp-baseline-20261031`, branch `codex/linux-cdp-baseline-20261031`. Prediction commit `243dc6a` preceded the run; measured checkout `8a5018d` adds only that notebook and the test-only runner. Product source, original tests, pyproject and lock are byte-unchanged from baseline. The unrelated original `/workspace/Footwork` checkout remains at `06ea918` with no working-tree edits.

One complete original batch passed **48/48, zero failures/errors/skips**, pytest exit **0**, runner exit **0**, in **6.01 seconds**. [JUnit](junit.xml) and [complete output](pytest.stdout.txt) retain each result: **17** effector, **21** deadline/transport, **10** launch-custody cases. All **three real Chromium cases** ran: declared candidates/redaction/omissions, before-dispatch mutation refusal plus stale refs after setup reload, and foreign/stale endpoint refusal. Three warnings are unregistered `browser` markers because checkout pytest configuration is deliberately absent; they did not skip or deselect tests.

## Exact installed artifact and source isolation

- Wheel: `jevdual-0.0.1-py3-none-any.whl`.
- SHA256: `edb26c26f2c45bcc344dd106e57e9fc47f793adbd02416b788dff016a7412219`.
- Existing standard-library builder verified **206** wheel entries against source; the runner byte-verified all **201** installed package files against that wheel. [Build receipt](build.json).
- Fresh consumer: `/workspace/scratch/footwork-cdp-qualification-20261031/consumer`; tests copied unchanged outside both checkouts to the sibling `tests/` directory. Exact test hashes and installed module origins are in [environment.json](environment.json).
- Installed with `--no-deps`; only pytest **8.4.2**, psutil **7.2.2**, websockets **15.0.1**, and pytest's own dependencies were added. Neither CUA nor browser-use is installed. This qualifies the observation effector boundary, not the future complete light installation recipe.
- Execution uses the consumer's `python -I -m pytest`, unset `PYTHONPATH`, explicit test-only configuration boundary and no external pytest plugin autoload. The unchanged lazy-import test also resolves its subprocess against installed code. [Command](command.json), [exact measured runner source](harness/baseline-measured.py.txt), [runnable helper](harness/baseline.py).

## Actual VM and process policy

Debian **13.6** (trixie), Linux **6.18.57**, native **x86-64**, CPython **3.12.14**, Chromium **154.0.8037.57** at `/usr/lib/chromium/chromium`. Chrome executable hash, UID1000, interpreter origins, dependency inventory, kernel-policy observations and rlimits are retained in [environment.json](environment.json). No Chrome sandbox-disabling argument was added.

The visible cgroup has `cpu.max=400000 100000` (**4 CPUs**) with effective cpuset `0-4`, `memory.max=17179869184` (**16 GiB**), `pids.max=max`, `memory.swap.max=max`. Actual host-reported SwapTotal/SwapFree are **0 KiB**. These are the current observed limits, not the earlier 2-CPU/3-GiB/512-PID acceptance constraints; no caps were silently imposed or changed. The exposed cgroup root cannot establish inaccessible ancestor policy. No VM, cloud resources or system package changes were made.

PID1 is `tail`, not a reaper. A dedicated test-only subreaper owns pytest and its adopted descendants; it performs **no adopted-child reaping until after pytest exits**, preserving the module's observed cleanup boundary. [The post-pytest snapshot](post-pytest-before-wrapper-reaping.json) contains **17 zombies, zero live children**: 16 Chromium/crashpad children and the TERM-resistant custody helper. The wrapper then reaped all17 with retained numeric wait statuses, issued **no extra signals**, and ended with **zero owned descendants**. [Cleanup receipt](cleanup.json), [observed process identities](owned-process-history.json).

This does not upgrade product cleanup into an atomic inventory, daemon-escape or global no-zombie guarantee. Known terminated zombies depend on their reaper. Parent-supplied candidate qualification must retain that distinction. Task-local wheel, consumer, test copies and synthetic profiles remain under the scratch directory for inspection; no unrelated processes or profiles were touched.

## Scope and handoff

No original failures occurred in this baseline batch; all warnings and original receipts are retained. An additional helper-only lint check found three import/UTC style findings, retained in [the original lint output](harness-lint-before.txt). The runnable helper received only those style corrections; its exact measured source is archived and hash-matches the run receipt. The baseline was not rerun or relabelled. [Final helper lint](harness-lint.txt) and [notebook validation](notebook-check.txt) pass. No product implementation was changed, no PR was opened or merged, and no typing, trusted click, product navigation, public CLI selection or durable mutation capability was enabled. The existing tests use their separate setup connection to load/reload only a loopback synthetic fixture; the observation effector itself continues to refuse mutations before dispatch.

Baseline preparation is complete. The candidate branch/SHA and full DOM-event click recipe have not yet been supplied. This batch qualifies only the baseline observation boundary in this recorded configuration, not a click candidate, Chrome156 parity, finite repeated reliability or the previous resource envelope. Implementation/review/PR/merge remain with the parent chat.
