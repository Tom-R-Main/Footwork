# Pinned Lightpanda Linux preparation — no Footwork candidate qualification

Only public `lightpanda-io/browser` GitHub asset **694146173**, `lightpanda-x86_64-linux`, was downloaded into `/workspace/scratch/footwork-lightpanda-preparation-20261031`. API/download records and exact size **77,129,032 bytes** match the pinned SHA256:

**`19f3fee25fb14bb75a1e0c1e0f8ab9cce842950544e4a144fbad3884c94b98a3`**.

The helper verified size, digest and ELF64 x86-64 machine **before** rename/chmod or execution. Hash remained identical afterward. [API metadata](asset-metadata.json), [download receipt](download.json), [pre-execution verification](verified-before-execution.json).

Binary location: `/workspace/scratch/footwork-lightpanda-preparation-20261031/lightpanda-x86_64-linux` (owned scratch, owner-executable only). No system installation or PATH change.

| Metadata invocation | Exit | Result |
|---|---:|---|
| `--version` | **1** | Guessed flag rejected: unknown command, `did_you_mean=version`; original failure retained |
| `--help` | **0** | Documents commands, including the `version` subcommand |
| `version` | **0** | **`1.1.0-nightly.11423+56980afde`** |

All commands had **10-second bounds**, no timeout/signal, telemetry disabled with `LIGHTPANDA_DISABLE_TELEMETRY=true`, core output disabled with `LIGHTPANDA_DISABLE_CORE_DUMP=1` and child-only RLIMIT_CORE0. Provider keys were omitted from child environment. Original [numeric commands](commands.json), [help](help.stdout.txt), [rejected flag](version.stderr.txt), [documented version output](version-subcommand.stdout.txt) and [its numeric receipt](version-subcommand.json) remain separate. No failed attempt was relabelled or hidden. The initial helper exited1; the documented-version helper exited0.

The Linux binary's reported git suffix is **56980afde**, matching the supplied Mac version string. This is self-reported binary provenance bound to the verified digest, not a reproducible-source-build claim. The browser-download URL contains the nightly tag, but **the nightly tag's target is not used as the binary's source identity**. No source checkout/build/audit was performed here; parent reference/source-audit claims remain separate.

## Actual VM facts

Debian13.6, Linux6.18.57, native x86-64, CPython3.12.14. CPU model **AMD EPYC 9V74 80-Core Processor**; this does not grant80 CPUs: visible logical CPU count is5, affinity/cpuset0-4, and cgroup quota is **4 CPUs** (`400000 100000`). Selected exposed flags include sse4_2/avx/avx2/bmi1/bmi2/avx512f.

Cgroup memory cap **16GiB** (`17179869184`), observed memory.current1697697792 bytes, pids.max=`max`, observed pids.current62, memory.swap.max=`max`; actual SwapTotal/SwapFree0KiB. Memory/PID event counters were zero. No 2CPU/8GB profile is claimed. [Complete selected environment facts](environment.json) contain no environment or credential dump.

Both helpers use an explicitly test-only child subreaper and actual direct-child Popen waits; observed descendants/adopted waits are empty. [Initial cleanup](cleanup.json), [version cleanup](version-subcommand.json). No browser service, Unix socket, page target, DOM read, mutation, reconnect, provider/model call or desktop capture was attempted. No permissions/elevation, source build, package/system install or cloud/VM resource was requested.

## Pending candidate

This is **binary metadata preparation only**. The Footwork one-shot read route, private socket, exactly-one-connection behavior, explicit target creation, DOM bounds and lack of mutation authority have not been qualified. Wait for the parent's exact pushed Footwork source SHA, wheel hash and test recipe. Typing/clicks/raw scripts/reconnect fallback remain outside scope. Prior PR18 evidence stays unchanged at7a874eb; parent owns implementation and PR/merge.
