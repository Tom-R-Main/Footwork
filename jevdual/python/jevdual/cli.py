"""``footwork``: point the dual-process loop at a running app and a task (P0, the operator surface).

    footwork run "Report the Team ID shown for com.execufunction.app" --app "Google Chrome" \\
        --url https://developer.apple.com/account/resources/identifiers/list \\
        --require "Reported the Team ID or that sign-in is needed; changed nothing"
    footwork run "Compute 6 times 7" --app Calculator --require "The display shows 42"
    footwork menu --app "Google Chrome"          # what System 1 would see, and how long it took
    footwork apps                                 # running apps the Driver can bind to

Defaults are the guarded configuration the experiments adopted: Jev as System 1 with the arbiter's
floors, Muse as System 2 on escalation, the verifier on every done, the one authorization boundary
on every route, a trace and a screenshot per step under ``--out``. Nothing is typed from chat: text
comes from the task sentence or ``--secret NAME=VALUE`` placeholders. ``--authorize`` names the
labels the boundary stands down for (the one change the operator approved), and a paused run prints
the exact flag that would let it continue.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any


def _split(s: str, sep: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in s.split(sep) if x.strip())


def _out_dir(arg: str | None) -> Path:
    return Path(arg) if arg else Path("runs") / time.strftime("%Y%m%d-%H%M%S")


async def cmd_apps(_: argparse.Namespace) -> int:
    from cua_driver import CuaDriver, ListAppsInput

    driver = CuaDriver.create()
    try:
        apps = await driver.list_apps(ListAppsInput())
        for a in sorted(apps.apps, key=lambda a: a.name.casefold()):
            print(f"{a.pid:>7}  {a.name}")
    finally:
        await driver.shutdown()
    return 0


async def cmd_menu(args: argparse.Namespace) -> int:
    from cua_driver import CuaDriver

    from jevdual.native import NativeBridge, find_window

    t0 = time.perf_counter()
    driver = CuaDriver.create()
    try:
        pid, wid, title = await find_window(driver, args.app, title_contains=args.window or "")
        nm = await NativeBridge(driver, pid, wid).observe(include_menu_bar=args.menu_bar)
    finally:
        await driver.shutdown()
    m = nm.menu
    print(f"{args.app}: window {wid} {title!r} in {time.perf_counter() - t0:.1f}s")
    print(f"{len(m.candidates)} candidates, omitted {m.omitted}, page text {len(m.page_text)} chars")
    for c in m.candidates:
        extra = f" value={c.value!r}" if c.value else ""
        sect = f" [{c.section}]" if c.section else ""
        print(f"  [{c.id:>4}] {c.role:<10} {c.label!r}{extra}{sect}")
    print("page text:", m.page_text[:600].replace("\n", " / "))
    return 0


def _step_line(o: Any) -> str:
    d = o.decision
    head = f"{d.operation} p={d.operation_confidence:.2f}" if d else "-"
    tgt = ""
    if d and d.target is not None and o.menu is not None:
        c = o.menu.menu.candidate(d.target)
        tgt = f" [{d.target}] {c.label if c else '?'!r}"
    what = o.verdict.reason[:70] if o.verdict else ""
    eff = f" -> {o.effect.effect}" if o.effect else ""
    times = f"menu {o.menu_ms / 1000:.1f}s jev {o.jev_ms / 1000:.1f}s"
    if o.llm_ms:
        times += f" s2 {o.llm_ms / 1000:.1f}s"
    return f"step {o.step:>2} {o.system}: {head}{tgt}{eff} | {what} | {times}"


async def cmd_run(args: argparse.Namespace) -> int:
    from cua_driver import CuaDriver
    from typesafe_sdk import AsyncTypeSafeClient

    from jevdual.arbiter import Arbiter, ArbiterPolicy
    from jevdual.authorize import Authorizer
    from jevdual.desktop import NativeAgent
    from jevdual.desktop_s2 import NativeS2, meta_chat_from_env
    from jevdual.keys import load_keys
    from jevdual.native import NativeBridge, find_window
    from jevdual.policy import JevPolicy
    from jevdual.trace import TraceWriter
    from jevdual.verify import ArbiterHook, Verifier

    keys = load_keys()
    if not keys.get("TYPESAFE_API_KEY"):
        print("TYPESAFE_API_KEY missing (0400 file under ~/.config/jevdual)", file=sys.stderr)
        return 2
    out = _out_dir(args.out)
    out.mkdir(parents=True, exist_ok=True)
    requirements = _split(args.require or "", ";")
    authorized = _split(args.authorize or "", ",")
    t_start = time.perf_counter()
    marks: list[tuple[str, float]] = []

    def mark(what: str) -> None:
        marks.append((what, time.perf_counter() - t_start))

    driver = CuaDriver.create()
    mark("driver up")
    try:
        pid, wid, title = await find_window(driver, args.app, title_contains=args.window or "")
        from jevdual.posture import ExecutionPolicy

        bridge = NativeBridge(driver, pid, wid, policy=ExecutionPolicy(args.mode), live_check=True)
        mark(f"bound to {args.app} window {wid} {title[:40]!r} ({args.mode})")
        if args.url:
            from urllib.parse import urlsplit

            from jevdual.native import address_bar, navigate_in_window

            try:
                first = await navigate_in_window(bridge, args.url)
            except LookupError as exc:
                print(f"--url: {exc}", file=sys.stderr)
                return 2
            host = urlsplit(args.url).netloc
            bar = address_bar(first)
            shown = (bar.value or "") if bar else ""
            if host and host not in shown and host not in first.menu.page_text:
                print(
                    f"after opening {args.url} the window's address bar reads {shown[:80]!r}. "
                    "Not running against a page that did not open.",
                    file=sys.stderr,
                )
                return 2
            mark(f"opened {args.url} in a new tab of window {wid} (address bar {shown[:50]!r})")
        trace = TraceWriter(out / "trace.jsonl")
        async with AsyncTypeSafeClient() as client:
            policy = JevPolicy(client)
            verifier = Verifier(client)
            hook = ArbiterHook(verifier, requirements, use_trajectory=True)
            s2 = None
            if not args.no_s2:
                chat = meta_chat_from_env()
                if chat is None:
                    print(
                        "MODEL_API_KEY missing: running System 1 only (escalations end the run)",
                        file=sys.stderr,
                    )
                else:
                    s2 = NativeS2(
                        chat,
                        policy=ArbiterPolicy.from_toml(),
                        verifier=verifier,
                        authorized_actions=authorized,
                    )
            agent = NativeAgent(
                bridge,
                policy,
                task=args.task,
                requirements=requirements,
                arbiter=Arbiter.from_toml(),
                verifier=hook,
                trace=trace,
                run_id=out.name,
                max_steps=args.steps,
                s2=s2,
                answer_expected=args.answer,
                secrets=_secrets(args.secret, args.app),
                authorizer=Authorizer(
                    policy=ArbiterPolicy.from_toml(),
                    authorized_actions=authorized,
                    judge=verifier.judge_destructive if s2 is not None else None,
                ),
            )
            agent.screenshot_dir = out / "screenshots"
            mark("agent ready")
            run = await agent.run()
            mark(f"run {run.status}")
        trace.close()
    finally:
        await driver.shutdown()

    for o in run.steps:
        print(_step_line(o))
    print()
    print(f"status: {run.status}: {run.reason[:200]}")
    if run.answer:
        tag = "answer" if run.answer_verified else "answer (unverified; " + run.answer_reason[:120] + ")"
        print(f"{tag}: {run.answer}")
    if run.status == "paused":
        label = _paused_label(run.reason)
        if label:
            print(f"to continue with that action authorized, rerun with: --authorize {label!r}")
    print(f"trace: {out / 'trace.jsonl'}; screenshots: {out / 'screenshots'}")
    print("timeline: " + "; ".join(f"{w} at {t:.1f}s" for w, t in marks))
    (out / "run.json").write_text(
        json.dumps(
            {
                "task": args.task,
                "app": args.app,
                "url": args.url,
                "requirements": requirements,
                "authorized": authorized,
                "status": run.status,
                "reason": run.reason,
                "answer": run.answer,
                "answer_verified": run.answer_verified,
                "steps": len(run.steps),
                "timeline": marks,
            },
            indent=1,
        )
    )
    return 0 if run.status == "done" else 1


def _paused_label(reason: str) -> str | None:
    import re

    m = re.search(r"on (?:click|type|append|enter|key|hotkey|menu) '([^']+)'", reason) or re.search(
        r"'([^']+)'", reason
    )
    return m.group(1) if m else None


def _secrets(pairs: list[str] | None, app: str) -> Any:
    if not pairs:
        return None
    from jevdual.secrets import SecretStore

    values = {}
    for p in pairs:
        if "=" not in p:
            raise SystemExit(f"--secret takes NAME=VALUE, not {p!r}")
        k, v = p.split("=", 1)
        values[k.strip()] = v
    return SecretStore({f"app://{app}": values})


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="footwork", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run a task in a running app")
    r.add_argument("task")
    r.add_argument("--app", required=True, help="the running app's name as the Driver lists it")
    r.add_argument("--url", help="open this URL in a new tab first (Chrome, Safari) and bind to that window")
    r.add_argument("--window", help="bind to the window whose title contains this")
    r.add_argument("--require", default="", help="semicolon-separated requirements the verifier checks")
    r.add_argument(
        "--authorize", default="", help="comma-separated labels the authorization boundary stands down for"
    )
    r.add_argument("--secret", action="append", help="NAME=VALUE the task refers to as {NAME}; never printed")
    r.add_argument("--steps", type=int, default=20)
    r.add_argument("--answer", action="store_true", help="the task asks for a reported value")
    r.add_argument("--no-s2", action="store_true", help="System 1 only")
    r.add_argument("--out", help="run directory (default runs/<timestamp>)")
    r.add_argument(
        "--mode",
        default="background_only",
        choices=("background_only", "foreground_permitted", "exclusive_desktop"),
        help="execution posture: background_only never takes the foreground (default); foreground_permitted "
        "takes it only after 3 s without your input; exclusive_desktop assumes nobody is using this desktop",
    )
    r.set_defaults(fn=cmd_run)
    m = sub.add_parser("menu", help="print the menu System 1 would see")
    m.add_argument("--app", required=True)
    m.add_argument("--window")
    m.add_argument("--menu-bar", action="store_true")
    m.set_defaults(fn=cmd_menu)
    a = sub.add_parser("apps", help="list running apps")
    a.set_defaults(fn=cmd_apps)

    from jevdual import session as S

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--session", help="session directory (default $FOOTWORK_SESSION or runs/session)")
        sp.add_argument("--text", type=int, default=3000, help="page text characters to print")

    st = sub.add_parser("start", help="bind a window and start a session you drive as System 2")
    st.add_argument("task")
    st.add_argument("--app", default="Google Chrome", help="the running app (native route)")
    st.add_argument(
        "--browser", action="store_true", help="footwork's own Chrome through the Driver's DevTools route"
    )
    st.add_argument("--url")
    st.add_argument("--window")
    st.add_argument("--require", default="")
    st.add_argument("--authorize", default="")
    st.add_argument("--answer", action="store_true")
    st.add_argument(
        "--mode",
        default="background_only",
        choices=("background_only", "foreground_permitted", "exclusive_desktop"),
        help="execution posture: background_only never takes the foreground (default); foreground_permitted "
        "takes it only after 3 s without your input; exclusive_desktop assumes nobody is using this desktop",
    )
    common(st)
    st.set_defaults(fn=S.cmd_start)
    lk = sub.add_parser("look", help="observe; prints the receipt for the last action")
    common(lk)
    lk.set_defaults(fn=S.cmd_look)
    do = sub.add_parser("do", help="dispatch one action through the boundary and get its receipt")
    do.add_argument("words", nargs="+")
    do.add_argument(
        "--authorize", default="", help="stand the boundary down for these labels, this action only"
    )
    do.add_argument("--settle", type=float, default=S.SETTLE_S)
    do.add_argument("--no-judge", action="store_true", help="skip the Jev destructive judgment on clicks")
    do.add_argument(
        "--route",
        choices=("trusted", "dom"),
        help="browser mode: the click route (default trusted; dom for radio, checkbox, switch)",
    )
    common(do)
    do.set_defaults(fn=S.cmd_do)
    s1 = sub.add_parser("s1", help="System 1's proposal on the current observation")
    s1.add_argument("--act", action="store_true", help="dispatch it through `do`")
    s1.add_argument("--authorize", default="")
    s1.add_argument("--settle", type=float, default=S.SETTLE_S)
    common(s1)
    s1.set_defaults(fn=S.cmd_s1)
    dn = sub.add_parser("done", help="ask the verifier to accept the task as done")
    dn.add_argument("answer", nargs="?", default="")
    common(dn)
    dn.set_defaults(fn=S.cmd_done)
    stt = sub.add_parser("status")
    common(stt)
    stt.set_defaults(fn=S.cmd_status)
    return ap


def main(argv: list[str] | None = None) -> int:
    import logging

    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    return asyncio.run(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
