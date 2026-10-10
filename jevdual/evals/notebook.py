"""Check and score the engineering notebook: predictions written before a test, and how they came out.

    uv run python -m evals.notebook docs/notebook            # score every file
    uv run python -m evals.notebook docs/notebook --check    # exit 1 on a malformed entry

The format is in ``docs/notebook/README.md``. An entry is a level-two heading
``## <ID> · <kind> · <YYYY-MM-DD HH:MM>`` followed by ``Field: text`` lines. Kinds and their
required fields:

- ``prediction``: Hypothesis, Test, Predicts, Against (Question, Alternatives, Refs optional).
- ``exploratory``: Question, Test.
- ``update``: Observed, Next; ``Resolves: <ID> = held | failed | inconclusive`` closes a
  prediction, and ``Inferred`` keeps interpretation apart from what was seen.
- ``summary``: Established, Uncertain, Decision.

Entries are appended, never edited: an outcome is a later ``update`` that resolves the prediction,
and a changed prediction is a new one with ``Revises: <ID>``. The score is what the notebook is for:
how often the diagnoses written before a test held, and which ones did not.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

KINDS = ("prediction", "exploratory", "update", "summary")
REQUIRED = {
    "prediction": ("Hypothesis", "Test", "Predicts", "Against"),
    "exploratory": ("Question", "Test"),
    "update": ("Observed", "Next"),
    "summary": ("Established", "Uncertain", "Decision"),
}
OUTCOMES = ("held", "failed", "inconclusive")
HEADING = re.compile(
    r"^## (?P<id>[A-Za-z][\w.-]*) · (?P<kind>\w+) · (?P<when>\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*$"
)
FIELD = re.compile(r"^(?:- )?\*{0,2}(?P<name>[A-Z][A-Za-z]+)\*{0,2}:\*{0,2}\s*(?P<text>.*)$")
RESOLVES = re.compile(r"^(?P<id>[A-Za-z][\w.-]*)\s*=\s*(?P<outcome>\w+)")


@dataclass
class Entry:
    file: str
    line: int
    id: str
    kind: str
    when: str
    fields: dict[str, str] = field(default_factory=dict)


@dataclass
class Notebook:
    entries: list[Entry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def predictions(self) -> list[Entry]:
        return [e for e in self.entries if e.kind == "prediction"]

    def outcomes(self) -> dict[str, tuple[str, Entry]]:
        """The last resolution of each prediction id, with the update that made it."""
        out: dict[str, tuple[str, Entry]] = {}
        for e in self.entries:
            m = RESOLVES.match(e.fields.get("Resolves", ""))
            if e.kind == "update" and m:
                out[m["id"]] = (m["outcome"], e)
        return out


def parse_file(path: Path, nb: Notebook) -> None:
    cur: Entry | None = None
    last_field: str | None = None
    for n, raw in enumerate(path.read_text().splitlines(), 1):
        if raw.startswith("## "):
            m = HEADING.match(raw)
            if not m:
                nb.errors.append(f"{path.name}:{n}: heading is not '## <ID> · <kind> · <YYYY-MM-DD HH:MM>'")
                cur = None
                continue
            cur = Entry(path.name, n, m["id"], m["kind"], m["when"])
            nb.entries.append(cur)
            last_field = None
            continue
        if cur is None:
            continue
        fm = FIELD.match(raw.strip())
        if fm and fm["name"] in _KNOWN_FIELDS:
            last_field = fm["name"]
            cur.fields[last_field] = fm["text"].strip()
        elif last_field and raw.strip():
            cur.fields[last_field] = (cur.fields[last_field] + " " + raw.strip()).strip()


_KNOWN_FIELDS = frozenset(
    {
        "Question", "Hypothesis", "Alternatives", "Test", "Predicts", "Against", "Refs", "Revises",
        "Observed", "Inferred", "Changes", "Next", "Resolves",
        "Established", "Uncertain", "Decision",
    }
)  # fmt: skip


def validate(nb: Notebook) -> None:
    seen: dict[str, Entry] = {}
    for e in nb.entries:
        where = f"{e.file}:{e.line} {e.id}"
        if e.id in seen:
            nb.errors.append(f"{where}: id already used at {seen[e.id].file}:{seen[e.id].line}")
        if e.kind not in KINDS:
            nb.errors.append(f"{where}: kind {e.kind!r} is not one of {', '.join(KINDS)}")
            continue
        for name in REQUIRED[e.kind]:
            if not e.fields.get(name):
                nb.errors.append(f"{where}: {e.kind} needs '{name}:'")
        for key in ("Resolves", "Revises"):
            if key not in e.fields:
                continue
            target = e.fields[key].split("=")[0].strip()
            prior = seen.get(target)
            if prior is None or prior.kind != "prediction":
                nb.errors.append(f"{where}: {key} names {target!r}, not an earlier prediction")
        m = RESOLVES.match(e.fields.get("Resolves", ""))
        if "Resolves" in e.fields and (not m or m["outcome"] not in OUTCOMES):
            nb.errors.append(f"{where}: Resolves must be '<ID> = {' | '.join(OUTCOMES)}'")
        seen[e.id] = e


def load(root: Path) -> Notebook:
    nb = Notebook()
    files = [root] if root.is_file() else sorted(p for p in root.glob("*.md") if p.name != "README.md")
    for p in files:
        parse_file(p, nb)
    validate(nb)
    return nb


def render(nb: Notebook) -> str:
    preds = nb.predictions()
    outcomes = nb.outcomes()
    counts = {o: sum(1 for p in preds if outcomes.get(p.id, ("",))[0] == o) for o in OUTCOMES}
    open_ = [p for p in preds if p.id not in outcomes]
    lines = [
        f"{len(nb.entries)} entries, {len(preds)} predictions: "
        + ", ".join(f"{counts[o]} {o}" for o in OUTCOMES)
        + f", {len(open_)} open"
    ]
    resolved = counts["held"] + counts["failed"]
    if resolved:
        lines.append(f"held rate {counts['held']}/{resolved} of predictions resolved held or failed")
    failed = [p for p in preds if outcomes.get(p.id, ("",))[0] == "failed"]
    if failed:
        lines.append("\nfailed (the diagnoses to learn from):")
        for p in failed:
            by = outcomes[p.id][1]
            lines.append(f"  {p.id} ({p.file}): {p.fields['Hypothesis'][:110]}")
            lines.append(f"      resolved by {by.id}: {by.fields.get('Observed', '')[:110]}")
    if open_:
        lines.append("\nopen:")
        lines.extend(f"  {p.id} ({p.file}, {p.when}): {p.fields.get('Predicts', '')[:100]}" for p in open_)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", type=Path, nargs="?", default=Path("docs/notebook"))
    ap.add_argument("--check", action="store_true", help="exit 1 when an entry is malformed")
    a = ap.parse_args(argv)
    nb = load(a.root)
    for err in nb.errors:
        print(f"error: {err}", file=sys.stderr)
    print(render(nb))
    return 1 if a.check and nb.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
