//! R1: paint-order occlusion, a port of `browser_use/dom/serializer/paint_order.py`.
//!
//! The Python adapter `jevdual._adapters.paint_order` walks the simplified tree
//! once (pre-order, the same order upstream's `collect_paint_order` uses) and
//! hands this module flat parallel arrays. Everything below is pure Rust; the
//! only Python object is the argument tuple at the boundary.
//!
//! Semantics reproduced exactly from upstream, including the parts the plan did
//! not spell out:
//! * groups are processed by descending paint order; inside a group every
//!   `contains` check runs before any `add`, and the adds are applied per
//!   document context in first-seen order, then per rect in node order;
//! * `RectUnion` stops accepting rects at 5000 and `contains` is the exact
//!   rectangle-subtraction test, so fragmentation order matters only through
//!   that cap, which is why node order is preserved end to end;
//! * a node whose background is transparent or whose opacity is below 0.8 is
//!   still tested for occlusion but never added to the union (the adapter
//!   evaluates that CSS rule in Python and passes a flag).

use pyo3::prelude::*;

/// Upstream `RectUnionPure._MAX_RECTS`.
pub const MAX_RECTS: usize = 5000;

/// Closed axis-aligned rectangle, `(x1, y1)` to `(x2, y2)`.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Rect {
    pub x1: f64,
    pub y1: f64,
    pub x2: f64,
    pub y2: f64,
}

impl Rect {
    #[must_use]
    pub const fn new(x1: f64, y1: f64, x2: f64, y2: f64) -> Self {
        Self { x1, y1, x2, y2 }
    }

    /// Upstream `Rect.intersects`: open on the shared edge.
    #[must_use]
    pub fn intersects(&self, o: &Rect) -> bool {
        !(self.x2 <= o.x1 || o.x2 <= self.x1 || self.y2 <= o.y1 || o.y2 <= self.y1)
    }

    /// Upstream `Rect.contains`: closed comparison.
    #[must_use]
    pub fn contains(&self, o: &Rect) -> bool {
        self.x1 <= o.x1 && self.y1 <= o.y1 && self.x2 >= o.x2 && self.y2 >= o.y2
    }
}

/// Up to four pieces of `a \ b`, in upstream's order (bottom, top, left, right).
/// Assumes `a` intersects `b`.
fn split_diff(a: &Rect, b: &Rect, out: &mut Vec<Rect>) {
    if a.y1 < b.y1 {
        out.push(Rect::new(a.x1, a.y1, a.x2, b.y1));
    }
    if b.y2 < a.y2 {
        out.push(Rect::new(a.x1, b.y2, a.x2, a.y2));
    }
    let y_lo = a.y1.max(b.y1);
    let y_hi = a.y2.min(b.y2);
    if a.x1 < b.x1 {
        out.push(Rect::new(a.x1, y_lo, b.x1, y_hi));
    }
    if b.x2 < a.x2 {
        out.push(Rect::new(b.x2, y_lo, a.x2, y_hi));
    }
}

/// Disjoint set of rectangles, a port of upstream `RectUnionPure`.
#[derive(Default, Debug)]
pub struct RectUnion {
    rects: Vec<Rect>,
}

impl RectUnion {
    #[must_use]
    pub fn len(&self) -> usize {
        self.rects.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.rects.is_empty()
    }

    /// True iff `r` is fully covered by the union.
    #[must_use]
    pub fn contains(&self, r: &Rect) -> bool {
        if self.rects.is_empty() {
            return false;
        }
        let mut stack = vec![*r];
        let mut next = Vec::new();
        for s in &self.rects {
            next.clear();
            for piece in &stack {
                if s.contains(piece) {
                    continue;
                }
                if piece.intersects(s) {
                    split_diff(piece, s, &mut next);
                } else {
                    next.push(*piece);
                }
            }
            if next.is_empty() {
                return true;
            }
            std::mem::swap(&mut stack, &mut next);
        }
        false
    }

    /// Insert `r` unless covered or the cap is reached. Returns whether the union grew.
    pub fn add(&mut self, r: Rect) -> bool {
        if self.rects.len() >= MAX_RECTS {
            return false;
        }
        if self.contains(&r) {
            return false;
        }
        let mut pending = vec![r];
        let mut next = Vec::new();
        for s in &self.rects {
            next.clear();
            for piece in &pending {
                if piece.intersects(s) {
                    split_diff(piece, s, &mut next);
                } else {
                    next.push(*piece);
                }
            }
            std::mem::swap(&mut pending, &mut next);
        }
        self.rects.extend(pending);
        true
    }
}

