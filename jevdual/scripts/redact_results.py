"""Redact secret values from an eval run directory in place (used for runs made before the runner installed the redactor)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jevdual.secrets import SecretStore

from evals.tasks.schema import load_all

values = {v for tasks in load_all().values() for t in tasks for v in t.secrets.values()}
store = SecretStore({f"secret_{i}": v for i, v in enumerate(sorted(values))}) if values else None
_red = store.redactor() if store else (lambda s: s)
# task ids are identifiers, not observations: never rewrite them, or result rows stop matching trace files
ids = sorted({t.id for tasks in load_all().values() for t in tasks}, key=len, reverse=True)
_protect = [i for i in ids if _red(i) != i]


def red(text: str) -> str:
    for k, i in enumerate(_protect):
        text = text.replace(i, f"\x00TASKID{k}\x00")
    text = _red(text)
    for k, i in enumerate(_protect):
        text = text.replace(f"\x00TASKID{k}\x00", i)
    return text


run = Path(sys.argv[1])
n = 0
for p in list(run.glob("*.json")) + list(run.glob("*.md")) + list(run.glob("traces/*.jsonl")) + list(run.glob("run.log")):
    t = p.read_text()
    r = red(t)
    if r != t:
        p.write_text(r)
        n += 1
print(f"redacted {n} files under {run}")
