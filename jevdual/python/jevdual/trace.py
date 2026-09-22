"""Step trace: one JSONL line per agent step, the single source the eval rig reads.

Schema is versioned. A header line records backend and configuration once per
run; every subsequent line is a ``StepRecord``. Secrets are redacted through the
``redactor`` hook (installed by ``jevdual.secrets``) before anything is written.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, Field

TRACE_SCHEMA_VERSION = 1

System = Literal["s1", "s2", "tool"]


class JevHead(BaseModel):
    """One Choice head from the fan-out: the chosen option and the full distribution."""

    choice: str
    confidence: float | None = None
    probabilities: dict[str, float] = Field(default_factory=dict)


class DecisionRecord(BaseModel):
    """What System 1 saw and answered. Absent on pure S2 steps."""

    operation: JevHead | None = None
    target: JevHead | None = None
    nouls: dict[str, float] = Field(default_factory=dict)
    model: str | None = None
    request_tokens: int | None = None
    latency_ms: float | None = None
    omitted_elements: int = 0


class ActionRecord(BaseModel):
    name: str
    params: dict[str, Any] = Field(default_factory=dict)


class Timings(BaseModel):
    dom_ms: float | None = None
    jev_ms: float | None = None
    llm_ms: float | None = None
    exec_ms: float | None = None
    step_ms: float | None = None


class Cost(BaseModel):
    jev_usd: float = 0.0
    llm_usd: float = 0.0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0


class StepRecord(BaseModel):
    schema_version: int = TRACE_SCHEMA_VERSION
    run_id: str
    step: int
    system: System
    url_before: str | None = None
    url_after: str | None = None
    decision: DecisionRecord | None = None
    arbiter_reason: str | None = None
    proposed: list[ActionRecord] = Field(default_factory=list)
    executed: list[ActionRecord] = Field(default_factory=list)
    result_error: str | None = None
    is_done: bool = False
    effect: str | None = None
    no_effect: bool = False
    memory_line: str | None = None
    timings: Timings = Field(default_factory=Timings)
    cost: Cost = Field(default_factory=Cost)
    ts: float = Field(default_factory=time.time)


class RunHeader(BaseModel):
    schema_version: int = TRACE_SCHEMA_VERSION
    kind: Literal["header"] = "header"
    run_id: str
    task: str
    arm: Literal["stock", "s1_only", "dual", "guarded", "delegate"]
    backend: str
    browser_use_version: str
    patches: dict[str, Any] = Field(default_factory=dict)
    jev_model: str | None = None
    llm_model: str | None = None
    arbiter_policy: dict[str, Any] = Field(default_factory=dict)
    started_at: float = Field(default_factory=time.time)


Redactor = Callable[[str], str]


class TraceWriter:
    """Append-only JSONL writer. ``redactor`` runs over every serialized line."""

    def __init__(self, path: str | os.PathLike[str], redactor: Redactor | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._redactor = redactor
        self._fh = self.path.open("a", encoding="utf-8")

    def set_redactor(self, redactor: Redactor | None) -> None:
        self._redactor = redactor

    def write(self, record: BaseModel) -> None:
        line = json.dumps(record.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
        if self._redactor is not None:
            line = self._redactor(line)
        self._fh.write(line + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def read_trace(path: str | os.PathLike[str]) -> tuple[RunHeader | None, list[StepRecord]]:
    """Parse a trace file back into models. Validation errors surface; the rig must not guess."""

    header: RunHeader | None = None
    steps: list[StepRecord] = []
    with Path(path).open(encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if obj.get("kind") == "header":
                header = RunHeader.model_validate(obj)
            else:
                steps.append(StepRecord.model_validate(obj))
    return header, steps
