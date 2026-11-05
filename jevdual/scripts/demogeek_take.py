"""Run DemoGeek iteration 6's TAKE.md journey through Footwork's filmed pointer mode.

    python scripts/demogeek_take.py OUT_DIR [--url http://localhost:8766/index.html] [--record]

Moves the real pointer and types. Run only inside the takeover protocol with nobody at the machine.
Setup (off camera): a fresh Chrome app window in its own profile with a 1440x900 CSS px content area, a
filmed session with TAKE.md's keep-out and rest position, and the pointer parked at rest. Rolling: steps
1-10 of TAKE.md. Every command's output and timing goes to OUT_DIR/take.jsonl; the run stops at the first
failed step, because a take is never retried mid-way.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

KEEP_OUT = "420,145,980,558"
REST = "360,460"
BRIEF = "Show how a failed webhook gets replayed in relay.dev"
REVISION = "Hold the replay scene a bit longer"
WINDOW = {"x": 36, "y": 40, "w": 1440, "h": 932}


SCENE = "Footwork DemoGeek take"
INPUT = "Footwork take window"


class TakeFailed(Exception):
    pass


class Obs:
    """OBS through scripts/obs_ws.py: a dedicated take scene with one window capture, recorded, then the
    previous program scene restored. Nothing else in the user's OBS setup is changed."""

    def __init__(self, take: Take) -> None:
        sys.path.insert(0, str(Path(__file__).parent))
        import obs_ws

        self.call = lambda *reqs: asyncio.run(obs_ws.call(list(reqs)))
        self.take = take
        self.previous: str | None = None
        self.input = INPUT

    def one(self, request: str, data: dict | None = None) -> dict:
        r = self.call((request, data or {}))[0]
        if not r["ok"]:
            raise TakeFailed(f"OBS {request} failed: {r['status']}")
        return r["data"] or {}

    def setup(self, window_id: int) -> dict:
        scenes = self.one("GetSceneList")
        self.previous = scenes["currentProgramSceneName"]
        if SCENE not in [x["sceneName"] for x in scenes["scenes"]]:
            self.one("CreateScene", {"sceneName": SCENE})
        settings = {
            "type": 1,
            "application": "com.google.Chrome",
            "window": window_id,
            "show_cursor": True,
            "hide_obs": True,
        }
        # Each take gets its own input. A screen_capture whose window closed keeps a dead stream:
        # retargeting it recorded black (FT3), and OBS acknowledges RemoveInput but keeps it listed.
        for old in self.one("GetSceneItemList", {"sceneName": SCENE})["sceneItems"]:
            self.one("RemoveSceneItem", {"sceneName": SCENE, "sceneItemId": old["sceneItemId"]})
        for i in self.one("GetInputList")["inputs"]:
            if i["inputName"].startswith(INPUT):
                self.call(("RemoveInput", {"inputName": i["inputName"]}))  # best effort
        self.input = f"{INPUT} {time.strftime('%H%M%S')}"
        self.one(
            "CreateInput",
            {
                "sceneName": SCENE,
                "inputName": self.input,
                "inputKind": "screen_capture",
                "inputSettings": settings,
            },
        )
        item = self.one("GetSceneItemId", {"sceneName": SCENE, "sourceName": self.input})["sceneItemId"]
        video = self.one("GetVideoSettings")
        self.one(
            "SetSceneItemTransform",
            {
                "sceneName": SCENE,
                "sceneItemId": item,
                "sceneItemTransform": {
                    "boundsType": "OBS_BOUNDS_SCALE_INNER",
                    "boundsWidth": video["baseWidth"],
                    "boundsHeight": video["baseHeight"],
                    "boundsAlignment": 0,
                    "alignment": 5,
                    "positionX": 0,
                    "positionY": 0,
                },
            },
        )
        readback = {
            "input": self.one("GetInputSettings", {"inputName": self.input}),
            "transform": self.one("GetSceneItemTransform", {"sceneName": SCENE, "sceneItemId": item}),
            "video": video,
            "record_directory": self.one("GetRecordDirectory"),
            "output": {
                name: self.one("GetProfileParameter", {"parameterCategory": cat, "parameterName": name})
                for cat, name in (
                    ("Output", "Mode"),
                    ("SimpleOutput", "RecFormat2"),
                    ("SimpleOutput", "RecEncoder"),
                    ("SimpleOutput", "RecQuality"),
                )
            },
        }
        got = readback["input"]["inputSettings"]
        if got.get("show_cursor") is not True or got.get("window") != window_id or got.get("type") != 1:
            raise TakeFailed(f"OBS capture readback differs: {got}")
        readback["frame"] = self.frame_check()
        (self.take.out / "obs-settings.json").write_text(json.dumps(readback, indent=1))
        self.take.record(step="setup", cmd="obs setup", code=0, readback=readback)
        return readback

    def frame_check(self, timeout: float = 5.0) -> dict:
        """The capture shows something: a source screenshot whose pixels are not one flat colour."""
        import base64
        import io

        from PIL import Image, ImageStat

        deadline, tries = time.monotonic() + timeout, 0
        while True:
            tries += 1
            r = self.call(
                ("GetSourceScreenshot", {"sourceName": self.input, "imageFormat": "png", "imageWidth": 160})
            )[0]
            if r["ok"]:
                data = r["data"]["imageData"].split(",", 1)[1]
                img = Image.open(io.BytesIO(base64.b64decode(data))).convert("L")
                stat = ImageStat.Stat(img)
                lo, hi = img.getextrema()
                result = {"tries": tries, "mean": round(stat.mean[0], 1), "range": [lo, hi], "size": img.size}
                if hi - lo >= 24:
                    return result
            else:
                result = {"tries": tries, "status": r["status"]}
            if time.monotonic() > deadline:
                raise TakeFailed(f"OBS capture shows no picture: {result}")
            time.sleep(0.25)

    def start(self) -> None:
        self.one("SetCurrentProgramScene", {"sceneName": SCENE})
        self.one("StartRecord")
        deadline = time.monotonic() + 10
        while not self.one("GetRecordStatus")["outputActive"]:
            if time.monotonic() > deadline:
                raise TakeFailed("OBS did not start recording")
            time.sleep(0.2)
        self.take.record(step="setup", cmd="obs recording", code=0)

    def stop(self) -> str | None:
        path = None
        if self.one("GetRecordStatus")["outputActive"]:
            path = self.one("StopRecord").get("outputPath")
        if self.previous:
            self.one("SetCurrentProgramScene", {"sceneName": self.previous})
        self.take.record(step="end", cmd="obs stopped", code=0, path=path)
        return path


