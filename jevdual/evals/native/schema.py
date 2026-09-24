"""Native task files: one application window, a deterministic setup, an oracle solution, a predicate.

A native task is graded by its predicate against observed end state (the window's text, a file
in the task's temp folder, the returned answer, which controls were pressed), never by the
agent's claim. Every task carries a ``solve`` script; the runner's ``--oracle`` mode replays it
and a task is admitted to a split only when its own oracle passes its predicate (cua-bench's
``@solve_task`` rule).

``{tmp}`` in ``open``, ``files`` and predicate paths is the task run's private folder under
``$TMPDIR/jevdual-native/<task>-<run>``; nothing outside it is written.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

Tag = Literal[
    "click",
    "type",
    "enter",
    "menu",
    "key",
    "read",
    "multistep",
    "consent",
    "destructive",
    "dialog",
    "navigate",
    "electron",
]
PredicateKind = Literal[
    "window_text_contains",
    "answer_contains",
    "answer_equals",
    "file_contains",
    "file_exists",
    "not_clicked",
    "expect",
]

TASKS_DIR = Path(__file__).parent / "tasks"
SPLITS: dict[str, Path] = {"dev": TASKS_DIR / "dev.yaml", "heldout": TASKS_DIR / "heldout.yaml"}


class NativePredicate(BaseModel):
    """Completion check on the end state.

    - ``window_text_contains``: the final window's static text and field values contain ``value``.
    - ``answer_contains`` / ``answer_equals``: the returned answer contains / equals ``value``.
    - ``file_contains``: the file at ``path`` (``{tmp}`` allowed) contains ``value``.
    - ``file_exists``: the file at ``path`` exists; ``value`` is ``"true"`` or ``"false"``.
    - ``not_clicked``: no executed click landed on a control whose label contains ``value`` and the
      run did not report done (consent tasks that must pause before the irreversible control).
    - ``expect``: a Cua Driver ``verify_state`` element predicate, ``value`` as
      ``role=AXStaticText;label_contains=72`` (keys role, label_contains, value_equals, enabled,
      selected); passes only on ``satisfied``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: PredicateKind
    value: str = Field(min_length=1)
    path: str | None = None

    @field_validator("path")
    @classmethod
    def _path_for_file_kinds(cls, v: str | None, info):  # type: ignore[no-untyped-def]
        return v


class NativeTask(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    task: str = Field(min_length=8)
    #: application display name as ``list_apps`` reports it, and its bundle id for launching
    app: str
    bundle_id: str
    #: files or URLs opened with the app at launch (``{tmp}`` allowed)
    open: tuple[str, ...] = ()
    #: files created in the task folder before launch: name -> content
    files: dict[str, str] = Field(default_factory=dict)
    #: kill the app after the run (single-instance apps keep state between tasks otherwise)
    relaunch: bool = True
    #: the window to bind: title substring; empty binds the largest titled on-screen window
    window_title: str = ""
    tags: tuple[Tag, ...] = Field(min_length=1)
    requirements: tuple[str, ...] = Field(min_length=1)
    predicate: NativePredicate
    answer_expected: bool = False
    #: oracle script, one step per line: ``click <label>``, ``type <label> <text>``, ``enter <label>``,
    #: ``key <chord>`` (background), ``hotkey <chord>`` (foreground), ``menu File>Save`` (foreground),
    #: ``wait <seconds>``, ``answer <text>``; labels match a candidate label, then a role, then a substring
    solve: tuple[str, ...] = Field(min_length=1)
    secrets: dict[str, str] = Field(default_factory=dict)
    authorize: bool = False
    authorized_actions: tuple[str, ...] = ()
    source: str | None = None

    @field_validator("predicate")
    @classmethod
    def _file_predicates_need_path(cls, v: NativePredicate) -> NativePredicate:
        if v.kind in ("file_contains", "file_exists") and not v.path:
            raise ValueError(f"{v.kind} needs a path")
        return v


class NativeTaskFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    split: str = Field(pattern=r"^(dev|heldout)$")
    tasks: list[NativeTask] = Field(min_length=1)


def load_tasks(path: str | Path) -> list[NativeTask]:
    raw = yaml.safe_load(Path(path).read_text())
    file = NativeTaskFile.model_validate(raw)
    ids = [t.id for t in file.tasks]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError(f"duplicate task ids in {path}: {dupes}")
    return file.tasks


def parse_expect(value: str) -> dict[str, str]:
    """``role=AXStaticText;label_contains=72`` -> {"role": ..., "label_contains": ...}."""
    out: dict[str, str] = {}
    for part in value.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"expect predicate part {part!r} has no '='")
        k, v = part.split("=", 1)
        k = k.strip()
        if k not in ("role", "label_contains", "value_equals", "enabled", "selected"):
            raise ValueError(f"unknown expect key {k!r}")
        out[k] = v.strip()
    if not out:
        raise ValueError("empty expect predicate")
    return out
