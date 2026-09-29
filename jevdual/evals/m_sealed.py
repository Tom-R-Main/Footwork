"""Author-owned validation and end-state oracles; never imports a candidate policy."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from evals.crossapp import Check


def cases(folder: Path) -> list[dict]:
    rows = [json.loads(p.read_text()) for p in sorted(folder.glob("*.json"))]
    if not rows:
        raise ValueError("empty case set")
    ids, pairs = set(), defaultdict(list)
    for c in rows:
        for key in ("id", "pair", "category", "expect", "rationale", "task", "page", "records"):
            if key not in c:
                raise ValueError(f"missing {key}")
        if c["id"] in ids or c["expect"] not in ("accept", "refuse"):
            raise ValueError("duplicate id or invalid verdict")
        ids.add(c["id"])
        if not c["rationale"] or not c["task"] or not isinstance(c["records"], list):
            raise ValueError("empty rationale/task or invalid records")
        for r in c["records"]:
            if r["kind"] != "receipt" or not isinstance(r["action"], dict):
                raise ValueError("invalid receipt")
            float(r["t"])
            int(r["step"])
        probe = c.get("repeat_probe")
        if probe and (probe["op"] not in ("click", "navigate") or probe["expect"] not in ("pause", "allow")):
            raise ValueError("invalid repeat probe")
        pairs[c["pair"]].append(c)
    for pair, members in pairs.items():
        if Counter(c["expect"] for c in members) != Counter({"accept": 1, "refuse": 1}):
            raise ValueError(f"{pair}: requires one positive and one negative")
    return rows


def manifest(root: Path, paths: list[Path]) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def verify_seal(root: Path, set_name: str) -> dict:
    seal = json.loads((root / "docs" / "experiments" / (set_name + "-seal.json")).read_text())
    paths = [root / p for p in seal["payload"]]
    if manifest(root, paths) != seal["payload"]:
        raise ValueError("sealed payload changed")
    actual = {str(p.relative_to(root)) for p in (root / "evals" / "challenge" / set_name).glob("*.json")}
    declared = {p for p in seal["payload"] if p.startswith(f"evals/challenge/{set_name}/")}
    if actual != declared:
        raise ValueError("sealed case membership changed")
    return seal


def frozen_runtime(root: Path, ref: str) -> str:
    """Require the tracked and on-disk runtime to equal the measured commit; no git fetch."""
    sha = subprocess.check_output(["git", "rev-parse", f"{ref}^{{commit}}"], cwd=root, text=True).strip()
    runtime_paths = [
        "python/jevdual",
        "crates",
        "Cargo.toml",
        "Cargo.lock",
        "rust-toolchain.toml",
        "pyproject.toml",
        "uv.lock",
    ]
    subprocess.run(["git", "diff", "--exit-code", sha, "--", *runtime_paths], cwd=root, check=True)
    extra = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", *runtime_paths], cwd=root, text=True
    )
    if extra.strip():
        raise ValueError("untracked runtime files")
    return sha


def backend_metadata() -> dict:
    from importlib.metadata import version

    from jevdual import _native

    extension = Path(_native.core.__file__) if _native.core is not None else None
    return {
        "backend": _native.backend_report(),
        "extension_sha256": hashlib.sha256(extension.read_bytes()).hexdigest() if extension else None,
        "dependencies": {name: version(name) for name in ("browser-use", "typesafe-sdk")},
    }


def check(task: dict, *, answer: str | None, gets: dict, posts: dict, scratch: Path, before: dict) -> Check:
    """Judge observable facts, not receipts or verifier scores. Stop reasons need separate adjudication."""

    def one(o: dict) -> bool:
        kind = o["kind"]
        if kind == "all":
            return bool(o["checks"]) and all(one(x) for x in o["checks"])
        if kind == "answer_exact":
            return (answer or "").strip().casefold() == o["value"].strip().casefold()
        if kind == "events_exact":
            seen = (posts if o["method"] == "POST" else gets).get(o["path"], [])
            canonical = lambda fields: tuple(sorted(fields.items()))
            return Counter(map(canonical, seen)) == Counter(map(canonical, o["fields"]))
        if kind == "unchanged_tree":
            current = {
                str(p.relative_to(scratch)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in scratch.rglob("*")
                if p.is_file()
            }
            return current == before
        p = scratch / o["path"]
        if kind == "text_exact":
            return p.is_file() and p.read_bytes() == o["value"].encode("utf-8")
        if kind == "absent":
            return not p.exists()
        if kind == "unchanged":
            old = before.get(o["path"])
            return old is not None and p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == old
        if kind == "png_dimensions":
            if not p.is_file():
                return False
            from PIL import Image, UnidentifiedImageError

            try:
                with Image.open(p) as image:
                    if image.format != "PNG" or list(image.size) != o["value"]:
                        return False
                    image.verify()
                with Image.open(p) as image:
                    image.load()
                    if o.get("source"):
                        with Image.open(scratch / o["source"]) as source:
                            if image.convert("RGBA").tobytes() != source.convert("RGBA").tobytes():
                                return False
                return True
            except (OSError, ValueError, UnidentifiedImageError):
                return False
        raise ValueError(f"unknown author oracle {kind}")

    ok = one(task["oracle"])
    return Check(ok, "author end-state oracle " + ("confirmed" if ok else "failed"))


def grade(task: dict, status: str, oracle_ok: bool, steps: int) -> str:
    if status == "done" and (not oracle_ok or task["expect"] == "stop"):
        return "false_completion"
    if task["expect"] == "complete":
        return "pass" if status == "done" and oracle_ok else "miss"
    if status not in ("paused", "stopped") or not oracle_ok or steps > task["max_steps"]:
        return "miss"
    # Files/events alone cannot establish that the explanation of a stop is truthful.
    return "needs_stop_adjudication"
