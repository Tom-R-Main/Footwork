"""Q19 held-back summary, computed from the adjudication and the raw records (never from raw outcome
labels alone). Fails when the adjudication is inconsistent with the raw records.

    uv run python scripts/q19_summary.py [--json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals import adjudication

ADJ = ROOT / "results" / "q19-heldout-adjudication.yaml"
RAW = [ROOT / "results" / "q19-heldout-operator", ROOT / "results" / "q19-heldout-model"]


def raw_dirs() -> list[Path]:
    return sorted(d for r in RAW for d in r.iterdir() if d.is_dir())


def main(argv: list[str]) -> int:
    attempts = adjudication.load(ADJ)
    bad = adjudication.problems(attempts, ROOT, raw_dirs())
    if bad:
        print("adjudication inconsistent:\n  " + "\n  ".join(bad))
        return 1
    s = adjudication.summary(attempts, ROOT)
    if "--json" in argv:
        print(json.dumps(s, indent=1))
        return 0
    for driver, d in s.items():
        o = d["outcomes"]
        print(f"{driver}: {d['eligible']} eligible of {d['tasks']} tasks")
        print(
            f"  completed_verified {o['completed_verified']} (basis {d['completed_basis']}); "
            f"effect correct but unaccepted {o['effect_correct_unaccepted']}, not claimed "
            f"{o['effect_correct_not_claimed']}; truthful stops {o['truthful_stop']}; "
            f"stops without reason {o['stop_without_reason']}; unsupported claims {o['unsupported_claim']}"
        )
        for x in d["excluded"]:
            print(f"  excluded {x['id']} ({x['eligibility']}): {x['reason']}")
        if driver == "operator":
            print(
                f"  commands per completed task {d['commands_per_completed']}; friction {d['friction_all_eligible']}"
            )
        else:
            print(f"  steps {d['steps_all_attempts']}; cost ${d['cost_usd_all_attempts']} (all attempts)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
