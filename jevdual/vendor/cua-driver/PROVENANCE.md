# CUA Driver source provenance

Source repository: https://github.com/trycua/cua
Reference commit: `5486b6246e4c807c0d793216e52df283671d9362` (release `cua-driver-rs-v0.46.0`).
Source directory: `libs/cua-driver/python/src/cua_driver`.
Python/native version: `0.46.0`. License: upstream MIT (`LICENSE.md`, copied as `LICENSE`).

Footwork distribution version: `0.46.0+footwork.5486b624.cleanup2.focus1.helptag1.connected4.locate5`. The published 0.46.0 wheel does not contain the required shutdown cleanup, foreground text focus, passive HelpTag, connected-node click and ref locate patches and cannot satisfy this exact dependency. The upstream Python `__version__` remains `0.46.0`.

The six Python files are copied byte-for-byte from the exact release source. The published macOS wheel has the same files except that its packaging removes the `x-release-please-version` comment from `__init__.py`. Generated records and native library must always be upgraded together.

| Source file | SHA256 |
| --- | --- |
| `__init__.py` | `968e30886e29ef5fc66316d4bb5aef46a30c9b8f5422635ac48982ab15379ddd` |
| `__main__.py` | `bcb78a6283dc6da69f3338879ae34a0f2dbeea3b444e4c3dd43f170d2922a387` |
| `_daemon.py` | `f6ce97a08ab5c124ba0210b00e44bd652b41cca5a9ae20a511a6409093e8f01e` |
| `_native.py` | `8bb3927dd6579d94468eb5c08b1700230359813074cd1959c2e226c318dd4828` |
| `_native_contract.py` | `f5237aa6dac954ea15959347ddaeb38e99b6df18c6c323093fabe275f27c808f` |
| `wrapper.py` | `cfd7abe6215aab7c1d8f66f2c15e6cd6ab7f150918de7b301b73c253e90a61d6` |

## Source archive

`native-source.tar.gz` SHA256: `0d4105b397b5cb86c23e480487324cfb5a8ce0e6e829bbb6bf7b40987047914a` (6,419,688 bytes). It is the end of a five-step patch chain on the selected release source: cleanup2, focus1, helptag1, connected4, locate5. Each step's manifest under `patches/` binds its base archive, patch, patched archive and changed files by SHA256. The focus1 archive (`804aeb8b2ba5b2b49772250a0435032bd9510835a56a33122d1cab531810cfb2`, 6,403,795 bytes) remains in Git history; `python3 scripts/cua_source_chain.py --base <focus1 archive> --output <file>` rebuilds this archive from it and checks every hash.

The complete upstream release archive has SHA256 `032ce99f2e33154082cf854a1a04213e8a7b9eeae0e524564c7c6adb0ae93112`. The selected, unpatched native archive has SHA256 `257a36f5a793ad66d9c3e276709a7c81b667ed960ca5a3544e2d0ea43678fad1`.

Selection includes `libs/cua-driver/rust`, `libs/cua-driver/wayland-helper`, `libs/cua/Cargo.toml`, `libs/cua/crates/cua-telemetry`, `libs/images/sandbox-images.json`, `libs/cua/crates/cua-teleport/src/ux/targets.json`, and `LICENSE.md`. Only regular source files and their ancestor directories are retained. Tar entries are path-sorted, with zero mtime/uid/gid and empty owner names; source file modes are preserved and directory mode is 0755. The PAX tar is compressed with Python gzip, empty filename, mtime zero, and compression level nine. No build artifacts or unrelated repository files are included.

## Required local cleanup patch

The exact release still spawns untracked browser/grant session-end work and returns from SDK shutdown without awaiting it. The four-file patch retains the previously reviewed cleanup2 implementation: runtime-owned task handles, cancellation-safe joining, completed-handle reaping, sticky abnormal-completion failure, and shutdown drain after session revocation. It does not change authorization predicates, Cargo dependencies or generated bindings. The SDK regression test adds a local AtomicBool import because the newer upstream test module no longer imports it.

