"""Strict bounded messages for the persistent loopback body adapter."""
import agent_bench
import bench
import order_protocol as storage

PROTOCOL = "footwork.body/1"
MAX_COMMANDS = 256
MAX_MEDIA = 2 * 1024 * 1024
Refusal = storage.Refusal
decode, encoded, sha = storage.decode, storage.encoded, storage.sha
fields, identity, finite = storage.fields, storage.identity, storage.finite
COMMAND_FIELDS = {"protocol", "adapter_id", "body_id", "source_sha256", "client_id", "lease_id",
                  "epoch", "command_id", "operation", "arguments"}
ENVELOPE_FIELDS = {"protocol", "adapter_id", "body_id", "source_sha256", "command_id", "request_sha256",
                   "state", "result", "reason", "receipt_scope", "recorded_epoch"}


def epoch(value):
    if type(value) is not int or not 1 <= value <= 2147483647:
        raise Refusal("boot epoch must be a positive bounded integer")
    return value


def digest(value):
    if not isinstance(value, str) or not storage.DIGEST.fullmatch(value):
        raise Refusal("SHA256 must be an exact lowercase digest")
    return value


def command_digest(request):
    return sha(encoded(request))


def validate_command(request):
    fields(request, COMMAND_FIELDS, "body command")
    if request["protocol"] != PROTOCOL:
        raise Refusal("unsupported body protocol")
    for key in ("adapter_id", "body_id", "client_id", "lease_id", "command_id"):
        identity(request[key])
    digest(request["source_sha256"])
    epoch(request["epoch"])
    operation, arguments = request["operation"], request["arguments"]
    if operation == "start_job":
        fields(arguments, ("job_id", "target_zone"), "start job")
        identity(arguments["job_id"])
        bench.validate_zone(arguments["target_zone"])
    elif operation == "observe":
        fields(arguments, (), "observe")
    elif operation == "propose":
        fields(arguments, ("challenge_id", "action", "intent", "target_x", "target_y"), "proposal")
        identity(arguments["challenge_id"])
        agent_bench.AgentBench._validate_action(arguments["action"], arguments["intent"],
                                               arguments["target_x"], arguments["target_y"])
        if arguments["action"] == "move" and not (-.32 <= arguments["target_x"] <= .18 and -.15 <= arguments["target_y"] <= .15):
            raise Refusal("proposal target exceeds the qualified pusher bounds")
    elif operation == "dispatch":
        fields(arguments, ("proposal_id",), "dispatch")
        identity(arguments["proposal_id"])
    elif operation == "disturb":
        fields(arguments, ("operation_id", "force_x_n", "steps"), "diagnostic disturbance")
        identity(arguments["operation_id"])
        force = finite(arguments["force_x_n"])
        if not 0 < abs(force) <= 2 or type(arguments["steps"]) is not int or not 1 <= arguments["steps"] <= 150:
            raise Refusal("diagnostic disturbance exceeds its bounded force or step count")
    else:
        raise Refusal("unsupported body operation")
    return request