class Take:
    def __init__(self, out: Path) -> None:
        self.out = out
        self.session = out / "session"
        self.log = (out / "take.jsonl").open("a")
        self.t0 = time.monotonic()

    def record(self, **kw) -> None:
        kw["t"] = round(time.monotonic() - self.t0, 3)
        self.log.write(json.dumps(kw) + "\n")
        self.log.flush()
        print(
            f"[{kw['t']:7.2f}] {kw.get('step', '')} {kw.get('cmd', '')} -> {kw.get('code', '')}", flush=True
        )

    def fw(self, step: str, *argv: str, ok: tuple[int, ...] = (0,)) -> str:
        cmd = ["footwork", *argv, "--session", str(self.session)]
        if argv[0] == "do":
            cmd += ["--no-judge", "--settle", "0.3"]
        started = time.monotonic()
        p = subprocess.run(["uv", "run", *cmd], capture_output=True, text=True, check=False)
        self.record(
            step=step,
            cmd=" ".join(argv),
            code=p.returncode,
            s=round(time.monotonic() - started, 2),
            out=p.stdout[-1500:],
            err=p.stderr[-600:],
        )
        if p.returncode not in ok or re.search(
            r"\b(refused|paused before dispatch|not sent)\b", p.stdout + p.stderr
        ):
            raise TakeFailed(
                f"{step}: {' '.join(argv)} exited {p.returncode}: {(p.stderr or p.stdout)[-400:]}"
            )
        return p.stdout

    def wait_for(self, step: str, label: str, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            p = subprocess.run(
                ["uv", "run", "footwork", "look", "--session", str(self.session)],
                capture_output=True,
                text=True,
                check=False,
            )
            if label in p.stdout:
                self.record(step=step, cmd=f"wait {label!r}", code=0)
                return
            time.sleep(0.4)
        raise TakeFailed(f"{step}: {label!r} did not appear within {timeout} s")


def chrome(out: Path, url: str) -> int:
    profile = out / "chrome-profile"
    subprocess.run(
        [
            "open",
            "-na",
            "Google Chrome",
            "--args",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--force-renderer-accessibility",
            f"--window-position={WINDOW['x']},{WINDOW['y']}",
            f"--window-size={WINDOW['w']},{WINDOW['h']}",
            f"--app={url}",
        ],
        check=True,
    )
    time.sleep(4)
    pids = subprocess.run(
        ["pgrep", "-f", f"user-data-dir={profile}"], capture_output=True, text=True, check=False
    ).stdout.split()
    if not pids:
        raise TakeFailed("setup: Chrome did not start")
    return min(int(p) for p in pids)


def overlays(pid: int) -> list[str]:
    """Windows above layer 0 that overlap the scene window below the menu bar (plan: overlay_present)."""
    import Quartz

    x, y, w, h = WINDOW["x"], WINDOW["y"], WINDOW["w"], WINDOW["h"]
    hits = []
    for win in Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, 0):
        b = win.get("kCGWindowBounds") or {}
        if win.get("kCGWindowLayer", 0) <= 0 or win.get("kCGWindowOwnerPID") == pid:
            continue
        bx, by, bw, bh = b.get("X", 0), b.get("Y", 0), b.get("Width", 0), b.get("Height", 0)
        if by + bh <= 33 or win.get("kCGWindowAlpha", 1) == 0:  # the menu-bar strip
            continue
        if bx < x + w and bx + bw > x and by < y + h and by + bh > y:
            hits.append(
                f"{win.get('kCGWindowOwnerName')} layer {win.get('kCGWindowLayer')} at {bx},{by} {bw}x{bh}"
            )
    return hits


