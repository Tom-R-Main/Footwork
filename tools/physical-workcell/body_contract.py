"""Device-independent bounded identity, lease, command and receipt schemas.

Operation arguments and lower-proof semantics belong to an explicit adapter
contract. Nothing here imports a simulator or grants physical authority.
"""
import order_protocol as storage

PROTOCOL = "footwork.body/1"
MAX_COMMANDS = 256
Refusal = storage.Refusal
decode, encoded, sha = storage.decode, storage.encoded, storage.sha
fields, identity, finite = storage.fields, storage.identity, storage.finite
PIN_KEYS = {"protocol", "adapter_id", "body_id", "source_sha256"}
IDENTITY_FIELDS = PIN_KEYS | {"epoch", "simulation"}
COMMAND_FIELDS = PIN_KEYS | {"client_id", "lease_id", "epoch", "command_id", "operation", "arguments"}
ENVELOPE_FIELDS = PIN_KEYS | {"command_id", "request_sha256", "state", "result", "reason", "receipt_scope", "recorded_epoch"}
RECEIPT_STATES = {"completed", "refused", "unknown", "not_seen", "not_accepted"}
TERMINAL_STATES = {"completed", "refused", "not_accepted"}
RECEIPT_SCOPE = "retained_command_result"


def epoch(value):
    if type(value) is not int or not 1 <= value <= 2147483647:
        raise Refusal("boot epoch must be a positive bounded integer")
    return value


def digest(value):
    if not isinstance(value, str) or not storage.DIGEST.fullmatch(value):
        raise Refusal("SHA256 must be an exact lowercase digest")
    return value


def validate_identity(value):
    fields(value, IDENTITY_FIELDS, "body identity")
    if value["protocol"] != PROTOCOL or value["simulation"] is not True:
        raise Refusal("unsupported body protocol or simulation identity")
    for key in ("adapter_id", "body_id"):
        identity(value[key])
    digest(value["source_sha256"])
    epoch(value["epoch"])
    return value


def command_digest(request):
    return sha(encoded(request))


def validate_command(request):
    fields(request, COMMAND_FIELDS, "body command")
    if request["protocol"] != PROTOCOL:
        raise Refusal("unsupported body protocol")
    for key in ("adapter_id", "body_id", "client_id", "lease_id", "command_id", "operation"):
        identity(request[key])
    digest(request["source_sha256"])
    epoch(request["epoch"])
    if not isinstance(request["arguments"], dict):
        raise Refusal("operation arguments must be an object")
    return request


def validate_lease_request(value):
    fields(value, ("client_id", "expected_epoch", "duration_s"), "lease request")
    identity(value["client_id"])
    epoch(value["expected_epoch"])
    duration = finite(value["duration_s"])
    if not .05 <= duration <= 30:
        raise Refusal("lease duration must be between 0.05 and 30 seconds")
    return duration


def validate_reconcile(value):
    fields(value, ("client_id", "lease_id", "epoch", "request_sha256"), "reconcile query")
    for key in ("client_id", "lease_id"):
        identity(value[key])
    epoch(value["epoch"])
    digest(value["request_sha256"])
    return value


def validate_envelope(value, request, request_sha256):
    fields(value, ENVELOPE_FIELDS, "command result envelope")
    for key in PIN_KEYS | {"command_id"}:
        if value[key] != request[key]:
            raise Refusal("command result identity changed")
    digest(value["request_sha256"])
    if (value["request_sha256"] != request_sha256 or value["receipt_scope"] != RECEIPT_SCOPE or
            not isinstance(value["state"], str) or value["state"] not in RECEIPT_STATES):
        raise Refusal("command result digest, scope or state is invalid")
    epoch(value["recorded_epoch"])
    if value["recorded_epoch"] != request["epoch"]:
        raise Refusal("historical command epoch changed")
    if value["reason"] is not None and not isinstance(value["reason"], str):
        raise Refusal("command reason must be text or null")
    if value["result"] is not None and not isinstance(value["result"], dict):
        raise Refusal("command result must be an object or null")
    if value["state"] == "completed" and not isinstance(value["result"], dict):
        raise Refusal("completed command needs its typed result")
    return value


def terminal(value, lower_unknown):
    """A lower unresolved effect cannot be cleared by a completed outer receipt."""
    if type(lower_unknown) is not bool:
        raise Refusal("operation contract must classify unresolved effects explicitly")
    return value["state"] in TERMINAL_STATES and not lower_unknown
