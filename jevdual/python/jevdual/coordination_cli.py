"""Inspect ownership and explicitly hand off a desktop reservation."""
from __future__ import annotations

import json
from urllib.parse import quote


def add_parser(sub):
    parser = sub.add_parser("control", help="inspect owners/waiters; reserve, yield or cancel exact ownership tokens")
    parser.add_argument("action", choices=("status", "reserve", "yield", "cancel", "observe", "recover"))
    parser.add_argument("token", nargs="?", help="exact token from control status; required for yield/cancel")
    parser.add_argument("--session", help="required session directory for reserve/observe")
    parser.add_argument("--input-cleaned", action="store_true",
                        help="recover only: confirm the dead owner's held buttons/modifiers were checked and released")
    parser.set_defaults(fn=command)


async def command(args):
    from .coordination import CoordinationError, Coordinator, app_resource
    from .session import SessionState, session_dir

    registry = Coordinator()
    if args.action == "status":
        print(json.dumps(registry.status(), indent=2))
        return 0
    if args.action == "recover":
        if not args.token or not args.input_cleaned:
            raise CoordinationError("recovery requires an exact orphan token and --input-cleaned")
        registry.recover(args.token)
        print("orphaned transaction released; persistent take reservations are retained")
        return 0
    if args.action in {"yield", "cancel"}:
        if not args.token:
            raise CoordinationError("yield/cancel requires the exact ownership token")
        registry.revoke(args.token)
        print("revoked; active input retains ownership until readback and cleanup finish")
        return 0
    if not args.session:
        raise CoordinationError("reserve/observe requires --session DIR")
    directory = session_dir(args.session).resolve()
    owner = str(directory)
    async with registry.claim(owner, ["session/" + quote(owner, safe="")]):
        state = SessionState.load(directory)
        if state.path.resolve() != directory:
            raise CoordinationError("session directory binding changed; refusing a handoff outside the owned session")
        if args.action == "observe":
            print(json.dumps({"source": "saved_observation", "live": False,
                              "snapshot": state.last_snapshot, "title": state.last_title,
                              "text": state.last_page_text, "elements": state.last_candidates}))
            return 0
        resources = ["desktop", app_resource(state.app)]
        old = state.coordination_token
        # A revoked token can only be replaced by this explicit reserve operation.
        active = any(r["token"] == old and r["state"] == "active"
                     for r in registry.status()["reservations"])
        async with registry.claim(owner, resources, reservation=old if active else "") as claim:
            token = registry.reserve(claim, resources)
            state.coordination_token = token
            try:
                state.save()
            except BaseException:
                registry.revoke(token)
                raise
            if active:
                registry.revoke(old)
            print(json.dumps({"token": token, "resources": resources, "session": owner}))
    return 0
