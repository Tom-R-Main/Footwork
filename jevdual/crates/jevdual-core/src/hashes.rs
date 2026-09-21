//! R3: batched element hashes (port of `EnhancedDOMTreeNode` hash methods).
//!
//! Owned by task R3.

use pyo3::prelude::*;

/// Placeholder until R3 lands.
#[pyfunction]
pub fn element_hashes_flat() -> PyResult<()> {
    Err(pyo3::exceptions::PyNotImplementedError::new_err(
        "element_hashes_flat: task R3",
    ))
}
