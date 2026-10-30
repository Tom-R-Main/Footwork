#!/bin/bash
# Run only in an isolated qualification environment. The supervisor owns D-Bus.
set -euo pipefail
exec "${FOOTWORK_DESKTOP_PYTHON:-python3}" -I -m jevdual.linux_session "$@"
