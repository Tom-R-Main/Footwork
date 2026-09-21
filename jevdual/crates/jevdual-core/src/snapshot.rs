//! R2: DOMSnapshot lookup (port of `browser_use/dom/enhanced_snapshot.py`).
//!
//! `snapshot_lookup_impl` is the pure-Rust body over flat arrays; the
//! `#[pyfunction] snapshot_lookup_flat` wrapper reads the raw CDP
//! `DOMSnapshot.captureSnapshot` dict, runs the body with the interpreter
//! detached, and returns parallel arrays keyed by backend node id. The Python
//! adapter `jevdual._adapters.snapshot_lookup` rebuilds browser-use's
//! `EnhancedSnapshotNode` dataclasses from those arrays.
//!
//! Every upstream rule is reproduced: first-occurrence layout index for a
//! duplicated `nodeIndex`, device-pixel-ratio division of `bounds` only,
//! raw `clientRects`/`scrollRects`, the ten required computed styles in order,
//! `inputValue` then `textValue` with the sensitive-input filter (type
//! password/file/hidden, autocomplete `cc-*` / `one-time-code`), and the
//! None-vs-False distinction for `isClickable` / `inputChecked` when the rare
//! data block is absent.

use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyFloat, PyInt, PyList, PyString};

/// Number of computed styles browser-use requests (`REQUIRED_COMPUTED_STYLES`);
/// `cursor` is the seventh.
pub const REQUIRED_STYLE_COUNT: usize = 10;
const CURSOR_STYLE_SLOT: usize = 6;
const SENSITIVE_INPUT_TYPES: [&str; 3] = ["password", "file", "hidden"];
const SENSITIVE_AUTOCOMPLETE_PREFIXES: [&str; 2] = ["cc-", "one-time-code"];

/// One document's arrays. String-valued fields are indices into the shared
/// strings table; only their bounds matter here, except for the sensitive
/// check, which is resolved before the input is built (see `sensitive`).
#[derive(Debug, Default, Clone)]
pub struct DocumentInput {
    pub backend_node_ids: Vec<i64>,
    /// Present iff the snapshot carried an `isClickable` block.
    pub clickable: Option<Vec<i64>>,
    /// (snapshot index, string index) pairs from `inputValue` then `textValue`,
    /// already filtered for sensitive inputs and string-table bounds.
    pub input_values: Vec<(i64, i64)>,
    /// Present iff the snapshot carried an `inputChecked` block.
    pub checked: Option<Vec<i64>>,
    pub node_index: Vec<i64>,
    pub bounds: Vec<Vec<f64>>,
    pub styles: Vec<Vec<i64>>,
    pub paint_orders: Vec<i64>,
    pub stacking_contexts: Vec<i64>,
    pub client_rects: Vec<Vec<f64>>,
    pub scroll_rects: Vec<Vec<f64>>,
}

/// Parallel arrays, one entry per backend node id (last write wins across
/// documents, as in upstream's dict assignment). Sentinel `-1` means None for
/// integer fields; `has_*` flags gate the rect arrays (4 values per node).
#[derive(Debug, Default, Clone, PartialEq)]
pub struct SnapshotOutput {
    pub ids: Vec<i64>,
    /// -1 None, 0 false, 1 true.
    pub clickable: Vec<i8>,
    /// String index of the cursor style, or -1.
    pub cursor: Vec<i64>,
    pub has_bounds: Vec<bool>,
    pub bounds: Vec<f64>,
    pub has_client_rect: Vec<bool>,
    pub client_rects: Vec<f64>,
    pub has_scroll_rect: Vec<bool>,
    pub scroll_rects: Vec<f64>,
    /// `REQUIRED_STYLE_COUNT` string indices per node, -1 when that slot is absent.
    pub styles: Vec<i64>,
    pub paint_order: Vec<i64>,
    pub stacking_context: Vec<i64>,
    /// String index of the (non-sensitive) input value, or -1.
    pub input_value: Vec<i64>,
    /// -1 None, 0 false, 1 true.
    pub input_checked: Vec<i8>,
}

