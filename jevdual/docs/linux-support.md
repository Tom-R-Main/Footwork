# Linux installation and qualification

Footwork's installed browser and native X11 paths were exercised on Linux on 2026-10-30. The public CLI read an owned Chrome page and appended exact text in Mousepad. The public MCP server appended once, returned the same result for a repeated token, and retained that result after restart. An independent file check confirmed the saved bytes. See [runtime evidence](../results/linux-support-20261030/runtime/report.md) for artifact hashes, commands and limits.

The portable product wheel uses Python for its optional Rust acceleration. Desktop control still needs the pinned native CUA wheel for the consumer's architecture and compatible Linux libraries. Consumer installation uses binary packages; it does not compile CUA or the optional Rust core. A source build belongs on the builder.

## Install and start

Use the generated bundle for your architecture and Linux distribution:

```sh
python3 /path/to/bundle/install.py --venv "$HOME/.local/share/footwork/venv"
export PATH="$HOME/.local/share/footwork/venv/bin:$PATH"
footwork tools
footwork doctor
footwork apps
```

The installer can use uv, an existing pip, or Python's bundled ensurepip. Python must already be installed. The bundle contains the product and CUA wheels; other binary dependencies are downloaded unless they are available offline. `--core-only` omits the simulator extra. An incompatible OS/architecture wheel is rejected before creating the environment.

Run native commands inside the desktop user's X11 and D-Bus session, with AT-SPI enabled. The runtime needs the X11/AT-SPI libraries and a desktop application exposing accessible controls. A display variable alone does not prove access. Linux `doctor` therefore reports runtime access as `not_checked`; a successful scoped observation establishes the actual connection.

For an already open Mousepad document:

```sh
footwork desktop start 'Append the approved note' --app Mousepad \
  --session "$HOME/footwork-session" --mode background_only
footwork desktop look --session "$HOME/footwork-session"
footwork desktop do append 'text area' 'The approved note' \
  --session "$HOME/footwork-session"
```

Use the label or ID returned by the current observation. The default posture keeps input in the background. Linux foreground input requires an explicitly dedicated `exclusive_desktop` session. Shared `foreground_permitted` input refuses because Linux idle, lock and focus-restoration guarantees have not been qualified. Explicit `cmd` means Super on Linux; save shortcuts use Control-S.

For Chrome installed outside the standard paths, set `FOOTWORK_CHROME_EXECUTABLE` to its actual binary. Footwork binds the owned profile, process incarnation and executable. It does not accept a process merely because its command line resembles Chrome. Rosetta-emulated Linux binaries report the emulator as their executable and fail this check; use native execution for that qualification.

If the qualified Linux browser remains running after its last window closes, the public startup route opens one through that executable and exact profile. Window discovery and attachment share a monotonic deadline and recheck the process incarnation. Failed or cancelled binding shuts down its driver and any newly launched helper; it does not terminate a reused browser. Recovery copies only an explicitly present `--no-sandbox` setting from that same qualified root, because Chromium also checks sandbox prerequisites in secondary helpers. Normal launches omit it, and arbitrary arguments are never copied. Qualification fixtures explicitly select this mode only in their isolated containers.

## Exact text and document scope

Linux text operations use a bounded AT-SPI adapter with process incarnation, X11 window geometry, accessibility-bus identity, unique owner/object path and ancestry checks. Complete values up to 65,536 codepoints are read independently of CUA's 4,096-character preview. Read-only text does not gain write operations from its role or token. Append checks the exact prior value and inserts once at its measured end; a lost acknowledgement is never retried automatically.

The MCP destination is an explicitly named, existing, owned Mousepad document. Its binding requires the qualified `/usr/bin/mousepad` process and the full absolute path in the window title. Basename-only titles, other applications and changed identities refuse. A leading modified marker is supported. A title match is document binding, not persistence proof. Historical operation completion and current agreement remain separate after restart.

Linux save dispatch retains its delivery receipt but does not infer a saved-file path for arbitrary apps. Use `check-file` or `check-artifact` with the explicitly selected path to establish persistence. The acceptance harness invokes save through the scoped native bridge and then runs the public artifact checker. It does not bypass the public command's model guard or claim that a model-backed save journey was tested.

## Optional tools

Linux camera capture uses FFmpeg V4L2 and requires an explicit `/dev/videoN` character device. Inventory is metadata, not proof of a physical camera or permission. The VM had no video device: missing-device refusal and conformance tests passed, while physical acquisition remains unqualified.

Linux inbox OCR uses installed Tesseract with English language data. Explicit horizontal mirror correction uses FFmpeg and retains the original image bytes. Engine/configuration, TSV evidence and source hashes accompany the review candidate. Confidence scores are engine-specific; reconstructed spacing is not exact source text. The existing digest-bound review and acceptance steps remain required. Direct and mirrored synthetic-image cases were exercised through the installed CLI.

The installed simulator's initialization/status path and Node-based discovery were also checked. Real robots, cameras and caller-supplied browser capture adapters require their own runtime evidence.

