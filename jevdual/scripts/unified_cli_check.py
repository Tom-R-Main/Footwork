"""Check the installed agent discovery boundary outside the source checkout."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--tools', action='store_true', help='Also execute installed simulator init/status')
    args = parser.parse_args()
    interpreter = os.path.abspath(args.python)
    evidence = []
    with tempfile.TemporaryDirectory(prefix='footwork-installed-cli-') as directory:
        for words in [('tools',), ('schema', 'browser', 'start'), ('schema', 'desktop', 'do'),
                      ('schema', 'capability', 'config')]:
            result = subprocess.run(
                [interpreter, '-I', '-m', 'jevdual.cli', '--json', *words],
                cwd=directory, capture_output=True, text=True, timeout=30, check=False,
            )
            if result.returncode:
                raise RuntimeError(f'Installed discovery failed: {words[0]}')
            value = json.loads(result.stdout)
            if value.get('exit_code') != 0 or value.get('effect_verification') != 'not_asserted':
                raise RuntimeError('Installed CLI envelope is missing conservative effect semantics')
            data = value.get('data')
            if not isinstance(data, dict):
                raise TypeError('Installed CLI did not return machine-readable discovery')
            if words == ('tools',) and not data.get('tools'):
                raise RuntimeError('Installed auxiliary catalog is empty')
            evidence.append({'command': list(words), 'passed': True})
        if args.tools:
            env = os.environ.copy()
            home = Path(directory).resolve() / 'tools'
            env['FOOTWORK_TOOL_OUTPUT_ROOT'] = str(home)
            bench = home / 'physical-workcell' / 'installed-smoke'
            for operation in ('init', 'status'):
                result = subprocess.run(
                    [interpreter, '-I', '-m', 'jevdual.cli', '--json', 'workcell', 'bench',
                     '--root', str(bench), operation], cwd=directory, env=env,
                    capture_output=True, text=True, timeout=60, check=False,
                )
                value = json.loads(result.stdout)
                if result.returncode or value.get('exit_code') != 0 or not value.get('data'):
                    raise RuntimeError('Installed workcell operation failed: ' + operation)
                evidence.append({'command': ['workcell', 'bench', operation], 'passed': True})
    print(json.dumps({'passed': True, 'checks': evidence}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
