"""RGB-only planner evidence and guarded proposals around unchanged SIM1 dynamics."""

import argparse
import contextlib
import importlib.util
import json
import struct
import sys
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

import mujoco
import numpy as np

BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("sim1_body", BASE / "workcell.py")
body = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(body)
Refusal = body.Refusal
SCHEMA = BASE / "proposal.schema.json"
SETTINGS = {"width": 640, "height": 360, "vertical_span_m": 0.6, "camera_z_m": 1.0,
            "box_tolerance_px": 8, "silhouette_size_tolerance_px": 8, "min_fill": 0.8,
            "component_min_pixels": 20, "edge_guard_px": 2,
            "max_forward_m": 0.12, "min_forward_m": 0.005, "target_y_limit_m": 0.01,
            "pusher_y_limit_m": 0.02, "completion_margin_m": 0.005}
SOURCE_KIND = "mujoco_simulation"


def fingerprint():
    return {"wrapper_sha256": body.sha(body.read_bytes(Path(__file__))),
            "schema_sha256": body.sha(body.read_bytes(SCHEMA)), "settings_sha256": body.sha(body.encoded(SETTINGS)),
            "base_fingerprints": body.fingerprints()}


def binding(root, manifest):
    expected = {"source_kind": SOURCE_KIND, "run_dir": str(root), "fingerprint": fingerprint(),
                "work_order_sha256": manifest["work_order_sha256"]}
    path = root / "vision-binding.json"
    if path.exists() or path.is_symlink():
        if body.decoded(body.read_bytes(path)) != expected:
            raise Refusal("image wrapper/schema/settings/source binding changed")
    else:
        body.create_file(path, body.encoded(expected))
    return expected


def image_paths(root, generation):
    return root / f"vision-frame-{generation:06d}.png", root / f"vision-view-{generation:06d}.json"


def proposal_path(root, token):
    body.op_path(root, token)  # Validate token without reserving a SIM1 operation.
    return root / f"vision-op-{body.sha(token.encode())}.json"


def load_proposal_record(path):
    record = body.decoded(body.read_bytes(path))
    if not isinstance(record, dict) or not isinstance(record.get("phase"), str) or record["phase"] not in {"pending", "unknown", "executed", "staged"}:
        raise Refusal("image proposal receipt is malformed")
    if not isinstance(record.get("proposal"), dict) or not isinstance(record.get("proposal_sha256"), str):
        raise Refusal("image proposal identity is malformed")
    proposal = schema(record["proposal"], path.parent)
    if record.get("source_kind") != SOURCE_KIND or proposal_path(path.parent, proposal["token"]) != path or not body.DIGEST.fullmatch(record["proposal_sha256"]):
        raise Refusal("image proposal token/file/source binding is invalid")
    bound = body.decoded(body.read_bytes(path.parent / "vision-binding.json"))
    if record.get("binding") != bound or bound.get("fingerprint") != fingerprint() or bound.get("run_dir") != str(path.parent):
        raise Refusal("retained image proposal fingerprint/binding changed")
    request_path = path.parent / f"vision-request-{body.sha(proposal['token'].encode())}.json"
    if request_path.exists() or record["phase"] in {"executed", "staged"}:
        content = body.read_bytes(request_path)
        if body.sha(content) != record["proposal_sha256"] or body.decoded(content) != proposal:
            raise Refusal("retained proposal bytes or digest changed")
    if record["phase"] in {"executed", "staged"}:
        native = body.load_op(body.op_path(path.parent, "vision-" + body.sha(proposal["token"].encode())))
        if native["phase"] != record["phase"] or record["phase"] != ("executed" if proposal["decision"] == "move" else "staged"):
            raise Refusal("image receipt does not match its retained native operation")
        if proposal["decision"] == "move":
            native_request = {"kind": "act", "expected_generation": proposal["generation"],
                              "target_x": proposal["target"]["x"], "target_y": proposal["target"]["y"]}
            after_generation, after_hash = native.get("after_generation"), native.get("after_state_sha256")
        else:
            native_request = {"kind": "complete", "work_order_sha256": bound["work_order_sha256"]}
            after_generation, after_hash = proposal["generation"], native.get("state_sha256")
        if native["request"] != native_request or record.get("after_generation") != after_generation or record.get("after_state_sha256") != after_hash:
            raise Refusal("historical native arguments or resulting state changed")
        image_path, view_path = image_paths(path.parent, proposal["generation"])
        frame = body.decoded(body.read_bytes(view_path))
        image = body.read_bytes(image_path)
        if (not isinstance(frame, dict) or frame.get("phase") != "ready" or frame.get("binding") != bound or
                frame.get("image_sha256") != proposal["image_sha256"] or body.sha(image) != proposal["image_sha256"]):
            raise Refusal("historical image source no longer matches its receipt")
        detected = locate(decode_png(image))
        visual = {"method": "color_specific_RGB", "block_box": detected["block"]["box"],
                  "image_center_world_xy": image_world_center(detected["block"]["box"])}
        if proposal["decision"] == "complete":
            visual["inside_with_margin"] = True
            if record.get("artifact_check") != native.get("artifact_check"):
                raise Refusal("historical software check changed")
        elif record.get("contact_statistics") != native.get("controller_evidence"):
            raise Refusal("historical contact evidence changed")
        if record.get("visual_check") != visual:
            raise Refusal("historical visual evidence changed")
    return record


