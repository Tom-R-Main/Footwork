#!/bin/zsh
# One live qualification of the staged release of main at 474958e, through its own interpreter only.
# Three probes in order, each once; stops at the first that does not hold. Usage: qualify-474958e.sh <name>
set -u
SP=/private/tmp/claude-501/-Users-thomasmain-projects-footwork/11a6d1b7-010c-448c-8d59-ce79ec3c24b4/scratchpad
W=/Users/thomasmain/projects/footwork/.claude/worktrees/point-drag/jevdual
REL=/Users/thomasmain/.local/share/footwork/releases/474958e48c0db404ffbe3b302bacef0df101c3d5
PY=$REL/bin/python
R=$SP/$1
[ -e $R ] && { echo "run dir exists"; exit 9; }
cd $W || exit 9
[ "$(git rev-parse HEAD)" = "$(git rev-parse claude/release-474958e-20261114)" ] || { echo "wrong branch"; exit 9; }
[ -z "$(git status --short -- scripts results/release-474958e-20261114/release_probe.py)" ] || { echo "probe sources dirty"; exit 9; }
[ "$(readlink /Users/thomasmain/.local/share/footwork/current)" = "/Users/thomasmain/.local/share/footwork/releases/6d571a1ed7c7bf77576279a01053f77fc20ce469" ] || { echo "current moved"; exit 9; }
mkdir $R
echo "start $(date +%H:%M:%S) probes-from $(git rev-parse HEAD) release 474958e python $PY driver $($PY -I -c 'import importlib.metadata as m; print(m.version("cua-driver"))')" | tee $R/launch.txt
held() { $PY -I -c "import json,sys; sys.exit(0 if json.load(open('$1')).get('held') else 1)" 2>/dev/null; }

echo "--- 1 release_probe $(date +%H:%M:%S)" | tee -a $R/launch.txt
FW_PROBE_PRIVATE=$R/release $PY -I results/release-474958e-20261114/release_probe.py > $R/1-release.stdout 2> $R/1-release.stderr
E1=$?; echo "release_probe exit=$E1 $(date +%H:%M:%S)" | tee -a $R/launch.txt; tail -c 1200 $R/1-release.stdout
if [ $E1 -ne 0 ]; then echo "STOPPED after release_probe" | tee -a $R/launch.txt; else
echo "--- 2 filmed page $(date +%H:%M:%S)" | tee -a $R/launch.txt
FOOTWORK_CHROME_PROFILE=$R/profile FOOTWORK_CHROME_PORT=9466 $PY -I scripts/probe_filmed_page_pointer.py --out $R/filmed > $R/2-filmed.stdout 2> $R/2-filmed.stderr
E2=$?; echo "filmed exit=$E2 held=$(held $R/filmed/verdict.json && echo true || echo false) $(date +%H:%M:%S)" | tee -a $R/launch.txt
if ! held $R/filmed/verdict.json; then echo "STOPPED after filmed page" | tee -a $R/launch.txt; tail -c 800 $R/2-filmed.stdout; else
echo "--- 3 drag-points $(date +%H:%M:%S)" | tee -a $R/launch.txt
$PY -I scripts/probe_drag_points.py --out $R/drag --gate-limit 40 > $R/3-drag.stdout 2> $R/3-drag.stderr
E3=$?; echo "drag exit=$E3 held=$(held $R/drag/run.json && echo true || echo false) $(date +%H:%M:%S)" | tee -a $R/launch.txt
cat $R/3-drag.stdout
fi; fi
echo "end $(date +%H:%M:%S)" | tee -a $R/launch.txt
echo "--- my own readings, separate from the probes'"
for P in $(grep -ho '"chrome_pid": [0-9]*' $R/drag/run.json 2>/dev/null | grep -o '[0-9]*'); do kill -0 $P 2>/dev/null && echo "drag chrome $P ALIVE" || echo "drag chrome $P gone"; done
echo "Chrome on port 9466: $(pgrep -f 'remote-debugging-port=9466' | wc -l | tr -d ' ') processes"
echo "filmed-probe profile dir present: $([ -e $R/profile ] && echo yes || echo no)"
echo "footwork-drag-points profiles left: $(find ${TMPDIR:-/tmp} -maxdepth 1 -name 'footwork-drag-points-*' 2>/dev/null | wc -l | tr -d ' ')"
echo "TextEdit processes started by the probe still running: see 1-release.stdout cleanup; TextEdit now: $(pgrep -x TextEdit | wc -l | tr -d ' ')"
echo "probe/drag-points/holder processes: $(pgrep -f 'probe_drag_points|probe_filmed_page_pointer|release_probe|jevdual.cli' | wc -l | tr -d ' ')"
echo "takeover/osascript processes: $(pgrep -f 'takeover.sh|osascript' | wc -l | tr -d ' ')"
echo "current -> $(readlink /Users/thomasmain/.local/share/footwork/current)"
$PY -I - <<'PY'
import Quartz
from jevdual.coordination import Coordinator
s = Coordinator().status()
print("registry requests:", len(s["requests"]), "orphaned:", [r["token"] for r in s["requests"] if r["state"] == "orphaned"],
      "active reservations:", [(r["token"][:8], r["owner"][-30:]) for r in s["reservations"] if r["state"] == "active"])
print("left button down:", bool(Quartz.CGEventSourceButtonState(Quartz.kCGEventSourceStateCombinedSessionState, Quartz.kCGMouseButtonLeft)))
p = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None)); print("pointer at:", round(p.x, 1), round(p.y, 1))
PY
