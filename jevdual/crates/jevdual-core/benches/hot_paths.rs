//! Criterion benches for the native hot paths. Each port adds a group here that
//! runs on inputs shaped like the recorded fixtures (the Python-side benches in
//! `tests/bench/` measure the same ports through the adapter, which is what
//! production pays).

use criterion::{Criterion, criterion_group, criterion_main};
use std::hint::black_box;

use _core::paint_order::{PaintNode, Rect, compute_removed};

fn bench_ping(c: &mut Criterion) {
    c.bench_function("ping", |b| b.iter(|| _core::ping_impl(black_box(41))));
}

/// A page-like layout: a card grid at increasing paint orders with header,
/// sidebar and a few overlays; about the node count of the Amazon fixture.
fn synthetic_page(n: usize) -> Vec<PaintNode> {
    let mut nodes = Vec::with_capacity(n);
    let mut seed: u64 = 0x2545_F491_4F6C_DD1D;
    let mut next = || {
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        seed
    };
    for i in 0..n {
        let col = (i % 6) as f64;
        let row = (i / 6) as f64;
        let x = 20.0 + col * 200.0 + (next() % 8) as f64;
        let y = 120.0 + row * 60.0 + (next() % 8) as f64;
        let w = 150.0 + (next() % 60) as f64;
        let h = 40.0 + (next() % 20) as f64;
        nodes.push(PaintNode {
            id: i as u64 + 1,
            rect: Rect::new(x, y, x + w, y + h),
            paint_order: (i % 37) as i64 + 1,
            context: 0,
            add_to_union: next() % 4 != 0,
        });
    }
    // Overlays drawn last, covering part of the grid.
    for k in 0..3u64 {
        let y = 200.0 + k as f64 * 300.0;
        nodes.push(PaintNode {
            id: 100_000 + k,
            rect: Rect::new(0.0, y, 1300.0, y + 250.0),
            paint_order: 1000 + k as i64,
            context: 0,
            add_to_union: true,
        });
    }
    nodes
}

fn bench_paint_order(c: &mut Criterion) {
    let mut group = c.benchmark_group("paint_order");
    for &n in &[500usize, 2500, 7000] {
        let nodes = synthetic_page(n);
        group.bench_function(format!("compute_removed/{n}"), |b| {
            b.iter(|| compute_removed(black_box(&nodes)))
        });
    }
    group.finish();
}

criterion_group!(benches, bench_ping, bench_paint_order);
criterion_main!(benches);
