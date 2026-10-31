"""Load a path-pinned passive receipt collector, without PYTHONPATH or checkout conftest."""
import importlib.util
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('vm_receipt_observer', Path(__file__).with_name('receipt_plugin.py'))
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)
raise SystemExit(pytest.main(sys.argv[1:], plugins=[plugin]))