`patches/session-cleanup-join.patch` is the inspectable diff against this release. `patches/session-cleanup-join.json` binds the original and patched file hashes and archive hashes. The previous 0.38 cleanup2 provenance, diff and manifest are retained under `history/`; its native archive remains in Git history. Prior qualification does not automatically qualify this newer build.

## Foreground text focus patch

The cleanup-only archive SHA256 is `233149903c53bb1ccdcf84c3693cabc3bcbf8bba4ebc25f3b5a7c60e63540ea4`.
`patches/foreground-text-focus.patch` applies on top of it. Its JSON manifest binds both archive
hashes, the patch hash and the before/after hashes of two private macOS Rust files. The six upstream
Python binding files and Rust dependencies remain unchanged; the four cleanup file hashes still
match the final archive.

The foreground text synthesizer previously ignored failed or lost field focus. The patch waits
for activation settling, then uses the existing bounded confirmed-key-focus helper with the
application's focused element identity immediately before synthesis. Failure returns
`target_focus_unconfirmed`, `effect:refused`, `dispatched:false` and `delivered_chars:0`.
An explicit foreground boolean controls the gate, including zero settling time. Existing
background focus behavior is retained. The guard proves OS field focus, not DOM acceptance or
server persistence. The SDK retains its existing no-retry behavior for uncertain web text.

## Build and qualification

Build the CLI and SDK together with Rust 1.97.1, `--release --locked --jobs 2`, and `CUA_DRIVER_GIT_SHA` set to the complete release commit. Build helpers verify and restore the exact source archive. No published native binary is substituted into the custom distribution. See [`../../docs/upstream/cua-driver-build.md`](../../docs/upstream/cua-driver-build.md).

The published macOS universal2 wheel used only for ABI comparison has SHA256 `80b1be9b9a6aca20d733b10f221f9e478e862cfbcac4ce413ce5af7c141aa46c`. Its successful import establishes matched published bindings, not the required cleanup guarantee. Final qualification must use the custom wheel and retain its checksum.

## Passive HelpTag patch (helptag1)

`patches/ordinary-helptag.patch` and its JSON manifest apply on top of the focus1 archive and
produce archive `938800555df9485aa4ed800a74ef795d05575efdbdea9c5f4ce6f6dd61b02fda`. It was first
qualified as an optional project overlay (`cleanup2.focus1.helptag1`) and is now step three of the
pinned chain. Only positively identified exact owned passive AXHelpTags can be excluded from
ordinary-window ranking; unknown/interactive peers stay ranked and HelpTag targets refuse before
activation. Activation sequence and success predicates are unchanged. Two private macOS Rust files
change; the six Python binding files do not.

## Connected-node click patch (connected4)

`patches/connected-click.patch` and its JSON manifest apply on top of the helptag1 archive and
produce archive `6f673125f9bece9777ef01c42575a93911153c37a19780f02cd40ef68d2fb94a`. A page-route click (`browser_click` with `input_route:"dom_event"`)
resolved its ref's backend node and ran the synthetic click sequence on it even when the page had
removed that node from its document, so a removed button's handlers still ran (Footwork notebook
BH13). The patch reads the node's `isConnected` on the resolved object, bounded by the existing
one-second baseline deadline, and refuses `browser_ref_stale` before any event unless it reads true;
an unreadable check also refuses. That guard runs before awaited scroll, box, cursor and baseline
calls, and a handler can remove the node during the sequence itself (Footwork notebook DC4), so
the sequence also checks, before every event and before the focus move, that the ref's node is
still in its document. It stops at the first check that fails and returns the events it sent:
none sent refuses `browser_ref_stale`; some sent reports an unverifiable partial delivery that
names where it stopped. When the hit-tested descendant leaves the document or the ref's node (an
icon re-rendered inside a button, or moved into another one) the remaining events go to the ref's
node, and the focus candidate is chosen after that check. The sequence counts in local primitives,
not page-replaceable built-ins, and returns an explicit completion receipt; an exception, a missing
value or any malformed receipt is reported as an interrupted, unverifiable click, never as a
confirmed or an undelivered one (Footwork notebook DC8). The click decides from the call helper's
own outcome and one dialog snapshot, so a dialog that interrupted the sequence stays the outcome
even after it closes, and only a completed receipt reaches semantic readback (DC14). A connected node is clicked exactly as
before. Two cua-driver-core browser files change (the tool and its mock-CDP tests); the generated
bindings and dependencies do not. connected1 (the guard alone), connected2 (without the receipt
and containment checks) and connected3 (without the single dialog snapshot) were never released.

