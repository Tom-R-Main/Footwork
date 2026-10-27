"""Bench-specific operation and proof schemas layered on the shared body wire."""
import order_protocol as storage

Refusal = storage.Refusal
MAX_MEDIA = 2 * 1024 * 1024


def validate_arguments(operation, arguments):
    if operation == "start_job":
        storage.fields(arguments, ("job_id", "target_zone"), "start job")
        storage.identity(arguments["job_id"])
        validate_zone(arguments["target_zone"])
    elif operation == "observe":
        storage.fields(arguments, (), "observe")
    elif operation == "propose":
        storage.fields(arguments, ("challenge_id", "action", "intent", "target_x", "target_y"), "proposal")
        storage.identity(arguments["challenge_id"])
        validate_action(arguments["action"], arguments["intent"],
                        arguments["target_x"], arguments["target_y"])
        if arguments["action"] == "move" and not (-.32 <= arguments["target_x"] <= .18 and -.15 <= arguments["target_y"] <= .15):
            raise Refusal("proposal target exceeds the qualified pusher bounds")
    elif operation == "dispatch":
        storage.fields(arguments, ("proposal_id",), "dispatch")
        storage.identity(arguments["proposal_id"])
    elif operation == "disturb":
        storage.fields(arguments, ("operation_id", "force_x_n", "steps"), "diagnostic disturbance")
        storage.identity(arguments["operation_id"])
        force = storage.finite(arguments["force_x_n"])
        if not 0 < abs(force) <= 2 or type(arguments["steps"]) is not int or not 1 <= arguments["steps"] <= 150:
            raise Refusal("diagnostic disturbance exceeds its bounded force or step count")
    else:
        raise Refusal("unsupported body operation")
    return arguments



def validate_zone(zone):
    storage.validate_zone(zone)
    if not (.02 <= zone["x_min"] < zone["x_max"] <= .12 and
            -.03 <= zone["y_min"] < zone["y_max"] <= .03 and
            zone["x_max"] - zone["x_min"] >= .04 and zone["y_max"] - zone["y_min"] >= .04):
        raise Refusal("job zone exceeds the qualified reachable center region")
    return dict(zone)


def validate_action(action, intent, x, y):
    if action not in {"move", "measure", "begin_reset", "finish_reset"} or not isinstance(intent, str) or not 1 <= len(intent.strip()) <= 2000:
        raise Refusal("proposal requires a supported action and bounded AI intent")
    if action == "move":
        return storage.finite(x), storage.finite(y)
    if x is not None or y is not None:
        raise Refusal("only move accepts target coordinates")
    return None, None


def challenge_packet(pinned, challenge):
    storage.fields(challenge, ("challenge_id", "session_id", "sequence", "observation_sha256",
                               "observation", "task", "image_path"), "body challenge")
    storage.identity(challenge["challenge_id"])
    packet = challenge["observation"]
    if (not isinstance(packet, dict) or not isinstance(challenge["image_path"], str) or
            storage.sha(storage.encoded(packet)) != challenge["observation_sha256"] or
            packet.get("bench_id") != pinned["body_id"] or
            not isinstance(packet.get("image_sha256"), str) or not storage.DIGEST.fullmatch(packet["image_sha256"]) or
            challenge["image_path"] != packet.get("image_path")):
        raise Refusal("body image challenge binding changed")
    return packet


class BenchOperations:
    """Required schema hooks for the reusable single-send client."""
    validate_arguments = staticmethod(validate_arguments)

    @staticmethod
    def is_unknown(result):
        return isinstance(result, dict) and result.get("outcome") == "unknown"

    @staticmethod
    def validate_result(request, result, pinned):
        operation = request["operation"]
        if operation == "observe":
            challenge_packet(pinned, result)
        elif operation == "dispatch":
            if (result.get("proposal_id") != request["arguments"]["proposal_id"] or
                    not isinstance(result.get("outcome"), str) or result["outcome"] not in {"executed", "refused", "unknown"}):
                raise Refusal("dispatch result identity or outcome changed")
            if result.get("next_observation") is not None:
                challenge_packet(pinned, result["next_observation"])
        elif operation == "propose":
            if not isinstance(result.get("proposal_id"), str) or result.get("challenge_id") != request["arguments"]["challenge_id"]:
                raise Refusal("proposal result identity changed")
            storage.identity(result["proposal_id"])
        elif result.get("bench_id") != pinned["body_id"]:
            raise Refusal("body result identity changed")
