# Exact passive HelpTag ordinary-window classification

Prediction: `5c1e6af`. The actual public CLI red is retained in the parent Studio
run; a transient same-PID layer-0 AXHelpTag displaced the requested ordinary window
in the SDK ranking despite correct process/key proof. The empty-action hypothesis
was disproved before this package: the actual tag has one AXRaise action.

The additive two-file Rust repair keeps activation sequence and independent
process/key/visibility/per-display postconditions unchanged. A competitor is removed
only with unique exact CGID, actual owner PID, literal AXHelpTag role, successful
typed empty/AXRaise-only action array, readable focused=false and successful
focus-settable=false, while the actual requested key window is observed after the
classification reads. Unknown/missing/duplicate/wrong-owner/interactive/action-error
or dialog/window cases remain competitors. A proven HelpTag requested target
refuses before activation in both exact activation entrypoints. No AXRaise action
is executed by the classifier; it performs only metadata reads.

The AX inventory is bounded to64 windows, a100ms census deadline and checked25ms
messaging timeouts; failed timeout configuration/read/type proof supplies no
exclusion. Action arrays are checked CFArray/CFString values with bounded counts;
failed action reads never become empty lists. Focus-settable errors never become
false. No host partial-result override or fallback is added.

Source archive SHA256:
`938800555df9485aa4ed800a74ef795d05575efdbdea9c5f4ce6f6dd61b02fda`.
Project overlay version: `0.46.0+footwork.5486b624.cleanup2.focus1.helptag1`.
Wheel SHA256:
`69a8fe983985c99f083438c7d985bcc31f65dce03a72407385219401805b2ad0`.
`runtime.json` binds imported module/native library, six unchanged Python bindings
and matching wheel/build-target native bytes. Historical focus1 overlay hashes are
unchanged. Default pyproject/uv.lock/vendor archive remain focus1; the additive
patch/manifest and builder reconstruct the optional local artifact explicitly.

Validation:

- `rust-red.txt`: two behavioral failures at the owning ranking/target seam.
- `rust-green-final.txt`: five pure classification/CFArray/settable checks pass.
- `rust-observation-final.txt`: fifteen pure exact-activation observation checks
  pass (overlap with three classification tests); real activation tests skipped.
- `overlay-focused.txt`:780 Python/ABI/native/CLI/authority/contracts pass on the
  new overlay; public partial refusal still withholds input. Simulated SDK replies
  are not claimed to test the Rust classifier.
- `build-wheel.txt`, `runtime.json`: final canonical offline build and exact-byte
  import qualification. Ruff, Rustfmt, notebook and diff checks pass.

Rebuild with `scripts/build_cua_helptag_overlay.py` from `jevdual/`; it uses the
unchanged canonical build hook, cached Hatchling1.32.4 and Rust1.97.1 with existing
project cargo-home/target, locked/offline and two jobs. No network or global install
was performed. The default or historical wrappers still use focus1; use the new
manifest-qualified frozen-source wrapper supplied with this candidate.

The parent owns the single final full Python regression and actual public GUI
qualification. The worker did not start a native driver, invoke activation, move
the pointer, type/click, change posture or call private activation probes.