def wrapper_unresolved(root):
    return any(load_proposal_record(path)["phase"] in {"pending", "unknown"} for path in root.glob("vision-op-*.json"))


def calibration():
    return {"projection": "orthographic", "width": 640, "height": 360, "vertical_span_m": 0.6,
            "world_frame": "sim_world", "image_x_direction": "world_positive_x", "image_y_direction": "world_negative_y",
            "meters_per_pixel": SETTINGS["vertical_span_m"] / SETTINGS["height"],
            "image_center_world_xy": [0.0, 0.0], "bbox_convention": "exclusive_max_pixel_edges"}


def camera_xml(root):
    tree = ET.fromstring(body.read_bytes(root / "model.xml"))
    ET.SubElement(tree.find("worldbody"), "camera", {"name": "vision_top", "projection": "orthographic",
                  "fovy": str(SETTINGS["vertical_span_m"]), "pos": "0 0 1", "xyaxes": "1 0 0 0 1 0"})
    return ET.tostring(tree, encoding="unicode")


def render_rgb(root, loaded):
    _, order, original_model, original_data = loaded
    render_xml = camera_xml(root)
    model = mujoco.MjModel.from_xml_string(render_xml)
    zone = order["target_zone"]
    marker = model.geom("inspection_zone")
    marker.pos[:2] = [(zone["x_min"] + zone["x_max"]) / 2, (zone["y_min"] + zone["y_max"]) / 2]
    marker.size[:2] = [(zone["x_max"] - zone["x_min"]) / 2, (zone["y_max"] - zone["y_min"]) / 2]
    spec = mujoco.mjtState.mjSTATE_INTEGRATION
    size = mujoco.mj_stateSize(original_model, spec)
    if size != mujoco.mj_stateSize(model, spec):
        raise Refusal("camera-only model changed native integration dimensions")
    state = np.empty(size)
    mujoco.mj_getState(original_model, original_data, state, spec)
    data = mujoco.MjData(model)
    mujoco.mj_setState(model, data, state, spec)
    mujoco.mj_forward(model, data)
    try:
        with mujoco.Renderer(model, height=SETTINGS["height"], width=SETTINGS["width"]) as renderer:
            renderer.update_scene(data, camera="vision_top")
            image = renderer.render().copy()
    except Exception as exc:
        raise Refusal("native RGB renderer unavailable; no image was fabricated") from exc
    return image, body.sha(render_xml.encode())