/// Upstream `_is_sensitive_input`: true for password/file/hidden inputs and
/// payment or one-time-code autocomplete fields. `attrs` are the node's
/// lowercased (name, value) attribute pairs.
#[must_use]
pub fn is_sensitive_input<'a>(attrs: impl IntoIterator<Item = (&'a str, &'a str)>) -> bool {
    for (name, value) in attrs {
        if name == "type" && SENSITIVE_INPUT_TYPES.contains(&value) {
            return true;
        }
        if name == "autocomplete"
            && SENSITIVE_AUTOCOMPLETE_PREFIXES
                .iter()
                .any(|p| value.starts_with(p))
        {
            return true;
        }
    }
    false
}

struct Entry {
    clickable: i8,
    cursor: i64,
    bounds: Option<[f64; 4]>,
    client: Option<[f64; 4]>,
    scroll: Option<[f64; 4]>,
    styles: [i64; REQUIRED_STYLE_COUNT],
    paint_order: i64,
    stacking: i64,
    input_value: i64,
    input_checked: i8,
}

fn rect(v: &[f64]) -> Option<[f64; 4]> {
    (v.len() >= 4).then(|| [v[0], v[1], v[2], v[3]])
}

/// Pure-Rust body: no Python objects, safe to run detached from the interpreter.
#[must_use]
pub fn snapshot_lookup_impl(
    docs: &[DocumentInput],
    strings_len: usize,
    device_pixel_ratio: f64,
) -> SnapshotOutput {
    let mut order: Vec<i64> = Vec::new();
    let mut entries: HashMap<i64, Entry> = HashMap::new();

    for doc in docs {
        // backend id -> snapshot index; a repeated id keeps its LAST index (dict assignment).
        let mut backend_to_snapshot: Vec<(i64, i64)> =
            Vec::with_capacity(doc.backend_node_ids.len());
        let mut seen: HashMap<i64, usize> = HashMap::with_capacity(doc.backend_node_ids.len());
        for (i, &bid) in doc.backend_node_ids.iter().enumerate() {
            match seen.get(&bid) {
                Some(&pos) => backend_to_snapshot[pos].1 = i as i64,
                None => {
                    seen.insert(bid, backend_to_snapshot.len());
                    backend_to_snapshot.push((bid, i as i64));
                }
            }
        }

        // snapshot index -> FIRST layout index.
        let mut layout_index: HashMap<i64, usize> = HashMap::with_capacity(doc.node_index.len());
        for (layout_idx, &node_idx) in doc.node_index.iter().enumerate() {
            layout_index.entry(node_idx).or_insert(layout_idx);
        }

        let clickable_set: Option<std::collections::HashSet<i64>> =
            doc.clickable.as_ref().map(|v| v.iter().copied().collect());
        let checked_set: Option<std::collections::HashSet<i64>> =
            doc.checked.as_ref().map(|v| v.iter().copied().collect());
        let mut input_value_by_index: HashMap<i64, i64> = HashMap::new();
        for &(idx, string_idx) in &doc.input_values {
            if string_idx >= 0 && (string_idx as usize) < strings_len {
                input_value_by_index.insert(idx, string_idx);
            }
        }

        for &(bid, snap_idx) in &backend_to_snapshot {
            let mut e = Entry {
                clickable: clickable_set
                    .as_ref()
                    .map_or(-1, |s| i8::from(s.contains(&snap_idx))),
                cursor: -1,
                bounds: None,
                client: None,
                scroll: None,
                styles: [-1; REQUIRED_STYLE_COUNT],
                paint_order: -1,
                stacking: -1,
                input_value: input_value_by_index.get(&snap_idx).copied().unwrap_or(-1),
                input_checked: checked_set
                    .as_ref()
                    .map_or(-1, |s| i8::from(s.contains(&snap_idx))),
            };
            if let Some(&li) = layout_index.get(&snap_idx) {
                if li < doc.bounds.len() {
                    if let Some(b) = rect(&doc.bounds[li]) {
                        e.bounds = Some(b.map(|v| v / device_pixel_ratio));
                    }
                    if li < doc.styles.len() {
                        for (i, &si) in doc.styles[li].iter().enumerate().take(REQUIRED_STYLE_COUNT)
                        {
                            if si >= 0 && (si as usize) < strings_len {
                                e.styles[i] = si;
                            }
                        }
                        e.cursor = e.styles[CURSOR_STYLE_SLOT];
                    }
                    if li < doc.paint_orders.len() {
                        e.paint_order = doc.paint_orders[li];
                    }
                    if li < doc.client_rects.len() {
                        e.client = rect(&doc.client_rects[li]);
                    }
                    if li < doc.scroll_rects.len() {
                        e.scroll = rect(&doc.scroll_rects[li]);
                    }
                    if li < doc.stacking_contexts.len() {
                        e.stacking = doc.stacking_contexts[li];
                    }
                }
            }
            if entries.insert(bid, e).is_none() {
                order.push(bid);
            }
        }
    }

    let n = order.len();
    let mut out = SnapshotOutput {
        ids: Vec::with_capacity(n),
        clickable: Vec::with_capacity(n),
        cursor: Vec::with_capacity(n),
        has_bounds: Vec::with_capacity(n),
        bounds: Vec::with_capacity(4 * n),
        has_client_rect: Vec::with_capacity(n),
        client_rects: Vec::with_capacity(4 * n),
        has_scroll_rect: Vec::with_capacity(n),
        scroll_rects: Vec::with_capacity(4 * n),
        styles: Vec::with_capacity(REQUIRED_STYLE_COUNT * n),
        paint_order: Vec::with_capacity(n),
        stacking_context: Vec::with_capacity(n),
        input_value: Vec::with_capacity(n),
        input_checked: Vec::with_capacity(n),
    };
    fn push_rect(has: &mut Vec<bool>, vals: &mut Vec<f64>, r: Option<[f64; 4]>) {
        has.push(r.is_some());
        vals.extend_from_slice(&r.unwrap_or([0.0; 4]));
    }
    for bid in order {
        let e = &entries[&bid];
        out.ids.push(bid);
        out.clickable.push(e.clickable);
        out.cursor.push(e.cursor);
        push_rect(&mut out.has_bounds, &mut out.bounds, e.bounds);
        push_rect(&mut out.has_client_rect, &mut out.client_rects, e.client);
        push_rect(&mut out.has_scroll_rect, &mut out.scroll_rects, e.scroll);
        out.styles.extend_from_slice(&e.styles);
        out.paint_order.push(e.paint_order);
        out.stacking_context.push(e.stacking);
        out.input_value.push(e.input_value);
        out.input_checked.push(e.input_checked);
    }
    out
}

