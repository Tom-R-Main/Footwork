"""R6 measurement: stdlib json.loads vs orjson.loads on recorded CDP snapshot payloads."""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

import orjson

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.fixtures.loader import load_fixture

SLUGS = ["wikipedia-python", "amazon-usb-c-hub", "github-browser-use"]
N = 15


def bench(fn, raw):
    times = []
    for _ in range(N):
        t0 = time.perf_counter()
        fn(raw)
        times.append((time.perf_counter() - t0) * 1000)
    return statistics.median(times), min(times), max(times)


def main() -> None:
    rows = []
    for slug in SLUGS:
        fx = load_fixture(slug)
        raw = json.dumps({"id": 1, "result": fx.snapshot})
        j = bench(json.loads, raw)
        o = bench(orjson.loads, raw)
        rows.append((slug, len(raw) / 1e6, j, o))
    out = [
        "# R6: CDP message decode, stdlib json vs orjson",
        "",
        f"Median of {N} runs, release orjson wheel, Python {sys.version.split()[0]}.",
        "",
        "| fixture | payload MB | json.loads ms (min..max) | orjson.loads ms (min..max) | speedup |",
        "|---|---|---|---|---|",
    ]
    for slug, mb, j, o in rows:
        out.append(
            f"| {slug} | {mb:.2f} | {j[0]:.1f} ({j[1]:.1f}..{j[2]:.1f}) | {o[0]:.1f} ({o[1]:.1f}..{o[2]:.1f}) | {j[0] / o[0]:.1f}x |"
        )
    out.append("")
    out.append(
        "Payload is the DOMSnapshot.captureSnapshot result wrapped as a CDP response, the largest message cdp-use decodes per step."
    )
    text = "\n".join(out)
    print(text)
    Path("results").mkdir(exist_ok=True)
    Path("results/r6-json-decode.md").write_text(text + "\n")


if __name__ == "__main__":
    main()
