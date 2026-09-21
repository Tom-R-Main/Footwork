"""Task file schema for the eval rig.

A task is graded by its predicate against observed state (final URL, captured
page text, or the returned answer), never by the agent's own claim of success.
``start_url`` may contain the placeholder ``{site}``, resolved at run time to
the fixture server's base URL.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

Tag = Literal[
    "navigate", "read", "type", "select", "destructive", "login", "modal", "pagination", "enter-submit", "live"
]
PredicateKind = Literal["url_contains", "page_text_contains", "answer_contains", "answer_equals", "not_reached"]

TASKS_DIR = Path(__file__).parent
DEV = TASKS_DIR / "dev.yaml"
HELDOUT = TASKS_DIR / "heldout.yaml"


class Predicate(BaseModel):
    """Completion check.

    - ``url_contains``: final URL contains ``value``.
    - ``page_text_contains``: final page's visible text contains ``value``.
    - ``answer_contains`` / ``answer_equals``: the returned answer contains / equals ``value``.
    - ``not_reached``: the run must end without ever loading a URL containing ``value``
      (destructive targets that need confirmation), and must not report ``done``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: PredicateKind
    value: str = Field(min_length=1)


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    task: str = Field(min_length=8)
    start_url: str
    tags: tuple[Tag, ...] = Field(min_length=1)
    requirements: tuple[str, ...] = Field(min_length=1)
    predicate: Predicate
    answer_expected: bool = False
    """True when the task asks for an answer (read tasks); the runner then captures the final answer."""

    @field_validator("start_url")
    @classmethod
    def _url_shape(cls, v: str) -> str:
        if not v.startswith(("{site}/", "https://")):
            raise ValueError("start_url must begin with '{site}/' or 'https://'")
        return v

    @property
    def is_live(self) -> bool:
        return "live" in self.tags

    def resolved_start_url(self, site: str) -> str:
        return self.start_url.replace("{site}", site.rstrip("/"))


class TaskFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    split: Literal["dev", "heldout"]
    tasks: list[Task] = Field(min_length=1)


def load_tasks(path: str | Path) -> list[Task]:
    """Load and validate a task file, rejecting duplicate ids within it."""
    raw = yaml.safe_load(Path(path).read_text())
    file = TaskFile.model_validate(raw)
    ids = [t.id for t in file.tasks]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError(f"duplicate task ids in {path}: {dupes}")
    return file.tasks


def load_all() -> dict[str, list[Task]]:
    return {"dev": load_tasks(DEV), "heldout": load_tasks(HELDOUT)}
