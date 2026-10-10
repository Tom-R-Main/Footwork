"""Portable shadow judgments. Categories are not calibrated Jev probabilities.

These contracts describe proposals and offered evidence, never execution authority.
Provider-native scores remain optional, separately attributed observations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


class JudgmentError(ValueError):
    """A bounded judgment failed its local contract (no provider content in errors)."""


@dataclass(frozen=True)
class NativeScore:
    provider: str
    model: str
    name: str
    value: float
    provenance: str

    def __post_init__(self):
        if (
            not all((self.provider, self.model, self.name, self.provenance))
            or isinstance(self.value, bool)
            or not math.isfinite(self.value)
        ):
            raise JudgmentError("native score requires finite value and provenance")


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _sources(source_ids: list[str]) -> dict[str, Any]:
    # An empty menu must permit [] while prohibiting invented source IDs.
    return {
        "type": "array",
        "items": {"type": "string", **({"enum": source_ids} if source_ids else {})},
        **({"maxItems": 0} if not source_ids else {}),
    }


def completion_schema(requirement_ids: list[str], source_ids: list[str]) -> dict[str, Any]:
    if not requirement_ids or len(set(requirement_ids)) != len(requirement_ids):
        raise JudgmentError("completion requires distinct requirement IDs")
    return _object(
        {
            "complete": {"type": "string", "enum": ["supported", "contradicted", "insufficient", "unknown"]},
            "answer_required": {"type": ["boolean", "null"]},
            "source_ids": _sources(source_ids),
            "requirements": {
                "type": "array",
                "minItems": len(requirement_ids),
                "maxItems": len(requirement_ids),
                "items": _object(
                    {
                        "id": {"type": "string", "enum": requirement_ids},
                        "verdict": {
                            "type": "string",
                            "enum": ["supported", "contradicted", "insufficient", "unknown"],
                        },
                        "source_ids": _sources(source_ids),
                    }
                ),
            },
        }
    )


def risk_schema(source_ids: list[str]) -> dict[str, Any]:
    return _object(
        {
            "effect": {"type": "string", "enum": ["harmful", "benign", "unknown"]},
            "permission_required": {"type": ["boolean", "null"]},
            "source_ids": _sources(source_ids),
        }
    )


def proposal_schema(menu_pairs: list[tuple[str, str | None]], revision: str) -> dict[str, Any]:
    operations = list(dict.fromkeys(op for op, _ in menu_pairs))
    targets = list(dict.fromkeys(target for _, target in menu_pairs if target is not None))
    return _object(
        {
            "decision": {"type": "string", "enum": ["propose", "abstain", "unknown"]},
            "revision": {"type": "string", "enum": [revision]},
            "operation": {"type": ["string", "null"], "enum": [*operations, None]},
            "target_id": {"type": ["string", "null"], "enum": [*targets, None]},
        }
    )


def validate_schema(value: Any, schema: dict[str, Any]) -> None:
    """Validate the closed schema subset used by the shadow harness.

    Unsupported schema keywords fail before dispatch; silently skipping constraints
    would make a valid-looking completion unsafe to use.
    """
    check_schema(schema)
    if "anyOf" in schema:
        for option in schema["anyOf"]:
            try:
                validate_schema(value, option)
                break
            except JudgmentError:
                continue
        else:
            raise JudgmentError("judgment does not match schema alternatives")
    kinds = schema.get("type")
    kinds = kinds if isinstance(kinds, list) else [kinds]
    matches = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value),
        "null": value is None,
    }
    if kinds != [None] and not any(matches.get(kind, False) for kind in kinds):
        raise JudgmentError("judgment type mismatch")
    if "enum" in schema and not any(type(value) is type(item) and value == item for item in schema["enum"]):
        raise JudgmentError("judgment outside enum")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is not False or set(schema.get("required", [])) != set(
            properties
        ):
            raise JudgmentError("judgment object schema must be closed and fully required")
        if set(value) != set(properties):
            raise JudgmentError("judgment fields mismatch")
        for key, item in value.items():
            validate_schema(item, properties[key])
    if isinstance(value, list):
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", math.inf):
            raise JudgmentError("judgment array length mismatch")
        if "items" not in schema:
            raise JudgmentError("judgment array requires item schema")
        for item in value:
            validate_schema(item, schema["items"])


def check_schema(schema: dict[str, Any]) -> None:
    supported = {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "enum",
        "anyOf",
        "minItems",
        "maxItems",
        "description",
        "title",
    }
    if not isinstance(schema, dict) or set(schema) - supported:
        raise JudgmentError("unsupported judgment schema keyword")
    kinds = schema.get("type", [])
    kinds = kinds if isinstance(kinds, list) else [kinds]
    allowed_types = {"object", "array", "string", "boolean", "integer", "number", "null"}
    if not set(kinds) <= allowed_types or (not kinds and not schema.get("anyOf")):
        raise JudgmentError("judgment schema requires supported type or alternatives")
    if "object" in kinds:
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is not False or set(schema.get("required", [])) != set(props):
            raise JudgmentError("judgment object schema must be closed and fully required")
        for child in props.values():
            check_schema(child)
    if "array" in kinds:
        if "items" not in schema:
            raise JudgmentError("judgment array requires item schema")
        check_schema(schema["items"])
    for alternative in schema.get("anyOf", []):
        check_schema(alternative)


def validate_completion(value: dict[str, Any], requirement_ids: list[str], source_ids: list[str]) -> None:
    validate_schema(value, completion_schema(requirement_ids, source_ids))
    if {r["id"] for r in value["requirements"]} != set(requirement_ids):
        raise JudgmentError("judgment requirement bindings mismatch")
    if len(set(value["source_ids"])) != len(value["source_ids"]):
        raise JudgmentError("duplicate evidence binding")
    if value["complete"] == "supported" and not value["source_ids"]:
        raise JudgmentError("supported completion requires offered evidence")
    for requirement in value["requirements"]:
        if len(set(requirement["source_ids"])) != len(requirement["source_ids"]):
            raise JudgmentError("duplicate evidence binding")
        if requirement["verdict"] == "supported" and not requirement["source_ids"]:
            raise JudgmentError("supported judgment requires offered evidence")


def validate_proposal(value: dict[str, Any], menu_pairs: list[tuple[str, str | None]], revision: str) -> None:
    validate_schema(value, proposal_schema(menu_pairs, revision))
    pair = (value["operation"], value["target_id"])
    if value["decision"] == "propose":
        if pair not in menu_pairs:
            raise JudgmentError("proposal operation-target pair not offered")
    elif pair != (None, None):
        raise JudgmentError("abstain or unknown must not propose an action")


def validate_risk(value: dict[str, Any], source_ids: list[str]) -> None:
    validate_schema(value, risk_schema(source_ids))
    if len(set(value["source_ids"])) != len(value["source_ids"]):
        raise JudgmentError("duplicate evidence binding")


def completion_admissible(value: dict[str, Any], requirement_ids: list[str], source_ids: list[str]) -> bool:
    """Experimental categorical bridge; shared deterministic floors still follow."""
    validate_completion(value, requirement_ids, source_ids)
    return (
        value["complete"] == "supported"
        and value["answer_required"] is not None
        and all(r["verdict"] == "supported" for r in value["requirements"])
    )
