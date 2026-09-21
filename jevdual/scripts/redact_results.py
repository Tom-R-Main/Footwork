"""Redact secret values from an eval run directory in place (used for runs made before the runner installed the redactor)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jevdual.secrets import SecretStore

from evals.tasks.schema import load_all

values = {v for tasks in load_all().values() for t in tasks for v in t.secrets.values()}
store = SecretStore({f"secret_{i}": v for i, v in enumerate(sorted(values))}) if values else None
red = store.redactor() if store else (lambda s: s)
run = Path(sys.argv[1])
n = 0
for p in list(run.glob("*.json")) + list(run.glob("*.md")) + list(run.glob("traces/*.jsonl")) + list(run.glob("run.log")):
    t = p.read_text()
    r = red(t)
    if r != t:
        p.write_text(r)
        n += 1
print(f"redacted {n} files under {run}")
