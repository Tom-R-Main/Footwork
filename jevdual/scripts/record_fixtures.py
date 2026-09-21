"""Record the exact CDP inputs browser-use's DOM pipeline consumes, for offline tests.

Usage: uv run python scripts/record_fixtures.py [slug ...]

For each page we call DomService._get_all_trees, which is the same code path the
agent uses (DOMSnapshot.captureSnapshot with REQUIRED_COMPUTED_STYLES, DOM.getDocument
depth=-1 pierce=True, Accessibility.getFullAXTree per frame, Page.getLayoutMetrics for
the device pixel ratio, plus JS click-listener detection). We also record the raw
layout metrics and the interactive element count from get_serialized_dom_tree at
capture time so equality tests have a ground truth.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import logging
import sys
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

logging.getLogger().setLevel(logging.ERROR)

from browser_use.browser.profile import BrowserProfile
from browser_use.browser.session import BrowserSession
from browser_use.dom.service import DomService
from browser_use.dom.views import DEFAULT_INCLUDE_ATTRIBUTES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "cdp"
PAGES = ROOT / "tests" / "fixtures" / "pages"


@dataclass(frozen=True)
class Page:
    slug: str
    url: str
    why: str
    settle_s: float = 2.5


def pages(local_base: str) -> list[Page]:
    return [
        Page("wikipedia-python", "https://en.wikipedia.org/wiki/Python_(programming_language)", "long article, many links, tables"),
        Page("github-browser-use", "https://github.com/browser-use/browser-use", "app-like layout, many buttons, nested menus"),
        Page("amazon-usb-c-hub", "https://www.amazon.com/s?k=usb+c+hub", "dense commerce grid, heavy computed styles"),
        Page("youtube-home", "https://www.youtube.com/", "shadow DOM everywhere (Polymer)", 5.0),
        Page("w3schools-iframe", "https://www.w3schools.com/html/html_iframe.asp", "cross-origin iframes"),
        Page("modal-over-content", f"{local_base}/modal_over_content.html", "fixed modal + backdrop covering a product grid (paint-order occlusion)", 1.0),
        Page("virtual-list", f"{local_base}/virtual_list.html", "virtualized list: 10,000 rows, only ~25 in the DOM at a time", 1.0),
        Page("ja-wikipedia-python", "https://ja.wikipedia.org/wiki/Python", "CJK text and labels"),
        Page("sensitive-fields", f"{local_base}/sensitive_fields.html", "password, cc-number, one-time-code, hidden and file inputs with pre-filled values", 1.0),
        Page("dense-links", f"{local_base}/dense_links.html", ">255 interactive elements in one viewport (360 links + 360 buttons)", 1.0),
        Page("hacker-news", "https://news.ycombinator.com/", "flat table layout, many small links"),
    ]


def serve_local() -> tuple[ThreadingHTTPServer, str]:
    handler = partial(SimpleHTTPRequestHandler, directory=str(PAGES))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


async def capture(bs: BrowserSession, page: Page) -> dict:
    await bs.navigate_to(page.url)
    await asyncio.sleep(page.settle_s)
    target_id = bs.agent_focus_target_id
    assert target_id is not None
    svc = DomService(bs)
    trees = await svc._get_all_trees(target_id)
    cdp = await bs.get_or_create_cdp_session(target_id=target_id, focus=False)
    metrics = await cdp.cdp_client.send.Page.getLayoutMetrics(session_id=cdp.session_id)
    state, _root, timing = await DomService(bs).get_serialized_dom_tree(None)
    text = state.llm_representation(include_attributes=DEFAULT_INCLUDE_ATTRIBUTES)
    return {
        "slug": page.slug,
        "url": page.url,
        "why": page.why,
        "captured_at": datetime.now(UTC).isoformat(),
        "browser_use_version": "0.13.10",
        "snapshot": trees.snapshot,
        "dom": trees.dom_tree,
        "ax": trees.ax_tree,
        "device_pixel_ratio": trees.device_pixel_ratio,
        "viewport": metrics,
        "js_click_listener_backend_ids": sorted(trees.js_click_listener_backend_ids or []),
        "element_count": len(state.selector_map),
        "selector_backend_node_ids": {str(k): v.backend_node_id for k, v in state.selector_map.items()},
        "llm_representation_chars": len(text),
        "timing_ms": {k: round(v, 1) for k, v in timing.items()},
    }


async def main(only: set[str]) -> None:
    server, base = serve_local()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"fixtures": [], "failed": []}
    manifest["failed"] = [f for f in manifest["failed"] if not only or f["slug"] in only]
    bs = BrowserSession(browser_profile=BrowserProfile(headless=True, window_size={"width": 1280, "height": 900}))
    await bs.start()
    try:
        for page in pages(base):
            if only and page.slug not in only:
                continue
            last_err = None
            for attempt in (1, 2):
                try:
                    rec = await asyncio.wait_for(capture(bs, page), timeout=90)
                    break
                except Exception as e:  # noqa: BLE001
                    last_err = f"{type(e).__name__}: {e}"[:300]
                    rec = None
                    await asyncio.sleep(2)
            if rec is None:
                print(f"FAIL {page.slug}: {last_err}")
                manifest["failed"].append({"slug": page.slug, "url": page.url, "error": last_err})
                continue
            path = OUT / f"{page.slug}.json.gz"
            with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as f:
                json.dump(rec, f, ensure_ascii=False, separators=(",", ":"))
            entry = {
                "slug": page.slug,
                "url": page.url,
                "why": page.why,
                "captured_at": rec["captured_at"],
                "element_count": rec["element_count"],
                "documents": len(rec["snapshot"].get("documents", [])),
                "snapshot_strings": len(rec["snapshot"].get("strings", [])),
                "size_kb": round(path.stat().st_size / 1024),
            }
            manifest["fixtures"] = [f for f in manifest["fixtures"] if f["slug"] != page.slug] + [entry]
            print(f"OK   {page.slug}: {entry['element_count']} elements, {entry['documents']} docs, {entry['size_kb']} KB")
    finally:
        await bs.kill()
        server.shutdown()
    manifest["fixtures"].sort(key=lambda f: f["slug"])
    manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    asyncio.run(main(set(sys.argv[1:])))
