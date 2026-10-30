# Linux qualification

Status on 2026-10-30: installation and host diagnostics are under qualification. Full Linux desktop support is not established.

The portable Footwork wheel uses Python for its optional accelerated functions. Desktop control still requires the exact native CUA wheel. The pinned CUA source includes a Linux implementation with native Rust AT-SPI access, but Footwork's direct accessibility helpers, shared-desktop posture, durable native identity and browser-to-TextEdit capability remain macOS-specific. A successful install is not evidence that those routes work on Linux.

## Probe a sandbox before building

From this checkout, run:

```sh
python3 -I -S jevdual/python/jevdual/host_probe.py
```

The single file can also be copied to a sandbox and run there with Python alone. It reads selected system facts without starting a browser, querying a user's desktop, installing tools or contacting a service. It reports visible cgroup memory/CPU limits separately from host capacity. Missing values are unknown, and session indicators are presence checks only. Executable discovery checks PATH; a browser installed elsewhere may still exist.

## Prepared Linux builder

`scripts/linux/Dockerfile` extends the cached ExecuFunction Ubuntu 24.04 amd64 workspace image. Its base was observed locally with image ID `sha256:cccffcb67e43865ba6b48e38519f1bab9cbdaf7a8294fc6089448e2777775542`. It supplies CUA's pinned Rust 1.97.1, uv 0.12.5, native development libraries, D-Bus, AT-SPI, Openbox and Mousepad. Building it downloads dependencies; it is not an offline build or a cloud allocation.

After network installation is authorized, build from the repository root:

```sh
docker build --pull=false --platform linux/amd64 \
  -t footwork-linux-builder:20261030 \
  -f jevdual/scripts/linux/Dockerfile jevdual/scripts/linux
```

On an arm64 Mac this executes amd64 userspace through emulation in Docker's Linux VM. It does not establish native arm64 support or reproduce the Meta sandbox's kernel and permission model. Use a task-owned container, explicit CPU/memory/shared-memory limits, an isolated display/session bus, no host desktop sockets, no privileged mode, and no credential mounts. Keep package builds separate from the small consumer-installation acceptance run.

The Dockerfile is prepared but has not yet been built or qualified. The cached base image has Python 3.12, a compiler, Xvfb and Chrome for Testing, but lacks Rust, uv, the native development packages and a working accessibility bus. The read-only probe ran in that base under a two-core, 2 GiB container limit.

## Remaining acceptance evidence

1. Build the exact CUA wheel on Linux and retain its hash, dependency/library report and source revision.
2. Install the real bundle outside the checkout without a consumer compiler. Check public discovery and diagnostics, native library loading and missing-prerequisite failures.
3. Observe an owned Linux browser and native editor through CUA in an isolated graphical session. Preserve exact text, fresh target identity and action/readback evidence.
4. Implement and qualify the remaining Footwork platform adapters. Exercise a browser-to-editor-to-saved-file journey through the installed CLI and MCP interface; read the resulting bytes independently.
5. Challenge stale targets, repeated requests, restarts, interrupted writes and uncertain delivery. Test X11 and Wayland separately. Retain existing refusals until their missing guarantees are proven.
6. Port and qualify camera/OCR and other advertised optional tool families. Real-device claims require device evidence; simulated inputs do not qualify hardware.

The existing macOS capability doctor retains its unsupported-platform blocker on Linux. Host prerequisite reporting does not override it. No merge, publication or hosted CI execution is implied by local checks.
