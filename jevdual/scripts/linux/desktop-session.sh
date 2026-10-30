#!/bin/bash
# Owned Linux fixture under dbus-run-session; use the installed Footwork Python.
set -euo pipefail
exec "${FOOTWORK_PYTHON:-python3}" "$(dirname "$0")/desktop_session.py" "$@"
