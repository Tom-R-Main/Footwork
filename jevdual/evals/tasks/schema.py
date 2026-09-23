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
    "navigate",
    "read",
    "type",
    "select",
    "destructive",
    "login",
    "modal",
    "pagination",
    "enter-submit",
    "live",
    "search",
    "form",
    "multistep",
    "consent",
    "tabs",
    "judged",
    "mind2web",
    "upstream",
]
PredicateKind = Literal[
    "url_contains", "page_text_contains", "answer_contains", "answer_equals", "not_reached", "judge"
]

TASKS_DIR = Path(__file__).parent
DEV = TASKS_DIR / "dev.yaml"
HELDOUT = TASKS_DIR / "heldout.yaml"
LIVE_DEV = TASKS_DIR / "live-dev.yaml"
LIVE_HELDOUT = TASKS_DIR / "live-heldout.yaml"
LIVE_UPSTREAM = TASKS_DIR / "live-upstream.yaml"
SPLITS: dict[str, Path] = {
    "dev": DEV,
    "heldout": HELDOUT,
    "live-dev": LIVE_DEV,
    "live-heldout": LIVE_HELDOUT,
    "live-upstream": LIVE_UPSTREAM,
}


class Predicate(BaseModel):
    """Completion check.

    - ``url_contains``: final URL contains ``value``.
    - ``page_text_contains``: final page's visible text contains ``value``.
    - ``answer_contains`` / ``answer_equals``: the returned answer contains / equals ``value``.
    - ``not_reached``: the run must end without ever loading a URL containing ``value``
      (destructive targets that need confirmation), and must not report ``done``.
    - ``judge``: no machine-checkable state; ``value`` is the success criteria handed to the
      upstream judge (browser-use's own judge prompt, run by the System 2 model) as ground
      truth. Reports mark these rows ``graded_by=judge``; they never mix into predicate rates.
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
    #: Secrets by name; values never appear in task text. The runner scopes them to the site origin.
    secrets: dict[str, str] = Field(default_factory=dict)
    #: The task explicitly wants an irreversible action (order placed, message sent); the destructive gate is off.
    authorize: bool = False
    #: Scope of that authorisation: target keywords the gate and arbiter stand down for (e.g. ["finish", "submit"]).
    #: Empty with ``authorize: true`` means task-wide, the old behaviour.
    authorized_actions: tuple[str, ...] = ()
    """True when the task asks for an answer (read tasks); the runner then captures the final answer."""
    #: Key intermediate states (WebCanvas-style): every checkpoint URL must have been visited for a pass.
    checkpoints: tuple[Predicate, ...] = ()
    #: Optional ground truth for the upstream judge on predicate-graded tasks (usually left unset so the
    #: judge stays a blind baseline; ``judge``-kind tasks use ``predicate.value`` instead).
    ground_truth: str | None = None
    #: Where the task came from (an upstream file or dataset id); documentation only.
    source: str | None = None

    @property
    def judge_ground_truth(self) -> str | None:
        return self.predicate.value if self.predicate.kind == "judge" else self.ground_truth

    @field_validator("checkpoints")
    @classmethod
    def _checkpoint_kinds(cls, v: tuple[Predicate, ...]) -> tuple[Predicate, ...]:
        bad = [c for c in v if c.kind != "url_contains"]
        if bad:
            raise ValueError("checkpoints are judged against visited URLs; only url_contains is supported")
        return v

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

    split: str = Field(pattern=r"^(dev|heldout|live-[a-z0-9-]+)$")
    tasks: list[Task] = Field(min_length=1)


def load_tasks(path: str | Path) -> list[Task]:
    """Load and validate a task file, rejecting duplicate ids within it."""
    raw = yaml.safe_load(Path(path).read_text())
    file = TaskFile.model_validate(raw)
    if file.split.startswith("live"):
        offenders = [t.id for t in file.tasks if not t.is_live or not t.start_url.startswith("https://")]
        if offenders:
            raise ValueError(f"{path}: live splits hold only live https tasks; offenders {offenders}")
    ids = [t.id for t in file.tasks]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError(f"duplicate task ids in {path}: {dupes}")
    return file.tasks


def load_all() -> dict[str, list[Task]]:
    """Every split that exists on disk, keyed by split name."""
    return {name: load_tasks(path) for name, path in SPLITS.items() if path.is_file()}