/// One simplified-tree node that carries a paint order and bounds.
#[derive(Clone, Copy, Debug)]
pub struct PaintNode {
    /// `backend_node_id`, returned when the node is occluded.
    pub id: u64,
    pub rect: Rect,
    pub paint_order: i64,
    /// Dense index of the `(session_id, iframe frame_id)` document context.
    pub context: u32,
    /// False when upstream's transparent/low-opacity rule keeps the rect out of the union.
    pub add_to_union: bool,
}

/// Backend node ids hidden by paint order, in the order upstream would flag them.
///
/// `nodes` must be in upstream's collection order (pre-order over the simplified tree).
#[must_use]
pub fn compute_removed(nodes: &[PaintNode]) -> Vec<u64> {
    let n_contexts = nodes
        .iter()
        .map(|n| n.context as usize + 1)
        .max()
        .unwrap_or(0);
    let mut unions: Vec<RectUnion> = (0..n_contexts).map(|_| RectUnion::default()).collect();

    // Groups by descending paint order; node order inside a group is preserved.
    let mut order: Vec<usize> = (0..nodes.len()).collect();
    order.sort_by_key(|&i| std::cmp::Reverse(nodes[i].paint_order));

    let mut removed = Vec::new();
    // (context, rects) in first-seen order within the group, like upstream's defaultdict.
    let mut to_add: Vec<(u32, Vec<Rect>)> = Vec::new();
    let mut slot_of: Vec<Option<usize>> = vec![None; n_contexts];

    let mut start = 0;
    while start < order.len() {
        let po = nodes[order[start]].paint_order;
        let mut end = start;
        while end < order.len() && nodes[order[end]].paint_order == po {
            end += 1;
        }

        for &i in &order[start..end] {
            let node = &nodes[i];
            if unions[node.context as usize].contains(&node.rect) {
                removed.push(node.id);
            }
            if !node.add_to_union {
                continue;
            }
            let slot = match slot_of[node.context as usize] {
                Some(s) => s,
                None => {
                    to_add.push((node.context, Vec::new()));
                    let s = to_add.len() - 1;
                    slot_of[node.context as usize] = Some(s);
                    s
                }
            };
            to_add[slot].1.push(node.rect);
        }
        for (ctx, rects) in to_add.drain(..) {
            slot_of[ctx as usize] = None;
            let union = &mut unions[ctx as usize];
            for r in rects {
                union.add(r);
            }
        }
        start = end;
    }
    removed
}

