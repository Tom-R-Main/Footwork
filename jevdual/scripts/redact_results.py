"""Redact secret values from an eval run directory in place (used for runs made before the runner installed the redactor)."""

import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jevdual.secrets import SecretStore

from evals.tasks.schema import load_all

values = {v for tasks in load_all().values() for t in tasks for v in t.secrets.values()}
# Q19 task files (evals/tasks/q19-*.yaml) carry their secrets in their own format
for f in sorted((Path(__file__).resolve().parents[1] / "evals" / "tasks").glob("q19-*.yaml")):
    values |= {
        str(v) for t in yaml.safe_load(f.read_text())["tasks"] for v in (t.get("secrets") or {}).values()
    }
# this Mac's identifiers (serial number, hardware UUID, provisioning UDID) appear in System Information
# and System Settings observations (Q19 D13, H04); read here, never written into the repo
_hw = subprocess.run(
    ["system_profiler", "SPHardwareDataType"], capture_output=True, text=True, check=False
).stdout
values |= {
    m.group(2).strip()
    for m in re.finditer(r"(Serial Number \(system\)|Hardware UUID|Provisioning UDID): (.+)", _hw)
}
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
for p in (
    list(run.rglob("*.json"))
    + list(run.rglob("*.jsonl"))
    + list(run.rglob("*.md"))
    + list(run.rglob("run.log"))
):
    t = p.read_text()
    r = red(t)
    if r != t:
        p.write_text(r)
        n += 1
print(f"redacted {n} files under {run}")