// ---------------------------------------------------------------------------
// Python boundary: reading the raw CDP dict.
// ---------------------------------------------------------------------------

/// How the wrapper reads the nested CDP lists.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Strategy {
    /// Manual iteration with `cast` (guide: "extract versus cast").
    Cast,
    /// Generic `extract::<Vec<Vec<_>>>()`.
    Extract,
}

fn get<'py>(d: &Bound<'py, PyDict>, key: &str) -> PyResult<Option<Bound<'py, PyAny>>> {
    match d.get_item(key)? {
        Some(v) if !v.is_none() => Ok(Some(v)),
        _ => Ok(None),
    }
}

fn as_f64(v: &Bound<'_, PyAny>) -> PyResult<f64> {
    if let Ok(f) = v.cast::<PyFloat>() {
        return Ok(f.value());
    }
    if let Ok(i) = v.cast::<PyInt>() {
        return i.extract::<i64>().map(|x| x as f64);
    }
    v.extract::<f64>()
}

fn as_i64(v: &Bound<'_, PyAny>) -> PyResult<i64> {
    if let Ok(i) = v.cast::<PyInt>() {
        return i.extract::<i64>();
    }
    v.extract::<i64>()
}

fn list_i64(v: Option<Bound<'_, PyAny>>, strategy: Strategy) -> PyResult<Vec<i64>> {
    let Some(v) = v else { return Ok(Vec::new()) };
    match strategy {
        Strategy::Extract => v.extract::<Vec<i64>>(),
        Strategy::Cast => {
            let list = v.cast::<PyList>()?;
            let mut out = Vec::with_capacity(list.len());
            for item in list.iter() {
                out.push(as_i64(&item)?);
            }
            Ok(out)
        }
    }
}

