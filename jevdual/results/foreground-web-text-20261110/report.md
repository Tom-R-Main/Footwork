# Explicit guarded foreground web type

The old native web route always requested background text delivery. The pinned CUA foreground
synthesizer also ignored unverified field focus. This candidate adds an explicit macOS native
type route and a fail-closed addressed-field guard in the pinned native implementation.

Prediction commits: b2548ca and ecd7375. Source archive SHA256:
`804aeb8b2ba5b2b49772250a0435032bd9510835a56a33122d1cab531810cfb2`.
Distribution: `cua-driver==0.46.0+footwork.5486b624.cleanup2.focus1`.
Wheel SHA256: `22083ce34aa45a2404bda2b27ad120156c7380da8a659879e00df139a69393ec`.

## Behavior and boundaries

`do type TARGET TEXT --web-text-delivery foreground` requires the new exact runtime, a native
macOS web field, a foreground posture and normal action gates. Shared foreground still requires
three seconds without human input. Browser mode, ordinary operations, file selectors, append,
mixed browser-route options, background-only posture and explicit no-judge refuse the option.

The transaction activates the exact window, reobserves and revalidates target identity/value,
then uses token-bound foreground Select All for replacement. A fresh observation and direct
AX value/full selected-range check must still agree before typing. Missing readable values are
never assumed empty. The CUA synthesizer proves addressed field focus after activation settling,
using an explicit foreground boolean so zero settling cannot skip the guard.

The strict route supplies positive character pacing. This disables the pinned SDK's batched
partial-tail retry even when incomplete ancestry makes web classification unavailable. The
Footwork transaction never retries after uncertain selection or text delivery. A structured SDK
zero-text refusal is retained separately when earlier preparation input makes the global operation
uncertain. Neither transport acknowledgment nor AX agreement proves DOM/server acceptance.

## Evidence

- `rust-red.txt`: three synthesis-boundary failures before the native fix.
- `rust-green.txt`:33 focused Rust tests pass, including focus error, unverified/lost focus,
  zero-settle foreground, one successful dispatch, structured zero-text refusal and unchanged background behavior.
- `python-red.txt`: the old public CLI rejects the missing opt-in option.
- `review-red.txt`: both unreadable-value and batched-tail review counterexamples fail before follow-up.
- `overlay-contracts.txt`:84 final focused CLI, ABI and source provenance tests pass on the exact overlay.
- `affected.txt`:407 affected tests passed at an earlier integration boundary; this is not the full default suite.
- `runtime.json`: exact loaded module/library paths, wheel/native/binding hashes and version gate.
- `build-native.txt` and `build-wheel.txt`: offline native release build and canonical Hatchling build hook.

The scoped UV resolver lacked Hatchling metadata, but the exact Hatchling1.32.4 and dependencies
were already present as extracted project-cache archives. The standard PEP517 build_wheel backend
was invoked from those cached modules, retaining the existing source-verifying native build hook.
There was no download, manual wheel repack, global installation, or generated ABI change. The four
cleanup2 native file hashes remain unchanged; the additional two-file patch and hash chain are in
vendor/cua-driver/patches/foreground-text-focus.{patch,json}.

## Root verification handoff

Project-local executable:

```sh
/Users/thomasmain/projects/footwork/jevdual/output/foreground-web-text/footwork
```

Full default offline suite, without syncing or changing the global installed release:

```sh
cd /Users/thomasmain/projects/footwork/jevdual
PYTHONPATH=/Users/thomasmain/projects/footwork/jevdual/output/foreground-web-text/overlay:/Users/thomasmain/projects/footwork/jevdual/python .venv/bin/python -m pytest -q
```

The overlay is project-local under output/foreground-web-text/overlay; the wrapper imports that CUA
package and the current checkout. Root must establish the frozen source commit, fresh target and
existing authorization before SUN11 live input. The worker performed no live UI actions. Live
Suno renderer acceptance, save/reopen behavior and musical quality remain unverified here.
