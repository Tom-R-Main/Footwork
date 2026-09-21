//! Native hot paths for jevdual.
//!
//! Every function exported here has a pure-Python twin under
//! `python/jevdual/_pure/`, and `tests/equality/` asserts the two agree on the
//! recorded CDP fixtures. Boundary rules: flat arrays or bytes in, flat arrays
//! or one immutable pyclass out, no per-node Python objects created here.

use pyo3::prelude::*;

/// Python module `jevdual._core`.
#[pymodule]
mod _core {
    use pyo3::prelude::*;

    /// Crate version; the Python shim logs it once so a trace records which backend ran.
    #[pyfunction]
    fn version() -> &'static str {
        env!("CARGO_PKG_VERSION")
    }

    /// Smoke check that the boundary round-trips an integer.
    #[pyfunction]
    fn ping(n: u64) -> PyResult<u64> {
        n.checked_add(1)
            .ok_or_else(|| pyo3::exceptions::PyOverflowError::new_err("ping overflow"))
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn version_matches_cargo() {
        assert_eq!(env!("CARGO_PKG_VERSION"), "0.0.1");
    }
}