fn list_list_i64(v: Option<Bound<'_, PyAny>>, strategy: Strategy) -> PyResult<Vec<Vec<i64>>> {
    let Some(v) = v else { return Ok(Vec::new()) };
    match strategy {
        Strategy::Extract => v.extract::<Vec<Vec<i64>>>(),
        Strategy::Cast => {
            let list = v.cast::<PyList>()?;
            let mut out = Vec::with_capacity(list.len());
            for item in list.iter() {
                out.push(list_i64(Some(item), strategy)?);
            }
            Ok(out)
        }
    }
}

fn list_list_f64(v: Option<Bound<'_, PyAny>>, strategy: Strategy) -> PyResult<Vec<Vec<f64>>> {
    let Some(v) = v else { return Ok(Vec::new()) };
    match strategy {
        Strategy::Extract => v.extract::<Vec<Vec<f64>>>(),
        Strategy::Cast => {
            let list = v.cast::<PyList>()?;
            let mut out = Vec::with_capacity(list.len());
            for item in list.iter() {
                let inner = item.cast::<PyList>()?;
                let mut row = Vec::with_capacity(inner.len());
                for x in inner.iter() {
                    row.push(as_f64(&x)?);
                }
                out.push(row);
            }
            Ok(out)
        }
    }
}

/// `rare.index` of a rare-data block, or None when the block is absent.
fn rare_index(
    nodes: &Bound<'_, PyDict>,
    key: &str,
    strategy: Strategy,
) -> PyResult<Option<Vec<i64>>> {
    match get(nodes, key)? {
        None => Ok(None),
        Some(block) => {
            let block = block.cast::<PyDict>()?;
            Ok(Some(list_i64(get(block, "index")?, strategy)?))
        }
    }
}

/// Lowercased (name, value) attribute pairs of one snapshot node, skipping
/// out-of-range indices exactly as upstream does.
fn node_attributes(
    strings: &Bound<'_, PyList>,
    attribute_lists: Option<&Bound<'_, PyList>>,
    snapshot_index: usize,
) -> PyResult<Vec<(String, String)>> {
    let Some(lists) = attribute_lists else {
        return Ok(Vec::new());
    };
    if snapshot_index >= lists.len() {
        return Ok(Vec::new());
    }
    let indices = lists.get_item(snapshot_index)?;
    let indices = indices.cast::<PyList>()?;
    let n = strings.len();
    let mut out = Vec::new();
    let vals: Vec<i64> = indices
        .iter()
        .map(|x| as_i64(&x))
        .collect::<PyResult<_>>()?;
    for pair in vals.chunks(2) {
        if pair.len() < 2 {
            break;
        }
        let (ni, vi) = (pair[0], pair[1]);
        if ni < 0 || vi < 0 || ni as usize >= n || vi as usize >= n {
            continue;
        }
        let name = strings
            .get_item(ni as usize)?
            .cast::<PyString>()?
            .to_str()?
            .to_lowercase();
        let value = strings
            .get_item(vi as usize)?
            .cast::<PyString>()?
            .to_str()?
            .to_lowercase();
        out.push((name, value));
    }
    Ok(out)
}

