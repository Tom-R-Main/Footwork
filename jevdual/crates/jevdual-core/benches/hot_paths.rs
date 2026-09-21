//! Criterion benches for the native hot paths. Each port adds a group here that
//! runs on the same recorded fixtures the Python baseline uses.

use criterion::{Criterion, criterion_group, criterion_main};
use std::hint::black_box;

fn bench_ping(c: &mut Criterion) {
    c.bench_function("ping", |b| b.iter(|| _core::ping_impl(black_box(41))));
}

criterion_group!(benches, bench_ping);
criterion_main!(benches);