def decode_png(content):
    if not content.startswith(b"\x89PNG\r\n\x1a\n") or len(content) > body.MAX_FILE:
        raise Refusal("image is not a bounded PNG")
    offset, compressed, header, ended = 8, bytearray(), None, False
    while offset < len(content):
        if offset + 12 > len(content):
            raise Refusal("PNG chunk is truncated")
        length = struct.unpack(">I", content[offset:offset + 4])[0]
        kind = content[offset + 4:offset + 8]
        end = offset + 8 + length
        if end + 4 > len(content) or length > body.MAX_FILE:
            raise Refusal("PNG chunk length is invalid")
        data = content[offset + 8:end]
        if struct.unpack(">I", content[end:end + 4])[0] != zlib.crc32(kind + data):
            raise Refusal("PNG chunk checksum mismatch")
        if kind == b"IHDR":
            if header is not None or length != 13:
                raise Refusal("PNG header is invalid")
            header = struct.unpack(">IIBBBBB", data)
        elif kind == b"IDAT":
            compressed.extend(data)
        elif kind == b"IEND":
            if length != 0 or end + 4 != len(content):
                raise Refusal("PNG end or trailing bytes are invalid")
            ended = True
        else:
            raise Refusal("unexpected PNG chunk")
        offset = end + 4
    if header != (640, 360, 8, 2, 0, 0, 0) or not ended:
        raise Refusal("PNG is not the calibrated RGB format")
    expected = 360 * (640 * 3 + 1)
    decoder = zlib.decompressobj()
    try:
        raw = decoder.decompress(bytes(compressed), expected + 1)
    except zlib.error as exc:
        raise Refusal("PNG pixels could not be decoded") from exc
    if len(raw) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise Refusal("PNG decompression exceeds or fails calibrated dimensions")
    rows = np.frombuffer(raw, dtype=np.uint8).reshape(360, 640 * 3 + 1)
    if np.any(rows[:, 0] != 0):
        raise Refusal("PNG row filter is unsupported")
    return rows[:, 1:].copy().reshape(360, 640, 3)


def components(mask):
    visited = np.zeros(mask.shape, dtype=bool)
    regions = []
    for row, column in np.argwhere(mask):
        if visited[row, column]:
            continue
        stack, points = [(int(row), int(column))], []
        visited[row, column] = True
        while stack:
            y, x = stack.pop()
            points.append((y, x))
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    stack.append((ny, nx))
        if len(points) >= SETTINGS["component_min_pixels"]:
            ys, xs = zip(*points, strict=True)
            regions.append({"box": [min(xs), min(ys), max(xs) + 1, max(ys) + 1], "pixels": len(points)})
    return regions


def silhouette(mask, name, expected_width, expected_height):
    regions = components(mask)
    if len(regions) != 1:
        raise Refusal(f"RGB {name} evidence is absent or ambiguous")
    region = regions[0]
    left, top, right, bottom = region["box"]
    width, height = right - left, bottom - top
    margin = SETTINGS["edge_guard_px"]
    tolerance = SETTINGS["silhouette_size_tolerance_px"]
    if (left <= margin or top <= margin or right >= 640 - margin or bottom >= 360 - margin or
            abs(width - expected_width) > tolerance or abs(height - expected_height) > tolerance or
            region["pixels"] / (width * height) < SETTINGS["min_fill"]):
        raise Refusal(f"RGB {name} silhouette is incomplete, off-frame or implausible")
    return region


def locate(image):
    if image.shape != (360, 640, 3) or image.dtype != np.uint8:
        raise Refusal("RGB image does not match calibration")
    red, green, blue = image.astype(np.float32).transpose(2, 0, 1)
    orange = (red >= 80) & (red >= 1.3 * green) & (green >= 1.35 * blue)
    blue_mask = (blue >= 80) & (blue >= 1.15 * green) & (green >= 1.3 * red)
    scale = calibration()["meters_per_pixel"]
    return {"block": silhouette(orange, "block", .07 / scale, .07 / scale),
            "pusher": silhouette(blue_mask, "pusher", .04 / scale, .14 / scale)}


def image_world_center(box):
    left, top, right, bottom = box
    scale = calibration()["meters_per_pixel"]
    return [((left + right) / 2 - 320) * scale, (180 - (top + bottom) / 2) * scale]


