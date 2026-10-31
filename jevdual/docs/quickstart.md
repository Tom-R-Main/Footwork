# Your first steps with Footwork

Get a checked result first. Then give Footwork a browser or a native app to work in.
For the reasons to add it to an existing agent setup, see [why Footwork](why-footwork.md).
The steps below use the installed CLI; discovery, exact file checks and browser observation do not
call a model provider.

## Install a bundle

You need an existing Python 3.11 or newer, below Python 4. A bundle contains the Footwork wheel,
the pinned native CUA wheel for one host platform, an installer and a SHA256 manifest. Choose a
bundle built for your OS and architecture, with compatible system libraries. Linux wheels have local
platform tags and make no manylinux compatibility promise.

If you already have a compatible bundle, install into a **new** environment:

```sh
python3 /path/to/footwork-bundle/install.py --venv "$HOME/.local/share/footwork/venv"
export PATH="$HOME/.local/share/footwork/venv/bin:$PATH"
footwork tools
footwork doctor
```

Replace `/path/to/footwork-bundle` with its actual location. The installer refuses an existing
environment. It uses installed Python and uv, pip or bundled ensurepip; binary dependencies may be
downloaded. The consumer needs no Rust compiler. Doctor reports prerequisites; a successful live
observation establishes access to the selected app.

To build a bundle from this repository, first install uv and the
[CUA native build prerequisites](upstream/cua-driver-build.md) for your platform. From the repository
root, with a new output directory:

```sh
rustup toolchain install 1.97.1 --profile minimal
cd jevdual
python3 scripts/build_agent_bundle.py --output ../output/footwork-bundle
```

Then use `output/footwork-bundle/install.py` from the repository root in the installation command
above. This builder compiles the pinned CUA native dependency and can download build dependencies.
If you already built the exact compatible CUA wheel, supply it with `--cua-wheel /path/to/cua_driver.whl`
to reuse that build. See [bundle details](unified-cli.md#build-one-bundle) for the artifact contract.
Footwork's pinned CUA dependency must be supplied by this build or a matching wheelhouse; a bare
registry install does not supply it.

## Check saved bytes

This small example needs no desktop, camera or model key. Create an expected note and a saved copy,
then ask Footwork to check their exact bytes:

```sh
FOOTWORK_DEMO=$(mktemp -d)
printf 'Footwork checked this note.\n' > "$FOOTWORK_DEMO/expected.txt"
cp "$FOOTWORK_DEMO/expected.txt" "$FOOTWORK_DEMO/note.txt"
FOOTWORK_SHA=$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$FOOTWORK_DEMO/expected.txt")
footwork check-artifact "$FOOTWORK_DEMO/note.txt" \
  --expected-file "$FOOTWORK_DEMO/expected.txt" --expected-sha256 "$FOOTWORK_SHA"
```

The result should report `ok: true`. Change the saved note and repeat the same check:

```sh
printf 'A different note.\n' > "$FOOTWORK_DEMO/note.txt"
footwork check-artifact "$FOOTWORK_DEMO/note.txt" \
  --expected-file "$FOOTWORK_DEMO/expected.txt" --expected-sha256 "$FOOTWORK_SHA"
```

Now the result should report `ok: false` and a nonzero exit status. That is the useful bit: the check
can distinguish saved bytes from an attempted save. The temporary files remain in `$FOOTWORK_DEMO`
for inspection.

## Open a browser session

Use a graphical session with a supported Chrome/Chromium installation. On macOS, grant the relevant
Accessibility permission to the terminal or agent host running Footwork. On Linux, follow the
[X11 session prerequisites](linux-support.md) first. If Chrome lives outside the standard paths,
set `FOOTWORK_CHROME_EXECUTABLE` to its actual executable, not a shell wrapper.

```sh
FOOTWORK_BROWSER_SESSION="$FOOTWORK_DEMO/browser-session"
footwork browser start "Read the example page" --url https://example.com \
  --session "$FOOTWORK_BROWSER_SESSION"
footwork browser look --session "$FOOTWORK_BROWSER_SESSION"
footwork browser read --match "Example Domain" --as heading --session "$FOOTWORK_BROWSER_SESSION"
footwork browser status --session "$FOOTWORK_BROWSER_SESSION"
```

`start` opens or binds Footwork's dedicated Chrome profile. `look` shows its current observation and
available targets. `read` retains the matched heading as a named value, `@heading`, with its source.
`status` shows the session record. On macOS, first attachment may require bringing that owned Chrome
window forward once. If startup refuses, correct its reported prerequisite and complete `start`
before proceeding.

The browser loads a public page in this example. Footwork does not request model judgment for these
commands. To let a model choose steps or judge completion, configure the relevant provider keys
through your existing secret-management workflow; see [operator commands](../../README.md#drive-it).
Use current target IDs from `look` for actions. A receipt describes the action's evidence; exit 0
alone is not proof that the wider task is complete.

## Choose your next route

- **Owned headless browser:** the [CDP preview](owned-cdp.md) adds guarded button activation and durable restart retention without a desktop at runtime. Typing and general browser completion remain unavailable; the light dependency-metadata split is still pending.
- **Native apps:** try the [macOS operator example](../../README.md#drive-it), or the
  [Linux Mousepad path](linux-support.md#exact-text-and-document-scope). Linux repeated desktop
  sessions have known native teardown aborts and target-readiness timeouts; current qualification
  remains bounded to the documented cases. Wayland and shared Linux foreground control are unqualified.
- **Agent integration:** the [MCP capability](capability-packaging.md) binds one explicit
  browser-to-document job, with retained operation status and restart recovery. Use the generated
  host configuration in the [agent-host recipe](installed-agent-host.md).
- **OCR, inspection and simulation:** `footwork tools` lists the bundled families and their
  prerequisites. `footwork schema inbox prepare` describes one command. OCR candidates require
  explicit review; simulator evidence does not qualify a physical robot or camera.
- **Machine-readable calls:** `footwork --json tools` returns the discovery envelope. See
  [structured invocation](unified-cli.md#structured-invocation-and-prerequisites) for bounded JSON
  requests and underlying exit codes.
