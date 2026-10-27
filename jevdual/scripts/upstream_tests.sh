#!/usr/bin/env bash
# Run the upstream browser-use CI modules that pin behaviour jevdual inherits, with the patches active.
# Extra arguments are passed to pytest (e.g. -x, -k). Requires the browser-use submodule checkout.
set -euo pipefail
cd "$(dirname "$0")/.."
UP=../browser-use/tests/ci
MODULES=(
  "$UP/test_browser_session.py"
  "$UP/test_cloud_hints.py"
  "$UP/test_multi_act_guards.py"
  "$UP/test_action_loop_detection.py"
  "$UP/test_redact_cascade.py"
  "$UP/test_variable_substitution.py"
  "$UP/test_dom_paint_order_serialization.py"
  "$UP/test_dom_visibility.py"
  "$UP/test_llm_output_truncation.py"
  "$UP/test_llm_retries.py"
  "$UP/test_tools.py"
  "$UP/security/test_sensitive_data.py"
)
# upstream modules import ``tests.ci.conftest``; make the submodule root importable first
export PYTHONPATH="$(cd ../browser-use && pwd)${PYTHONPATH:+:$PYTHONPATH}"
# Match upstream's loop ownership: its browser fixtures and event buses span tests.
# -c /dev/null intentionally skips upstream project setup, so keep these explicit.
exec uv run pytest -p jevdual.upstream_pytest -c /dev/null --rootdir=../browser-use --confcutdir="$UP" \
  -o asyncio_mode=auto -o asyncio_default_fixture_loop_scope=session \
  -o asyncio_default_test_loop_scope=session -p no:cacheprovider -q --timeout=240 "${MODULES[@]}" "$@"
