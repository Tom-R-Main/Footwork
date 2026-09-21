//! Native hot paths for jevdual.
//!
//! Every function exported here has a pure-Python twin under
//! `python/jevdual/_pure/`, and `tests/equality/` asserts the two agree on the
//! recorded CDP fixtures. Boundary rules live in `docs/rust-boundary.md`: flat
//! arrays or bytes in, flat arrays or one immutable pyclass out, no per-node
//! Python objects created here.

use pyo3::prelude::*;

pub mod evidence;
pub mod hashes;
pub mod paint_order;
pub mod snapshot;

/// Pure-Rust body of `ping`, kept out of the Python module so benches and unit
/// tests can call it without an interpreter.
#[must_use]
pub fn ping_impl(n: u64) -> Option<u64> {
    n.checked_add(1)
}

/// Python module `jevdual._core`.
#[pymodule]
mod _core {
    use pyo3::prelude::*;

    #[pymodule_export]
    use crate::evidence::evidence_match_flat;
    #[pymodule_export]
    use crate::hashes::element_hashes_flat;
    #[pymodule_export]
    use crate::paint_order::paint_order_flat;
    #[pymodule_export]
    use crate::snapshot::snapshot_lookup_flat;

    /// Crate version; the Python shim logs it once so a trace records which backend ran.
    #[pyfunction]
    fn version() -> &'static str {
        env!("CARGO_PKG_VERSION")
    }

    /// Smoke check that the boundary round-trips an integer.
    #[pyfunction]
    fn ping(n: u64) -> PyResult<u64> {
        crate::ping_impl(n)
            .ok_or_else(|| pyo3::exceptions::PyOverflowError::new_err("ping overflow"))
    }
}

#[cfg(test)]
mod tests {
    use super::ping_impl;

    #[test]
    fn version_matches_cargo() {
        assert_eq!(env!("CARGO_PKG_VERSION"), "0.0.1");
    }

    #[test]
    fn ping_overflows_to_none() {
        assert_eq!(ping_impl(1), Some(2));
        assert_eq!(ping_impl(u64::MAX), None);
    }
}
