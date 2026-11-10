"""Run selected IR2 effect-journal cases in the Mac's isolated Linux VM."""

import hashlib
import json
import os
import sys
from pathlib import Path

IR1 = Path("/repo/jevdual/scripts/ir1_replay_audit")
sys.path.insert(0, str(IR1))
from run import target_case


def main() -> None:
    task = Path(sys.argv[1])
    output = Path(sys.argv[2])
    output.mkdir(parents=True, exist_ok=False)
    binary = task / "bin/ir1-probe"
    build = json.loads((task / "build.json").read_text())
    assert build["compile_exit"] == build["link_exit"] == 0
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == build["probe_sha256"]

    # The fixture inherits only these ordinary container values. No host
    # credential, display, Wayland or shared accessibility socket enters it.
    keep = {"PATH", "HOME", "LANG", "LC_ALL", "IR2_FROZEN_COMMIT"}
    for key in list(os.environ):
        if key not in keep:
            os.environ.pop(key, None)
    cases = [
        (arm, mode, 100 if mode == "withhold" else None, f"{arm}-{mode}")
        for arm in ("set_value_on", "write_through_editable_proxies")
        for mode in ("ack", "false", "error", "withhold")
    ]
    cases += [
        ("public_set_ref", mode, None, f"public-set-ref-{mode}")
        for mode in ("ack", "false", "error", "withhold")
    ]
    cases += [
        ("direct_timeout", "withhold", 100, "direct-client-timeout-control"),
        ("double_set_control", "ack", None, "equal-final-value-double-effect-control"),
    ]
    records = [target_case(IR1, task, output, *case) for case in cases]
    failures = []
    for record in records:
        label = record["label"]
        if "infrastructure_error" in record or record.get("watchdog_expired") or record.get("result") is None:
            failures.append({"label": label, "reason": "unavailable client or fixture"})
            continue
        arm, mode = record["boundary"], record["fixture_mode"]
        result = record["result"]
        journal = [json.loads(line) for line in (output / label / "target.jsonl").read_text().splitlines()]
        attempts = [event for event in journal if event["kind"] == "method_received"]
        effects = [event for event in journal if event["kind"] == "effect_applied"]
        replies = [event for event in journal if event["kind"] == "reply_behavior"]
        cleanup = json.loads((output / label / "cleanup.json").read_text())
        if len(attempts) != record["attempts"] or len(effects) != record["effects"]:
            failures.append({"label": label, "reason": "summary and independent journal differ"})
        if len(cleanup) != 2 or any(not row["wait_completed"] or row["escalated"] for row in cleanup):
            failures.append({"label": label, "reason": "owned fixture cleanup incomplete"})
        if mode in ("error", "withhold", "false") and (not replies or replies[0]["behavior"] != mode):
            failures.append({"label": label, "reason": "requested reply fault not observed"})
        if mode in ("error", "withhold") and len(effects) == 1 and replies and effects[0]["monotonic_ns"] >= replies[0]["monotonic_ns"]:
            failures.append({"label": label, "reason": "effect not journaled before reply fault"})
        if arm == "double_set_control":
            expected = (2, 2, True)
        elif arm == "direct_timeout":
            expected = (1, 1, False)
        elif mode == "ack":
            expected = (1, 1, True)
        elif mode == "false":
            expected = (2, 1, True)
        else:
            expected = (1, 1, False)
        actual = (record["attempts"], record["effects"], result.get("ok"))
        if actual != expected:
            failures.append({"label": label, "reason": "attempt/effect/outcome mismatch", "actual": actual, "expected": expected})
        if mode in ("error", "withhold") and arm != "direct_timeout" and "text_write_uncertain" not in str(result.get("error", "")):
            failures.append({"label": label, "reason": "missing typed uncertainty"})
    summary = {
        "scope": "actual pinned Linux helpers and public retained-ref function in private D-Bus; not registered TypeText or SetValueTool and not Footwork product",
        "frozen_commit": os.environ.get("IR2_FROZEN_COMMIT"),
        "candidate_patch_sha256": build["candidate_patch_sha256"],
        "binary_sha256": build["probe_sha256"],
        "case_count": len(records),
        "failures": failures,
        "cases": records,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"case_count": len(records), "failures": failures}), flush=True)
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
