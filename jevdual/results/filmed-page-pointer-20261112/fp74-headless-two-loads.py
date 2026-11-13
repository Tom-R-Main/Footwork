"""Load the probe's fixture twice in headless Chrome (no window, temporary profile, no debugging port) and
print what each document posted: FP74's one new field, and that the script still runs."""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "scripts")
import probe_filmed_page_pointer as probe  # noqa: E402
import probe_page_effects  # noqa: E402

out = Path(sys.argv[1])
(out / "served").mkdir()
probe_page_effects.FIXTURE = probe.FIXTURE
server, port = probe_page_effects._serve(out / "served")
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
for load in (1, 2):
    done = subprocess.run([chrome, "--headless=new", f"--user-data-dir={out / 'profile'}", "--no-first-run",
                           "--disable-gpu", "--virtual-time-budget=1800", "--dump-dom", f"http://127.0.0.1:{port}/"],
                          capture_output=True, text=True, timeout=60, check=False)
    print("load", load, "exit", done.returncode, "dom bytes", len(done.stdout))
time.sleep(0.5)
rows = [json.loads(line) for line in (out / "served/page-events.jsonl").read_text().splitlines()]
for row in rows:
    print({k: (row[k] if k != "detail" else sorted(row[k])) for k in ("n", "doc", "type", "detail")})
docs = [row.get("doc") for row in rows]
print("documents", len(set(docs)), "all named", all(isinstance(d, str) and d for d in docs),
      "each numbered from one", sorted(row["n"] for row in rows if row["type"] == "loaded") == [1, 1])
