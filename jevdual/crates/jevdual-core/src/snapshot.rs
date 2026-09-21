//! R2: DOMSnapshot lookup (port of `browser_use/dom/enhanced_snapshot.py`).
//!
//! Owned by task R2. The Python adapter `jevdual._adapters.snapshot_lookup`
//! passes the raw snapshot arrays and rebuilds `EnhancedSnapshotNode`s.

use pyo3::prelude::*;

/// Placeholder until R2 lands.
#[pyfunction]
pub fn snapshot_lookup_flat() -> PyResult<()> {
    Err(pyo3::exceptions::PyNotImplementedError::new_err(
        "snapshot_lookup_flat: task R2",
    ))
}