def view(root):
    loaded = body.load(root)
    manifest, order, _, _ = loaded
    bind = binding(root, manifest)
    if body.unresolved(root, manifest) or wrapper_unresolved(root):
        raise Refusal("unresolved simulator or image proposal blocks fresh planner evidence")
    generation = manifest["generation"]
    image_path, receipt_path = image_paths(root, generation)
    if receipt_path.exists() or receipt_path.is_symlink():
        receipt = body.decoded(body.read_bytes(receipt_path))
        return checked_view(root, loaded, receipt)
    if image_path.exists() or image_path.is_symlink():
        raise Refusal("unreceipted image exists; it will not be overwritten or promoted")
    pending = {"source_kind": SOURCE_KIND, "phase": "pending", "generation": generation,
               "state_sha256": manifest["state_sha256"], "binding": bind}
    body.utils.persist(receipt_path, pending)
    image, render_model_sha = render_rgb(root, loaded)
    locate(image)  # Full visibility is an evidence prerequisite, not a task outcome.
    content = body.png_bytes(image)
    body.create_file(image_path, content)
    packet = {"source_kind": SOURCE_KIND, "phase": "ready", "run_dir": str(root), "generation": generation,
              "image_path": str(image_path), "image_sha256": body.sha(content), "state_sha256": manifest["state_sha256"],
              "binding": bind, "calibration": calibration(), "render_model_sha256": render_model_sha,
              "task_intent": {k: order[k] for k in ("order_id", "project", "part_id", "target_zone")},
              "perception_scope": "color_specific_RGB; current agent supplies proposals", "proposal_schema_path": str(SCHEMA)}
    body.utils.persist(receipt_path, packet)
    return checked_view(root, loaded, packet)


def checked_view(root, loaded, receipt):
    manifest, order = loaded[:2]
    if not isinstance(receipt, dict) or receipt.get("phase") != "ready":
        raise Refusal("image intent has no complete receipt; it cannot be rerendered or promoted")
    body.fields(receipt, ("source_kind", "phase", "run_dir", "generation", "image_path", "image_sha256",
                         "state_sha256", "binding", "calibration", "render_model_sha256", "task_intent",
                         "perception_scope", "proposal_schema_path"), "retained planner image packet")
    if (receipt.get("generation") != manifest["generation"] or receipt.get("state_sha256") != manifest["state_sha256"] or
            receipt.get("binding") != binding(root, manifest) or receipt.get("calibration") != calibration()):
        raise Refusal("image generation/state/calibration/source binding is stale or changed")
    if (receipt.get("source_kind") != SOURCE_KIND or receipt.get("run_dir") != str(root) or
            receipt.get("task_intent") != {k: order[k] for k in ("order_id", "project", "part_id", "target_zone")} or
            receipt.get("proposal_schema_path") != str(SCHEMA) or
            receipt.get("render_model_sha256") != body.sha(camera_xml(root).encode()) or
            receipt.get("perception_scope") != "color_specific_RGB; current agent supplies proposals"):
        raise Refusal("retained planner task/run/render metadata changed")
    image_path, _ = image_paths(root, manifest["generation"])
    content = body.read_bytes(image_path)
    if receipt.get("image_path") != str(image_path) or body.sha(content) != receipt.get("image_sha256"):
        raise Refusal("retained image is missing or changed")
    locate(decode_png(content))
    return receipt


