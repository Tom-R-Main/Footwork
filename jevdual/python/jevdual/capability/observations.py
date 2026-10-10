"""Bounded observations and process-local offered targets for the thin slice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .contracts import CapabilityError


@dataclass(frozen=True)
class OfferedTarget:
    resource: str
    observation: str
    candidate_id: int
    label: str
    role: str
    frame: tuple[float, float, float, float] | None
    value: str
    move: str = "append"


class Observations:
    def __init__(self) -> None:
        self.targets: dict[str, OfferedTarget] = {}
        self.current: dict[str, str] = {}

    def project(
        self,
        resource: str,
        snapshot: Any,
        *,
        writable: bool,
        unavailable: dict[int, str] | None = None,
    ) -> dict[str, Any]:
        # Bound memory: retain only targets from the current observation per resource.
        self.targets = {k: v for k, v in self.targets.items() if v.resource != resource}
        observation = "obs_" + uuid4().hex
        self.current[resource] = observation
        rows = []
        unavailable = unavailable or {}
        for candidate in snapshot.menu.candidates[:50]:
            row: dict[str, Any] = {"label": candidate.label, "role": candidate.role}
            value = snapshot.values.get(candidate.id, candidate.value)
            if value is not None:
                row["value"] = value[:4096]
                row["value_truncated"] = len(value) > 4096
            if writable and "append" in candidate.operations and candidate.id in snapshot.values:
                target = "target_" + uuid4().hex
                self.targets[target] = OfferedTarget(
                    resource,
                    observation,
                    candidate.id,
                    candidate.label,
                    candidate.role,
                    snapshot.frames.get(candidate.id),
                    snapshot.values[candidate.id],
                )
                exact = snapshot.values[candidate.id]
                row.update(
                    target=target,
                    moves=["append"],
                    value_exact=True,
                    append_separator="" if not exact or exact.endswith("\n") else "\n",
                )
            else:
                row["moves"] = []
                if candidate.id in unavailable:
                    row.update(value_exact=False, unavailable_reason=unavailable[candidate.id])
            rows.append(row)
        return {
            "schema_version": "1",
            "resource": resource,
            "observation": observation,
            "title": snapshot.menu.title,
            "url": snapshot.menu.url,
            "text": snapshot.menu.page_text[:6000],
            "elements": rows,
            "coverage": {
                "elements_complete": bool(snapshot.elements_complete),
                "truncated": bool(snapshot.truncated) or len(snapshot.menu.candidates) > 50,
                "text_truncated": len(snapshot.menu.page_text) > 6000,
                "degraded": bool(snapshot.degraded),
                "omitted": snapshot.menu.omitted,
            },
            "next": "Pass new content to act; the target's append_separator is added automatically. "
            "Supplied text stays literal. Observe this resource again for readback."
            if writable
            else "Read the source value from text; bind destination to append it.",
        }

    def resolve(self, target: str) -> OfferedTarget:
        offered = self.targets.get(target)
        if offered is None:
            raise CapabilityError(
                "stale_target", "Target expired or belongs to another process; observe again"
            )
        return offered
