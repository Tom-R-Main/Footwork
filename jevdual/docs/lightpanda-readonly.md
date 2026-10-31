# Read a page without a desktop

The Lightpanda route gives an agent bounded DOM text from a fresh browser process. It needs no
desktop session, model key, CUA driver or Chrome process at runtime. Website JavaScript can populate
the page before the read, while Footwork exposes no click, typing or raw-script command.

Use it when the agent needs page content and does not need to operate the interface. The observation
names its engine and source, withholds form/editable values, and reports its limits. It does not
pretend DOM text is rendered text or claim that a task is complete.

## Start with the engine pin

After installing Footwork, inspect the artifact for your host:

```sh
footwork browser lightpanda artifact
footwork schema browser lightpanda read
footwork browser lightpanda guide
```

The artifact command reports the external binary name, immutable GitHub asset ID, byte count and
SHA256 expected by this version of Footwork. Provision that binary through your existing artifact
workflow. The command never downloads, installs or builds an engine. A different digest or an
unsupported platform refuses; there is no source-build fallback.

This tranche pins Linux x86-64 and macOS arm64 artifacts. Linux needs a compatible glibc-based host.
The external engine is separate from the Footwork wheel. Footwork's dependency metadata still
declares its full dependencies; the binary-only light metadata split remains a later package.

## Read one URL

```sh
footwork --json browser lightpanda read https://example.org/ \
  --executable /absolute/path/to/lightpanda
```

Alternatively, set `FOOTWORK_LIGHTPANDA_EXECUTABLE` or put the pinned executable on PATH. Doctor
reports its presence and byte-pin match without starting it:

```sh
footwork doctor
```

Each read owns a fresh private Unix socket and one connection. The connected kernel peer must be the
actual launched process and user. Footwork creates a real page target on that connection, loads the
requested HTTP(S) URL, captures the DOM, then closes the connection and stops the original child.
It never substitutes another endpoint or reconnects to a new browser after a failure.

The default capture deadline is 30 seconds. `--timeout` accepts 1–60 seconds, followed by bounded
cleanup. `--work-dir` can select a fresh, short absolute directory; existing directories are refused.
Default temporary storage is removed after verified bounded cleanup and retained when cleanup is
unverified. The private socket and peer checks are cooperative custody, not isolation from arbitrary
code running as the same user.

## What the result means

The structured result separates `capture_completed`, the `observation`, `cleanup`, and `completion`.
It also records the CDP method names sent, without their parameters. Read those fields rather than
using the process exit code as a completion certificate.

| Field | Scope |
| --- | --- |
| `observation.content` and `text` | Bounded DOM content from the capture interval |
| `page` | URL with query/fragment withheld, full-URL digest, and title from the same DOM reply |
| `identity` | Owned process, binary digest, connection, target, session and reported document identifiers |
| `actions: []`, `mutation_authority: false` | No later input is authorized by this observation |
| `complete: false`, `capture.atomic: false` | No whole-page completeness or atomic snapshot claim |
| `completion: not_asserted` | Reading a page does not establish business completion |
| `cleanup.status` | Bounded owned-process cleanup, independently of capture success |

The projector withholds input, textarea, select, editable subtrees and associated form labels. It
omits scripts, styles, templates, embedded frames and shadow roots from content. Query values and
fragments are withheld from emitted page/link URLs. Link destinations are withheld when the DOM
contains a base href, because the engine does not report a qualified effective document base. It does not provide layout, screenshots,
visibility, accessibility equivalence or actionable element refs. CSS-hidden DOM text can remain.

Reported target/frame/root changes during capture refuse. Matching numeric identifiers still does
not prove an atomic or mutation-safe document binding. After cleanup, the result is a saved
observation; a later read starts another browser with fresh state.

## Explicit budgets and boundaries

One browser connection, 4 MiB incoming WebSocket messages, 10,000 DOM nodes, 256 content records,
32,768 text characters and 262,144 serialized observation bytes bound this route. These are limits,
not reserved CPU/RAM or measured performance promises.

Initial URL loading executes website code and may have network effects. “Read-only” describes
Footwork's input surface; it does not promise that a website is side-effect-free. The load event is
the setup boundary, without a claim of complete network idle or all future asynchronous content.

There is no input admission in this profile, so no Jev guard is bypassed. The guarded Chromium route
keeps its own authority protocol. **Typing remains disabled.** A future Lightpanda mutation route
requires separate target, realm, style, guard and independent-effect qualification.

Cleanup uses the actual child handle and a bounded inventory. A killed root can leave cleanup
unverified. Neither a stopped browser nor test-only orphan reaping settles a business effect or
proves that every possible descendant was inventoried.