def schema(proposal, root):
    if not isinstance(proposal, dict) or proposal.get("decision") not in {"move", "complete"}:
        raise Refusal("proposal decision is invalid")
    keys = ["version", "run_dir", "generation", "image_sha256", "token", "block_box", "decision"]
    if proposal["decision"] == "move":
        keys.append("target")
    body.fields(proposal, keys, "image proposal")
    if type(proposal["version"]) is not int or proposal["version"] != 1 or proposal["run_dir"] != str(root):
        raise Refusal("proposal version or exact run binding is invalid")
    if type(proposal["generation"]) is not int or not 0 <= proposal["generation"] <= 999999:
        raise Refusal("proposal generation is invalid")
    if not isinstance(proposal["image_sha256"], str) or not body.DIGEST.fullmatch(proposal["image_sha256"]):
        raise Refusal("proposal image digest is invalid")
    proposal_path(root, proposal["token"])
    box = proposal["block_box"]
    if not isinstance(box, list) or len(box) != 4 or any(type(value) is not int for value in box):
        raise Refusal("proposed block box must contain four integer pixel edges")
    if not 0 <= box[0] < box[2] <= 640 or not 0 <= box[1] < box[3] <= 360:
        raise Refusal("proposed block box is outside the image or malformed")
    if proposal["decision"] == "move":
        body.fields(proposal["target"], ("x", "y"), "pusher target")
        x, y = (body.number(proposal["target"][axis]) for axis in ("x", "y"))
        if not body.CONTROLLER["x_min"] <= x <= body.CONTROLLER["x_max"] or abs(y) > SETTINGS["target_y_limit_m"]:
            raise Refusal("pusher target is outside the admitted forward-motion envelope")
    return proposal


def public_receipt(record, root=None, manifest=None):
    result = {"source_kind": SOURCE_KIND, "perception": "color_specific_RGB", "token": record["proposal"]["token"],
              "decision": record["proposal"]["decision"], "phase": record["phase"], "historical_phase": record["phase"],
              "receipt_scope": "historical_operation",
              "image_generation": record["proposal"]["generation"], "image_sha256": record["proposal"]["image_sha256"],
              "replayed": False, "fresh_view_required": record["phase"] == "executed"}
    for key in ("after_generation", "after_state_sha256"):
        if key in record:
            result[key] = record[key]
    if record["proposal"]["decision"] == "move":
        result["command"] = dict(record["proposal"]["target"])
    if isinstance(record.get("contact_statistics"), dict):
        result["contact_statistics"] = {key: record["contact_statistics"][key] for key in
            ("native_steps", "pusher_block_contact_samples", "max_axis_actuator_force_n", "command_speed_limit_m_s")
            if key in record["contact_statistics"]}
    if isinstance(record.get("visual_check"), dict):
        result["historical_visual_check"] = {key: record["visual_check"][key] for key in
            ("method", "block_box", "image_center_world_xy", "inside_with_margin") if key in record["visual_check"]}
    if isinstance(record.get("artifact_check"), dict):
        result["historical_software_artifact_check"] = {key: record["artifact_check"][key] for key in
            ("ok", "expected_sha256", "source_sha256", "observed_sha256", "expected_bytes", "observed_bytes")
            if key in record["artifact_check"]}
        result["historical_software_artifact_check"]["historical"] = True
    if record["phase"] in {"pending", "unknown"}:
        result.update(phase="unknown", reason="image proposal outcome is unresolved; no effects are replayed")
    if root is not None and manifest is not None:
        if body.unresolved(root, manifest) or wrapper_unresolved(root):
            result.update(phase="unknown", reason="current workcell has an unresolved operation")
        elif record["phase"] == "staged":
            checked = body.artifact_check(root, manifest["result_sha256"])
            result["current_software_artifact_check"] = checked
            if not checked["ok"]:
                result.update(phase="unknown", reason="current staged software artifact is missing or changed")
    return result


