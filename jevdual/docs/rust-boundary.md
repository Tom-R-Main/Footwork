# Rust boundary rules

The native extension (`crates/jevdual-core`, published as `jevdual._core`) exists for one
reason: measured hot paths in the DOM pipeline. Every function it exports has a pure-Python
twin, and the two are held equal by tests over recorded CDP fixtures. This page is the
contract for adding a port. PyO3 references are to the 0.29 guide (https://pyo3.rs/main/).

## Boundary

- **Flat in, flat out.** Pass flat arrays (`Vec<f64>`, `Vec<u32>`, `&[u8]`) or bytes into
  Rust, and return flat arrays or one immutable `#[pyclass]`. Never build one Python object
  per DOM node inside Rust; that is the cost the port is removing.
- **`cast`, not `extract`, for native types.** `extract` converts a downcast failure into a
  `PyErr`, which is expensive on polymorphic paths; `cast` avoids it (guide: Performance,
  "extract versus cast").
- **`intern!` repeated keys.** Every `&str` to `PyString` conversion allocates; use
  `pyo3::intern!(py, "key")` for dict keys and attribute names reused per call site.
- **Detach for CPU.** Wrap any section over about 1 ms in `Python::detach` (formerly
  `allow_threads`) so other threads can run; nothing inside may touch Python objects.
- **Free-threaded ready.** Exported `#[pyclass]` types are immutable, `Send + Sync`, with no
  interior mutability. Since PyO3 0.28 `#[pymodule]` attests thread-safety by default
  (guide: Supporting Free-Threaded CPython); we keep that default, so a port that needs
  `gil_used = true` must justify it in review.
- **Errors are `PyResult`.** Translate every failure into a typed Python exception; a panic
  across the FFI boundary is a bug.
- **Keep the Rust body callable without Python.** Put the algorithm in a plain `pub fn` at
  the crate root (see `ping_impl`) and have the `#[pyfunction]` wrap it; benches and unit
  tests then run without an interpreter, and the `rlib` crate type exposes it to
  `benches/`.

## Equality contract

- `python/jevdual/_native.py` holds `FUNCTIONS`, the registry of hot paths: name ->
  (pure module, attribute). `native_or_pure(name)` resolves to the native export when the
  extension is loaded and provides that attribute, otherwise to the pure twin, logging the
  fallback once. `backend_report()` is written into every trace header.
- The Python-level signature of the twin is the contract. If the Rust side wants flat
  arrays, put the flattening adapter in `_native.py` (or a small Python wrapper) so callers
  never branch on backend.
- `JEVDUAL_PURE_PY=1` forces pure Python for everything (the extension is not even
  imported). CI runs the suite in both modes.
- `tests/equality/` parametrizes over every fixture in `tests/fixtures/cdp/`. A test for a
  port that is not built yet **skips** with reason `native not built for <name>`; it must
  never silently pass. `diff_report` prints the first ten field-level differences instead
  of a bare assert.
- Tree-based ports (paint order, hashing) need the pre-paint-order simplified tree, rebuilt
  from a fixture by `tests/fixtures/replay.py` (task C1) plus
  `DOMTreeSerializer._create_simplified_tree`; the harness skips with reason
  `replay helper not available` until that helper exists.

## Benchmarks

- Rust: `cargo bench -p jevdual-core` (criterion, `benches/hot_paths.rs`). Release profile
  is `lto = "fat"`, `codegen-units = 1`.
- Python: `JEVDUAL_BENCH=1 uv run pytest tests/bench -q` (pytest-benchmark). Bench tests
  are skipped by default so the ordinary suite stays fast. Record baselines in `results/`
  before a port and after it, with fixture name, median, and variance.

## Adding a port (four steps)

1. **Twin first.** Write `python/jevdual/_pure/<name>.py` exposing `<name>(...)` with the
   upstream semantics (wrap browser-use where it exists), register it in `FUNCTIONS`, and
   add `tests/equality/test_<name>.py` with a pure-vs-pure determinism test and a
   pure-vs-native test that skips until built. Add a baseline to `tests/bench/`.
2. **Rust body.** Implement `pub fn <name>_impl(...)` at the crate root over flat inputs,
   with unit and `proptest` property tests, and a criterion group in `benches/hot_paths.rs`.
3. **Export.** Add the `#[pyfunction] <name>` wrapper inside `mod _core`, plus any adapter
   in `_native.py` that flattens the twin's inputs. `maturin develop --release`.
4. **Prove it.** `uv run pytest tests/equality -q` green on every fixture in both modes,
   then record the before/after numbers in `results/<task>-<name>.md`.