fn read_document(
    doc: &Bound<'_, PyDict>,
    strings: &Bound<'_, PyList>,
    strategy: Strategy,
) -> PyResult<DocumentInput> {
    let nodes = doc
        .get_item("nodes")?
        .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("nodes"))?;
    let nodes = nodes.cast::<PyDict>()?.clone();
    let layout = doc
        .get_item("layout")?
        .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("layout"))?;
    // Upstream treats a falsy layout as "no nodeIndex".
    let layout: Option<Bound<'_, PyDict>> = match layout.cast::<PyDict>() {
        Ok(d) if !d.is_empty() => Some(d.clone()),
        _ => None,
    };

    let strings_len = strings.len();
    let attribute_lists = match get(&nodes, "attributes")? {
        Some(a) => Some(a.cast::<PyList>()?.clone()),
        None => None,
    };

    // inputValue then textValue; later writes win; sensitive inputs never enter.
    let mut input_values: Vec<(i64, i64)> = Vec::new();
    for key in ["inputValue", "textValue"] {
        let Some(block) = get(&nodes, key)? else {
            continue;
        };
        let block = block.cast::<PyDict>()?;
        let idx = list_i64(get(block, "index")?, strategy)?;
        let val = list_i64(get(block, "value")?, strategy)?;
        for (&i, &s) in idx.iter().zip(val.iter()) {
            if s < 0 || s as usize >= strings_len {
                continue;
            }
            if i < 0 {
                continue;
            }
            let attrs = node_attributes(strings, attribute_lists.as_ref(), i as usize)?;
            if is_sensitive_input(attrs.iter().map(|(a, b)| (a.as_str(), b.as_str()))) {
                continue;
            }
            input_values.push((i, s));
        }
    }

    let mut input = DocumentInput {
        backend_node_ids: list_i64(get(&nodes, "backendNodeId")?, strategy)?,
        clickable: rare_index(&nodes, "isClickable", strategy)?,
        input_values,
        checked: rare_index(&nodes, "inputChecked", strategy)?,
        ..DocumentInput::default()
    };
    if let Some(layout) = layout {
        input.node_index = list_i64(get(&layout, "nodeIndex")?, strategy)?;
        input.bounds = list_list_f64(get(&layout, "bounds")?, strategy)?;
        input.styles = list_list_i64(get(&layout, "styles")?, strategy)?;
        input.paint_orders = list_i64(get(&layout, "paintOrders")?, strategy)?;
        input.client_rects = list_list_f64(get(&layout, "clientRects")?, strategy)?;
        input.scroll_rects = list_list_f64(get(&layout, "scrollRects")?, strategy)?;
        input.stacking_contexts = match get(&layout, "stackingContexts")? {
            Some(sc) => list_i64(get(sc.cast::<PyDict>()?, "index")?, strategy)?,
            None => Vec::new(),
        };
    }
    Ok(input)
}

