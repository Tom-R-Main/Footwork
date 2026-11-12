import subprocess
import sys
import types
from pathlib import Path
import pytest

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'python'))
for name in ('drag', 'filmed', 'session'):
    module_name = 'jevdual.' + name
    file = root / 'python' / 'jevdual' / (name + '.py')
    source = subprocess.check_output(['git', 'show', 'b6a291b:' + str(file.relative_to(root.parent))], cwd=root).decode()
    module = types.ModuleType(module_name)
    module.__file__ = str(file)
    sys.modules[module_name] = module
    exec(compile(source, str(file), 'exec'), module.__dict__)
    import jevdual
    setattr(jevdual, name, module)
raise SystemExit(pytest.main(['-q', *(sys.argv[1:] or ['tests/test_drag.py', 'tests/test_drag_session.py', 'tests/test_filmed_session.py', 'tests/test_pointer_scale.py'])]))
