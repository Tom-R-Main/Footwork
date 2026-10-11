"""Small contracts for the single-process, fixture-scoped capability slice.

The host sees five tools. An offered target contains its resource, observation
and move binding; callers need not reconstruct those fields for every append.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from .completion import REPORT_SCHEMA, ReportError, check_report

Disposition = Literal["applied", "partial", "refused", "not_sent", "unknown"]
Phase = Literal["not_sent", "sent", "ambiguous"]
ReadbackOutcome = Literal["applied", "absent", "partial", "duplicate", "indeterminate"]


class CapabilityError(Exception):
    """Known no-send refusal; unexpected dispatch errors must remain unknown."""

    def __init__(self, code: str, message: str, operation_id: str | None = None):
        super().__init__(message)
        self.code = code
        self.operation_id = operation_id

    def to_result(self) -> dict[str, Any]:
        result: dict[str, Any] = {"code": self.code, "message": str(self)}
        if self.operation_id:
            result["operation_id"] = self.operation_id
        return {"schema_version": "1", "error": result}


@dataclass(frozen=True)
class Validated:
    resource: str
    observation: str
    target: str | None
    move: str
    args: dict[str, Any]
    # Private execution context, never serialized or treated as durable identity.
    context: Any = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class DispatchOutcome:
    phase: Phase
    effect_hint: str
    error: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


class Backend(Protocol):
    async def validate(
        self, resource: str, observation: str, target: str | None, move: str, args: dict[str, Any]
    ) -> Validated: ...

    async def dispatch(self, validated: Validated) -> DispatchOutcome: ...

    async def readback(self, validated: Validated) -> dict[str, Any]: ...

    def same_incarnation(self, resource: str) -> bool: ...


TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "report": {
        "description": "Validate a structured completion report against all admitted operations in this task. "
        "Reports historical execution only, never current document state, disk persistence or a broader job. "
        "Unknown operations cannot be reported completed. Never sends input or reconciles operations. "
        "The host adapter must publish only trusted_summary, not unvalidated model prose.",
        "inputSchema": REPORT_SCHEMA,
    },
    "bind": {
        "description": "Bind source or destination from the configured fixture scope. Returns an observation. "
        "Source is read-only. Destination offers append targets. No apps or tabs are created.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string", "enum": ["source", "destination"]}},
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    "observe": {
        "description": "Read a bound resource and receive fresh targets and visible values. "
        "A new observation expires its prior targets. Document readback proves field content, not disk persistence.",
        "inputSchema": {
            "type": "object",
            "properties": {"resource": {"type": "string", "minLength": 1}},
            "required": ["resource"],
            "additionalProperties": False,
        },
    },
    "act": {
        "description": "Append text once using an offered destination target. The tool adds one newline "
        "before text only when the existing field is nonempty and lacks a terminal newline; "
        "the target shows this as append_separator. Pass new content without adding that separator yourself. "
        "Supplied text is preserved literally, including intentional leading/trailing whitespace. "
        "Returns an operation ID and exact "
        "readback. Optional client_token must be unique per intended effect; reuse it only to collect or retry "
        "that same operation. Identical repeats return the original operation. After a lost "
        "reply or unknown result call status; do not issue another append to obtain a cleaner receipt.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "minLength": 1},
                "text": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 4096,
                    "description": "New content, preserved literally. The tool adds the target's "
                    "append_separator; include a leading newline only if an additional blank line is intended.",
                },
                "client_token": {"type": "string", "minLength": 1, "maxLength": 128},
            },
            "required": ["target", "text"],
            "additionalProperties": False,
        },
    },
    "status": {
        "description": "Read an operation or find this task's unresolved operations after a lost reply/restart. "
        "reconcile collects retained execution evidence and reports current agreement separately. Never repeats input. "
        "An unknown outcome blocks conflicting appends and may require an operator to inspect the document.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "minLength": 1},
                "client_token": {"type": "string", "minLength": 1, "maxLength": 128},
                "reconcile": {"type": "boolean", "default": False},
            },
            "additionalProperties": False,
        },
    },
}


def check_arguments(tool: str, arguments: Any) -> dict[str, Any]:
    """Validate the deliberately flat schemas without another schema runtime."""
    if tool not in TOOL_SCHEMAS:
        raise CapabilityError("unknown_tool", f"Unknown tool {tool!r}")
    if not isinstance(arguments, dict):
        raise CapabilityError("invalid_arguments", "Arguments must be an object")
    if tool == "report":
        try:
            return check_report(arguments)
        except ReportError as exc:
            raise CapabilityError("invalid_arguments", str(exc)) from exc
    schema = TOOL_SCHEMAS[tool]["inputSchema"]
    properties = schema["properties"]
    if set(arguments) - set(properties):
        raise CapabilityError("invalid_arguments", "Unknown argument")
    if set(schema.get("required", ())) - set(arguments):
        raise CapabilityError("invalid_arguments", "Missing required argument")
    for name, value in arguments.items():
        spec = properties[name]
        if spec["type"] == "boolean":
            if type(value) is not bool:
                raise CapabilityError("invalid_arguments", f"{name} must be a boolean")
        else:
            if not isinstance(value, str) or not value or not value.strip():
                raise CapabilityError("invalid_arguments", f"{name} must be a nonempty string")
            if len(value) > spec.get("maxLength", 4096):
                raise CapabilityError("invalid_arguments", f"{name} is too long")
            if "enum" in spec and value not in spec["enum"]:
                raise CapabilityError("invalid_arguments", f"Invalid {name}")
    if tool == "status" and "operation" in arguments and "client_token" in arguments:
        raise CapabilityError("invalid_arguments", "Choose operation or client_token")
    return arguments