## Reproduce the isolated qualification

`scripts/linux/Dockerfile` defaults to the cached ExecuFunction Ubuntu 24.04 amd64 workspace image. It installs the pinned Rust 1.97.1 and uv 0.12.5 builders, native libraries, Xvfb, D-Bus, Openbox, Mousepad and optional OCR/inspection tools. Building downloads dependencies. It does not allocate a cloud VM.

```sh
docker build --pull=false --platform linux/amd64 \
  -t footwork-linux-builder:20261030 \
  -f jevdual/scripts/linux/Dockerfile jevdual/scripts/linux
```

The amd64 wheel was built and installed in that ExecuFunction-derived image. Full desktop identity qualification used native arm64 execution in the same local Linux VM, extending the cached Ubuntu 26.04 desktop image with `BASE_IMAGE` and `BUILD_USER=ubuntu`. That arm64 wheel is not a claim of compatibility with older glibc distributions.

Run containers with `--init` to reap exited browser processes, explicit CPU/memory/PID/swap limits, no host desktop sockets, no credentials and no privileged mode. The desktop user must have a passwd entry so D-Bus can authenticate it. Start the owned supervisor with the installed interpreter:

```sh
FOOTWORK_DESKTOP_PYTHON=/path/to/installed/bin/python \
  scripts/linux/desktop-session.sh /fresh/session-state
# For user-owned extracted desktop packages, add:
# --rootless-prefix /path/to/sysroot
```

The supervisor reserves an unused display through Xvfb's native `-displayfd` protocol and owns its Xvfb, D-Bus, Openbox and Mousepad processes. An explicit `--display` retains occupied-display refusal. It creates private config/cache/data/state/runtime directories; ambient profiles are never cleared or reused. `session.json` records transitions and resource diagnostics. The `started` marker appears only after bounded X handshake, WM selection plus EWMH self-reference, accessibility-bus and exact fixture document/text checks. A recovery dialog refuses readiness. The chosen display is in `display`, not assumed to be `:99`.

Wait for `started`, then run `scripts/linux/qualify.py` with the installed Python, state directory, fresh output directory and actual installed Chrome ELF binary. Signal the supervisor with TERM/INT to stop it. A component exit, changed WM/accessibility identity or incomplete process census invalidates the marker before bounded cleanup; recorded escalation requests (`forced_pids`), live `survivors` and orphan `zombies` remain distinct.

Cleanup separates custody, signal identity and wait ownership. Groups/ancestry discover observed owned members; individual pidfds deliver signals after owner/start checks across acquisition. A leader fd is never treated as tree-wide cleanup. Unsupported, denied and exhausted fd paths have explicit outcomes and no numeric fallback; unsupported startup refuses before launching components. Direct child identities are read independently of the bounded census. Truncated or inaccessible inventories retain known identities and set cleanup uncertainty, even when the observed survivor list is empty. The runner owns its direct child waits without installing a global reaper. A container init remains required for adopted orphans; escaping before observation is outside that descendant snapshot guarantee.

During browser recovery an invocation-owned forwarding helper must finish and be reaped before unique-root discovery resumes. The exact executable/profile/port/UID predicate continues to refuse an unrelated second root; no matching PID is arbitrarily excluded.

The fixture Chrome command explicitly disables the sandbox only inside this isolated test environment. The ordinary product launcher keeps its default sandbox behavior. See the [Debian runtime tranche evidence](../results/linux-runtime-tranche-20261030/report.md) for the source/wheel identities, 512-PID/two-core/3-GiB/zero-swap run and retained failures.

The [consolidated VM acceptance](../results/linux-consolidation-vm-20261030/report.md) identifies the combined build separately. Its standalone installed journey, real delayed-helper recovery, refusal control and isolated lifecycle gates passed. Repeated multi-session batches also exposed intermittent native target timeouts and one nonzero native teardown after CLI JSON success; these remain unresolved and are not converted into passing runs. The recorded diagnostic profile used `--probe-timeout 10` within the same 30-second startup deadline; that setting did not eliminate the batch timeouts. Readiness remains bounded and conservative.

For optional tools, run `scripts/linux/qualify_optional.py` with the installed Python, a fresh `--output` directory and an installed TrueType `--font`. It creates synthetic direct/mirrored images, checks the exact fixture candidate before accepting it, and tests camera inventory and missing-device refusal. It never opens a video device.

For a lightweight prerequisite inventory, `python3 -I -S jevdual/python/jevdual/host_probe.py` needs only Python. It reads selected host/cgroup facts without opening a desktop or network connection. PID limits/current/events, memory/swap counters and selected PID1 facts are diagnostic snapshots; inaccessible, hidden or delegated limits and actual orphan-reaping behavior remain unknown. Finite observed limits are not capacity reservations.

Wayland, shared-desktop foreground coexistence, physical devices, the actual Meta sandbox and provider-backed planning were not exercised. The local branch is not a published release; hosted CI and merge are separate actions.
