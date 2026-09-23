from jevdual.trace import (
    TRACE_SCHEMA_VERSION,
    ActionRecord,
    DecisionRecord,
    JevHead,
    RunHeader,
    StepRecord,
    TraceWriter,
    read_trace,
)


def test_round_trip_and_redaction(tmp_path):
    path = tmp_path / "run.jsonl"
    with TraceWriter(path, redactor=lambda s: s.replace("hunter2", "[REDACTED]")) as w:
        w.write(
            RunHeader(
                run_id="r1",
                task="log in with hunter2",
                arm="dual",
                backend="pure-python",
                browser_use_version="0.13.10",
            )
        )
        w.write(
            StepRecord(
                run_id="r1",
                step=1,
                system="s1",
                decision=DecisionRecord(
                    operation=JevHead(
                        choice="click", confidence=0.8, probabilities={"click": 0.8, "type": 0.2}
                    ),
                    target=JevHead(choice="7", confidence=0.6, probabilities={"7": 0.6, "9": 0.4}),
                    nouls={"goal_done": 0.05, "stuck": 0.1},
                ),
                proposed=[ActionRecord(name="click", params={"index": 7})],
                executed=[ActionRecord(name="click", params={"index": 7})],
                memory_line="S1 step 1: click [7] with password hunter2",
            )
        )
        w.write(StepRecord(run_id="r1", step=2, system="s2", is_done=True))
    header, steps = read_trace(path)
    assert header is not None and header.schema_version == TRACE_SCHEMA_VERSION
    assert "hunter2" not in path.read_text()
    assert header.task == "log in with [REDACTED]"
    assert [s.system for s in steps] == ["s1", "s2"]
    assert steps[0].decision.operation.probabilities["click"] == 0.8
    assert steps[1].is_done


def test_stock_run_is_representable():
    # An S2-only (stock browser-use) run has no decision; the rig compares arms on this shape.
    rec = StepRecord(run_id="r", step=1, system="s2")
    assert rec.decision is None and rec.arbiter_reason is None


def test_run_header_accepts_every_eval_arm():
    from jevdual.trace import RunHeader

    from evals.runner import ARMS

    for arm in ARMS:
        RunHeader(
            run_id="r",
            task="t",
            arm=("s1_only" if arm == "scripted" else arm),
            backend="pure-python",
            browser_use_version="0",
        )


def test_step_record_carries_menu_and_verification_scores():
    from jevdual.trace import TRACE_SCHEMA_VERSION, MenuEntry, StepRecord

    r = StepRecord(
        run_id="r",
        step=1,
        system="s1",
        menu=[
            MenuEntry(id=3, label="Sign in", role="button"),
            MenuEntry(id=6, label="Username", role="input", input_type="text", value=""),
        ],
        verify={"band": "verify", "complete": 0.81, "unmet": {"Signed in": 0.35}},
    )
    d = r.model_dump()
    assert d["schema_version"] == TRACE_SCHEMA_VERSION == 2
    assert d["menu"][1]["label"] == "Username" and d["verify"]["complete"] == 0.81
    assert StepRecord(run_id="r", step=2, system="s2").menu == []  # older records and S2 steps: empty
