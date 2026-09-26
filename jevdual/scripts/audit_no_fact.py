"""Package E: what the claim check fails to find when it demotes a done for "no fact found on the page".

For every verification in the given runs' traces whose reason is the no-fact rule, grade each atom of
the done text by kind: a whole clause taken after a status label or a colon (more than six words), an
atom carrying a parenthetical aside, or a plain value. Page text is not in the traces, so this says
what the atoms were, not which ones the page lacked.

    uv run python scripts/audit_no_fact.py results/q12-live-dev-r1 results/q12-live-dev-r2 ...
"""

from __future__ import annotations

import collections
import glob
import json
import sys

from jevdual.verify import extract_atoms, split_claims


def kind(atom: str) -> str:
    if "(" in atom:
        return "parenthetical"
    if len(atom.split()) > 6:
        return "clause"
    return "value"


def main(dirs: list[str]) -> None:
    kinds: collections.Counter[str] = collections.Counter()
    sentences: collections.Counter[str] = collections.Counter()
    status_prefix = 0
    total = 0
    tasks: collections.Counter[str] = collections.Counter()
    for d in dirs:
        for f in sorted(glob.glob(f"{d}/traces/*.jsonl")):
            for line in open(f):
                e = json.loads(line)
                v = e.get("verify") or {}
                if "no fact found" not in (v.get("reason") or ""):
                    continue
                done = [a for a in e.get("executed") or [] if a.get("name") == "done"]
                if not done:
                    continue
                total += 1
                tasks[f.split("/")[-1].rsplit("-", 2)[0]] += 1
                text = done[0]["params"].get("text", "")
                status_prefix += text.lstrip().upper().startswith("UNVERIFIED:")
                for s in split_claims(text):
                    atoms = extract_atoms(s)
                    if not atoms:
                        sentences["narrative"] += 1
                        continue
                    ks = {kind(a) for a in atoms}
                    for a in atoms:
                        kinds[kind(a)] += 1
                    sentences["has only clause or parenthetical atoms" if ks <= {"clause", "parenthetical"} else "has a plain value"] += 1
    print(f"no-fact verifications with a done text: {total}; done text starting 'UNVERIFIED:': {status_prefix}")
    print("atoms by kind:", dict(kinds))
    print("sentences:", dict(sentences))
    print("by task:", tasks.most_common(12))


if __name__ == "__main__":
    main(sys.argv[1:])
