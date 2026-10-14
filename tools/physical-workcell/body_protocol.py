"""Compatibility facade for the strict simulated bench body protocol.

New adapters use body_contract plus their explicit operation schemas; this
facade retains the existing bench vocabulary and bounds.
"""
import body_contract as contract
from bench_body_contract import MAX_MEDIA, validate_arguments
from body_contract import (
    COMMAND_FIELDS,
    ENVELOPE_FIELDS,
    MAX_COMMANDS,
    PROTOCOL,
    Refusal,
    command_digest,
    decode,
    digest,
    encoded,
    epoch,
    fields,
    finite,
    identity,
    sha,
)

__all__ = ["COMMAND_FIELDS", "ENVELOPE_FIELDS", "MAX_COMMANDS", "MAX_MEDIA", "PROTOCOL", "Refusal",
           "command_digest", "decode", "digest", "encoded", "epoch", "fields", "finite", "identity", "sha",
           "validate_command"]


def validate_command(request):
    contract.validate_command(request)
    validate_arguments(request["operation"], request["arguments"])
    return request