/// Read a raw `DOMSnapshot.captureSnapshot` result and return parallel arrays
/// keyed by backend node id (see `SnapshotOutput`). `strategy` is `"cast"`
/// (default) or `"extract"`, kept so the two input-reading paths can be measured.
#[pyfunction]
#[pyo3(signature = (snapshot, device_pixel_ratio = 1.0, strategy = "cast"))]
pub fn snapshot_lookup_flat<'py>(
    py: Python<'py>,
    snapshot: &Bound<'py, PyDict>,
    device_pixel_ratio: f64,
    strategy: &str,
) -> PyResult<Bound<'py, PyDict>> {
    let strategy = match strategy {
        "cast" => Strategy::Cast,
        "extract" => Strategy::Extract,
        other => {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "unknown strategy {other:?}"
            )));
        }
    };
    let strings = get(snapshot, "strings")?
        .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("strings"))?
        .cast::<PyList>()?
        .clone();
    let mut docs: Vec<DocumentInput> = Vec::new();
    if let Some(documents) = get(snapshot, "documents")? {
        for doc in documents.cast::<PyList>()?.iter() {
            docs.push(read_document(doc.cast::<PyDict>()?, &strings, strategy)?);
        }
    }
    let strings_len = strings.len();
    let out = py.detach(|| snapshot_lookup_impl(&docs, strings_len, device_pixel_ratio));

    let result = PyDict::new(py);
    result.set_item(pyo3::intern!(py, "ids"), out.ids)?;
    result.set_item(pyo3::intern!(py, "clickable"), out.clickable)?;
    result.set_item(pyo3::intern!(py, "cursor"), out.cursor)?;
    result.set_item(pyo3::intern!(py, "has_bounds"), out.has_bounds)?;
    result.set_item(pyo3::intern!(py, "bounds"), out.bounds)?;
    result.set_item(pyo3::intern!(py, "has_client_rect"), out.has_client_rect)?;
    result.set_item(pyo3::intern!(py, "client_rects"), out.client_rects)?;
    result.set_item(pyo3::intern!(py, "has_scroll_rect"), out.has_scroll_rect)?;
    result.set_item(pyo3::intern!(py, "scroll_rects"), out.scroll_rects)?;
    result.set_item(pyo3::intern!(py, "styles"), out.styles)?;
    result.set_item(pyo3::intern!(py, "paint_order"), out.paint_order)?;
    result.set_item(pyo3::intern!(py, "stacking_context"), out.stacking_context)?;
    result.set_item(pyo3::intern!(py, "input_value"), out.input_value)?;
    result.set_item(pyo3::intern!(py, "input_checked"), out.input_checked)?;
    result.set_item(pyo3::intern!(py, "style_count"), REQUIRED_STYLE_COUNT)?;
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sensitive_filter_matches_upstream_rules() {
        assert!(is_sensitive_input([("type", "password")]));
        assert!(is_sensitive_input([("type", "file")]));
        assert!(is_sensitive_input([("type", "hidden")]));
        assert!(is_sensitive_input([("autocomplete", "cc-number")]));
        assert!(is_sensitive_input([("autocomplete", "one-time-code")]));
        assert!(is_sensitive_input([
            ("name", "q"),
            ("autocomplete", "cc-csc")
        ]));
        assert!(!is_sensitive_input([("type", "text")]));
        assert!(!is_sensitive_input([
            ("type", "email"),
            ("autocomplete", "username")
        ]));
        assert!(!is_sensitive_input([("autocomplete", "ccx")]));
        assert!(!is_sensitive_input(std::iter::empty()));
    }

    fn doc() -> DocumentInput {
        DocumentInput {
            backend_node_ids: vec![10, 11, 12, 11],
            clickable: Some(vec![1]),
            input_values: vec![(1, 5), (3, 6)],
            checked: None,
            node_index: vec![0, 1, 1, 3],
            bounds: vec![
                vec![0.0, 0.0, 100.0, 50.0],
                vec![2.0, 4.0, 6.0, 8.0],
                vec![9.0, 9.0, 9.0, 9.0],
                vec![1.0],
            ],
            styles: vec![
                vec![],
                vec![0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11],
                vec![],
                vec![99],
            ],
            paint_orders: vec![0, 1, 2],
            stacking_contexts: vec![0, 0],
            client_rects: vec![vec![], vec![1.0, 1.0, 1.0, 1.0]],
            scroll_rects: vec![vec![], vec![]],
        }
    }

    #[test]
    fn last_backend_index_wins_and_first_layout_index_wins() {
        let out = snapshot_lookup_impl(&[doc()], 12, 2.0);
        assert_eq!(out.ids, vec![10, 11, 12]);
        // backend 11 appears at snapshot indices 1 and 3; the last (3) wins, whose layout
        // index is 3 (bounds too short -> no bounds, styles index 99 out of range).
        let i11 = 1;
        assert!(!out.has_bounds[i11]);
        assert_eq!(out.input_value[i11], 6);
        assert_eq!(out.clickable[i11], 0);
        assert_eq!(&out.styles[i11 * 10..i11 * 10 + 10], &[-1; 10]);
        // backend 10 -> snapshot 0 -> layout 0, bounds divided by dpr 2.
        assert!(out.has_bounds[0]);
        assert_eq!(&out.bounds[0..4], &[0.0, 0.0, 50.0, 25.0]);
        assert_eq!(out.clickable[0], 0);
        assert_eq!(out.input_checked[0], -1);
        // backend 12 -> snapshot 2 -> no layout entry.
        assert!(!out.has_bounds[2]);
        assert_eq!(out.paint_order[2], -1);
    }

    #[test]
    fn styles_take_ten_and_cursor_is_slot_six() {
        let mut d = doc();
        d.backend_node_ids = vec![1];
        d.node_index = vec![0];
        d.bounds = vec![vec![0.0, 0.0, 1.0, 1.0]];
        d.styles = vec![vec![0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11]];
        d.clickable = None;
        d.input_values = vec![];
        let out = snapshot_lookup_impl(&[d], 12, 1.0);
        assert_eq!(&out.styles[0..10], &[0, 1, 2, 3, 4, 5, 7, 8, 9, 10]);
        assert_eq!(out.cursor[0], 7);
        assert_eq!(out.clickable[0], -1);
    }
}