def wait_idle(take: Take, quiet_s: float = 3.0, timeout: float = 20.0) -> None:
    """Refuse to roll while a person is using the mouse or keyboard: need quiet_s with no input."""
    import Quartz

    state = Quartz.kCGEventSourceStateCombinedSessionState
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        idle = Quartz.CGEventSourceSecondsSinceLastEventType(state, Quartz.kCGAnyInputEventType)
        if idle >= quiet_s:
            take.record(step="setup", cmd="idle", code=0, idle_s=round(idle, 1))
            return
        time.sleep(0.25)
    raise TakeFailed(
        f"setup: input_active: the mouse or keyboard was used in the last {quiet_s} s for {timeout} s"
    )


def run(take: Take, url: str, obs: Obs | None, *, allow_overlay: bool = False) -> None:
    pid = chrome(take.out, url)
    if found := overlays(pid):
        take.record(step="setup", cmd="overlay_present", code=0 if allow_overlay else 1, overlays=found)
        if not allow_overlay:
            raise TakeFailed(f"setup: overlay_present: {found}; hide them and start again")
    out = take.fw(
        "setup",
        "start",
        "Make a Relay demo in DemoGeek",
        "--app",
        "Google Chrome",
        "--pid",
        str(pid),
        "--window",
        "DemoGeek",
        "--mode",
        "exclusive_desktop",
        "--pointer-motion",
        "filmed",
        "--rest",
        REST,
        "--authorize",
        "Send",
    )
    if "content 1440x900" not in out:
        raise TakeFailed(f"setup: the content area is not 1440x900 CSS px: {out[:300]}")
    take.wait_for("setup", "'Message'", 10)  # Chrome builds web accessibility lazily
    wait_idle(take)
    take.fw("setup", "park", "--place")
    if obs is not None:
        window_id = int(re.search(r"bound Google Chrome window (\d+)", out).group(1))
        obs.setup(window_id)
        obs.start()
        time.sleep(1.0)  # a still lead-in before the first gesture
    take.record(step="rolling", cmd="filmed_phase rolling")
    # 1-2: brief
    # a web textarea offers type, not click: in a filmed take, type travels to the field first
    take.fw("1", "do", "type", "Message", BRIEF)
    take.fw("2", "do", "key", "Return")
    take.wait_for("2", "'45 sec'", 15)
    # 3: length
    take.fw("3", "do", "click", "45 sec")
    take.wait_for("3", "'Record it'", 15)
    # 4: hover each scene, hover to hover
    for n in range(1, 5):
        take.fw("4", "point", f"Scene {n}:")  # Chrome's groups are collapsed by the Driver; point finds them
        time.sleep(0.7)
    # 5-6: record, then park while the product draws its own cursor
    # "Record it" is in the chat column, outside the frame. The product draws its own cursor from Record
    # on, so the keep-out is armed right after the click (the pointer is on the button) and before the park
    take.fw("5", "do", "click", "Record it")
    take.fw("5", "keep-out", KEEP_OUT)
    take.fw("6", "park")
    take.wait_for("5", "'See proof'", 15)
    # 7: revision
    take.fw("7", "do", "type", "Message", REVISION)
    take.fw("7", "do", "key", "Return")
    take.wait_for("7", "is now 12s", 15)
    # 8-9: jump to the replay segment, then waypoint below the frame and open the proof
    take.fw("8", "do", "click", "Replay it, 12 seconds. Click to jump.")
    take.fw("9", "park", "400", "765")
    take.fw("9", "do", "click", "See proof")
    # 10: rest and hold
    take.fw("10", "park")
    time.sleep(2)
    take.record(step="end", cmd="take complete")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--url", default="http://localhost:8766/index.html")
    ap.add_argument("--record", action="store_true", help="record with OBS (needs OBS_WEBSOCKET_PASSWORD)")
    ap.add_argument(
        "--allow-overlay", action="store_true", help="diagnostic only: proceed over a layer>0 window"
    )
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    take = Take(out)
    obs = Obs(take) if args.record else None
    code = 0
    try:
        run(take, args.url, obs, allow_overlay=args.allow_overlay)
    except TakeFailed as exc:
        take.record(step="failed", cmd=str(exc)[:500])
        print(f"take failed: {exc}", file=sys.stderr)
        code = 1
    finally:
        if obs is not None:
            try:
                path = obs.stop()
                if path and Path(path).exists():
                    moved = out / Path(path).name
                    shutil.move(path, moved)
                    take.record(step="end", cmd="recording moved", code=0, path=str(moved))
                    print(f"recording: {moved}")
            except TakeFailed as exc:
                print(f"OBS cleanup: {exc}", file=sys.stderr)
                code = 1
        subprocess.run(["pkill", "-f", f"user-data-dir={out / 'chrome-profile'}"], check=False)
    return code


if __name__ == "__main__":
    sys.exit(main())
