//! Criterion bench for the R2 snapshot-lookup body over a synthetic document
//! shaped like the Wikipedia fixture (about 13.5k laid-out nodes, 10 styles each).

use criterion::{Criterion, criterion_group, criterion_main};
use std::hint::black_box;

use _core::snapshot::{DocumentInput, snapshot_lookup_impl};

fn synthetic(n: usize) -> DocumentInput {
    DocumentInput {
        backend_node_ids: (0..n as i64).map(|i| i + 1).collect(),
        clickable: Some((0..n as i64).step_by(6).collect()),
        input_values: (0..n as i64).step_by(700).map(|i| (i, 3)).collect(),
        checked: Some(vec![5, 9]),
        node_index: (0..n as i64).collect(),
        bounds: (0..n)
            .map(|i| vec![i as f64, 2.0 * i as f64, 100.0, 20.5])
            .collect(),
        styles: (0..n)
            .map(|_| vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
            .collect(),
        paint_orders: (0..n as i64).collect(),
        stacking_contexts: (0..n as i64).map(|i| i % 3).collect(),
        client_rects: (0..n)
            .map(|i| {
                if i % 2 == 0 {
                    vec![]
                } else {
                    vec![1.0, 2.0, 3.0, 4.0]
                }
            })
            .collect(),
        scroll_rects: (0..n).map(|_| vec![]).collect(),
    }
}

fn bench(c: &mut Criterion) {
    let doc = synthetic(13_500);
    c.bench_function("snapshot_lookup_impl/13.5k", |b| {
        b.iter(|| snapshot_lookup_impl(black_box(std::slice::from_ref(&doc)), 14_000, 1.0))
    });
}

criterion_group!(benches, bench);
criterion_main!(benches);
