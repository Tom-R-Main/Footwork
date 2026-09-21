"""R5 measurement: replayed DOM pipeline (get_dom_tree + serializer, CPU only) unpatched vs patched.

Runs with JEVDUAL_NATIVE_SNAPSHOT honoured as set in the environment; paint order goes
native whenever R1 is built. Median of N runs per fixture; writes results/r5-dom-pipeline.md.
"""

from __future__ import annotations

import gc
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jevdual import patch

from tests.fixtures import replay
from tests.fixtures.loader import fixture_slugs

N = int(os.environ.get("JEVDUAL_BENCH_N", "10"))
PHASES = (
    "build_snapshot_lookup_ms",
    "construct_enhanced_tree_ms",
    "create_simplified_tree_ms",
    "calculate_paint_order_ms",
    "optimize_tree_ms",
    "assign_interactive_indices_ms",
)


def run(slug: str) -> tuple[float, dict[str, float]]:
    times: list[float] = []
    phases: dict[str, list[float]] = {k: [] for k in PHASES}
    for _ in range(N):
        gc.collect()
        t0 = time.perf_counter()
        _state, _root, timing = replay.replay_serialized.__wrapped__(slug)  # bypass @cache
        times.append((time.perf_counter() - t0) * 1000)
        for k in PHASES:
            phases[k].append(float(timing.get(k, 0.0)))
    return statistics.median(times), {k: statistics.median(v) for k, v in phases.items()}


def main() -> None:
    slugs = fixture_slugs()
    patch.uninstall()
    off = {s: run(s) for s in slugs}
    active = patch.install()
    on = {s: run(s) for s in slugs}
    patch.uninstall()

    lines = [
        "# R5: DOM pipeline CPU (replayed get_dom_tree + serializer), unpatched vs patched",
        "",
        f"Median of {N} runs, gc.collect() before each, Python {sys.version.split()[0]}, patches active: {active}.",
        "CDP round trips are excluded; this is the CPU that follows them per step.",
        "",
        "| fixture | unpatched ms | patched ms | delta ms | paint order off/on ms | snapshot lookup off/on ms |",
        "|---|---|---|---|---|---|",
    ]
    for s in slugs:
        a, pa = off[s]
        b, pb = on[s]
        lines.append(
            f"| {s} | {a:.1f} | {b:.1f} | {b - a:+.1f} | {pa['calculate_paint_order_ms']:.1f}/{pb['calculate_paint_order_ms']:.1f} "
            f"| {pa['build_snapshot_lookup_ms']:.1f}/{pb['build_snapshot_lookup_ms']:.1f} |"
        )
    lines.append("")
    for s in ("wikipedia-python", "amazon-usb-c-hub"):
        if s in on:
            _b, pb = on[s]
            residual = ", ".join(f"{k.removesuffix('_ms')} {v:.1f}" for k, v in pb.items())
            lines.append(f"Residual per phase with patches on, {s}: {residual} ms.")
    g3 = all(on[s][0] < 50.0 for s in ("wikipedia-python", "amazon-usb-c-hub") if s in on)
    lines.append("")
    lines.append(f"G3 gate (DOM CPU < 50 ms on wikipedia and amazon with patches on): {'MET' if g3 else 'NOT MET'}.")
    text = "\n".join(lines)
    print(text)
    Path("results").mkdir(exist_ok=True)
    Path("results/r5-dom-pipeline.md").write_text(text + "\n")


if __name__ == "__main__":
    main()
