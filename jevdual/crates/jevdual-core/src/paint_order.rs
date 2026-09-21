//! R1: paint-order occlusion (port of `browser_use/dom/serializer/paint_order.py`).
//!
//! Owned by task R1. The Python adapter `jevdual._adapters.paint_order` flattens
//! the simplified tree into arrays and calls `paint_order_flat`.

use pyo3::prelude::*;

/// Placeholder until R1 lands; the adapter reports `available() == False` while this raises.
#[pyfunction]
pub fn paint_order_flat() -> PyResult<()> {
    Err(pyo3::exceptions::PyNotImplementedError::new_err(
        "paint_order_flat: task R1",
    ))
}
