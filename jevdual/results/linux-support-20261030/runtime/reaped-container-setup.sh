#!/bin/sh
# Executed setup; copies reuse the already installed final wheel and test dependencies.
docker run -d --name footwork-linux-reaped-20261030 --init --cpus=2 --memory=3g --pids-limit=512 --shm-size=512m --cap-drop=ALL --security-opt=no-new-privileges -v /Users/thomasmain/projects/footwork/.worktrees/linux-support/output/linux-support:/artifacts -v /Users/thomasmain/projects/footwork/.worktrees/linux-support:/source:ro footwork-linux-native-tools:20261030 -c 'exec sleep infinity'
docker cp footwork-linux-final-20261030:/workspace/footwork - | docker cp - footwork-linux-reaped-20261030:/workspace
docker cp footwork-linux-final-20261030:/workspace/source - | docker cp - footwork-linux-reaped-20261030:/workspace
docker exec footwork-linux-reaped-20261030 dbus-run-session -- bash /source/jevdual/scripts/linux/desktop-session.sh /workspace/linux-desktop-reaped
# Desktop command is held in a separate terminal session while this runs.
docker exec footwork-linux-reaped-20261030 /workspace/footwork/bin/python /source/jevdual/scripts/linux/qualify.py --state /workspace/linux-desktop-reaped --output /artifacts/final-runtime/qualified-reaped-ready --chrome /opt/google/chrome/chrome
docker exec -w /workspace/source/jevdual -e PYTHONPATH=python -e JEVDUAL_PURE_PY=1 -e ANONYMIZED_TELEMETRY=false -e BROWSER_USE_CLOUD_SYNC=false footwork-linux-reaped-20261030 /workspace/footwork/bin/python -m pytest -q tests/test_agent_loop.py
docker exec -w /workspace/source/jevdual -e PYTHONPATH=python -e JEVDUAL_PURE_PY=1 -e ANONYMIZED_TELEMETRY=false -e BROWSER_USE_CLOUD_SYNC=false footwork-linux-reaped-20261030 /workspace/footwork/bin/python -m pytest -q -m browser tests/test_chrome_profile.py tests/test_control_state_browser.py