## Ref locate patch (locate5)

`patches/ref-locate.patch` and its JSON manifest apply on top of the connected4 archive and produce
the pinned archive. `get_browser_state` gains a third mode: with `target_id`, `tab_id` and
`locate_ref` it returns only a `locate` block for that current ref. It proves the binding and the
ref's document as a click does and refuses a stale or removed node with `browser_ref_stale`, then
only reads: the node's `getBoundingClientRect` and what `elementFromPoint` finds at its centre (the
page-route click sequence's own geometry, in viewport CSS px), the border-box centre from
`DOM.getBoxModel` as a check that runs no page script, and the viewport's zoom and pinch scale from
`Page.getLayoutMetrics`. The same page function reports `clipped`, whether an ancestor that clips or
scrolls its overflow leaves part of the rectangle outside its padding box (the case in which the
click's own `DOM.scrollIntoViewIfNeeded`, or a type's `DOM.focus`, would scroll the target), and
`visibility_state`, the document's; with `locate_point` it also reports what `elementFromPoint`
finds at that point, as `point`. It reports `focused` (the node is the active element of its
document or shadow root) and `page_focused` (its document has focus): when both hold, a type's
`DOM.focus` changes nothing in the page. The connected check and the page function run in an
isolated world of the tab's main frame (`Page.createIsolatedWorld`, named `cua-driver-locate`,
without universal access, the node resolved into its context). That world shares the page's DOM
and none of its script objects, so a page that replaced `elementFromPoint`,
`getBoundingClientRect` or `getComputedStyle` in its own world does not answer for the browser.
The reply says `world: "isolated"`, and is unavailable (`world_unavailable`) when no such world
can be made; nothing is read in the page's own world instead. `Page.createIsolatedWorld` joins
the reviewed method list for personal-profile connections for this read alone: it adds no script
to the page's world and does not outlive the document. That Chrome's isolated world is out of a
page's reach is Chrome's behaviour, which the mock cannot show; Footwork's live probe has a step
for it (notebook FP20). The clip test follows the flat tree, skips the root element, skips
`body` only when its overflow propagates to the viewport (the root's overflow is `visible` and
neither element has containment), and tests every other ancestor whether or not it is the node's
containing block (so it errs toward reporting a clip). Its geometry holds for translation and
scaling by positive factors only, so a node that is, or lies under, an element that is rotated (a
half turn included), skewed, reflected (a negative axis in `transform` or `scale`), transformed in
3D or placed on a motion path is reported unavailable (`transformed`). The mock-CDP tests supply
the page function's result; Footwork's `tests/test_locate_page_function.py` takes the function from
this archive and runs it in Node on stand-in elements. Nothing is scrolled, focused or dispatched and no snapshot is taken; a ref
in a child frame is reported unavailable. The block is geometry for moving a filmed pointer onto a
target (Footwork notebook FP3, FP4), never an action authority. It is not taken from the semantic
snapshot's layout bounds: those are in physical pixels while the viewport metrics are in CSS pixels
(FP3), which also makes the unpatched snapshot's `visibility` unreliable at a device scale factor
other than 1; that upstream behaviour is unchanged here. Three cua-driver-core browser files change
(the tools, their mock-CDP tests and the CDP method list); the generated bindings and dependencies
do not. An earlier
rects1 step (a rectangle on each snapshot ref), locate1 (this step without the clip test, the
visibility state and the point) locate2 (with a body always skipped and no transform check), locate3 (which let a
reflection, a half turn and a motion path through) and locate4 (which read in the page's own
script world and reported no focus) were withdrawn before release.