def apply(root, proposal_file, proposal_sha256):
    if not isinstance(proposal_sha256, str) or not body.DIGEST.fullmatch(proposal_sha256):
        raise Refusal("proposal SHA256 must be exact lowercase hexadecimal")
    content = body.read_bytes(Path(proposal_file))
    if body.sha(content) != proposal_sha256:
        raise Refusal("proposal bytes do not match their bound digest")
    proposal = schema(body.decoded(content), root)
    loaded = body.load(root)
    manifest, order, _, _ = loaded
    binding(root, manifest)
    path = proposal_path(root, proposal["token"])
    if path.exists() or path.is_symlink():
        retained = load_proposal_record(path)
        if retained["proposal"] != proposal or retained["proposal_sha256"] != proposal_sha256:
            raise Refusal("image token belongs to different proposal bytes or arguments")
        return public_receipt(retained, root, manifest)
    if wrapper_unresolved(root) or body.unresolved(root, manifest) or manifest["phase"] == "completed":
        raise Refusal("unresolved or staged workcell cannot accept another image proposal")
    if proposal["generation"] != manifest["generation"]:
        raise Refusal("image proposal generation is stale")
    image_path, receipt_path = image_paths(root, proposal["generation"])
    receipt = checked_view(root, loaded, body.decoded(body.read_bytes(receipt_path)))
    if receipt["image_sha256"] != proposal["image_sha256"]:
        raise Refusal("proposal names a different image")
    located = locate(decode_png(body.read_bytes(image_path)))
    block_box = located["block"]["box"]
    if any(abs(actual - proposed) > SETTINGS["box_tolerance_px"] for actual, proposed in zip(block_box, proposal["block_box"], strict=True)):
        raise Refusal("proposed block box does not match independent RGB silhouette evidence")
    center = image_world_center(block_box)
    pusher = image_world_center(located["pusher"]["box"])
    visual_check = {"method": "color_specific_RGB", "block_box": block_box, "image_center_world_xy": center}
    if proposal["decision"] == "move":
        x, y = proposal["target"]["x"], proposal["target"]["y"]
        forward = x - pusher[0]
        if not SETTINGS["min_forward_m"] <= forward <= SETTINGS["max_forward_m"] or abs(pusher[1]) > SETTINGS["pusher_y_limit_m"]:
            raise Refusal("move must be a bounded forward increment from the RGB pusher estimate")
    else:
        zone, margin = order["target_zone"], SETTINGS["completion_margin_m"]
        if not (zone["x_min"] + margin <= center[0] <= zone["x_max"] - margin and
                zone["y_min"] + margin <= center[1] <= zone["y_max"] - margin):
            raise Refusal("fresh RGB block center is outside the conservative inspection zone")
        visual_check["inside_with_margin"] = True
    record = {"source_kind": SOURCE_KIND, "phase": "pending", "proposal": proposal,
              "proposal_sha256": proposal_sha256, "binding": binding(root, manifest), "visual_check": visual_check}
    body.utils.persist(path, record)
    try:
        body.create_file(root / f"vision-request-{body.sha(proposal['token'].encode())}.json", content)
        base_token = "vision-" + body.sha(proposal["token"].encode())
        if proposal["decision"] == "move":
            base = body.act(root, base_token, proposal["generation"], x, y)
            record["command"] = dict(proposal["target"])
            record["contact_statistics"] = base["operation"].get("controller_evidence", {})
        else:
            base = body.complete(root, base_token)
            record["artifact_check"] = base["operation"].get("artifact_check", {})
        base_phase = base["operation"]["phase"]
        record["phase"] = base_phase if base_phase in {"executed", "staged"} else "unknown"
        record["after_generation"] = base["observation"]["generation"]
        record["after_state_sha256"] = base["observation"]["state_sha256"]
        body.utils.persist(path, record)
    except (Exception, KeyboardInterrupt):  # noqa: BLE001 - never repeat an unreceipted image decision
        record["phase"] = "unknown"
        with contextlib.suppress(OSError):
            body.utils.persist(path, record)
    return public_receipt(record, root, body.load(root)[0])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("view", "apply"):
        child = sub.add_parser(command)
        child.add_argument("--run-dir", required=True)
        if command == "apply":
            child.add_argument("--proposal-file", required=True)
            child.add_argument("--proposal-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        root = body.directory(args.run_dir)
        with body.utils.locked(root):
            result = view(root) if args.command == "view" else apply(root, args.proposal_file, args.proposal_sha256)
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return 2 if result["phase"] in {"pending", "unknown"} else 0
    except (Refusal, OSError, KeyError, TypeError, ValueError, AttributeError, KeyboardInterrupt) as exc:
        reason = str(exc) if isinstance(exc, Refusal) else "image evidence or proposal is malformed or unavailable"
        print(json.dumps({"source_kind": SOURCE_KIND, "phase": "refused", "reason": reason}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