/// Python entry point. Parallel arrays: `ids`, `rects` (four floats per node:
/// x1, y1, x2, y2), `paint_orders`, `contexts`, `add_to_union`.
#[pyfunction]
pub fn paint_order_flat(
    py: Python<'_>,
    ids: Vec<u64>,
    rects: Vec<f64>,
    paint_orders: Vec<i64>,
    contexts: Vec<u32>,
    add_to_union: Vec<bool>,
) -> PyResult<Vec<u64>> {
    let n = ids.len();
    if rects.len() != 4 * n
        || paint_orders.len() != n
        || contexts.len() != n
        || add_to_union.len() != n
    {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "paint_order_flat: length mismatch (ids={n}, rects={}, paint_orders={}, contexts={}, add_to_union={})",
            rects.len(),
            paint_orders.len(),
            contexts.len(),
            add_to_union.len()
        )));
    }
    let nodes: Vec<PaintNode> = (0..n)
        .map(|i| PaintNode {
            id: ids[i],
            rect: Rect::new(
                rects[4 * i],
                rects[4 * i + 1],
                rects[4 * i + 2],
                rects[4 * i + 3],
            ),
            paint_order: paint_orders[i],
            context: contexts[i],
            add_to_union: add_to_union[i],
        })
        .collect();
    Ok(py.detach(move || compute_removed(&nodes)))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn r(x1: f64, y1: f64, x2: f64, y2: f64) -> Rect {
        Rect::new(x1, y1, x2, y2)
    }

    #[test]
    fn rect_relations_match_upstream_edge_rules() {
        let a = r(0.0, 0.0, 10.0, 10.0);
        assert!(
            !a.intersects(&r(10.0, 0.0, 20.0, 10.0)),
            "touching edges do not intersect"
        );
        assert!(a.intersects(&r(9.0, 9.0, 20.0, 20.0)));
        assert!(a.contains(&r(0.0, 0.0, 10.0, 10.0)), "contains is closed");
        assert!(!a.contains(&r(0.0, 0.0, 10.0, 10.1)));
    }

    #[test]
    fn split_diff_pieces_in_upstream_order() {
        let mut out = Vec::new();
        split_diff(&r(0.0, 0.0, 10.0, 10.0), &r(3.0, 3.0, 6.0, 6.0), &mut out);
        assert_eq!(
            out,
            vec![
                r(0.0, 0.0, 10.0, 3.0),
                r(0.0, 6.0, 10.0, 10.0),
                r(0.0, 3.0, 3.0, 6.0),
                r(6.0, 3.0, 10.0, 6.0)
            ]
        );
    }

    #[test]
    fn union_covers_by_composition() {
        let mut u = RectUnion::default();
        assert!(!u.contains(&r(0.0, 0.0, 1.0, 1.0)));
        assert!(u.add(r(0.0, 0.0, 5.0, 10.0)));
        assert!(u.add(r(5.0, 0.0, 10.0, 10.0)));
        assert!(
            u.contains(&r(2.0, 2.0, 8.0, 8.0)),
            "covered across two disjoint rects"
        );
        assert!(!u.contains(&r(2.0, 2.0, 11.0, 8.0)));
        assert!(!u.add(r(1.0, 1.0, 2.0, 2.0)), "already covered");
        assert_eq!(u.len(), 2);
    }

    #[test]
    fn union_cap_refuses_new_rects() {
        let mut u = RectUnion::default();
        for i in 0..MAX_RECTS {
            let x = i as f64 * 2.0;
            assert!(u.add(r(x, 0.0, x + 1.0, 1.0)));
        }
        assert!(!u.add(r(-10.0, -10.0, -9.0, -9.0)));
        assert_eq!(u.len(), MAX_RECTS);
    }

    /// Exact coverage on an integer grid must equal brute-force cell coverage,
    /// whatever the insertion order. Deterministic LCG, no dependencies.
    #[test]
    fn union_contains_matches_brute_force() {
        let mut seed: u64 = 0x9E37_79B9_7F4A_7C15;
        let mut next = || {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            seed
        };
        for _ in 0..200 {
            let mut u = RectUnion::default();
            let mut grid = [[false; 12]; 12];
            for _ in 0..6 {
                let x1 = (next() % 10) as usize;
                let y1 = (next() % 10) as usize;
                let x2 = x1 + 1 + (next() % 3) as usize;
                let y2 = y1 + 1 + (next() % 3) as usize;
                u.add(r(x1 as f64, y1 as f64, x2 as f64, y2 as f64));
                for row in grid.iter_mut().take(y2).skip(y1) {
                    for cell in row.iter_mut().take(x2).skip(x1) {
                        *cell = true;
                    }
                }
            }
            for _ in 0..10 {
                let x1 = (next() % 10) as usize;
                let y1 = (next() % 10) as usize;
                let x2 = x1 + 1 + (next() % 3) as usize;
                let y2 = y1 + 1 + (next() % 3) as usize;
                let expected = (y1..y2).all(|y| (x1..x2).all(|x| grid[y][x]));
                let actual = u.contains(&r(x1 as f64, y1 as f64, x2 as f64, y2 as f64));
                assert_eq!(expected, actual, "rect {x1},{y1}-{x2},{y2}");
            }
        }
    }

    #[test]
    fn higher_paint_order_occludes_lower_in_same_context_only() {
        let nodes = [
            PaintNode {
                id: 1,
                rect: r(0.0, 0.0, 10.0, 10.0),
                paint_order: 1,
                context: 0,
                add_to_union: true,
            },
            PaintNode {
                id: 2,
                rect: r(2.0, 2.0, 4.0, 4.0),
                paint_order: 5,
                context: 0,
                add_to_union: true,
            },
            PaintNode {
                id: 3,
                rect: r(2.0, 2.0, 4.0, 4.0),
                paint_order: 0,
                context: 0,
                add_to_union: true,
            },
            PaintNode {
                id: 4,
                rect: r(2.0, 2.0, 4.0, 4.0),
                paint_order: 0,
                context: 1,
                add_to_union: true,
            },
            PaintNode {
                id: 5,
                rect: r(20.0, 20.0, 30.0, 30.0),
                paint_order: 9,
                context: 0,
                add_to_union: false,
            },
            PaintNode {
                id: 6,
                rect: r(21.0, 21.0, 22.0, 22.0),
                paint_order: 3,
                context: 0,
                add_to_union: true,
            },
        ];
        // 3 is under 2 (and 1); 4 is in another context; 6 is under 5 but 5 is transparent.
        assert_eq!(compute_removed(&nodes), vec![3]);
    }

    #[test]
    fn checks_within_a_group_precede_adds() {
        let nodes = [
            PaintNode {
                id: 1,
                rect: r(0.0, 0.0, 10.0, 10.0),
                paint_order: 2,
                context: 0,
                add_to_union: true,
            },
            PaintNode {
                id: 2,
                rect: r(1.0, 1.0, 2.0, 2.0),
                paint_order: 2,
                context: 0,
                add_to_union: true,
            },
        ];
        assert!(
            compute_removed(&nodes).is_empty(),
            "same paint order never occludes itself"
        );
    }
}
