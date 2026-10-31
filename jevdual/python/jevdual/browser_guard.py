"""Configured browser judgment behind the existing keyword/destructive boundary.

An external adapter is trusted policy code, not a security sandbox. It supplies
probabilities; it cannot disable the code-owned keyword gate or change thresholds.
No adapter is bundled that approves actions. Missing judgment always refuses.
"""

from __future__ import annotations

import asyncio
import json
import os


class GuardRefused(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


async def _adapter(command: list[str], payload: dict) -> list[float]:
    if (not isinstance(command, list) or not command
            or any(not isinstance(x, str) or not x for x in command)
            or not os.path.isabs(command[0])):
        raise GuardRefused("guard_unavailable", "guard adapter needs an absolute executable path")
    process = await asyncio.create_subprocess_exec(
        *command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL, limit=65537,
    )
    try:
        process.stdin.write(json.dumps(payload, allow_nan=False).encode() + b"\n")
        await process.stdin.drain()
        process.stdin.close()
        try:
            raw = await process.stdout.readexactly(65537)
        except asyncio.IncompleteReadError as exc:
            raw = exc.partial
        if len(raw) > 65536:
            raise ValueError("oversize guard reply")
        if await process.wait() != 0:
            raise ValueError("guard failed")
        reply = json.loads(raw)
        if (not isinstance(reply, dict)
                or set(reply) != {"producer", "version", "digest", "probabilities"}
                or reply["producer"] != "footwork.browser.guard"
                or type(reply["version"]) is not int or reply["version"] != 1
                or reply["digest"] != payload["digest"]):
            raise ValueError("unbound guard reply")
        return reply["probabilities"]
    finally:
        if process.returncode is None:
            process.kill()
        await process.wait()


async def authorize(config: dict, binding: dict, snapshot: dict, ref: str, request_digest: str) -> dict:
    from jevdual.arbiter import ArbiterPolicy
    from jevdual.authorize import Authorizer, NativeAction
    from jevdual.menu import Menu
    from jevdual.native import NativeMenu

    row = next((row for row in snapshot.get("refs", []) if row.get("ref") == ref), None)
    if row is None:
        raise GuardRefused("stale_ref", "the guard has no matching observed target")
    page = snapshot.get("page") or {}
    page_text = " ".join(str(item.get("name", "")) for item in snapshot.get("content_refs", []))[:300]
    menu = Menu(str(page.get("url", "")), str(page.get("title", "")), page_text, (), {})
    nm = NativeMenu(menu, {}, "cdp", binding["pid"], 0, "Chrome", True, False, False)
    command = config.get("guard_command")

    async def judge(task, targets, *, url, title):
        if command is not None:
            return await _adapter(command, {
                "producer": "footwork.browser.guard.request", "version": 1,
                "digest": request_digest, "task": task, "targets": targets, "url": url, "title": title,
                "binding": binding,
            })
        # Explicit environment configuration only; do not load unrelated key files.
        if not os.environ.get("TYPESAFE_API_KEY"):
            raise GuardRefused("guard_unavailable", "configure Jev or an explicit judgment adapter")
        from typesafe_sdk import AsyncTypeSafeClient

        from jevdual.verify import Verifier

        async with AsyncTypeSafeClient() as client:
            return await Verifier(client).judge_destructive(task, targets, url=url, title=title)

    authorizer = Authorizer(policy=ArbiterPolicy.from_toml(), judge=judge)
    action = NativeAction("click", str(row.get("name", "")), "s2",
                          context=f"{menu.title} {menu.page_text}")
    try:
        reason = await asyncio.wait_for(authorizer.check(nm, action, task=config["task"]), timeout=15)
    except Exception as exc:
        raise GuardRefused("guard_unavailable", "configured judgment failed; nothing dispatched") from exc
    if reason:
        raise GuardRefused("guard_refused", "configured guard paused this activation; nothing dispatched")
    # Authorizer records every successful judge result. A keyword-only path is not authorization.
    if not authorizer.judgments or "error" in authorizer.judgments[-1]:
        raise GuardRefused("guard_unavailable", "no qualified judgment; nothing dispatched")
    return {"producer": "footwork.browser.guard", "version": 1, "decision": "allow", "digest": request_digest}
